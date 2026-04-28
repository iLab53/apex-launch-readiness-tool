from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


MEMORY_RUN_LIMIT = 10

# Urgency rank â€” higher number = more urgent
URGENCY_RANK: dict[str, int] = {
    "Immediate (0-30d)": 3,
    "Immediate (0\u201330d)": 3,
    "Near-term (30-90d)": 2,
    "Near-term (30\u201390d)": 2,
    "Strategic (90d+)": 1,
}

MEMORY_DIR = Path(__file__).parent.parent / "memory"
COMM_EX_DIR = Path(__file__).parent.parent / "comm-ex" / "outputs"


def _action_key(rec):
    return rec.get("recommended_action", "")[:50]


def _empty_template(asset_id: str) -> dict:
    return {
        "asset_id": asset_id,
        "brand_name": "",
        "last_updated": "",
        "run_count": 0,
        "recommendation_history": [],
        "delta_summary": {},
    }


def load_memory(asset_id: str) -> dict:
    """
    Read memory/apex_memory_{asset_id}.json.

    Returns the memory dict. If the file does not exist, returns an empty
    template â€” never raises FileNotFoundError.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / f"apex_memory_{asset_id}.json"
    if not path.exists():
        return _empty_template(asset_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_template(asset_id)


def save_memory(asset_id: str, memory_dict: dict) -> None:
    """
    Write the memory dict to memory/apex_memory_{asset_id}.json.
    Creates memory/ if it does not exist.
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / f"apex_memory_{asset_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(memory_dict, f, indent=2, ensure_ascii=False)


def compute_delta(
    prev_recs: list[dict],
    curr_recs: list[dict],
    prev_lrs: Optional[float] = None,
    curr_lrs: Optional[float] = None,
) -> dict:
    """
    Compare two recommendation lists.

    Matches recommendations by the first 50 characters of
    recommended_action (NOT rec_id, which changes every run).
    """
    prev_index = {_action_key(r): r for r in prev_recs}
    curr_keys: set[str] = set()

    new_recs: list[str] = []
    escalated_recs: list[str] = []
    resolved_recs: list[str] = []
    stable_recs: list[str] = []

    for rec in curr_recs:
        key = _action_key(rec)
        curr_keys.add(key)

        if key not in prev_index:
            new_recs.append(key)
        else:
            prev_rec = prev_index[key]
            curr_rank = URGENCY_RANK.get(rec.get("urgency", ""), 0)
            prev_rank = URGENCY_RANK.get(prev_rec.get("urgency", ""), 0)
            if curr_rank > prev_rank:
                escalated_recs.append(key)
            else:
                stable_recs.append(key)

    for key in prev_index:
        if key not in curr_keys:
            resolved_recs.append(key)

    lrs_dropped = (
        prev_lrs is not None
        and curr_lrs is not None
        and (prev_lrs - curr_lrs) > 5
    )
    lrs_rose = (
        prev_lrs is not None
        and curr_lrs is not None
        and (curr_lrs - prev_lrs) > 0
    )

    if escalated_recs or lrs_dropped:
        trend = "DETERIORATING"
    elif not new_recs and not escalated_recs and (lrs_rose or prev_lrs is None):
        trend = "IMPROVING"
    else:
        trend = "STABLE"

    return {
        "new_recs": new_recs,
        "escalated_recs": escalated_recs,
        "resolved_recs": resolved_recs,
        "stable_recs": stable_recs,
        "trend": trend,
    }


