"""
patch_day9_modules.py
=====================
Replaces the render_module_3() and render_module_4() stub bodies in
dashboard/streamlit_app.py with the Day 9 implementations stored in
day9_m3.py and day9_m4.py.

Modules 1, 2, and 5 are NOT touched.

Run from the repo root:
    python patch_day9_modules.py

Safe to re-run: if stubs are already replaced it does nothing.
"""

import pathlib
import sys

STREAMLIT_PATH = pathlib.Path("dashboard") / "streamlit_app.py"
M3_SRC_PATH    = pathlib.Path("day9_m3.py")
M4_SRC_PATH    = pathlib.Path("day9_m4.py")


def main():
    # -- Locate implementation source files --
    for p in (M3_SRC_PATH, M4_SRC_PATH, STREAMLIT_PATH):
        if not p.exists():
            print(f"ERROR: Required file not found: {p}")
            print("Make sure you ran the Copy-Item commands for all three files.")
            sys.exit(1)

    m3_src = M3_SRC_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"
    m4_src = M4_SRC_PATH.read_text(encoding="utf-8").rstrip("\n") + "\n"

    # -- Read the target file --
    lines = STREAMLIT_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    # -- Locate function boundaries --
    def find_def(name):
        for i, line in enumerate(lines):
            if line.strip().startswith("def " + name + "("):
                return i
        return None

    idx3 = find_def("render_module_3")
    idx4 = find_def("render_module_4")
    idx5 = find_def("render_module_5")

    if None in (idx3, idx4, idx5):
        print("ERROR: Could not locate render_module_3/4/5 in streamlit_app.py")
        print("  idx3={0}  idx4={1}  idx5={2}".format(idx3, idx4, idx5))
        sys.exit(1)

    # -- Check if already patched --
    block3 = "".join(lines[idx3:idx4])
    block4 = "".join(lines[idx4:idx5])
    if ("Stub active." not in block3 and "coming in Day 9" not in block3
            and "Stub active." not in block4 and "coming in Day 9" not in block4):
        print("INFO: Modules 3 and 4 are already patched -- nothing to do.")
        return

    # -- Build patched content --
    before = "".join(lines[:idx3])
    after  = "".join(lines[idx5:])
    new_content = before + "\n" + m3_src + "\n\n" + m4_src + "\n\n" + after

    # -- Syntax check before writing --
    try:
        compile(new_content, str(STREAMLIT_PATH), "exec")
    except SyntaxError as exc:
        print("ERROR: Syntax error in patched result at line {0}: {1}".format(exc.lineno, exc.msg))
        sys.exit(1)

    STREAMLIT_PATH.write_text(new_content, encoding="utf-8")
    print("SUCCESS: {0} patched.".format(STREAMLIT_PATH))
    print("  render_module_3() -- HTA & Market Access  [day9_m3.py]")
    print("  render_module_4() -- Competitive Response [day9_m4.py]")
    print("\nNext: streamlit run dashboard/streamlit_app.py")


if __name__ == "__main__":
    main()
