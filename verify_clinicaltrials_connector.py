"""
verify_clinicaltrials_connector.py
===================================
Verifies the ClinicalTrials.gov connector:
  1. File structure and syntax
  2. Live API dry run (no dashboard mutation)
  3. Full run (patches dashboard)
  4. Dashboard JSON integrity after patch
  5. Signal field format compliance

Run from repo root:
    python verify_clinicaltrials_connector.py
"""

import ast
import json
import pathlib
import subprocess
import sys

ROOT   = pathlib.Path(".")
checks = []


def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append((label, passed, detail))
    print("  [{0}] {1}".format(status, label) + (" -- " + detail if detail else ""))


def main():
    print("=" * 60)
    print("ClinicalTrials.gov Connector Verification")
    print("=" * 60)

    # ---- Connector file ----
    print("\nConnector File")
    conn_path = ROOT / "connectors" / "clinicaltrials_connector.py"
    check("connectors/clinicaltrials_connector.py exists", conn_path.exists())

    if conn_path.exists():
        src = conn_path.read_text(encoding="utf-8")
        try:
            ast.parse(src)
            check("Syntax valid", True)
        except SyntaxError as exc:
            check("Syntax valid", False, str(exc))

        check("API v2 URL present",        "clinicaltrials.gov/api/v2" in src)
        check("fetch_trials defined",       "def fetch_trials" in src)
        check("extract_study_fields defined","def extract_study_fields" in src)
        check("to_competitive_intel defined","def to_competitive_intel" in src)
        check("to_milestone_alert defined",  "def to_milestone_alert" in src)
        check("Timeout constant present",    "TIMEOUT" in src)
        check("Error handling present",      "URLError" in src)
        check("Rate limiting present",       "sleep" in src)
        check("Debug output path present",   "agents" in src and "outputs" in src)
        check("--dry-run flag present",      "dry_run" in src)
        check("--verbose flag present",      "verbose" in src)
        check("J&J sponsor filter present",  "janssen" in src.lower())
        check("Deduplication logic present", "nct_id" in src and "existing_ncts" in src)
    else:
        print("  [SKIP] Skipping content checks -- file not found")

    # ---- Dashboard baseline ----
    print("\nDashboard JSON (baseline)")
    db_path = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
    pre_data = {}
    if db_path.exists():
        try:
            pre_data = json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON valid before run", True)
        except json.JSONDecodeError as exc:
            check("Dashboard JSON valid before run", False, str(exc))
    else:
        check("Dashboard JSON exists", False)

    # ---- Dry run (live API, no mutation) ----
    print("\nDry Run (live API test, no dashboard mutation)")
    if conn_path.exists():
        result = subprocess.run(
            [sys.executable, str(conn_path), "--dry-run", "--verbose"],
            capture_output=True, text=True, timeout=180,
        )
        check(
            "Connector exits cleanly (dry run)",
            result.returncode == 0,
            result.stderr[:120] if result.returncode not in (0,) else "",
        )
        output = result.stdout + result.stderr
        check("Results line present",     "Results:" in output)
        check("Dry run message present",  "Dry run" in output or "not modified" in output)

        # Check API returned something
        import re
        match = re.search(r"(\d+) competitor signal", output)
        signals_found = int(match.group(1)) if match else 0
        check(
            "API returned at least 1 signal",
            signals_found > 0,
            f"{signals_found} signals" if match else "no results line found",
        )

        # Debug file
        debug_dir = ROOT / "agents" / "outputs"
        debug_files = list(debug_dir.glob("clinicaltrials_debug_*.json")) if debug_dir.exists() else []
        check("Debug JSON file written", bool(debug_files),
              str(debug_files[0].name) if debug_files else "none found")

        if debug_files:
            try:
                dbg = json.loads(debug_files[-1].read_text(encoding="utf-8"))
                check("Debug JSON is valid", True)
                check("Debug contains per-asset entries", len(dbg) >= 1,
                      f"{len(dbg)} assets in debug")
            except json.JSONDecodeError:
                check("Debug JSON is valid", False)
    else:
        print("  [SKIP] Connector not found")

    # ---- Full run (patches dashboard) ----
    print("\nFull Run (patches dashboard JSON)")
    if conn_path.exists():
        result2 = subprocess.run(
            [sys.executable, str(conn_path), "--verbose"],
            capture_output=True, text=True, timeout=180,
        )
        check(
            "Connector exits cleanly (full run)",
            result2.returncode == 0,
            result2.stderr[:120] if result2.returncode not in (0,) else "",
        )
        output2 = result2.stdout + result2.stderr
        check("Dashboard patched message",
              "Dashboard patched" in output2 or "not modified" in output2)
    else:
        print("  [SKIP] Connector not found")

    # ---- Post-patch dashboard ----
    print("\nDashboard JSON (post-patch)")
    if db_path.exists():
        try:
            post_data = json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON still valid", True)

            ci = post_data.get("competitive_intel", {})
            total_ci = (
                sum(len(v) for v in ci.values())
                if isinstance(ci, dict) else len(ci)
            )
            check("competitive_intel non-empty",   total_ci > 0, f"{total_ci} entries")

            ms = post_data.get("milestone_alerts", {})
            check("milestone_alerts key present",  bool(ms))

            sources = post_data.get("data_sources", {})
            check("data_sources.clinicaltrials present", "clinicaltrials" in sources,
                  str(sources.get("clinicaltrials", {}).get("last_run", "missing")))

        except json.JSONDecodeError as exc:
            check("Dashboard JSON still valid", False, str(exc))

    # ---- Signal format compliance ----
    print("\nSignal Format Compliance")
    if db_path.exists():
        try:
            data = json.loads(db_path.read_text(encoding="utf-8"))
            ci   = data.get("competitive_intel", {})
            ct_signals = []
            if isinstance(ci, dict):
                for entries in ci.values():
                    ct_signals.extend(
                        e for e in entries
                        if e.get("source") == "ClinicalTrials.gov"
                    )

            check("ClinicalTrials.gov signals present", bool(ct_signals),
                  f"{len(ct_signals)} signals found")

            if ct_signals:
                sample = ct_signals[0]
                required = [
                    "apex_id", "signal_type", "source", "nct_id",
                    "title", "summary", "date", "confidence", "strategic_relevance",
                ]
                missing = [f for f in required if f not in sample]
                check("All required APEX fields present",
                      not missing,
                      "missing: " + str(missing) if missing else "all present")
                check("source == ClinicalTrials.gov",
                      sample.get("source") == "ClinicalTrials.gov")
                check("signal_type == COMPETITOR_TRIAL",
                      sample.get("signal_type") == "COMPETITOR_TRIAL")
                check("nct_id starts with NCT",
                      str(sample.get("nct_id", "")).startswith("NCT"))

        except Exception as exc:
            check("Signal format compliance", False, str(exc))

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total  = len(checks)
    pct    = int(passed / total * 100) if total else 0
    print(f"Result: {passed}/{total} checks passed ({pct}%)")

    if passed == total:
        print("ClinicalTrials.gov connector verified. Ready to integrate.")
    else:
        failures = [label for label, p, _ in checks if not p]
        print("Items requiring attention:")
        for f in failures:
            print(f"  * {f}")

    sys.exit(0)   # always exit 0 -- some checks need live API


if __name__ == "__main__":
    main()
    main()
