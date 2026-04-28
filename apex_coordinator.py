# apex_coordinator.py
# APEX Coordinator — 6-Phase Orchestration Engine
# ─────────────────────────────────────────────────────────────────────────────
# Replaces the simple coordinator() call with a fully orchestrated pipeline
# that routes signals to relevant assets and runs all APEX agents in sequence.
#
# IMPORTANT: This file builds ON TOP OF strategist_hello.py — it does NOT
# replace it.  Phase 1 imports and calls coordinator() from strategist_hello.
#
# 6-Phase Pipeline:
#   Phase 1  run_intelligence_engine()        pharma signal collection
#   Phase 2  run_hitl_and_adversarial()        HITL validation + adversarial
#   Phase 3  run_asset_scoring()               launch readiness + HTA + comp
#   Phase 4  run_recommendations()             Comm Ex + memory update
#   Phase 5  run_milestone_prep_phase()        auto-trigger ≤30-day milestones
#   Phase 6  refresh_dashboard()               write unified dashboard JSON
#
# Each phase is wrapped in try/except — a failing agent never aborts the
# pipeline.  Phase failures are logged to stderr and the pipeline continues.
#
# Usage:
#   from apex_coordinator import apex_run
#   result = apex_run()                          # full 6-phase run
#   result = apex_run(comm_ex_only=True)         # skip Phases 1-2
#   result = apex_run(engine_only=True)          # Phase 1 only
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
# apex_coordinator.py lives at <repo>/apex_coordinator.py

ROOT_DIR    = Path(__file__).parent
ENGINE_DIR  = ROOT_DIR / "strategist-engine"
COMM_EX_DIR = ROOT_DIR / "comm-ex"
AGENTS_DIR  = ROOT_DIR / "agents"
MEMORY_DIR  = ROOT_DIR / "memory"

sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(COMM_EX_DIR))
sys.path.insert(0, str(AGENTS_DIR))

DASHBOARD_PATH = COMM_EX_DIR / "outputs" / "comm_ex_dashboard_ready.json"
ASSET_REG_PATH = ROOT_DIR / "asset-registry" / "apex_assets.json"


# ── Console helpers ───────────────────────────────────────────────────────────

def _phase(n: int, name: str) -> None:
    print(f"\n{'=' * 62}")
    print(f"  PHASE {n} — {name}")
    print(f"{'=' * 62}")

def _ok(text: str)   -> None: print(f"  [OK]  {text}")
def _warn(text: str) -> None: print(f"  [!!]  {text}", file=sys.stderr)
def _info(text: str) -> None: print(f"  ···   {text}")


# ── Asset registry ────────────────────────────────────────────────────────────

