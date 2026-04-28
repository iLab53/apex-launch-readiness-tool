# fix_asset_registry.py — run from repo root inside your venv
# python fix_asset_registry.py

import json
from pathlib import Path

p = Path("asset-registry/apex_assets.json")
raw = json.loads(p.read_text())

# The file is { "version": "1.0.0", "last_updated": "...", "assets": [...] }
assets = raw["assets"]

stage_map = {
    "pre-launch":  "PRE-LAUNCH",
    "pre launch":  "PRE-LAUNCH",
    "launch":      "LAUNCH",
    "post-launch": "POST-LAUNCH",
    "post launch": "POST-LAUNCH",
    "approved":    "POST-LAUNCH",
    "marketed":    "POST-LAUNCH",
    "phase 3":     "PRE-LAUNCH",
    "phase3":      "PRE-LAUNCH",
    "phase iii":   "PRE-LAUNCH",
    "phase ii":    "PRE-LAUNCH",
    "filed":       "PRE-LAUNCH",
    "nda filed":   "PRE-LAUNCH",
    "bla filed":   "PRE-LAUNCH",
}

for i, asset in enumerate(assets):
    # Add apex_id mapped from existing asset_id if missing
    if "apex_id" not in asset:
        existing_id = asset.get("asset_id", "")
        # If asset_id already looks like APEX-001, use it; otherwise generate
        if existing_id.upper().startswith("APEX-"):
            asset["apex_id"] = existing_id.upper()
        else:
            asset["apex_id"] = f"APEX-{i+1:03d}"

    # Add asset_stage mapped from lifecycle_stage if missing
    if "asset_stage" not in asset:
        raw_stage = asset.get("lifecycle_stage", "").lower().strip()
        asset["asset_stage"] = stage_map.get(raw_stage, raw_stage.upper() if raw_stage else "POST-LAUNCH")

    # Add upcoming_milestones placeholder if missing
    if "upcoming_milestones" not in asset:
        asset["upcoming_milestones"] = []

# Write back the full structure (preserves version, last_updated, etc.)
raw["assets"] = assets
p.write_text(json.dumps(raw, indent=2))

print(f"Updated {len(assets)} assets in {p}")
print()
print(f"  {'apex_id':<12} {'brand_name':<22} {'asset_stage':<16} {'lifecycle_stage':<20} milestones")
print(f"  {'-'*12} {'-'*22} {'-'*16} {'-'*20} ----------")
for a in assets:
    print(f"  {a['apex_id']:<12} {a['brand_name']:<22} {a['asset_stage']:<16} {a.get('lifecycle_stage',''):<20} {len(a['upcoming_milestones'])}")
