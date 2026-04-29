"""
verify_day11.py
===============
Automated Day 11 checklist verification.

Run from the repo root after completing all Day 11 steps:
    python verify_day11.py
"""

import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(".")
checks = []


def check(label, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    checks.append((label, passed, detail))
    print("  [{0}] {1}".format(status, label) + (" -- " + detail if detail else ""))


def main():
    print("=" * 60)
    print("APEX Day 11 Verification")
    print("=" * 60)

    # ---- Nightly script ----
    print("\nnightly_apex_run.py")
    nightly = ROOT / "nightly_apex_run.py"
    check("nightly_apex_run.py exists", nightly.exists())

    if nightly.exists():
        src = nightly.read_text(encoding="utf-8")
        try:
            ast.parse(src)
            check("nightly_apex_run.py syntax valid", True)
        except SyntaxError as e:
            check("nightly_apex_run.py syntax valid", False, str(e))

        check("sys.path insert present (import guard)", "sys.path.insert" in src)
        check("apex_run imported", "from apex_coordinator import apex_run" in src
              or "apex_coordinator" in src)
        check("LOG_PATH defined", "LOG_PATH" in src)
        check("logs/ mkdir present", "mkdir" in src)
        check("ISO timestamp in log format", "isoformat()" in src)
        check("SUCCESS log format", "SUCCESS" in src)
        check("FAILED log format with traceback", "FAILED" in src and "traceback" in src)
        check("--verbose flag handled", "--verbose" in src)

    # ---- Logs directory ----
    print("\nLogs directory")
    logs_dir = ROOT / "logs"
    check("logs/ directory exists", logs_dir.exists() and logs_dir.is_dir())
    gitkeep = logs_dir / ".gitkeep"
    check("logs/.gitkeep present", gitkeep.exists())

    # ---- Codex skills ----
    print("\nCodex Skills")
    skills_dir = ROOT / ".codex" / "skills"
    check(".codex/skills/ directory exists", skills_dir.exists() and skills_dir.is_dir())

    for skill_name in ("apex-run.yaml", "apex-add-asset.yaml", "apex-scorecard.yaml"):
        skill_file = skills_dir / skill_name
        check("{0} exists".format(skill_name), skill_file.exists())

        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            check("{0} has name field".format(skill_name), "name:" in content)
            check("{0} has description field".format(skill_name), "description:" in content)
            has_cmd_or_prompt = "command:" in content or "prompt:" in content
            check("{0} has command or prompt field".format(skill_name), has_cmd_or_prompt)

    # Specific content checks
    if (skills_dir / "apex-run.yaml").exists():
        rc = (skills_dir / "apex-run.yaml").read_text(encoding="utf-8")
        check("apex-run.yaml references run_apex.py", "run_apex.py" in rc)
        check("apex-run.yaml has mode input", "mode" in rc)

    if (skills_dir / "apex-add-asset.yaml").exists():
        ac = (skills_dir / "apex-add-asset.yaml").read_text(encoding="utf-8")
        check("apex-add-asset.yaml has apex_id input", "apex_id" in ac)
        check("apex-add-asset.yaml has brand_name input", "brand_name" in ac)
        check("apex-add-asset.yaml references apex_assets.json", "apex_assets.json" in ac)

    if (skills_dir / "apex-scorecard.yaml").exists():
        sc = (skills_dir / "apex-scorecard.yaml").read_text(encoding="utf-8")
        check("apex-scorecard.yaml references --scorecard flag", "--scorecard" in sc)
        check("apex-scorecard.yaml has apex_id input", "apex_id" in sc)

    # ---- Nightly log (only if a test run was done) ----
    print("\nNightly Log (if test run complete)")
    log_file = logs_dir / "nightly_run.log"
    if log_file.exists() and log_file.stat().st_size > 0:
        last_line = log_file.read_text(encoding="utf-8").strip().splitlines()[-1]
        check("Log file has entries", True, last_line[:80])
        check("Log entry contains SUCCESS or FAILED", "SUCCESS" in last_line or "FAILED" in last_line)
        check("Log entry has timestamp", "T" in last_line and ":" in last_line)
    else:
        check("Log file has entries", False,
              "Run: python nightly_apex_run.py --verbose to generate first log entry")

    # ---- Summary ----
    print("\n" + "=" * 60)
    passed = sum(1 for _, p, _ in checks if p)
    total = len(checks)
    pct = int(passed / total * 100) if total else 0
    print("Result: {0}/{1} checks passed ({2}%)".format(passed, total, pct))

    if passed == total:
        print("Day 11 verification COMPLETE. Ready to commit.")
        print('\ngit add nightly_apex_run.py logs/.gitkeep .codex/skills/')
        print('git commit -m "feat: add nightly automation script and three Codex skills"')
    else:
        failed = [label for label, p, _ in checks if not p]
        print("FAILED checks:")
        for label in failed:
            print("  * " + label)
        sys.exit(1)


if __name__ == "__main__":
    main()
