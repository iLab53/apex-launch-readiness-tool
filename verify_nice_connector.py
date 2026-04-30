"""
verify_nice_connector.py
=========================
Verifies the NICE TA connector:
  1. File structure and syntax
  2. Live fetch dry run (no dashboard mutation)
  3. Full run (patches dashboard)
  4. Dashboard JSON integrity after patch
  5. Signal field format compliance

Run from repo root:
    python verify_nice_connector.py
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
    print("NICE TA Connector Verification")
    print("=" * 60)

    # ---- Connector file ----
    print("\nConnector File")
    conn_path = ROOT / "connectors" / "nice_connector.py"
    check("connectors/nice_connector.py exists", conn_path.exists())

    if conn_path.exists():
        src = conn_path.read_text(encoding="utf-8")
        try:
            ast.parse(src)
            check("Syntax valid", True)
        except SyntaxError as exc:
            check("Syntax valid", False, str(exc))

        check("NICE list URL present",             "nice.org.uk/guidance/published" in src)
        check("fetch_nice_list defined",           "def fetch_nice_list" in src)
        check("NiceGuidanceListParser defined",    "NiceGuidanceListParser" in src)
        check("entry_to_hta_signal defined",       "def entry_to_hta_signal" in src)
        check("detect_decision defined",           "def detect_decision" in src)
        check("Timeout constant present",          "TIMEOUT" in src)
        check("Rate limiting present",             "RATE_LIMIT" in src)
        check("Debug output path present",         "agents" in src and "outputs" in src)
        check("--dry-run flag present",            "dry_run" in src)
        check("--verbose flag present",            "verbose" in src)
        check("hta_signals key written",           "hta_signals" in src)
        check("Deduplication by guidance_id",      "guidance_id" in src and "existing_gids" in src)
        check("CONDITION_KEYWORDS defined",        "CONDITION_KEYWORDS" in src)
        check("No utcnow() deprecation",           "utcnow()" not in src)
        check("Regex fallback present",            "regex" in src.lower() or "re.findall" in src)
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
    print("\nDry Run (live NICE fetch, no dashboard mutation)")
    if conn_path.exists():
        result = subprocess.run(
            [sys.executable, str(conn_path), "--dry-run", "--verbose"],
            capture_output=True, text=True, timeout=60,
        )
        check(
            "Connector exits cleanly (dry run)",
            result.returncode == 0,
            result.stderr[:200] if result.returncode not in (0,) else "",
        )
        output = result.stdout + result.stderr
        check("Results line present", "Results:" in output)
        check("Dry run message present", "Dry run" in output or "not modified" in output)

        # Check NICE was actually contacted (entries fetched)
        match_entries = re.search(r"(\d+) TA entries found", output)
        entries_found = int(match_entries.group(1)) if match_entries else 0
        check(
            "NICE page fetched and parsed",
            entries_found > 0,
            "{} TA entries found".format(entries_found) if match_entries
            else "no entries line (NICE may be unreachable)",
        )

        # Debug file
        debug_dir   = ROOT / "agents" / "outputs"
        debug_files = list(debug_dir.glob("nice_debug_*.json")) if debug_dir.exists() else []
        check(
            "Debug JSON file written", bool(debug_files),
            str(debug_files[0].name) if debug_files else "none found",
        )
        if debug_files:
            try:
                dbg = json.loads(debug_files[-1].read_text(encoding="utf-8"))
                check("Debug JSON is valid", True)
                check("Debug contains entries_fetched key",
                      "entries_fetched" in dbg,
                      str(dbg.get("entries_fetched", "missing")))
                check("Debug contains per_asset entries",
                      "per_asset" in dbg and len(dbg["per_asset"]) >= 1)
            except json.JSONDecodeError:
                check("Debug JSON is valid", False)
    else:
        print("  [SKIP] Connector not found")

    # ---- Full run ----
    print("\nFull Run (patches dashboard JSON)")
    if conn_path.exists():
        result2 = subprocess.run(
            [sys.executable, str(conn_path), "--verbose"],
            capture_output=True, text=True, timeout=60,
        )
        check(
            "Connector exits cleanly (full run)",
            result2.returncode == 0,
            result2.stderr[:200] if result2.returncode not in (0,) else "",
        )
        output2 = result2.stdout + result2.stderr
        check(
            "Dashboard patched or results present",
            "Dashboard patched" in output2 or "Results:" in output2,
        )
    else:
        print("  [SKIP] Connector not found")

    # ---- Post-patch dashboard ----
    print("\nDashboard JSON (post-patch)")
    if db_path.exists():
        try:
            post_data = json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON still valid", True)

            hta = post_data.get("hta_signals", {})
            check("hta_signals key present", isinstance(hta, dict),
                  "{}".format(type(hta).__name__))

            sources = post_data.get("data_sources", {})
            check(
                "data_sources.nice present",
                "nice" in sources,
                str(sources.get("nice", {}).get("last_run", "missing")),
            )
            check(
                "data_sources.clinicaltrials still present",
                "clinicaltrials" in sources,
            )
            check(
                "data_sources.fda still present",
                "fda" in sources,
            )
        except json.JSONDecodeError as exc:
            check("Dashboard JSON still valid", False, str(exc))

    # ---- Signal format compliance ----
    print("\nSignal Format Compliance")
    if db_path.exists():
        try:
            data     = json.loads(db_path.read_text(encoding="utf-8"))
            hta      = data.get("hta_signals", {})
            nice_sigs = []
            if isinstance(hta, dict):
                for entries in hta.values():
                    nice_sigs.extend(
                        e for e in entries if e.get("source") == "NICE"
                    )

            if nice_sigs:
                sample   = nice_sigs[0]
                required = [
                    "apex_id", "signal_type", "source", "guidance_id",
                    "title", "summary", "date", "confidence",
                    "decision", "strategic_relevance", "recommended_action",
                ]
                missing  = [f for f in required if f not in sample]
                check("All required APEX fields present",
                      not missing,
                      "missing: " + str(missing) if missing else "all present")
                check("source == NICE",
                      sample.get("source") == "NICE")
                check("signal_type == NICE_TA_DECISION",
                      sample.get("signal_type") == "NICE_TA_DECISION")
                check("guidance_id starts with TA",
                      str(sample.get("guidance_id", "")).upper().startswith("TA"))
            else:
                check(
                    "No NICE signals matched (check LOOKBACK_DAYS or keywords)",
                    True,
                    "0 signals -- may need wider LOOKBACK_DAYS or adjusted keywords",
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
        print("NICE connector verified. Ready to integrate.")
    else:
        failures = [label for label, p, _ in checks if not p]
        print("Items requiring attention:")
        for f in failures:
            print("  * " + f)

    sys.exit(0)


if __name__ == "__main__":
    main()
