# run_comm_ex.py
# AI & Digital Transformation Tool — Johnson & Johnson Innovative Medicine
"""
Main entry point for the AI & Digital Transformation pipeline.

Orchestrates two phases:
  Phase 1 — Intelligence Engine (pharma regulatory + market signals)
             Runs the multi-agent strategist pipeline adapted for pharma sources.
             Output: strategist-engine/reports/strategist_run_*.json
                     strategist-engine/reports/strategist_briefing_*.html

  Phase 2 — Comm Ex Layer (commercialization recommendations)
             Translates the intelligence briefing into structured commercial
             recommendations for J&J 3M teams: Marketing, Medical Affairs,
             Market Access.
             Output: comm-ex/outputs/comm_ex_recommendations_*.json
                     comm-ex/outputs/comm_ex_summary_*.txt
                     comm-ex/outputs/comm_ex_dashboard_ready.json

Usage:
  python run_comm_ex.py                    # Full pipeline (engine + comm ex)
  python run_comm_ex.py --comm-ex-only     # Skip engine, use latest briefing
  python run_comm_ex.py --engine-only      # Run engine only, skip comm ex
  python run_comm_ex.py --verbose          # Detailed progress output (default)
  python run_comm_ex.py --quiet            # Suppress non-essential output
"""

import argparse
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).parent
ENGINE_DIR = ROOT_DIR / "strategist-engine"
COMM_EX_DIR = ROOT_DIR / "comm-ex"

# Add engine to path so we can import coordinator
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(COMM_EX_DIR))


# ── Console helpers ───────────────────────────────────────────────────────────

def _banner(text: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)

