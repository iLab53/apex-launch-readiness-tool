from __future__ import annotations

import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Path setup â€” add at top of apex_coordinator.py
ROOT_DIR    = Path(__file__).parent
ENGINE_DIR  = ROOT_DIR / 'strategist-engine'
COMM_EX_DIR = ROOT_DIR / 'comm-ex'
AGENTS_DIR  = ROOT_DIR / 'agents'
MEMORY_DIR  = ROOT_DIR / 'memory'
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(COMM_EX_DIR))
sys.path.insert(0, str(AGENTS_DIR))

# Dashboard output â€” Phase 6 must write to this exact path
DASHBOARD_PATH = COMM_EX_DIR / 'outputs' / 'comm_ex_dashboard_ready.json'
ASSET_REG_PATH = ROOT_DIR / "asset-registry" / "apex_assets.json"


def _phase(n: int, name: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  PHASE {n} Ã¢â‚¬â€ {name}")
    print(f"{'=' * 62}")


def _ok(text: str) -> None:
    print(f"  [OK]  {text}")


def _warn(text: str) -> None:
    print(f"  [!!]  {text}", file=sys.stderr)


def _info(text: str) -> None:
    print(f"  Ã‚Â·Ã‚Â·Ã‚Â·   {text}")


def load_assets() -> list[dict]:
    if not ASSET_REG_PATH.exists():
        _warn(f"Asset registry not found: {ASSET_REG_PATH}")
        return []
    with open(ASSET_REG_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return registry if isinstance(registry, list) else registry.get("assets", [])


def extract_briefing(engine_result: Optional[dict]) -> Optional[str]:
    if not engine_result:
        return None
    return engine_result.get("briefing") or engine_result.get("summary") or None


def load_latest_briefing() -> Optional[str]:
    reports_dir = ENGINE_DIR / "reports"
    if not reports_dir.exists():
        return None
    htmls = sorted(reports_dir.glob("strategist_briefing_*.html"))
    if htmls:
        return htmls[-1].read_text(encoding="utf-8")
    jsons = sorted(reports_dir.glob("strategist_run_*.json"))
    if jsons:
        data = json.loads(jsons[-1].read_text(encoding="utf-8"))
        return data.get("briefing") or data.get("summary")
    return None


# Milestone date helper â€” Quarter format parser
# 'Q1' â†’ 03-31, 'Q2' â†’ 06-30, 'Q3' â†’ 09-30, 'Q4' â†’ 12-31
# e.g. '2026-Q2' â†’ datetime(2026, 6, 30)
_QUARTER_ENDS = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _parse_milestone_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

    match = re.fullmatch(r"(\d{4})-Q([1-4])", date_str)
    if match:
        year, quarter = int(match.group(1)), int(match.group(2))
        month, day = _QUARTER_ENDS[quarter]
        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    return None


def _milestone_within_days(milestone: dict, days: int = 30) -> bool:
    today = datetime.now().date()
    m_date = _parse_milestone_date(milestone.get("date", ""))
    if m_date is None:
        return False
    delta = (m_date.date() - today).days
    return 0 <= delta <= days


def run_intelligence_engine(verbose: bool = True) -> Optional[dict]:
    t0 = time.time()
    try:
        from strategist_hello import coordinator  # type: ignore[import]
        result = coordinator()
        elapsed = time.time() - t0
        if verbose:
            sigs = len(result.get("final_signals", []))
            _ok(f"Intelligence engine complete Ã¢â‚¬â€ {sigs} signals ({elapsed:.1f}s)")
        return result
    except ImportError:
        _warn("strategist_hello.py not found Ã¢â‚¬â€ Phase 1 skipped")
        return None
    except Exception as exc:
        _warn(f"Phase 1 (intelligence engine) failed: {exc}")
        traceback.print_exc(file=sys.stderr)
        return None


def run_hitl_and_adversarial(
    engine_result: Optional[dict],
    verbose: bool = True,
) -> Optional[dict]:
    if engine_result is None:
        if verbose:
            _info("Phase 2 skipped Ã¢â‚¬â€ no engine result to validate")
        return None

    try:
        if verbose:
            hitl = engine_result.get("hitl_output")
            adv = engine_result.get("adversarial_output")
            _ok("HITL output present") if hitl else _info("HITL output not in engine result")
            _ok("Adversarial output present") if adv else _info("Adversarial output not in engine result")
        return engine_result
    except Exception as exc:
        _warn(f"Phase 2 (HITL/adversarial) failed: {exc}")
        traceback.print_exc(file=sys.stderr)
        return engine_result


def run_asset_scoring(
    briefing: Optional[str],
    assets: list[dict],
    verbose: bool = True,
) -> dict:
    scoring: dict[str, dict] = {}
    briefing_text = briefing or ""
    hta_kws = ["NICE", "HTA", "ICER", "cost-effectiveness", "QALY", "EUnetHTA"]
    risk_kws = ["competitor", "biosimilar", "PDUFA", "competitive threat", "rival"]

    hta_signal = any(kw.lower() in briefing_text.lower() for kw in hta_kws)
    risk_signal = any(kw.lower() in briefing_text.lower() for kw in risk_kws)

    for asset in assets:
        apex_id = asset.get("apex_id", "UNKNOWN")
        asset_name = asset.get("brand_name", apex_id)
        t0 = time.time()
        entry: dict = {"status": "ok"}

        try:
            from launch_readiness_agent import score_asset  # type: ignore[import]
            score = score_asset(asset, briefing=briefing)
            entry["launch_readiness"] = score
            if verbose:
                tier = score.get("overall", {}).get("readiness_tier", "?")
                _ok(f"{asset_name} ({apex_id}) readiness: {tier} [{time.time()-t0:.1f}s]")
        except ImportError:
            entry["status"] = "launch_readiness_agent_missing"
            if verbose:
                _info(f"{asset_name}: launch_readiness_agent not found Ã¢â‚¬â€ skipping")
        except Exception as exc:
            _warn(f"launch_readiness_agent failed for {apex_id}: {exc}")
            traceback.print_exc(file=sys.stderr)
            entry["status"] = "error"
            entry["error"] = str(exc)

        if hta_signal:
            try:
                from hta_strategy_agent import run_hta_analysis  # type: ignore[import]
                entry["hta"] = run_hta_analysis(asset, briefing=briefing)
                if verbose:
                    _ok(f"{asset_name} ({apex_id}) HTA analysis complete")
            except ImportError:
                if verbose:
                    _info(f"hta_strategy_agent not available for {apex_id}")
            except Exception as exc:
                _warn(f"hta_strategy_agent failed for {apex_id}: {exc}")
                traceback.print_exc(file=sys.stderr)

        if risk_signal:
            try:
                from competitive_response_agent import run_competitive_response  # type: ignore[import]
                entry["competitive_response"] = run_competitive_response(asset, briefing=briefing)
                if verbose:
                    _ok(f"{asset_name} ({apex_id}) competitive response complete")
            except ImportError:
                if verbose:
                    _info(f"competitive_response_agent not available for {apex_id}")
            except Exception as exc:
                _warn(f"competitive_response_agent failed for {apex_id}: {exc}")
                traceback.print_exc(file=sys.stderr)

        scoring[apex_id] = entry

    return scoring


def run_recommendations(
    briefing: Optional[str],
    assets: list[dict],
    scoring_results: dict,
    verbose: bool = True,
) -> dict:
    rec_result: dict = {"recs": [], "paths": {}, "memory_deltas": {}}

    try:
        from comm_ex_generator import run as _comm_ex_run  # type: ignore[import]
        result = _comm_ex_run(briefing=briefing, verbose=verbose)
        rec_result["recs"] = result.get("recs", [])
        rec_result["paths"] = result.get("paths", {})
        if verbose:
            _ok(f"Comm Ex complete Ã¢â‚¬â€ {len(rec_result['recs'])} recommendations")
    except ImportError:
        _warn("comm_ex_generator not found Ã¢â‚¬â€ Phase 4 Comm Ex skipped")
    except Exception as exc:
        _warn(f"Phase 4 (Comm Ex generator) failed: {exc}")
        traceback.print_exc(file=sys.stderr)

    try:
        from memory_agent import run_memory_report  # type: ignore[import]
        for asset in assets:
            apex_id = asset.get("apex_id", "")
            if not apex_id:
                continue
            try:
                delta_map = run_memory_report(asset_id=apex_id, verbose=False)
                asset_delta = delta_map.get(apex_id, {})
                rec_result["memory_deltas"][apex_id] = {
                    "new": len(asset_delta.get("new_recs", [])),
                    "escalated": len(asset_delta.get("escalated_recs", [])),
                    "resolved": len(asset_delta.get("resolved_recs", [])),
                    "stable": len(asset_delta.get("stable_recs", [])),
                    "trend": asset_delta.get("trend", "STABLE"),
                }
                if verbose:
                    d = rec_result["memory_deltas"][apex_id]
                    _ok(f"Memory updated {apex_id} Ã¢â‚¬â€ new:{d['new']} escalated:{d['escalated']} trend:{d['trend']}")
            except Exception as exc:
                _warn(f"Memory update failed for {apex_id}: {exc}")
                rec_result["memory_deltas"][apex_id] = {"status": "error", "error": str(exc)}
    except ImportError:
        if verbose:
            _info("memory_agent not available Ã¢â‚¬â€ memory update skipped")

    return rec_result


def run_milestone_prep_phase(
    assets: list[dict],
    verbose: bool = True,
) -> dict:
    results: dict[str, list] = {}

    try:
        from milestone_prep_agent import run_milestone_prep  # type: ignore[import]
    except ImportError:
        if verbose:
            _info("milestone_prep_agent not available Ã¢â‚¬â€ Phase 5 skipped")
        return results

    for asset in assets:
        apex_id = asset.get("apex_id", "UNKNOWN")
        milestones = asset.get("upcoming_milestones", [])
        triggered: list[dict] = []

        for m in milestones:
            if not _milestone_within_days(m, days=30):
                continue
            m_type = m.get("type", "GOVERNANCE").upper()
            try:
                doc = run_milestone_prep(apex_id, m_type, verbose=False)
                triggered.append({
                    "milestone_type": m_type,
                    "milestone_label": m.get("label", m_type),
                    "milestone_date": m.get("date", ""),
                    "document_id": doc.get("document_id", ""),
                })
                if verbose:
                    _ok(f"{apex_id} Ã¢â‚¬â€ auto-triggered {m_type} (date: {m.get('date', '?')})")
            except Exception as exc:
                _warn(f"Milestone prep failed for {apex_id}/{m_type}: {exc}")
                traceback.print_exc(file=sys.stderr)

        if triggered:
            results[apex_id] = triggered

    if verbose and not results:
        _info("No assets have milestones within 30 days Ã¢â‚¬â€ Phase 5 complete (no triggers)")

    return results


def refresh_dashboard(
    rec_result: dict,
    scoring_results: dict,
    milestone_result: dict,
    verbose: bool = True,
) -> Path:
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if DASHBOARD_PATH.exists():
        try:
            existing = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    unified = {
        **existing,
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": "2.0",
            "pipeline": "apex_coordinator",
        },
        "distribution": existing.get("distribution", {}),
        "top_risks": existing.get("top_risks", []),
        "top_opportunities": existing.get("top_opportunities", []),
        "launch_readiness": {
            apex_id: v["launch_readiness"]
            for apex_id, v in scoring_results.items()
            if v.get("launch_readiness")
        },
        "hta_events": {
            apex_id: v["hta"]
            for apex_id, v in scoring_results.items()
            if v.get("hta")
        },
        "competitive_intel": {
            apex_id: v["competitive_response"]
            for apex_id, v in scoring_results.items()
            if v.get("competitive_response")
        },
        "memory_deltas": rec_result.get("memory_deltas", {}),
        "rec_count": len(rec_result.get("recs", [])),
        "output_paths": rec_result.get("paths", {}),
        "milestone_alerts": milestone_result,
    }

    DASHBOARD_PATH.write_text(
        json.dumps(unified, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if verbose:
        _ok(f"Dashboard refreshed: {DASHBOARD_PATH.name}")
        _info(f"Top-level keys: {list(unified.keys())}")

    return DASHBOARD_PATH


def apex_run(
    full: bool = True,
    comm_ex_only: bool = False,
    engine_only: bool = False,
    verbose: bool = True,
) -> dict:
    run_start = time.time()
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode = "comm-ex-only" if comm_ex_only else ("engine-only" if engine_only else "full")

    if verbose:
        print("\n" + "Ã¢â€“Ë†" * 62)
        print("  APEX COMMERCIAL INTELLIGENCE PIPELINE")
        print(f"  {run_ts}  |  mode: {mode}")
        print("Ã¢â€“Ë†" * 62)

    assets = load_assets()
    if verbose:
        _info(f"Loaded {len(assets)} assets from registry")

    engine_result: Optional[dict] = None
    if not comm_ex_only:
        if verbose:
            _phase(1, "Pharma Intelligence Engine")
        engine_result = run_intelligence_engine(verbose=verbose)
        if engine_result is None and verbose:
            _warn("Phase 1 failed Ã¢â‚¬â€ will fall back to latest briefing on disk")

    if engine_only:
        if verbose:
            print(f"\n  Engine-only run complete ({time.time()-run_start:.1f}s)")
        return {"engine_result": engine_result, "mode": mode}

    if not comm_ex_only:
        if verbose:
            _phase(2, "HITL + Adversarial Validation")
        engine_result = run_hitl_and_adversarial(engine_result, verbose=verbose)

    briefing = extract_briefing(engine_result) or load_latest_briefing()
    if verbose:
        if briefing:
            _info(f"Briefing: {len(briefing)} chars")
        else:
            _warn("No briefing available Ã¢â‚¬â€ Phases 3-4 will use TA defaults")

    if verbose:
        _phase(3, "Asset Scoring  (Launch Readiness + HTA + Competitive)")
    scoring_results = run_asset_scoring(briefing, assets, verbose=verbose)

    if verbose:
        _phase(4, "Recommendations + Memory Update")
    rec_result = run_recommendations(briefing, assets, scoring_results, verbose=verbose)

    if verbose:
        _phase(5, "Milestone Prep  (auto-trigger Ã¢â€°Â¤30 days)")
    milestone_result = run_milestone_prep_phase(assets, verbose=verbose)

    if verbose:
        _phase(6, "Dashboard Refresh")
    dashboard_path = refresh_dashboard(
        rec_result, scoring_results, milestone_result, verbose=verbose
    )

    elapsed = time.time() - run_start
    unified = {
        "run_timestamp": run_ts,
        "elapsed_seconds": round(elapsed, 1),
        "mode": mode,
        "assets_processed": len(assets),
        "engine_result": engine_result,
        "scoring_results": scoring_results,
        "rec_result": rec_result,
        "milestone_result": milestone_result,
        "dashboard_path": str(dashboard_path),
    }

    if verbose:
        milestones_triggered = sum(len(v) for v in milestone_result.values())
        print("\n" + "Ã¢â€“Ë†" * 62)
        print(f"  APEX RUN COMPLETE Ã¢â‚¬â€ {elapsed:.1f}s")
        print(f"    Recommendations:        {len(rec_result.get('recs', []))}")
        print(f"    Assets scored:          {len(scoring_results)}")
        print(f"    Milestones triggered:   {milestones_triggered}")
        print(f"    Dashboard:              {dashboard_path.name}")
        print("Ã¢â€“Ë†" * 62)

    return unified

