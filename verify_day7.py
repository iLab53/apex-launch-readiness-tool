# verify_day7.py  -- run from repo root inside your venv
# python verify_day7.py

import sys, json, inspect
from pathlib import Path
from datetime import datetime

ROOT = Path(".")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "strategist-engine"))
sys.path.insert(0, str(ROOT / "comm-ex"))
sys.path.insert(0, str(ROOT / "agents"))

results = {}

# 1. Import apex_coordinator
try:
    from apex_coordinator import (
        apex_run, load_assets, extract_briefing,
        load_latest_briefing, _parse_milestone_date,
        _milestone_within_days, _phase, _ok, _warn, _info,
    )
    results["import"] = "PASS"
except Exception as e:
    results["import"] = "FAIL: " + str(e)

# 2. load_assets returns 7 assets
try:
    assets = load_assets()
    count = len(assets)
    results["load_assets"] = ("PASS: " + str(count) + " assets") if count == 7 else ("FAIL: expected 7, got " + str(count))
except Exception as e:
    results["load_assets"] = "FAIL: " + str(e)

# 3. All assets have required keys
try:
    required = {"apex_id", "asset_id", "brand_name", "therapeutic_area",
                "asset_stage", "upcoming_milestones"}
    bad = [a.get("apex_id", a.get("asset_id", "?")) for a in assets
           if not required.issubset(a.keys())]
    results["asset_schema"] = "PASS" if not bad else "FAIL: missing keys on " + str(bad)
except Exception as e:
    results["asset_schema"] = "FAIL: " + str(e)

# 4. Quarter date parser returns correct datetime values
try:
    cases = {
        "2026-Q1": datetime(2026, 3, 31),
        "2026-Q2": datetime(2026, 6, 30),
        "2026-Q3": datetime(2026, 9, 30),
        "2026-Q4": datetime(2026, 12, 31),
        "2026-07-15": datetime(2026, 7, 15),
    }
    failures = []
    for k, expected in cases.items():
        got = _parse_milestone_date(k)
        # Compare as strings to handle date vs datetime subclass difference
        if str(got)[:10] != str(expected)[:10]:
            failures.append(k + " -> got " + str(got))
    results["date_parser"] = "PASS" if not failures else "FAIL: " + str(failures)
except Exception as e:
    results["date_parser"] = "FAIL: " + str(e)

# 5. apex_run signature has correct params
try:
    sig = inspect.signature(apex_run)
    params = set(sig.parameters.keys())
    expected = {"full", "comm_ex_only", "engine_only", "verbose"}
    missing = expected - params
    results["apex_run_signature"] = "PASS" if not missing else "FAIL: missing " + str(missing)
except Exception as e:
    results["apex_run_signature"] = "FAIL: " + str(e)

# 6. run_comm_ex.py references apex_coordinator
try:
    # Support both naming conventions
    entry = None
    for name in ("run_apex.py", "run_comm_ex.py"):
        candidate = Path(name)
        if candidate.exists():
            entry = candidate
            break
    if entry is None:
        results["run_apex_wired"] = "FAIL: neither run_apex.py nor run_comm_ex.py found"
    else:
        source = entry.read_text(encoding="utf-8", errors="replace")
        uses_new = "apex_coordinator" in source or "apex_run" in source
        uses_old_only = ("from strategist_hello import coordinator" in source
                         and "apex_coordinator" not in source)
        if uses_new and not uses_old_only:
            results["run_apex_wired"] = "PASS: " + entry.name + " references apex_coordinator"
        else:
            results["run_apex_wired"] = "FAIL: " + entry.name + " does not call apex_coordinator"
except Exception as e:
    results["run_apex_wired"] = "FAIL: " + str(e)

# 7. Dashboard JSON exists with Phase 6 keys
try:
    dash = Path("comm-ex/outputs/comm_ex_dashboard_ready.json")
    if dash.exists():
        d = json.loads(dash.read_text(encoding="utf-8"))
        needed = {"launch_readiness", "hta_events", "competitive_intel",
                  "memory_deltas", "milestone_alerts"}
        missing_keys = needed - d.keys()
        results["dashboard_json"] = ("PASS" if not missing_keys
                                     else "WARN: missing keys " + str(missing_keys))
    else:
        results["dashboard_json"] = "WARN: file not found -- run: python run_comm_ex.py --comm-ex-only"
except Exception as e:
    results["dashboard_json"] = "FAIL: " + str(e)

# 8. apex_coordinator.py exists at repo root
results["file_exists"] = ("PASS" if Path("apex_coordinator.py").exists()
                          else "FAIL: apex_coordinator.py not found at repo root")

# -- Print results -------------------------------------------------------------
print()
print("=" * 64)
print("  DAY 7 VERIFICATION -- APEX Coordinator")
print("=" * 64)
all_pass = True
for check, result in results.items():
    if result.startswith("PASS"):
        status = "PASS"
    elif result.startswith("WARN"):
        status = "WARN"
    else:
        status = "FAIL"
        all_pass = False
    print("  [" + status + "]" + " " * (6 - len(status)) + check.ljust(26) + result)
print()
print("  Overall: ALL PASS -- Day 7 complete" if all_pass
      else "  Overall: GAPS DETECTED -- review FAIL items above")
print("=" * 64)