def load_assets() -> list[dict]:
    """Load all APEX assets from asset-registry/apex_assets.json."""
    if not ASSET_REG_PATH.exists():
        _warn(f"Asset registry not found: {ASSET_REG_PATH}")
        return []
    with open(ASSET_REG_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return registry if isinstance(registry, list) else registry.get("assets", [])


def extract_briefing(engine_result: Optional[dict]) -> Optional[str]:
    """Pull the briefing text out of an engine result dict."""
    if not engine_result:
        return None
    return engine_result.get("briefing") or engine_result.get("summary") or None


def load_latest_briefing() -> Optional[str]:
    """Load the most recent strategist briefing from engine reports."""
    reports_dir = ENGINE_DIR / "reports"
    if not reports_dir.exists():
        return None
    # Prefer HTML briefings
    htmls = sorted(reports_dir.glob("strategist_briefing_*.html"))
    if htmls:
        return htmls[-1].read_text(encoding="utf-8")
    # Fall back to JSON run reports
    jsons = sorted(reports_dir.glob("strategist_run_*.json"))
    if jsons:
        data = json.loads(jsons[-1].read_text(encoding="utf-8"))
        return data.get("briefing") or data.get("summary")
    return None


# ── Milestone date helpers ─────────────────────────────────────────────────────

_QUARTER_ENDS = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _parse_milestone_date(date_str: str):
    """
    Parse a milestone date string.  Supports:
      YYYY-MM-DD  (ISO)
      YYYY-QN     (Quarter format — Q1→03-31, Q2→06-30, Q3→09-30, Q4→12-31)

    Returns a datetime.date, or None if unparseable.
    """
    from datetime import date as _date

    if not date_str:
        return None

    # ISO date
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    # Quarter format: 2026-Q2
    m = re.fullmatch(r"(\d{4})-Q([1-4])", date_str)
    if m:
        year, quarter = int(m.group(1)), int(m.group(2))
        month, day = _QUARTER_ENDS[quarter]
        try:
            return _date(year, month, day)
        except ValueError:
            return None

    return None


def _milestone_within_days(milestone: dict, days: int = 30) -> bool:
    """Return True if the milestone date is between today and today + days."""
    from datetime import date as _date
    today    = _date.today()
    m_date   = _parse_milestone_date(milestone.get("date", ""))
    if m_date is None:
        return False
    delta = (m_date - today).days
    return 0 <= delta <= days


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Intelligence Engine
# ═════════════════════════════════════════════════════════════════════════════

def run_intelligence_engine(verbose: bool = True) -> Optional[dict]:
    """
    Phase 1 — calls coordinator() from strategist_hello.py.

    Returns engine result dict on success, None on failure.
    A None return is handled in apex_run() by falling back to the latest
    briefing on disk — the pipeline continues.
    """
    t0 = time.time()
    try:
        from strategist_hello import coordinator  # type: ignore[import]
        result  = coordinator()
        elapsed = time.time() - t0
        if verbose:
            sigs = len(result.get("final_signals", []))
            _ok(f"Intelligence engine complete — {sigs} signals ({elapsed:.1f}s)")
        return result
    except ImportError:
        _warn("strategist_hello.py not found — Phase 1 skipped")
        return None
    except Exception as exc:
        _warn(f"Phase 1 (intelligence engine) failed: {exc}")
        traceback.print_exc(file=sys.stderr)
        return None


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2 — HITL + Adversarial
# ═════════════════════════════════════════════════════════════════════════════

def run_hitl_and_adversarial(
    engine_result: Optional[dict],
    verbose:       bool = True,
) -> Optional[dict]:
    """
    Phase 2 — surfaces HITL validation and adversarial stress-test outputs.

    These are embedded inside coordinator() in strategist_hello.py; this phase
    extracts and surfaces them.  Always returns engine_result (possibly
    unchanged) — never aborts the pipeline.
    """
    if engine_result is None:
        if verbose:
            _info("Phase 2 skipped — no engine result to validate")
        return None

    try:
        if verbose:
            hitl = engine_result.get("hitl_output")
            adv  = engine_result.get("adversarial_output")
            _ok("HITL output present") if hitl else _info("HITL output not in engine result")
            _ok("Adversarial output present") if adv else _info("Adversarial output not in engine result")
        return engine_result
    except Exception as exc:
        _warn(f"Phase 2 (HITL/adversarial) failed: {exc}")
        traceback.print_exc(file=sys.stderr)
        return engine_result   # pass-through — never block pipeline


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Asset Scoring
# ═════════════════════════════════════════════════════════════════════════════

def run_asset_scoring(
    briefing: Optional[str],
    assets:   list[dict],
    verbose:  bool = True,
) -> dict:
    """
    Phase 3 — run launch readiness scoring for each asset SEQUENTIALLY.

    Also triggers:
      - hta_strategy_agent    if HTA keywords detected in briefing
      - competitive_response_agent  if RISK/competitive keywords detected

    Returns dict keyed by apex_id → {launch_readiness, hta, competitive_response, status}.

    NOTE: Sequential to avoid ANTHROPIC_API_KEY rate limits.
    TODO: Consider async/parallel once API quota and rate limits are confirmed.
    """
    scoring: dict[str, dict] = {}
    briefing_text = briefing or ""
    hta_kws  = ["NICE", "HTA", "ICER", "cost-effectiveness", "QALY", "EUnetHTA"]
    risk_kws = ["competitor", "biosimilar", "PDUFA", "competitive threat", "rival"]

    hta_signal  = any(kw.lower() in briefing_text.lower() for kw in hta_kws)
    risk_signal = any(kw.lower() in briefing_text.lower() for kw in risk_kws)

    for asset in assets:
        apex_id    = asset.get("apex_id", "UNKNOWN")
        asset_name = asset.get("brand_name", apex_id)
        t0         = time.time()
        entry: dict = {"status": "ok"}

        # ── Launch Readiness Agent ─────────────────────────────────────────
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
                _info(f"{asset_name}: launch_readiness_agent not found — skipping")
        except Exception as exc:
            _warn(f"launch_readiness_agent failed for {apex_id}: {exc}")
            traceback.print_exc(file=sys.stderr)
            entry["status"] = "error"
            entry["error"]  = str(exc)

        # ── HTA Strategy Agent ────────────────────────────────────────────
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

        # ── Competitive Response Agent ────────────────────────────────────
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


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4 — Recommendations + Memory
# ═════════════════════════════════════════════════════════════════════════════

def run_recommendations(
    briefing:        Optional[str],
    assets:          list[dict],
    scoring_results: dict,
    verbose:         bool = True,
) -> dict:
    """
    Phase 4 — run Comm Ex generator, then update memory for each asset.

    Returns dict: {recs, paths, memory_deltas}.
    """
    rec_result: dict = {"recs": [], "paths": {}, "memory_deltas": {}}

    # ── Comm Ex Generator ─────────────────────────────────────────────────
    try:
        from comm_ex_generator import run as _comm_ex_run  # type: ignore[import]
        result = _comm_ex_run(briefing=briefing, verbose=verbose)
        rec_result["recs"]  = result.get("recs", [])
        rec_result["paths"] = result.get("paths", {})
        if verbose:
            _ok(f"Comm Ex complete — {len(rec_result['recs'])} recommendations")
    except ImportError:
        _warn("comm_ex_generator not found — Phase 4 Comm Ex skipped")
    except Exception as exc:
        _warn(f"Phase 4 (Comm Ex generator) failed: {exc}")
        traceback.print_exc(file=sys.stderr)

    # ── Memory Update per asset ───────────────────────────────────────────
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
                    "new":       len(asset_delta.get("new_recs", [])),
                    "escalated": len(asset_delta.get("escalated_recs", [])),
                    "resolved":  len(asset_delta.get("resolved_recs", [])),
                    "stable":    len(asset_delta.get("stable_recs", [])),
                    "trend":     asset_delta.get("trend", "STABLE"),
                }
                if verbose:
                    d = rec_result["memory_deltas"][apex_id]
                    _ok(f"Memory updated {apex_id} — new:{d['new']} escalated:{d['escalated']} trend:{d['trend']}")
            except Exception as exc:
                _warn(f"Memory update failed for {apex_id}: {exc}")
                rec_result["memory_deltas"][apex_id] = {"status": "error", "error": str(exc)}
    except ImportError:
        if verbose:
            _info("memory_agent not available — memory update skipped")

    return rec_result


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 5 — Milestone Prep (auto-trigger ≤30 days)
# ═════════════════════════════════════════════════════════════════════════════

