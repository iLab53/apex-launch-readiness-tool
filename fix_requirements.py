# fix_requirements.py -- run from repo root inside your venv
# python fix_requirements.py
# Reads requirements.txt regardless of encoding, rewrites as clean UTF-8,
# and ensures streamlit and plotly are present.

from pathlib import Path

p = Path("requirements.txt")

# Try encodings in order until one works
content = None
for enc in ("utf-16", "utf-8-sig", "utf-8", "cp1252"):
    try:
        content = p.read_text(encoding=enc)
        print(f"Read with encoding: {enc}")
        break
    except Exception:
        continue

if content is None:
    print("ERROR: could not read requirements.txt with any known encoding")
    raise SystemExit(1)

# Normalise line endings, strip blank lines
lines = [l.rstrip() for l in content.splitlines()]
lines = [l for l in lines if l.strip()]

# Ensure streamlit and plotly are present (add if missing)
has_streamlit = any("streamlit" in l.lower() for l in lines)
has_plotly    = any("plotly" in l.lower() for l in lines)

if not has_streamlit:
    lines.append("streamlit>=1.30.0")
    print("Added: streamlit>=1.30.0")
else:
    print("OK: streamlit already present")

if not has_plotly:
    lines.append("plotly>=5.18.0")
    print("Added: plotly>=5.18.0")
else:
    print("OK: plotly already present")

# Write back as clean UTF-8, one package per line, no blank lines
p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nRewritten as UTF-8: {len(lines)} packages total")
