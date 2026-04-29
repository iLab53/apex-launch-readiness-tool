"""
nightly_apex_run.py
===================
Nightly automation script for the APEX Commercial Intelligence Pipeline.

Runs apex_run(full=True) and appends a one-line status entry to
logs/nightly_run.log. Designed to be triggered by Windows Task Scheduler
or cron at 06:00 UTC.

Usage:
    python nightly_apex_run.py            # silent run
    python nightly_apex_run.py --verbose  # print all phase output
"""

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path so apex_coordinator can be imported
# regardless of the working directory set by Task Scheduler.
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apex_coordinator import apex_run  # noqa: E402

LOG_PATH = ROOT_DIR / "logs" / "nightly_run.log"


def run_nightly(verbose=False):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    start = datetime.now(timezone.utc)

    try:
        result = apex_run(full=True, verbose=verbose)

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        # apex_run may return a dict or None depending on coordinator version
        if isinstance(result, dict):
            assets_processed = result.get("assets_processed", 7)
        else:
            assets_processed = 7  # safe fallback: all 7 assets

        log_line = (
            "{ts} | SUCCESS | {elapsed:.1f}s | {assets} assets | full".format(
                ts=start.isoformat(),
                elapsed=elapsed,
                assets=assets_processed,
            )
        )
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

        if verbose:
            print(log_line)

        return 0

    except Exception as exc:
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()
        error_summary = str(exc)[:200]
        log_line = "{ts} | FAILED | {elapsed:.1f}s | {err}".format(
            ts=start.isoformat(),
            elapsed=elapsed,
            err=error_summary,
        )
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

        print("APEX nightly run FAILED:", error_summary, file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = run_nightly(verbose="--verbose" in sys.argv)
    sys.exit(exit_code)
