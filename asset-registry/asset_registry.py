"""
asset_registry.py — APEX Asset Registry
----------------------------------------
Loads and queries the J&J Innovative Medicine asset database (apex_assets.json).
Provides formatted asset context for injection into Claude API prompts.

Functions:
    load_assets()                        -> dict
    get_asset(asset_id)                  -> dict | None
    filter_by_ta(therapeutic_area)       -> list[dict]
    filter_by_stage(lifecycle_stage)     -> list[dict]
    format_asset_context_for_prompt(asset_id) -> str
"""

import json
import os
from pathlib import Path
from typing import Optional

# ── Registry path ──────────────────────────────────────────────────────────────
_REGISTRY_PATH = Path(__file__).parent / "apex_assets.json"

# ── Module-level cache (loaded once per process) ───────────────────────────────
_REGISTRY_CACHE: Optional[dict] = None


def load_assets() -> dict:
    """
    Load the full asset registry from apex_assets.json.
    Caches the result in memory to avoid redundant disk reads.

    Returns:
        dict: Full registry dict with 'version', 'last_updated', and 'assets' list.

    Raises:
        FileNotFoundError: If apex_assets.json does not exist at expected path.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    global _REGISTRY_CACHE
    if _REGISTRY_CACHE is None:
        if not _REGISTRY_PATH.exists():
            raise FileNotFoundError(
                f"Asset registry not found at: {_REGISTRY_PATH}\n"
                "Ensure apex_assets.json is in the asset-registry/ directory."
            )
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            _REGISTRY_CACHE = json.load(f)
    return _REGISTRY_CACHE


def get_asset(asset_id: str) -> Optional[dict]:
    """
    Retrieve a single asset by its APEX asset ID.

    Args:
        asset_id: Asset identifier, e.g. "APEX-001" or "APEX-007".
                  Case-insensitive.

    Returns:
        dict: Asset record, or None if not found.
    """
    registry = load_assets()
    asset_id_upper = asset_id.upper().strip()
    for asset in registry.get("assets", []):
        if asset.get("asset_id", "").upper() == asset_id_upper:
            return asset
    return None


def filter_by_ta(therapeutic_area: str) -> list:
    """
    Return all assets matching a therapeutic area (case-insensitive).

    Args:
        therapeutic_area: One of "Oncology", "Immunology", "Neuroscience".

    Returns:
        list[dict]: Matching asset records (may be empty).
    """
    registry = load_assets()
    ta_lower = therapeutic_area.lower().strip()
    return [
        asset for asset in registry.get("assets", [])
        if asset.get("therapeutic_area", "").lower() == ta_lower
    ]


def filter_by_stage(lifecycle_stage: str) -> list:
    """
    Return all assets at a given lifecycle stage (case-insensitive).

    Args:
        lifecycle_stage: One of "PRE-LAUNCH", "LAUNCH", "POST-LAUNCH".

    Returns:
        list[dict]: Matching asset records (may be empty).
    """
    registry = load_assets()
    stage_upper = lifecycle_stage.upper().strip()
    return [
        asset for asset in registry.get("assets", [])
        if asset.get("lifecycle_stage", "").upper() == stage_upper
    ]


def format_asset_context_for_prompt(asset_id: str) -> str:
    """
    Build a structured text block describing a specific asset for injection
    into a Claude API prompt. Returns an empty string if the asset is not found
    (caller should proceed with generic context).

    This is the primary integration point between the asset registry and
    comm_ex_generator.py. The output is appended to PROMPT_TEMPLATE before
    the Claude API call.

    Args:
        asset_id: APEX asset ID, e.g. "APEX-002".

    Returns:
        str: Formatted context block, or "" if asset_id is unknown.

    Example output:
        === ASSET CONTEXT ===
        Asset: Carvykti (ciltacabtagene autoleucel) | APEX-002
        Therapeutic Area: Oncology | Stage: LAUNCH
        Indication: Relapsed/Refractory Multiple Myeloma
        ...
    """
    asset = get_asset(asset_id)
    if asset is None:
        return ""

    lines = [
        "=== ASSET CONTEXT ===",
        f"Asset: {asset['brand_name']} ({asset['generic_name']}) | {asset['asset_id']}",
        f"Therapeutic Area: {asset['therapeutic_area']} | Stage: {asset['lifecycle_stage']}",
        f"Indication: {asset['indication']}",
        f"Formulations: {', '.join(asset.get('formulations', []))}",
        "",
        "Regulatory Status:",
    ]
    for agency, status in asset.get("regulatory_status", {}).items():
        lines.append(f"  • {agency}: {status}")

    lines += [
        "",
        "Key Competitors:",
        *[f"  • {c}" for c in asset.get("key_competitors", [])],
        "",
        "Comm Ex Priorities:",
        *[f"  • {p}" for p in asset.get("comm_ex_priorities", [])],
        "",
        "Medical Affairs Focus:",
        *[f"  • {m}" for m in asset.get("medical_affairs_focus", [])],
        "",
        "Market Access Focus:",
        *[f"  • {a}" for a in asset.get("market_access_focus", [])],
        "",
        "Approved Key Messages:",
        *[f"  {i+1}. {msg}" for i, msg in enumerate(asset.get("key_messages", []))],
        "",
        f"Notes: {asset.get('notes', '')}",
        "=== END ASSET CONTEXT ===",
    ]

    return "\n".join(lines)


# ── CLI utility (python asset_registry.py APEX-001) ───────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python asset_registry.py <ASSET_ID>")
        print("       python asset_registry.py --list")
        print("       python asset_registry.py --ta Oncology")
        print("       python asset_registry.py --stage LAUNCH")
        sys.exit(0)

    arg = sys.argv[1]

    if arg == "--list":
        registry = load_assets()
        print(f"APEX Asset Registry v{registry['version']} ({registry['last_updated']})")
        print(f"{'ID':<12} {'Brand':<15} {'TA':<15} {'Stage':<12} {'Indication'}")
        print("-" * 80)
        for a in registry["assets"]:
            print(f"{a['asset_id']:<12} {a['brand_name']:<15} {a['therapeutic_area']:<15} "
                  f"{a['lifecycle_stage']:<12} {a['indication'][:40]}")

    elif arg == "--ta":
        ta = sys.argv[2] if len(sys.argv) > 2 else ""
        assets = filter_by_ta(ta)
        print(f"Assets in {ta}: {len(assets)} found")
        for a in assets:
            print(f"  {a['asset_id']} — {a['brand_name']} ({a['lifecycle_stage']})")

    elif arg == "--stage":
        stage = sys.argv[2] if len(sys.argv) > 2 else ""
        assets = filter_by_stage(stage)
        print(f"Assets at stage {stage}: {len(assets)} found")
        for a in assets:
            print(f"  {a['asset_id']} — {a['brand_name']} ({a['therapeutic_area']})")

    else:
        context = format_asset_context_for_prompt(arg)
        if context:
            print(context)
        else:
            print(f"Asset '{arg}' not found. Run with --list to see all assets.")
