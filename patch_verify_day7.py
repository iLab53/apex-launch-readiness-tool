# patch_verify_day7.py — run from repo root inside your venv
# python patch_verify_day7.py
# Fixes two issues in verify_day7.py:
#   1. Required asset keys updated to match actual registry schema
#   2. Date comparison updated to use datetime (not date) to match _parse_milestone_date return type

from pathlib import Path

p = Path("verify_day7.py")
src = p.read_text()

# Fix 1 — correct required keys
old_keys = 'required = {"apex_id", "brand_name", "therapeutic_area", "asset_stage", "upcoming_milestones"}'
new_keys = 'required = {"apex_id", "asset_id", "brand_name", "therapeutic_area", "asset_stage", "upcoming_milestones"}'
if old_keys in src:
    src = src.replace(old_keys, new_keys)
    print("Patched: required asset keys")
else:
    print("SKIP: required keys line not found — may already be patched or formatted differently")

# Fix 2 — import datetime alongside date
old_import = "from datetime import date"
new_import = "from datetime import date, datetime"
if old_import in src and "from datetime import date, datetime" not in src:
    src = src.replace(old_import, new_import)
    print("Patched: datetime import")
else:
    print("SKIP: datetime import already correct")

# Fix 3 — replace date(...) comparisons with datetime(...)
replacements = [
    ('date(2026, 3, 31)', 'datetime(2026, 3, 31)'),
    ('date(2026, 6, 30)', 'datetime(2026, 6, 30)'),
    ('date(2026, 9, 30)', 'datetime(2026, 9, 30)'),
    ('date(2026, 12, 31)', 'datetime(2026, 12, 31)'),
    ('date(2026, 7, 15)', 'datetime(2026, 7, 15)'),
]
for old, new in replacements:
    if old in src:
        src = src.replace(old, new)
        print(f"Patched: {old} -> {new}")

p.write_text(src)
print()
print("verify_day7.py patched successfully.")
