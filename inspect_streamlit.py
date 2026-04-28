# inspect_streamlit.py -- run from repo root inside your venv
# python inspect_streamlit.py

import re
from pathlib import Path

src = Path("dashboard/streamlit_app.py").read_text(encoding="utf-8", errors="replace")
lines = src.splitlines()

print("=" * 64)
print("  streamlit_app.py -- content inspection")
print("=" * 64)
print(f"  Total lines: {len(lines)}")
print()

# 1. All def statements
defs = [(i+1, l.strip()) for i, l in enumerate(lines) if l.strip().startswith("def ")]
print(f"  FUNCTIONS DEFINED ({len(defs)}):")
for ln, d in defs:
    print(f"    line {ln:>4}: {d}")
print()

# 2. session_state references
ss_lines = [(i+1, l.strip()) for i, l in enumerate(lines) if "session_state" in l]
print(f"  SESSION_STATE REFERENCES ({len(ss_lines)}):")
for ln, l in ss_lines[:10]:
    print(f"    line {ln:>4}: {l[:90]}")
if len(ss_lines) > 10:
    print(f"    ... and {len(ss_lines)-10} more")
print()

# 3. Sidebar / module selector
sidebar_lines = [(i+1, l.strip()) for i, l in enumerate(lines)
                 if any(kw in l for kw in ["sidebar", "selectbox", "radio", "multiselect", "module"])]
print(f"  SIDEBAR / MODULE LINES ({len(sidebar_lines)}):")
for ln, l in sidebar_lines[:15]:
    print(f"    line {ln:>4}: {l[:90]}")
if len(sidebar_lines) > 15:
    print(f"    ... and {len(sidebar_lines)-15} more")
print()

# 4. DASHBOARD_PATH or dashboard JSON reference
dash_lines = [(i+1, l.strip()) for i, l in enumerate(lines)
              if any(kw in l for kw in ["DASHBOARD", "dashboard_ready", "generated_at", "comm_ex"])]
print(f"  DASHBOARD PATH / META REFERENCES ({len(dash_lines)}):")
for ln, l in dash_lines[:10]:
    print(f"    line {ln:>4}: {l[:90]}")
print()

# 5. First 30 lines
print("  FIRST 30 LINES:")
for i, l in enumerate(lines[:30], 1):
    print(f"    {i:>4}: {l}")
print()

# 6. requirements.txt
req = Path("requirements.txt")
if req.exists():
    print("  requirements.txt CONTENT:")
    for l in req.read_text(encoding="utf-8", errors="replace").splitlines():
        print(f"    {l}")
