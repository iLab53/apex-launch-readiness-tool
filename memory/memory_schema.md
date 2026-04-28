# Memory File Schema — memory/apex_memory_{asset_id}.json
# One file per asset. Appended after every pipeline run.
# History capped at MEMORY_RUN_LIMIT = 10 entries.

```json
{
  "asset_id": "APEX-001",
  "brand_name": "Darzalex",
  "last_updated": "2026-04-27T06:00:00Z",
  "run_count": 4,
  "recommendation_history": [
    {
      "run_id": "run_20260427_001",
      "run_date": "2026-04-27",
      "recommendations": [
        {
          "rec_id": "REC-001",
          "recommended_action": "Accelerate payer pre-approval meetings...",
          "confidence": 0.85,
          "timeline": "Immediate (0-30d)",
          "audience": "Market Access"
        }
      ],
      "launch_readiness_score": 72.5
    }
  ],
  "delta_summary": {
    "new_recs":       ["REC-005"],
    "escalated_recs": ["REC-002"],
    "resolved_recs":  ["REC-001"],
    "stable_recs":    ["REC-003", "REC-004"],
    "trend":          "DETERIORATING"
  }
}
```

## Field Reference

| Field | Type | Description |
|---|---|---|
| `asset_id` | string | APEX asset ID, e.g. "APEX-001" |
| `brand_name` | string | Brand name, populated from asset registry |
| `last_updated` | ISO datetime | Timestamp of last pipeline run |
| `run_count` | int | Total pipeline runs for this asset |
| `recommendation_history` | array | Capped at MEMORY_RUN_LIMIT = 10 |
| `run_id` | string | Unique run identifier |
| `launch_readiness_score` | float or null | Overall LRS score if scorecard was run |
| `delta_summary.trend` | string | IMPROVING \| STABLE \| DETERIORATING |

## Delta Classification Rules

- **NEW** — `recommended_action[:50]` not seen in previous run
- **ESCALATED** — same action key; urgency rank moved up (Strategic → Immediate)
- **RESOLVED** — was in previous run; absent from current run
- **STABLE** — same action key; urgency unchanged or decreased

## Trend Logic

- **DETERIORATING** — any escalated recs, OR LRS score dropped >5 points
- **IMPROVING** — no new/escalated recs, AND LRS score rose (or no score change)
- **STABLE** — all other cases