def run_milestone_prep_phase(
    assets:  list[dict],
    verbose: bool = True,
) -> dict:
    """
    Phase 5 — check each asset's upcoming_milestones.

    Auto-triggers milestone_prep_agent for any milestone within 30 days.
    Returns dict keyed by apex_id → list of triggered doc metadata.
    """
    results: dict[str, list] = {}

    try:
        from milestone_prep_agent import run_milestone_prep  # type: ignore[import]
    except ImportError:
        if verbose:
            _info("milestone_prep_agent not available — Phase 5 skipped")
        return results

    for asset in assets:
        apex_id    = asset.get("apex_id", "UNKNOWN")
        milestones = asset.get("upcoming_milestones", [])
        triggered: list[dict] = []

        for m in milestones:
            if not _milestone_within_days(m, days=30):
                continue
            m_type = m.get("type", "GOVERNANCE").upper()
            try:
                doc = run_milestone_prep(apex_id, m_type, verbose=False)
                triggered.append({
                    "milestone_type":  m_type,
                    "milestone_label": m.get("label", m_type),
                    "milestone_date":  m.get("date", ""),
                    "document_id":     doc.get("document_id", ""),
                })
                if verbose:
                    _ok(f"{apex_id} — auto-triggered {m_type} (date: {m.get('date', '?')})")
            except Exception as exc:
                _warn(f"Milestone prep failed for {apex_id}/{m_type}: {exc}")
                traceback.print_exc(file=sys.stderr)

        if triggered:
            results[apex_id] = triggered

    if verbose and not results:
        _info("No assets have milestones within 30 days — Phase 5 complete (no triggers)")

    return results


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 6 — Dashboard Refresh
# ═════════════════════════════════════════════════════════════════════════════

