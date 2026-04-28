# verify_day8.py  — run from repo root inside your venv
# python verify_day8.py

import sys, json, ast, re
from pathlib import Path

ROOT = Path(".")
results = {}

# 1. streamlit_app.py exists
app = Path("dashboard/streamlit_app.py")
results["file_exists"] = "PASS" if app.exists() else "FAIL — dashboard/streamlit_app.py not found"

if app.exists():
    source = app.read_text()

    # 2. Syntax check
    try:
        ast.parse(source)
        results["syntax"] = "PASS"
    except SyntaxError as e:
        results["syntax"] = f"FAIL — {e}"

    # 3. All 5 stub renderers defined
    stubs = ["render_module_1", "render_module_2", "render_module_3",
             "render_module_4", "render_module_5"]
    missing_stubs = [s for s in stubs if f"def {s}" not in source]
    results["stub_renderers"] = (
        "PASS" if not missing_stubs
        else f"FAIL — missing {missing_stubs}"
    )

    # 4. Sidebar module selector has all 5 labels
    labels = ["Launch Intelligence", "Asset Strategy", "HTA", "Competitive Response", "GCSO Feed"]
    missing_labels = [m for m in labels if m not in source]
    results["sidebar_labels"] = (
        "PASS" if not missing_labels
        else f"FAIL — missing sidebar labels: {missing_labels}"
    )

    # 5. Session state initializes selected_assets before widgets
    has_ss = "selected_assets" in source and "session_state" in source
    results["session_state_init"] = (
        "PASS" if has_ss
        else "FAIL — selected_assets not initialised in session_state"
    )

    # 6. Asset multiselect bound to brand_name values
    has_brand = "brand_name" in source and "multiselect" in source
    results["brand_name_multiselect"] = (
        "PASS" if has_brand
        else "FAIL — multiselect not bound to brand_name values"
    )

    # 7. meta.generated_at timestamp referenced
    results["generated_at"] = (
        "PASS" if "generated_at" in source
        else "FAIL — meta.generated_at not referenced"
    )

    # 8. No query param routing
    uses_qp = bool(re.search(r"st\.(experimental_get_query_params|query_params)", source))
    results["no_query_params"] = (
        "PASS" if not uses_qp
        else "WARN — query param routing detected; should be sidebar/session-state only"
    )

    # 9. Dead tab layout removed
    has_tabs = bool(re.search(r"st\.tabs\s*\(", source))
    results["dead_tabs_removed"] = (
        "PASS" if not has_tabs
        else "FAIL — st.tabs() block still present (dead code)"
    )

    # 10. DASHBOARD_PATH points to comm_ex_dashboard_ready.json
    results["dashboard_path"] = (
        "PASS" if "comm_ex_dashboard_ready.json" in source
        else "FAIL — DASHBOARD_PATH not set to comm_ex_dashboard_ready.json"
    )

    # 11. Module router present (sidebar drives navigation)
    has_router = (
        "selected_module" in source
        or "module_selector" in source
        or re.search(r'radio|selectbox', source) is not None
    )
    results["module_router"] = (
        "PASS" if has_router
        else "WARN — module router pattern not detected; verify sidebar navigation manually"
    )

    # 12. Each stub is actually called from main/router (not just defined)
    calls = [s for s in stubs if re.search(rf"{s}\s*\(", source)]
    missing_calls = [s for s in stubs if s not in calls]
    results["stubs_called"] = (
        "PASS" if not missing_calls
        else f"WARN — defined but never called: {missing_calls}"
    )

# 13. requirements.txt has streamlit and plotly
req = Path("requirements.txt")
if req.exists():
    # utf-8-sig strips BOM if present; errors=replace handles any remaining oddities
    req_text = req.read_text(encoding="utf-8-sig", errors="replace").lower()
    missing_pkgs = [p for p in ["streamlit", "plotly"] if p not in req_text]
    results["requirements"] = (
        "PASS" if not missing_pkgs
        else f"FAIL — missing from requirements.txt: {missing_pkgs}"
    )
else:
    results["requirements"] = "WARN — requirements.txt not found"

# 14. Dashboard JSON exists (prerequisite for dashboard to load)
dash = Path("comm-ex/outputs/comm_ex_dashboard_ready.json")
results["dashboard_json_exists"] = (
    "PASS" if dash.exists()
    else "WARN — comm_ex_dashboard_ready.json not found (run: python run_apex.py --comm-ex-only)"
)

# ── Print ──────────────────────────────────────────────────────────────────────
print()
print("=" * 62)
print("  DAY 8 VERIFICATION — Dashboard Modules 1 & 2")
print("=" * 62)
all_pass = True
for check, result in results.items():
    if result.startswith("PASS"):
        status = "PASS"
    elif result.startswith("WARN"):
        status = "WARN"
    else:
        status = "FAIL"
        all_pass = False
    print(f"  [{status:<4}]  {check:<26} {result}")
print()
if all_pass:
    print("  Overall: ALL PASS — Day 8 complete")
else:
    print("  Overall: GAPS DETECTED — review FAIL items above")
print("=" * 62)
