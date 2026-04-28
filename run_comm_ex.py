# run_comm_ex.py
# AI & Digital Transformation Tool Ã¢â‚¬â€ Johnson & Johnson Innovative Medicine
"""
Main entry point for the AI & Digital Transformation pipeline.

Orchestrates two phases:
  Phase 1 Ã¢â‚¬â€ Intelligence Engine (pharma regulatory + market signals)
             Runs the multi-agent strategist pipeline adapted for pharma sources.
             Output: strategist-engine/reports/strategist_run_*.json
                     strategist-engine/reports/strategist_briefing_*.html

  Phase 2 Ã¢â‚¬â€ Comm Ex Layer (commercialization recommendations)
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

ROOT_DIR = Path(__file__).parent
ENGINE_DIR = ROOT_DIR / "strategist-engine"
COMM_EX_DIR = ROOT_DIR / "comm-ex"

sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(COMM_EX_DIR))


def _banner(text: str) -> None:
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width)


def _section(text: str) -> None:
    print(f"\n{'Ã¢â€â‚¬' * 50}")
    print(f"  {text}")
    print(f"{'Ã¢â€â‚¬' * 50}")


def _ok(text: str) -> None:
    print(f"  [OK]  {text}")


def _warn(text: str) -> None:
    print(f"  [!!]  {text}")


def _info(text: str) -> None:
    print(f"  Ã‚Â·Ã‚Â·Ã‚Â·   {text}")


def run_intelligence_engine(verbose: bool = True) -> dict:
    if verbose:
        _section("PHASE 1 Ã¢â‚¬â€ Pharma Intelligence Engine")
        _info("Fetching signals from FDA, EMA, NICE, CMS, ICER, ClinicalTrials.gov...")

    t0 = time.time()

    try:
        from strategist_hello import coordinator
        result = coordinator()
        elapsed = time.time() - t0

        if verbose:
            sigs = len(result.get("final_signals", []))
            _ok(f"Engine complete Ã¢â‚¬â€ {sigs} signals processed in {elapsed:.1f}s")
            report = result.get("report_path", "")
            if report:
                _ok(f"Report: {Path(report).name}")

        return result

    except Exception as e:
        _warn(f"Intelligence engine failed: {e}")
        if verbose:
            traceback.print_exc()
        raise


def run_comm_ex(briefing: str | None = None, verbose: bool = True) -> dict:
    if verbose:
        _section("PHASE 2 Ã¢â‚¬â€ Commercialization Excellence Layer")
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


def _validate_coverage(recs: list[dict], verbose: bool = True) -> bool:
    from collections import Counter
    stages = Counter(r.get("asset_stage", "") for r in recs)
    funcs = Counter(r.get("function_owner", "") for r in recs)
    areas = Counter(r.get("therapeutic_area", "") for r in recs)

    checks = {
        "PRE-LAUNCH Ã¢â€°Â¥ 2": stages.get("PRE-LAUNCH", 0) >= 2,
        "LAUNCH Ã¢â€°Â¥ 2": stages.get("LAUNCH", 0) >= 2,
        "POST-LAUNCH Ã¢â€°Â¥ 2": stages.get("POST-LAUNCH", 0) >= 2,
        "Ã¢â€°Â¥ 2 functions": len(funcs) >= 2,
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


def main(
    engine_only: bool = False,
    comm_ex_only: bool = False,
    verbose: bool = True,
) -> None:
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if verbose:
        _banner("AI & Digital Transformation Tool | J&J Innovative Medicine")
        print(f"  {run_date}")
        print(f"  Engine only: {engine_only} | Comm Ex only: {comm_ex_only}")

    t_start = time.time()
    engine_result = None
    comm_ex_result = None

    if not comm_ex_only:
        try:
            engine_result = run_intelligence_engine(verbose=verbose)
        except Exception:
            print("\n[ABORT] Intelligence engine failed. Cannot continue without briefing.\n")
            sys.exit(1)

    if engine_only:
        _banner("Engine-only run complete")
        return

    try:
        comm_ex_result = run_comm_ex(briefing=None, verbose=verbose)
    except Exception:
        print("\n[ABORT] Comm Ex layer failed.\n")
        sys.exit(1)

    recs = comm_ex_result.get("recs", [])
    all_pass = _validate_coverage(recs, verbose=verbose)
    elapsed = time.time() - t_start

    if verbose:
        _banner(f"Run Complete | {elapsed:.1f}s | {len(recs)} Recommendations")

        dash = comm_ex_result.get("dashboard", {})
        coverage = dash.get("coverage_check", {})
        dist = dash.get("distribution", {})

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
                owner = a.get("function_owner", "")
                rec_id = a.get("rec_id", "")
                action = a.get("recommended_action", "")[:90]
                print(f"    [{rec_id}] {owner}")
                print(f"      {action}...")
                print()

        print(f"  Coverage validation: {'ALL PASS' if all_pass else 'GAPS DETECTED Ã¢â‚¬â€ review output'}")
        print()

        paths = comm_ex_result.get("paths", {})
        print("  OUTPUT FILES")
        for label, path in paths.items():
            print(f"    {label:<20} {path}")
        print()


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    parser = argparse.ArgumentParser(
        description="AI & Digital Transformation Tool Ã¢â‚¬â€ J&J Innovative Medicine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_comm_ex.py                              Full pipeline (engine + comm ex)
  python run_comm_ex.py --comm-ex-only               Comm ex only (uses latest briefing)
  python run_comm_ex.py --engine-only                Engine only (no comm ex)
  python run_comm_ex.py --quiet                      Minimal output
  python run_comm_ex.py --asset APEX-001 --scorecard Generate scorecard for one asset
  python run_comm_ex.py --memory-report              Delta report vs previous run
  python run_comm_ex.py --memory-report --asset APEX-004
  python run_comm_ex.py --milestone-prep APEX-001 LRR
""",
    )
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="Run intelligence engine only Ã¢â‚¬â€ do not generate Comm Ex recommendations",
    )
    parser.add_argument(
        "--comm-ex-only",
        action="store_true",
        help="Skip engine Ã¢â‚¬â€ load latest briefing and generate Comm Ex recommendations only",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed progress output",
    )
    parser.add_argument(
        "--asset",
        metavar="APEX_ID",
        default=None,
        help="Target a specific asset, e.g. APEX-001.  Used with --scorecard and --memory-report.",
    )
    parser.add_argument(
        "--scorecard",
        action="store_true",
        default=False,
        help="Generate a Launch Readiness Scorecard for the given --asset.",
    )
    parser.add_argument(
        "--memory-report",
        action="store_true",
        default=False,
        help=(
            "Print a longitudinal delta report comparing current Comm Ex output "
            "against the previous run stored in memory/.  "
            "Classifies each rec as NEW / ESCALATED / RESOLVED / STABLE.  "
            "Optionally scoped to one asset with --asset."
        ),
    )
    parser.add_argument(
        "--milestone-prep",
        nargs=2,
        metavar=("ASSET_ID", "MILESTONE_TYPE"),
        help="Generate milestone prep document. Example: --milestone-prep APEX-004 LRR",
    )

    args = parser.parse_args()

    if args.memory_report:
        sys.path.insert(0, str(ROOT_DIR / "agents"))
        from memory_agent import run_memory_report
        run_memory_report(
            asset_id=args.asset,
            verbose=not args.quiet,
        )
        sys.exit(0)

    if args.milestone_prep:
        asset_id, milestone_type = args.milestone_prep
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))
        from milestone_prep_agent import generate_milestone_prep
        try:
            path = generate_milestone_prep(asset_id, milestone_type)
            print(f"Milestone prep document saved to: {path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    if args.scorecard:
        if not args.asset:
            print("Error: --scorecard requires --asset <ASSET_ID>.", file=sys.stderr)
            print("  Example: python run_comm_ex.py --asset APEX-001 --scorecard", file=sys.stderr)
            sys.exit(1)
        from scorecard_generator import generate_scorecard
        generate_scorecard(args.asset)
        sys.exit(0)

    if args.engine_only and args.comm_ex_only:
        print("Error: --engine-only and --comm-ex-only are mutually exclusive.")
        sys.exit(1)

    main(
        engine_only=args.engine_only,
        comm_ex_only=args.comm_ex_only,
        verbose=not args.quiet,
    )

