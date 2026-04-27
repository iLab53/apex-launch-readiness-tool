import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_PATH = Path(__file__).parent / "reports" / "run_memory.jsonl"


def save_run_memory(run_id: str, run_date: str, analytics: dict, decision_review: dict, signals: list[dict]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    region_counts = {}
    for s in signals:
        region = s.get("region", "Other")
        region_counts[region] = region_counts.get(region, 0) + 1

    record = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_date": run_date,
        "total_raw_signals": analytics.get("total_raw_signals", 0),
        "validated_signals": len(signals),
        "flagged_signals": analytics.get("challenge_count", 0),
        "dedup_removed": analytics.get("dedup_removed", 0),
        "decision_quality_score": decision_review.get("decision_quality_score", 0),
        "decision_verdict": decision_review.get("verdict", "UNKNOWN"),
        "region_counts": region_counts,
    }

    with open(MEMORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_run_memory(limit: int = 10) -> list[dict]:
    if not MEMORY_PATH.exists():
        return []

    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    return rows[-limit:]


def build_trend_summary(limit: int = 5) -> dict:
    history = load_run_memory(limit=limit)

    if len(history) < 2:
        return {
            "has_history": False,
            "summary": "Not enough prior runs for trend analysis.",
        }

    latest = history[-1]
    previous = history[-2]

    return {
        "has_history": True,
        "latest_score": latest.get("decision_quality_score", 0),
        "previous_score": previous.get("decision_quality_score", 0),
        "score_change": latest.get("decision_quality_score", 0) - previous.get("decision_quality_score", 0),
        "latest_validated": latest.get("validated_signals", 0),
        "previous_validated": previous.get("validated_signals", 0),
        "validated_change": latest.get("validated_signals", 0) - previous.get("validated_signals", 0),
        "latest_flagged": latest.get("flagged_signals", 0),
        "previous_flagged": previous.get("flagged_signals", 0),
        "flagged_change": latest.get("flagged_signals", 0) - previous.get("flagged_signals", 0),
        "summary": (
            f"Decision quality changed by "
            f"{latest.get('decision_quality_score', 0) - previous.get('decision_quality_score', 0)} points; "
            f"validated signals changed by "
            f"{latest.get('validated_signals', 0) - previous.get('validated_signals', 0)}."
        ),
    }
