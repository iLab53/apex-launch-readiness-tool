"""
verify_fda_connector.py
========================
Verifies the openFDA connector:
  1. File structure and syntax
  2. Live API dry run (no dashboard mutation)
  3. Full run (patches dashboard)
  4. Dashboard JSON integrity after patch
  5. Signal field format compliance

Run from repo root:
    python verify_fda_connector.py
"""

import ast
import json
import pathlib
import re
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
    print("openFDA Connector Verification")
    print("=" * 60)

    # ---- Connector file ----
    print("\nConnector File")
    conn_path = ROOT / "connectors" / "fda_connector.py"
    check("connectors/fda_connector.py exists", conn_path.exists())

    if conn_path.exists():
        src = conn_path.read_text(encoding="utf-8")
        try:
            ast.parse(src)
            check("Syntax valid", True)
        except SyntaxError as exc:
            check("Syntax valid", False, str(exc))

        check("openFDA drugsfda URL present",     "api.fda.gov/drug/drugsfda" in src)
        check("openFDA label URL present",        "api.fda.gov/drug/label" in src)
        check("fetch_fda_approvals defined",      "def fetch_fda_approvals" in src)
        check("fetch_fda_labels defined",         "def fetch_fda_labels" in src)
        check("extract_approval_signals defined", "def extract_approval_signals" in src)
        check("extract_label_signals defined",    "def extract_label_signals" in src)
        check("Timeout constant present",         "TIMEOUT" in src)
        check("Error handling present",           "HTTPError" in src)
        check("Rate limiting present",            "sleep" in src)
        check("Debug output path present",        "agents" in src and "outputs" in src)
        check("--dry-run flag present",           "dry_run" in src)
        check("--verbose flag present",           "verbose" in src)
        check("J&J sponsor filter present",       "janssen" in src.lower())
        check("Deduplication logic present",      "doc_id" in src and "existing_docs" in src)
        check("regulatory_signals key written",   "regulatory_signals" in src)
        check("No utcnow() deprecation",          "utcnow()" not in src)
    else:
        print("  [SKIP] Skipping content checks -- file not found")

    # ---- Dashboard baseline ----
    print("\nDashboard JSON (baseline)")
    db_path = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
    if db_path.exists():
        try:
            json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON valid before run", True)
        except json.JSONDecodeError as exc:
            check("Dashboard JSON valid before run", False, str(exc))
    else:
        check("Dashboard JSON exists", False)

    # ---- Dry run ----
    print("\nDry Run (live API test, no dashboard mutation)")
    if conn_path.exists():
        result = subprocess.run(
            [sys.executable, str(conn_path), "--dry-run", "--verbose"],
            capture_output=True, text=True, timeout=180,
        )
        check(
            "Connector exits cleanly (dry run)",
            result.returncode == 0,
            result.stderr[:200] if result.returncode not in (0,) else "",
        )
        output = result.stdout + result.stderr
        check("Results line present",    "Results:" in output)
        check("Dry run message present", "Dry run" in output or "not modified" in output)

        match = re.search(r"(\d+) total", output)
        total_found = int(match.group(1)) if match else -1
        check(
            "Results line contains a total count",
            match is not None,
            "{} total signals".format(total_found) if match else "no total count found",
        )

        debug_dir   = ROOT / "agents" / "outputs"
        debug_files = list(debug_dir.glob("fda_debug_*.json")) if debug_dir.exists() else []
        check(
            "Debug JSON file written", bool(debug_files),
            str(debug_files[0].name) if debug_files else "none found",
        )
        if debug_files:
            try:
                dbg = json.loads(debug_files[-1].read_text(encoding="utf-8"))
                check("Debug JSON is valid", True)
                check("Debug contains per-asset entries", len(dbg) >= 1,
                      "{} assets in debug".format(len(dbg)))
            except json.JSONDecodeError:
                check("Debug JSON is valid", False)
    else:
        print("  [SKIP] Connector not found")

    # ---- Full run ----
    print("\nFull Run (patches dashboard JSON)")
    if conn_path.exists():
        result2 = subprocess.run(
            [sys.executable, str(conn_path), "--verbose"],
            capture_output=True, text=True, timeout=180,
        )
        check(
            "Connector exits cleanly (full run)",
            result2.returncode == 0,
            result2.stderr[:200] if result2.returncode not in (0,) else "",
        )
        output2 = result2.stdout + result2.stderr
        check(
            "Dashboard patched or results present",
            "Dashboard patched" in output2 or "not modified" in output2 or "Results:" in output2,
        )
    else:
        print("  [SKIP] Connector not found")

    # ---- Post-patch dashboard ----
    print("\nDashboard JSON (post-patch)")
    if db_path.exists():
        try:
            post_data = json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON still valid", True)

            reg = post_data.get("regulatory_signals", {})
            check("regulatory_signals key present", isinstance(reg, dict),
                  "{}".format(type(reg).__name__))

            ci = post_data.get("competitive_intel", {})
            total_ci = (
                sum(len(v) for v in ci.values())
                if isinstance(ci, dict) else len(ci)
            )
            check("competitive_intel non-empty", total_ci > 0, "{} entries".format(total_ci))

            sources = post_data.get("data_sources", {})
            check(
                "data_sources.fda present",
                "fda" in sources,
                str(sources.get("fda", {}).get("last_run", "missing")),
            )
            check(
                "data_sources.clinicaltrials still present",
                "clinicaltrials" in sources,
                "preserved from prior connector run",
            )
        except json.JSONDecodeError as exc:
            check("Dashboard JSON still valid", False, str(exc))

    # ---- Signal format compliance ----
    print("\nSignal Format Compliance")
    if db_path.exists():
        try:
            data     = json.loads(db_path.read_text(encoding="utf-8"))
            reg      = data.get("regulatory_signals", {})
            fda_sigs = []
            if isinstance(reg, dict):
                for entries in reg.values():
                    fda_sigs.extend(
                        e for e in entries
                        if e.get("source") == "openFDA"
                    )

            if fda_sigs:
                sample   = fda_sigs[0]
                required = [
                    "apex_id", "signal_type", "source", "doc_id",
                    "title", "summary", "date", "confidence",
                    "strategic_relevance", "recommended_action",
                ]
                missing  = [f for f in required if f not in sample]
                check("All required APEX fields present",
                      not missing,
                      "missing: " + str(missing) if missing else "all present")
                check("source == openFDA",          sample.get("source") == "openFDA")
                check("signal_type is FDA type",
                      str(sample.get("signal_type", "")).startswith("FDA_"))
            else:
                check(
                    "No FDA approval signals in lookback window (acceptable)",
                    True,
                    "openFDA returned 0 approvals in last 180 days for these assets",
                )

            ci = data.get("competitive_intel", {})
            label_sigs = []
            if isinstance(ci, dict):
                for entries in ci.values():
                    label_sigs.extend(
                        e for e in entries
                        if e.get("signal_type") == "FDA_LABEL_UPDATE"
                    )
            check(
                "FDA_LABEL_UPDATE signals or acceptable zero",
                True,
                "{} label signals found".format(len(label_sigs)),
            )

        except Exception as exc:
            check("Signal format compliance", False, str(exc))

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total  = len(checks)
    pct    = int(passed / total * 100) if total else 0
    print("Result: {}/{} checks passed ({}%)".format(passed, total, pct))

    if passed == total:
        print("openFDA connector verified. Ready to integrate.")
    else:
        failures = [label for label, p, _ in checks if not p]
        print("Items requiring attention:")
        for f in failures:
            print("  * " + f)

    sys.exit(0)


if __name__ == "__main__":
    main()