def _section(text: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")

def _ok(text: str) -> None:
    print(f"  [OK]  {text}")

def _warn(text: str) -> None:
    print(f"  [!!]  {text}")

def _info(text: str) -> None:
    print(f"  ···   {text}")


# ── Phase 1: Intelligence Engine ──────────────────────────────────────────────

def run_intelligence_engine(verbose: bool = True) -> dict:
    """
    Run the pharma-adapted STRATEGIST intelligence engine.
    Returns the coordinator result dict.
    """
    if verbose:
        _section("PHASE 1 — Pharma Intelligence Engine")
        _info("Fetching signals from FDA, EMA, NICE, CMS, ICER, ClinicalTrials.gov...")

    t0 = time.time()

    try:
        # Import coordinator from engine directory
        from strategist_hello import coordinator
        result = coordinator()
        elapsed = time.time() - t0

        if verbose:
            sigs = len(result.get("final_signals", []))
            _ok(f"Engine complete — {sigs} signals processed in {elapsed:.1f}s")
            report = result.get("report_path", "")
            if report:
                _ok(f"Report: {Path(report).name}")

        return result

    except Exception as e:
        _warn(f"Intelligence engine failed: {e}")
        if verbose:
            traceback.print_exc()
        raise


# ── Phase 2: Comm Ex Layer ────────────────────────────────────────────────────

def run_comm_ex(briefing: str | None = None, verbose: bool = True) -> dict:
    """
    Run the Comm Ex recommendations layer.
    If briefing is None, loads the latest from engine reports.
    Returns the comm ex result dict.
    """
    if verbose:
        _section("PHASE 2 — Commercialization Excellence Layer")
        _info("Generating Comm Ex recommendations for Marketing / Medical Affairs / Market Access...")

    try:
        from comm_ex_generator import run
        result = run(briefing=briefing, verbose=verbose)

        if verbose:
            n = len(result.get("recs", []))
            _ok(f"{n} Comm Ex recommendations generated")
            for label, path in result.get("paths", {}).items():
                _ok(f"{label:<20}: {Path(path).name}")

        return result

    except Exception as e:
        _warn(f"Comm Ex layer failed: {e}")
        if verbose:
            traceback.print_exc()
        raise


# ── Coverage validation ───────────────────────────────────────────────────────

def _validate_coverage(recs: list[dict], verbose: bool = True) -> bool:
    """
    Check that mandatory distribution requirements are met.
    Returns True if all checks pass.
    """
    from collections import Counter
    stages = Counter(r.get("asset_stage", "") for r in recs)
    funcs  = Counter(r.get("function_owner", "") for r in recs)
    areas  = Counter(r.get("therapeutic_area", "") for r in recs)

    checks = {
        "PRE-LAUNCH ≥ 2":   stages.get("PRE-LAUNCH", 0) >= 2,
        "LAUNCH ≥ 2":       stages.get("LAUNCH", 0) >= 2,
        "POST-LAUNCH ≥ 2":  stages.get("POST-LAUNCH", 0) >= 2,
        "≥ 2 functions":    len(funcs) >= 2,
        "Oncology present": areas.get("Oncology", 0) >= 1,
        "Immunology present": areas.get("Immunology", 0) >= 1,
    }

    if verbose:
        _section("Coverage Validation")
        for label, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            marker = "OK" if passed else "!!"
            print(f"  [{marker}] {label:<30} {status}")

    return all(checks.values())


# ── Main orchestrator ─────────────────────────────────────────────────────────

def main(
    engine_only: bool = False,
    comm_ex_only: bool = False,
    verbose: bool = True,
) -> None:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if verbose:
        _banner(f"AI & Digital Transformation Tool | J&J Innovative Medicine")
        print(f"  {run_date}")
        print(f"  Engine only: {engine_only} | Comm Ex only: {comm_ex_only}")

    t_start = time.time()
    engine_result  = None
    comm_ex_result = None

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    if not comm_ex_only:
        try:
            engine_result = run_intelligence_engine(verbose=verbose)
        except Exception:
            print("\n[ABORT] Intelligence engine failed. Cannot continue without briefing.\n")
            sys.exit(1)

    if engine_only:
        _banner("Engine-only run complete")
        return

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    try:
        comm_ex_result = run_comm_ex(briefing=None, verbose=verbose)
    except Exception:
        print("\n[ABORT] Comm Ex layer failed.\n")
        sys.exit(1)

    # ── Validation ────────────────────────────────────────────────────────────
    recs = comm_ex_result.get("recs", [])
    all_pass = _validate_coverage(recs, verbose=verbose)

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_start

    if verbose:
        _banner(f"Run Complete | {elapsed:.1f}s | {len(recs)} Recommendations")

        dash = comm_ex_result.get("dashboard", {})
        coverage = dash.get("coverage_check", {})
        dist     = dash.get("distribution", {})

        print("\n  DISTRIBUTION")
        for k, v in dist.get("by_asset_stage", {}).items():
            print(f"    {k:<20} {v}")
        print()
        for k, v in dist.get("by_function", {}).items():
            print(f"    {k:<20} {v}")
        print()

        print("  COVERAGE CHECK")
        for k, v in coverage.items():
            print(f"    {k:<30} {v}")
        print()

        imm = dash.get("immediate_actions", [])
        if imm:
            print(f"  IMMEDIATE ACTIONS ({len(imm)})")
            for a in imm:
                owner  = a.get("function_owner","")
                rec_id = a.get("rec_id","")
                action = a.get("recommended_action","")[:90]
                print(f"    [{rec_id}] {owner}")
                print(f"      {action}...")
                print()

        print(f"  Coverage validation: {'ALL PASS' if all_pass else 'GAPS DETECTED — review output'}")
        print()

        paths = comm_ex_result.get("paths", {})
        print("  OUTPUT FILES")
        for label, path in paths.items():
            print(f"    {label:<20} {path}")
        print()


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ensure Unicode output works on Windows terminals
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    parser = argparse.ArgumentParser(
        description="AI & Digital Transformation Tool — J&J Innovative Medicine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_comm_ex.py                 Full pipeline (engine + comm ex)
  python run_comm_ex.py --comm-ex-only  Comm ex only (uses latest briefing)
  python run_comm_ex.py --engine-only   Engine only (no comm ex)
  python run_comm_ex.py --quiet         Minimal output
""",
    )
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="Run intelligence engine only — do not generate Comm Ex recommendations",
    )
    parser.add_argument(
        "--comm-ex-only",
        action="store_true",
        help="Skip engine — load latest briefing and generate Comm Ex recommendations only",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed progress output",
    )

    args = parser.parse_args()

    if args.engine_only and args.comm_ex_only:
        print("Error: --engine-only and --comm-ex-only are mutually exclusive.")
        sys.exit(1)

    main(
        engine_only=args.engine_only,
        comm_ex_only=args.comm_ex_only,
        verbose=not args.quiet,
    )
