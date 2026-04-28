# inspect_dashboard_json.py -- run from repo root inside your venv
# python inspect_dashboard_json.py
# Shows exactly what keys and sample data are in comm_ex_dashboard_ready.json

import json
from pathlib import Path

p = Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"

if not p.exists():
    print("ERROR: comm_ex_dashboard_ready.json not found.")
    print("Run: python run_comm_ex.py --comm-ex-only")
    raise SystemExit(1)

d = json.loads(p.read_text(encoding="utf-8"))

print("=" * 60)
print("  comm_ex_dashboard_ready.json -- structure inspection")
print("=" * 60)
print(f"  Top-level keys: {list(d.keys())}")
print()

for key, val in d.items():
    if isinstance(val, list):
        print(f"  [{key}]  list of {len(val)} items")
        if val:
            first = val[0]
            if isinstance(first, dict):
                print(f"    first item keys: {list(first.keys())}")
                for k2, v2 in first.items():
                    preview = str(v2)[:60]
                    print(f"      {k2}: {preview}")
    elif isinstance(val, dict):
        print(f"  [{key}]  dict with keys: {list(val.keys())}")
        for k2, v2 in val.items():
            if isinstance(v2, dict):
                print(f"    {k2}: dict keys {list(v2.keys())[:4]}")
            elif isinstance(v2, list):
                print(f"    {k2}: list of {len(v2)}")
            else:
                print(f"    {k2}: {str(v2)[:60]}")
    else:
        print(f"  [{key}]  {type(val).__name__}: {str(val)[:60]}")
    print()

# Specific check for launch_readiness / scorecard
for check_key in ("launch_readiness", "scorecard", "scorecards", "lrs", "asset_scores"):
    if check_key in d:
        print(f"  FOUND key '{check_key}'")
    else:
        print(f"  NOT FOUND: '{check_key}'")

# Check agents/outputs for scorecard files
agents_out = Path("agents") / "outputs"
if agents_out.exists():
    sc_files = sorted(agents_out.glob("launch_readiness_scorecard_*.json"))
    print(f"\n  Scorecard files in agents/outputs: {len(sc_files)}")
    for f in sc_files:
        print(f"    {f.name}")
else:
    print("\n  agents/outputs directory not found")
