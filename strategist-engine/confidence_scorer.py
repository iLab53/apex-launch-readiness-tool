"""
NAVIGATOR -- Confidence Scorer
Deterministic 3-factor formula. No LLM calls.
"""
import datetime

TIER_WEIGHTS = {"TIER_1": 1.0, "TIER_2": 0.8, "TIER_3": 0.6}
TIER_3_CAP   = 0.60

def score_signal(signal: dict) -> dict:
    tier    = TIER_WEIGHTS.get(signal.get("source_tier", "TIER_3"), 0.6)
    urls    = len(signal.get("corroboration_urls", []))
    corr    = 1.0 if urls == 0 else (1.2 if urls == 1 else 1.4)
    pub     = signal.get("publication_date", "")
    try:
        days = (datetime.date.today() - datetime.date.fromisoformat(pub)).days
        recency = 1.0 if days <= 7 else (0.85 if days <= 30 else 0.70)
    except (ValueError, TypeError):
        recency = 0.7
    raw   = (tier * 0.50) + (corr * 0.30) + (recency * 0.20)
    final = min(1.0, raw)
    if signal.get("source_tier") == "TIER_3":
        final = min(final, TIER_3_CAP)
    signal["confidence_score"]     = round(final, 3)
    signal["confidence_rationale"] = (
        f"tier={tier:.2f}*0.50 + corr={corr:.2f}*0.30 + recency={recency:.2f}*0.20={raw:.3f}"
        + (f" (capped at {TIER_3_CAP})" if signal.get("source_tier") == "TIER_3" else "")
    )
    return signal
