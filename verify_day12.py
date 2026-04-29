"""
verify_day12.py
===============
Pre-demo validation checklist for Day 12.
Checks the static repo state -- does NOT run the pipeline.

Run from the repo root:
    python verify_day12.py

For full end-to-end pipeline validation, run:
    python run_apex.py --verbose
then re-run this script.
"""

import ast
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(".")
checks = []


def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append((label, passed, detail))
    print("  [{0}] {1}".format(status, label) + (" -- " + detail if detail else ""))


def main():
    print("=" * 60)
    print("APEX Day 12 Pre-Demo Validation")
    print("=" * 60)

    # ---- Python environment ----
    print("\nPython Environment")
    ver = sys.version_info
    check("Python >= 3.10", ver >= (3, 10),
          "{0}.{1}.{2}".format(ver.major, ver.minor, ver.micro))

    # ---- Core files ----
    print("\nCore Files")
    required_files = [
        "apex_coordinator.py",
        "run_apex.py",
        "nightly_apex_run.py",
        "export_gcso_briefing.py",
        "asset-registry/apex_assets.json",
        "comm-ex/outputs/comm_ex_dashboard_ready.json",
        "dashboard/streamlit_app.py",
        ".codex/skills/apex-run.yaml",
        ".codex/skills/apex-add-asset.yaml",
        ".codex/skills/apex-scorecard.yaml",
        "logs/.gitkeep",
    ]
    for f in required_files:
        p = ROOT / f
        check(f + " present", p.exists())

    # ---- Asset registry ----
    print("\nAsset Registry")
    registry_path = ROOT / "asset-registry" / "apex_assets.json"
    if registry_path.exists():
        try:
            raw = json.loads(registry_path.read_text(encoding="utf-8"))
            assets = raw.get("assets", raw) if isinstance(raw, dict) else raw
            check("Asset registry loads as valid JSON", True)
            check("7 assets present", len(assets) == 7,
                  "{0} assets found".format(len(assets)))
        except Exception as e:
            check("Asset registry loads as valid JSON", False, str(e))

    # ---- Dashboard JSON ----
    print("\nDashboard JSON")
    db_path = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
    EXPECTED_KEYS = {
        "meta", "top_risks", "top_opportunities", "launch_readiness",
        "hta_events", "competitive_intel", "memory_deltas",
        "milestone_alerts",
    }
    if db_path.exists():
        try:
            data = json.loads(db_path.read_text(encoding="utf-8"))
            check("Dashboard JSON valid", True)
            present_keys = set(data.keys())
            missing_keys = EXPECTED_KEYS - present_keys
            check("All 8 expected keys present", not missing_keys,
                  "missing: " + str(missing_keys) if missing_keys else "all present")
            check("hta_events non-empty", bool(data.get("hta_events")))
            check("competitive_intel non-empty", bool(data.get("competitive_intel")))
            check("milestone_alerts non-empty", bool(data.get("milestone_alerts")))
            check("launch_readiness non-empty", bool(data.get("launch_readiness")))
            check("memory_deltas present", bool(data.get("memory_deltas")))
        except Exception as e:
            check("Dashboard JSON valid", False, str(e))

    # ---- Memory files ----
    print("\nMemory Files")
    memory_dir = ROOT / "memory"
    if memory_dir.exists():
        mem_files = list(memory_dir.glob("apex_memory_APEX-*.json"))
        check("7 memory files present", len(mem_files) == 7,
              "{0} found".format(len(mem_files)))
        if mem_files:
            try:
                sample = json.loads(mem_files[0].read_text(encoding="utf-8"))
                run_count = sample.get("run_count", 0)
                check("Memory files have run_count", "run_count" in sample,
                      "sample run_count={0}".format(run_count))
            except Exception:
                check("Memory files have run_count", False, "parse error")
    else:
        check("memory/ directory exists", False)

    # ---- Streamlit app ----
    print("\nStreamlit App")
    app_path = ROOT / "dashboard" / "streamlit_app.py"
    if app_path.exists():
        content = app_path.read_text(encoding="utf-8")
        try:
            ast.parse(content)
            check("streamlit_app.py syntax valid", True)
        except SyntaxError as e:
            check("streamlit_app.py syntax valid", False, str(e))

        check("All 5 modules present",
              all("def render_module_{0}".format(i) in content for i in range(1, 6)))
        check("GCSO Feed expander in sidebar", "GCSO" in content)
        check("Refresh Dashboard Data button", "Refresh Dashboard Data" in content)
        check("Module stubs replaced",
              "Stub active." not in content and "coming in Day" not in content)

    # ---- Export briefing script ----
    print("\nExport Script")
    export_path = ROOT / "export_gcso_briefing.py"
    if export_path.exists():
        src = export_path.read_text(encoding="utf-8")
        try:
            ast.parse(src)
            check("export_gcso_briefing.py syntax valid", True)
        except SyntaxError as e:
            check("export_gcso_briefing.py syntax valid", False, str(e))
        check("All 3 briefing sections present",
              "Immediate" in src and "milestone" in src.lower() and "readiness" in src.lower())
        check("Bootstrap CDN referenced", "bootstrap" in src.lower())
        check("CONFIDENTIAL footer present", "CONFIDENTIAL" in src)

    # ---- Nightly log ----
    print("\nNightly Automation")
    log_path = ROOT / "logs" / "nightly_run.log"
    if log_path.exists() and log_path.stat().st_size > 0:
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        last = lines[-1] if lines else ""
        check("Nightly log has entries", bool(lines),
              "{0} total entries".format(len(lines)))
        check("Last log entry is SUCCESS",
              "SUCCESS" in last, last[:80] if last else "empty")
    else:
        check("Nightly log has entries", False,
              "Run: python nightly_apex_run.py --verbose")

    # ---- Codex skills ----
    print("\nCodex Skills")
    for skill in ("apex-run", "apex-add-asset", "apex-scorecard"):
        p = ROOT / ".codex" / "skills" / (skill + ".yaml")
        check(skill + ".yaml present", p.exists())

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total  = len(checks)
    pct    = int(passed / total * 100) if total else 0
    print("Result: {0}/{1} checks passed ({2}%)".format(passed, total, pct))

    if passed == total:
        print("Day 12 validation COMPLETE. System is demo-ready.")
        print("\nFinal steps:")
        print("  python export_gcso_briefing.py")
        print("  git tag -a v1.0 -m \"APEX Pipeline v1.0\"")
        print("  git push origin main --tags")
    else:
        failed = [label for label, p, _ in checks if not p]
        print("Items requiring attention ({0}):".format(len(failed)))
        for label in failed:
            print("  * " + label)
        # Exit 0 on Day 12 -- some checks require a live pipeline run
        # and should not block demo prep.
        print("\nNote: checks marked FAIL that require a pipeline run")
        print("will pass after: python run_apex.py --verbose")


if __name__ == "__main__":
    main()
