"""
verify_day10.py
===============
Automated Day 10 checklist verification.

Run from the repo root after completing all Day 10 steps:
    python verify_day10.py
"""

import json
import pathlib
import sys

DASHBOARD_PATH = pathlib.Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"
STREAMLIT_PATH = pathlib.Path("dashboard") / "streamlit_app.py"

checks = []

def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append((label, passed, detail))
    print("  [{0}] {1}".format(status, label) + (" -- " + detail if detail else ""))


def main():
    print("=" * 60)
    print("APEX Day 10 Verification")
    print("=" * 60)

    # ---- Dashboard JSON ----
    print("\nDashboard JSON")
    if not DASHBOARD_PATH.exists():
        check("Dashboard JSON exists", False, str(DASHBOARD_PATH))
    else:
        with open(DASHBOARD_PATH, encoding="utf-8") as f:
            data = json.load(f)

        ms = data.get("milestone_alerts", {})
        lr = data.get("launch_readiness", {})
        recs = data.get("recs", [])

        check("milestone_alerts present", "milestone_alerts" in data)
        check("milestone_alerts non-empty", bool(ms),
              "{0} milestones across {1} assets".format(
                  sum(len(v) for v in ms.values()), len(ms)) if ms else "empty")
        check("launch_readiness present", "launch_readiness" in data)
        check("launch_readiness non-empty", bool(lr),
              "{0} assets seeded".format(len(lr)) if lr else "empty")
        check("recs key present for GCSO Feed", bool(recs),
              "{0} recs".format(len(recs)) if recs else "empty -- GCSO Immediate Actions will be blank")

        # Spot-check milestone structure
        if ms:
            first_asset = next(iter(ms))
            first_ms = ms[first_asset][0] if ms[first_asset] else {}
            required = {"apex_id", "milestone_type", "milestone_label",
                        "milestone_date", "document_id", "days_to_event"}
            missing = required - set(first_ms.keys())
            check("Milestone has all required fields", not missing,
                  "missing: {0}".format(missing) if missing else "sample: " + first_asset)

    # ---- Streamlit app ----
    print("\nStreamlit App")
    if not STREAMLIT_PATH.exists():
        check("streamlit_app.py exists", False, str(STREAMLIT_PATH))
    else:
        content = STREAMLIT_PATH.read_text(encoding="utf-8")

        m5_block = (
            content.split("def render_module_5")[1].split("def render_sidebar")[0]
            if "def render_module_5" in content and "def render_sidebar" in content
            else ""
        )

        check("render_module_5 stub replaced",
              "coming in Day 10" not in m5_block and "Stub active." not in m5_block)
        check("Portfolio bar chart code present", "px.bar" in m5_block or "bar_chart" in m5_block)
        check("3 summary metrics present", m5_block.count(".metric(") >= 3)
        check("Milestone calendar expanders present", "st.expander" in m5_block)
        check("4-column card layout present", "st.columns" in m5_block)
        check("Get Briefing Doc download button present",
              "download_button" in m5_block and "Briefing" in m5_block)
        check("GCSO Feed expander in sidebar",
              "GCSO Intelligence Feed" in content or "GCSO" in content)
        check("Refresh Dashboard Data button present", "Refresh Dashboard Data" in content)
        check("All 5 modules navigable",
              all("def render_module_{0}".format(i) in content for i in range(1, 6)))

        try:
            compile(content, str(STREAMLIT_PATH), "exec")
            check("streamlit_app.py syntax valid", True)
        except SyntaxError as exc:
            check("streamlit_app.py syntax valid", False, str(exc))

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total  = len(checks)
    pct    = int(passed / total * 100) if total else 0
    print("Result: {0}/{1} checks passed ({2}%)".format(passed, total, pct))

    if passed == total:
        print("Day 10 verification COMPLETE. Ready to commit.")
        print('\ngit add dashboard/streamlit_app.py comm-ex/outputs/comm_ex_dashboard_ready.json')
        print('git commit -m "feat: add Dashboard Module 5, GCSO Feed and refresh -- dashboard complete"')
    else:
        failed = [label for label, p, _ in checks if not p]
        print("FAILED checks:")
        for label in failed:
            print("  * " + label)
        sys.exit(1)


if __name__ == "__main__":
    main()
