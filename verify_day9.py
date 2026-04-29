"""
verify_day9.py
==============
Automated Day 9 checklist verification.

Run from the repo root after completing all Day 9 steps:
    python verify_day9.py

Checks:
  [1] hta_events present and non-empty in dashboard JSON
  [2] competitive_intel present and non-empty in dashboard JSON
  [3] render_module_3 stub has been replaced in streamlit_app.py
  [4] render_module_4 stub has been replaced in streamlit_app.py
  [5] streamlit_app.py passes Python syntax check
  [6] HTA event structure has required fields for at least one asset
  [7] Competitive intel structure has required fields for at least one asset
  [8] Both modules have download button code present
"""

import json
import pathlib
import sys

DASHBOARD_PATH = pathlib.Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"
STREAMLIT_PATH = pathlib.Path("dashboard") / "streamlit_app.py"

REQUIRED_HTA_FIELDS = {
    "apex_id", "hta_body", "decision_type",
    "indication", "decision_date", "reimbursement_strategy", "evidence_gap",
}
REQUIRED_INTEL_FIELDS = {
    "apex_id", "threat_event", "function_owner",
    "priority", "action_30d", "kpi", "escalation_flag",
}

checks = []  # list of (label, passed: bool, detail: str)


def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append((label, passed, detail))
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))


def main():
    print("=" * 60)
    print("APEX Day 9 Verification")
    print("=" * 60)

    # ---- Dashboard JSON checks ----
    print("\nDashboard JSON")
    if not DASHBOARD_PATH.exists():
        check("Dashboard JSON exists", False, str(DASHBOARD_PATH))
        # Can't continue JSON checks
        checks.append(("hta_events present", False, "file missing"))
        checks.append(("competitive_intel present", False, "file missing"))
    else:
        with open(DASHBOARD_PATH, encoding="utf-8") as f:
            data = json.load(f)

        hta = data.get("hta_events", {})
        intel = data.get("competitive_intel", {})

        check("hta_events key present in JSON", "hta_events" in data)
        check(
            "hta_events non-empty",
            bool(hta),
            f"{sum(len(v) for v in hta.values())} events across {len(hta)} assets" if hta else "empty",
        )
        check("competitive_intel key present in JSON", "competitive_intel" in data)
        check(
            "competitive_intel non-empty",
            bool(intel),
            f"{sum(len(v) for v in intel.values())} plans across {len(intel)} assets" if intel else "empty",
        )

        # Field structure check — sample first asset
        if hta:
            first_asset = next(iter(hta))
            first_event = hta[first_asset][0] if hta[first_asset] else {}
            missing_hta = REQUIRED_HTA_FIELDS - set(first_event.keys())
            check(
                "HTA event has all required fields",
                not missing_hta,
                f"missing: {missing_hta}" if missing_hta else f"sample asset: {first_asset}",
            )
        else:
            check("HTA event has all required fields", False, "no data to check")

        if intel:
            first_asset = next(iter(intel))
            first_plan = intel[first_asset][0] if intel[first_asset] else {}
            missing_intel = REQUIRED_INTEL_FIELDS - set(first_plan.keys())
            check(
                "Competitive intel plan has all required fields",
                not missing_intel,
                f"missing: {missing_intel}" if missing_intel else f"sample asset: {first_asset}",
            )
        else:
            check("Competitive intel plan has all required fields", False, "no data to check")

    # ---- Streamlit app checks ----
    print("\nStreamlit App")
    if not STREAMLIT_PATH.exists():
        check("streamlit_app.py exists", False, str(STREAMLIT_PATH))
    else:
        content = STREAMLIT_PATH.read_text(encoding="utf-8")

        # Stub replacement
        check(
            "render_module_3 stub replaced",
            "Module 3 body coming in Day 9" not in content
            and "Stub active." not in content.split("def render_module_3")[1].split("def render_module_4")[0]
            if "def render_module_3" in content and "def render_module_4" in content
            else False,
        )
        check(
            "render_module_4 stub replaced",
            "Module 4 body coming in Day 9" not in content
            and "Stub active." not in content.split("def render_module_4")[1].split("def render_module_5")[0]
            if "def render_module_4" in content and "def render_module_5" in content
            else False,
        )

        # Syntax check
        try:
            compile(content, str(STREAMLIT_PATH), "exec")
            check("streamlit_app.py syntax valid", True)
        except SyntaxError as exc:
            check("streamlit_app.py syntax valid", False, str(exc))

        # Download buttons present
        m3_block = (
            content.split("def render_module_3")[1].split("def render_module_4")[0]
            if "def render_module_3" in content and "def render_module_4" in content
            else ""
        )
        m4_block = (
            content.split("def render_module_4")[1].split("def render_module_5")[0]
            if "def render_module_4" in content and "def render_module_5" in content
            else ""
        )
        check(
            "Module 3 has Export HTA Events download button",
            "download_button" in m3_block and "hta" in m3_block.lower(),
        )
        check(
            "Module 4 has Export Playbook download button",
            "download_button" in m4_block and "csv" in m4_block.lower(),
        )
        check(
            "Module 4 has escalation_flag logic",
            "escalation_flag" in m4_block,
        )
        check(
            "Module 4 has multiselect filters",
            "multiselect" in m4_block,
        )

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total = len(checks)
    pct = int(passed / total * 100) if total else 0
    print(f"Result: {passed}/{total} checks passed ({pct}%)")

    if passed == total:
        print("Day 9 verification COMPLETE. Ready to commit.")
        print(
            '\ngit add dashboard/streamlit_app.py comm-ex/outputs/comm_ex_dashboard_ready.json'
        )
        print(
            'git commit -m "feat: add Dashboard Modules 3 & 4 — HTA intelligence and competitive response playbook"'
        )
    else:
        failed = [label for label, p, _ in checks if not p]
        print("FAILED checks:")
        for label in failed:
            print(f"  • {label}")
        sys.exit(1)


if __name__ == "__main__":
    main()