def update_memory(
    asset_id: str,
    run_id: str,
    run_date: str,
    new_recs: list[dict],
    lrs_score: Optional[float] = None,
) -> dict:
    """
    Main orchestration function.
    """
    memory = load_memory(asset_id)

    run_record: dict = {
        "run_id": run_id,
        "run_date": run_date,
        "recommendations": new_recs,
        "launch_readiness_score": lrs_score,
    }

    memory["recommendation_history"].append(run_record)
    memory["recommendation_history"] = memory["recommendation_history"][-MEMORY_RUN_LIMIT:]

    history = memory["recommendation_history"]
    if len(history) >= 2:
        prev_run = history[-2]
        curr_run = history[-1]
        prev_recs = prev_run.get("recommendations", [])
        curr_recs = curr_run.get("recommendations", [])
        prev_lrs = prev_run.get("launch_readiness_score")
        curr_lrs = curr_run.get("launch_readiness_score")
        delta = compute_delta(prev_recs, curr_recs, prev_lrs, curr_lrs)
    else:
        delta = {
            "new_recs": [_action_key(r) for r in new_recs],
            "escalated_recs": [],
            "resolved_recs": [],
            "stable_recs": [],
            "trend": "STABLE",
        }

    memory["delta_summary"] = delta
    memory["run_count"] = memory.get("run_count", 0) + 1
    memory["last_updated"] = datetime.now(timezone.utc).isoformat()

    save_memory(asset_id, memory)
    return memory


def get_trend_summary(asset_id: str) -> str:
    memory = load_memory(asset_id)
    run_count = memory.get("run_count", 0)
    brand_name = memory.get("brand_name") or asset_id
    delta = memory.get("delta_summary", {})

    if run_count == 0:
        return (
            f"{brand_name} has not been scored by the pipeline yet. "
            f"Run: python run_apex.py --score-asset {asset_id} to generate the first record."
        )

    trend = delta.get("trend", "STABLE")
    escalated = len(delta.get("escalated_recs", []))
    new_count = len(delta.get("new_recs", []))
    resolved = len(delta.get("resolved_recs", []))

    detail_parts = []
    if escalated:
        detail_parts.append(f"{escalated} escalated recommendation{'s' if escalated != 1 else ''}")
    if new_count:
        detail_parts.append(f"{new_count} new recommendation{'s' if new_count != 1 else ''}")
    if resolved:
        detail_parts.append(f"{resolved} resolved recommendation{'s' if resolved != 1 else ''}")

    detail = (", ".join(detail_parts) + " and ") if detail_parts else ""

    return (
        f"{brand_name} has run {run_count} pipeline cycle{'s' if run_count != 1 else ''}. "
        f"The last delta shows {detail}a {trend} trend."
    )


def run_memory_report(
    asset_id: Optional[str] = None,
    verbose: bool = True,
) -> dict:
    """
    Callable from run_comm_ex.py --memory-report.
    """
    outputs = sorted(COMM_EX_DIR.glob("comm_ex_recommendations_*.json"))
    if not outputs:
        print("  [!!]  No comm ex output files found in comm-ex/outputs/", file=sys.stderr)
        return {}

    with open(outputs[-1], "r", encoding="utf-8") as f:
        data = json.load(f)
    all_recs: list[dict] = data if isinstance(data, list) else data.get("recs", [])

    recs_by_asset: dict[str, list[dict]] = {}
    for rec in all_recs:
        aid = (rec.get("asset_id") or "UNKNOWN").upper()
        if asset_id and aid != asset_id.upper():
            continue
        recs_by_asset.setdefault(aid, []).append(rec)

    if not recs_by_asset:
        target = f" for {asset_id}" if asset_id else ""
        print(f"  [!!]  No recommendations found{target} in latest output.", file=sys.stderr)
        return {}

    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    results: dict[str, dict] = {}

    if verbose:
        print("\n" + "=" * 60)
        print("  APEX MEMORY DELTA REPORT")
        print("=" * 60)

    for aid, recs in recs_by_asset.items():
        if aid == "UNKNOWN":
            continue
        memory = update_memory(aid, run_id, run_date, recs)
        delta = memory.get("delta_summary", {})
        results[aid] = delta

        if verbose:
            print(f"\n  Asset: {aid}")
            print(f"    Run count : {memory['run_count']}")
            print(f"    Trend     : {delta.get('trend', 'STABLE')}")
            print(f"    NEW       : {len(delta.get('new_recs', []))}")
            print(f"    ESCALATED : {len(delta.get('escalated_recs', []))}")
            print(f"    RESOLVED  : {len(delta.get('resolved_recs', []))}")
            print(f"    STABLE    : {len(delta.get('stable_recs', []))}")
            if delta.get("escalated_recs"):
                print(f"    Escalated : {', '.join(delta['escalated_recs'])}")

    if verbose:
        print()

    return results

