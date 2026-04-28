# generate_all_scorecards.py -- run from repo root inside your venv
# python generate_all_scorecards.py
# Generates Launch Readiness Scorecards for all APEX assets that
# don't already have a scorecard file in agents/outputs/.

import sys
import json
import importlib
from pathlib import Path

REPO_ROOT  = Path(".").resolve()
AGENTS_OUT = REPO_ROOT / "agents" / "outputs"
ASSET_REG  = REPO_ROOT / "asset-registry" / "apex_assets.json"

# ── Find scorecard_generator.py wherever it lives in the repo ────────────────
def _find_and_import_generator():
    candidates = [
        REPO_ROOT,
        REPO_ROOT / "agents",
        REPO_ROOT / "scorecard",
    ]
    # Also search one level deep
    for d in list(REPO_ROOT.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            candidates.append(d)

    for c in candidates:
        if (c / "scorecard_generator.py").exists():
            if str(c) not in sys.path:
                sys.path.insert(0, str(c))
            print(f"  Found scorecard_generator.py in: {c}")
            return importlib.import_module("scorecard_generator")

    raise ImportError(
        "scorecard_generator.py not found in repo. "
        "Copy it from the workspace folder:\n"
        "  Copy-Item 'C:\\Users\\kaibo\\OneDrive\\Documents\\Claude\\Projects\\AI & Digital Transformation tool\\scorecard_generator.py' ."
    )


def get_all_asset_ids():
    raw    = json.loads(ASSET_REG.read_text(encoding="utf-8"))
    assets = raw.get("assets", raw)
    return [a.get("apex_id") or a.get("asset_id") for a in assets if a.get("apex_id") or a.get("asset_id")]


def already_generated(asset_id):
    return len(sorted(AGENTS_OUT.glob(f"launch_readiness_scorecard_{asset_id}_*.json"))) > 0


def run():
    gen_mod    = _find_and_import_generator()
    generate   = gen_mod.generate_scorecard
    asset_ids  = get_all_asset_ids()

    print(f"Assets found: {asset_ids}")
    print()

    skipped, generated, failed = [], [], []

    for aid in asset_ids:
        if already_generated(aid):
            print(f"  [SKIP]  {aid} -- scorecard already exists")
            skipped.append(aid)
            continue
        try:
            sc = generate(aid)
            print(f"  [OK]    {aid} -- score={sc.get('overall_score')} tier={sc.get('overall_tier')}")
            generated.append(aid)
        except Exception as e:
            print(f"  [FAIL]  {aid} -- {e}")
            failed.append(aid)

    print()
    print("=" * 50)
    print(f"  Generated : {len(generated)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failed)}")
    if failed:
        print(f"  Failed IDs: {failed}")
    print()
    if not failed:
        print("  All scorecards ready.")
        print("  Restart Streamlit and click Refresh Dashboard Data to see the LRS chart.")
    else:
        print("  Re-run for failed assets. Check ANTHROPIC_API_KEY is set.")


if __name__ == "__main__":
    run()