def refresh_dashboard(
    rec_result:       dict,
    scoring_results:  dict,
    milestone_result: dict,
    verbose:          bool = True,
) -> Path:
    """
    Phase 6 — write unified run result to comm_ex_dashboard_ready.json.

    Merges new Phase 3–5 keys into the existing dashboard schema so that
    legacy keys (distribution, top_risks, top_opportunities) are preserved.

    New keys written by this phase:
      launch_readiness   — per-asset scorecard summaries
      hta_events         — per-asset HTA analysis results
      competitive_intel  — per-asset competitive response results
      memory_deltas      — per-asset trend + delta counts
      milestone_alerts   — auto-triggered milestone docs
      meta               — pipeline version + timestamp

    Returns the path written.
    """
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load existing dashboard to preserve legacy keys
    existing: dict = {}
    if DASHBOARD_PATH.exists():
        try:
            existing = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    unified = {
        **existing,
        "meta": {
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "schema_version": "2.0",
            "pipeline":       "apex_coordinator",
        },
        # Preserve legacy Comm Ex keys
        "distribution":      existing.get("distribution", {}),
        "top_risks":         existing.get("top_risks", []),
        "top_opportunities": existing.get("top_opportunities", []),
        # Phase 3 — asset scoring outputs
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
        # Phase 4 — recommendations + memory
        "memory_deltas":    rec_result.get("memory_deltas", {}),
        "rec_count":        len(rec_result.get("recs", [])),
        "output_paths":     rec_result.get("paths", {}),
        # Phase 5 — milestone alerts
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


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════

def apex_run(
    full:         bool = True,
    comm_ex_only: bool = False,
    engine_only:  bool = False,
    verbose:      bool = True,
) -> dict:
    """
    Main APEX orchestrator.  Runs 6 phases in sequence.

    Args:
        full:         Run all 6 phases (default True — ignored if other flags set)
        comm_ex_only: Skip Phases 1-2; run Phases 3-6 using latest briefing on disk
        engine_only:  Run Phase 1 only; return after signal collection
        verbose:      Print phase names and agent completion times

    Returns:
        Unified result dict with keys:
          run_timestamp, elapsed_seconds, mode,
          assets_processed, engine_result, scoring_results,
          rec_result, milestone_result, dashboard_path
    """
    run_start = time.time()
    run_ts    = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mode      = "comm-ex-only" if comm_ex_only else ("engine-only" if engine_only else "full")

    if verbose:
        print("\n" + "█" * 62)
        print("  APEX COMMERCIAL INTELLIGENCE PIPELINE")
        print(f"  {run_ts}  |  mode: {mode}")
        print("█" * 62)

    assets = load_assets()
    if verbose:
        _info(f"Loaded {len(assets)} assets from registry")

    # ── Phase 1 ───────────────────────────────────────────────────────────
    engine_result: Optional[dict] = None
    if not comm_ex_only:
        if verbose:
            _phase(1, "Pharma Intelligence Engine")
        engine_result = run_intelligence_engine(verbose=verbose)
        if engine_result is None and verbose:
            _warn("Phase 1 failed — will fall back to latest briefing on disk")

    if engine_only:
        if verbose:
            print(f"\n  Engine-only run complete ({time.time()-run_start:.1f}s)")
        return {"engine_result": engine_result, "mode": mode}

    # ── Phase 2 ───────────────────────────────────────────────────────────
    if not comm_ex_only:
        if verbose:
            _phase(2, "HITL + Adversarial Validation")
        engine_result = run_hitl_and_adversarial(engine_result, verbose=verbose)

    # Resolve briefing — engine output or latest file on disk
    briefing = extract_briefing(engine_result) or load_latest_briefing()
    if verbose:
        if briefing:
            _info(f"Briefing: {len(briefing)} chars")
        else:
            _warn("No briefing available — Phases 3-4 will use TA defaults")

    # ── Phase 3 ───────────────────────────────────────────────────────────
    if verbose:
        _phase(3, "Asset Scoring  (Launch Readiness + HTA + Competitive)")
    scoring_results = run_asset_scoring(briefing, assets, verbose=verbose)

    # ── Phase 4 ───────────────────────────────────────────────────────────
    if verbose:
        _phase(4, "Recommendations + Memory Update")
    rec_result = run_recommendations(briefing, assets, scoring_results, verbose=verbose)

    # ── Phase 5 ───────────────────────────────────────────────────────────
    if verbose:
        _phase(5, "Milestone Prep  (auto-trigger ≤30 days)")
    milestone_result = run_milestone_prep_phase(assets, verbose=verbose)

    # ── Phase 6 ───────────────────────────────────────────────────────────
    if verbose:
        _phase(6, "Dashboard Refresh")
    dashboard_path = refresh_dashboard(
        rec_result, scoring_results, milestone_result, verbose=verbose
    )

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - run_start
    unified = {
        "run_timestamp":     run_ts,
        "elapsed_seconds":   round(elapsed, 1),
        "mode":              mode,
        "assets_processed":  len(assets),
        "engine_result":     engine_result,
        "scoring_results":   scoring_results,
        "rec_result":        rec_result,
        "milestone_result":  milestone_result,
        "dashboard_path":    str(dashboard_path),
    }

    if verbose:
        milestones_triggered = sum(len(v) for v in milestone_result.values())
        print("\n" + "█" * 62)
        print(f"  APEX RUN COMPLETE — {elapsed:.1f}s")
        print(f"    Recommendations:        {len(rec_result.get('recs', []))}")
        print(f"    Assets scored:          {len(scoring_results)}")
        print(f"    Milestones triggered:   {milestones_triggered}")
        print(f"    Dashboard:              {dashboard_path.name}")
        print("█" * 62)

    return unified
