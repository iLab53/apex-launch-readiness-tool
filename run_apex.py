"""
run_apex.py
===========
CLI entry point for the APEX Commercial Intelligence Pipeline.
Wraps apex_coordinator.apex_run() with argument parsing.

Usage:
    python run_apex.py --verbose                  # full pipeline
    python run_apex.py --comm-ex-only --verbose   # skip signal collection
    python run_apex.py --engine-only --verbose    # signal collection only
    python run_apex.py --asset APEX-004 --scorecard --verbose
"""

import argparse
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from apex_coordinator import apex_run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="APEX Commercial Intelligence Pipeline CLI"
    )
    parser.add_argument("--verbose", action="store_true",
                        help="Stream phase-by-phase progress to stdout")
    parser.add_argument("--comm-ex-only", action="store_true", dest="comm_ex_only",
                        help="Skip Phase 1 signal collection (faster)")
    parser.add_argument("--engine-only", action="store_true", dest="engine_only",
                        help="Run Phase 1 signal collection only")
    parser.add_argument("--asset", type=str, default=None, metavar="APEX_ID",
                        help="Limit run to a single asset, e.g. APEX-004")
    parser.add_argument("--scorecard", action="store_true",
                        help="Generate launch readiness scorecard for --asset")
    args = parser.parse_args()

    # Determine mode
    if args.comm_ex_only:
        mode = "comm-ex-only"
    elif args.engine_only:
        mode = "engine-only"
    else:
        mode = "full"

    # Build kwargs — apex_run accepts whatever the coordinator supports
    kwargs = dict(mode=mode, verbose=args.verbose)
    if args.asset:
        kwargs["asset_id"] = args.asset
    if args.scorecard:
        kwargs["scorecard"] = True

    try:
        result = apex_run(**kwargs)
        status = result.get("status", "unknown") if isinstance(result, dict) else "done"
        if args.verbose:
            print(f"\nrun_apex.py: pipeline finished — status={status}")
        return 0 if status in ("success", "done") else 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
