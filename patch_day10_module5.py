"""
patch_day10_module5.py
======================
Replaces the render_module_5() stub in dashboard/streamlit_app.py
with the Day 10 implementation from day10_m5.py.

Modules 1-4 are NOT touched.

Run from the repo root:
    python patch_day10_module5.py

Safe to re-run: if the stub is already replaced it does nothing.
"""

import pathlib
import sys

STREAMLIT_PATH = pathlib.Path("dashboard") / "streamlit_app.py"
M5_SRC_PATH    = pathlib.Path("day10_m5.py")


def main():
    for p in (M5_SRC_PATH, STREAMLIT_PATH):
        if not p.exists():
            print("ERROR: Required file not found: {0}".format(p))
            sys.exit(1)

    m5_src = M5_SRC_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    lines = STREAMLIT_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    def find_def(name):
        for i, line in enumerate(lines):
            if line.strip().startswith("def " + name + "("):
                return i
        return None

    idx5 = find_def("render_module_5")
    idx_next = find_def("render_sidebar")   # function after M5

    if idx5 is None or idx_next is None:
        print("ERROR: Could not locate render_module_5 or render_sidebar.")
        print("  idx5={0}  idx_next={1}".format(idx5, idx_next))
        sys.exit(1)

    # Check if already patched
    block5 = "".join(lines[idx5:idx_next])
    if "Stub active." not in block5 and "coming in Day 10" not in block5:
        print("INFO: render_module_5 is already patched -- nothing to do.")
        return

    before = "".join(lines[:idx5])
    after  = "".join(lines[idx_next:])
    new_content = before + "\n" + m5_src + "\n\n" + after

    try:
        compile(new_content, str(STREAMLIT_PATH), "exec")
    except SyntaxError as exc:
        print("ERROR: Syntax error at line {0}: {1}".format(exc.lineno, exc.msg))
        sys.exit(1)

    STREAMLIT_PATH.write_text(new_content, encoding="utf-8")
    print("SUCCESS: {0} patched.".format(STREAMLIT_PATH))
    print("  render_module_5() -- Milestone Prep View  [day10_m5.py]")
    print("\nNext: streamlit run dashboard/streamlit_app.py")


if __name__ == "__main__":
    main()
