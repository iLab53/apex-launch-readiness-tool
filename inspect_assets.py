# inspect_assets.py — run from repo root inside your venv
# python inspect_assets.py

import json
from pathlib import Path

p = Path("asset-registry/apex_assets.json")
raw = json.loads(p.read_text())

print("Top-level type:", type(raw).__name__)
print()

if isinstance(raw, dict):
    print("Top-level keys:", list(raw.keys()))
    print()
    for key, val in raw.items():
        print(f"  [{key}]  type={type(val).__name__}  ", end="")
        if isinstance(val, list):
            print(f"len={len(val)}")
            if val:
                print(f"    First item type: {type(val[0]).__name__}")
                if isinstance(val[0], dict):
                    print(f"    First item keys: {list(val[0].keys())}")
                else:
                    print(f"    First item value: {repr(val[0])[:80]}")
        else:
            print(repr(val)[:80])

elif isinstance(raw, list):
    print(f"List length: {len(raw)}")
    print()
    if raw:
        print(f"First item type: {type(raw[0]).__name__}")
        if isinstance(raw[0], dict):
            print(f"First item keys: {list(raw[0].keys())}")
            print()
            print("First item full content:")
            print(json.dumps(raw[0], indent=2))
        else:
            print(f"First item value: {repr(raw[0])[:200]}")
            print()
            print("All items:")
            for item in raw:
                print(f"  {repr(item)[:100]}")
