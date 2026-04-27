# Asset Registry — Function Signatures (Codex Handoff)

**Day 1 | APEX Build Roadmap**  
Generated: 2026-04-27 | Status: IMPLEMENTED — files live, ready for Codex review

---

## Files Delivered

| File | Purpose |
|------|---------|
| `asset-registry/apex_assets.json` | 7 J&J assets, full schema |
| `asset-registry/asset_registry.py` | 5 functions + CLI |
| `asset-registry/__init__.py` | Package init |

---

## Function Signatures

```python
# asset_registry.py

def load_assets() -> dict:
    """
    Load apex_assets.json (cached per process).
    Returns full registry: { version, last_updated, assets: [...] }
    Raises FileNotFoundError if apex_assets.json is missing.
    """

def get_asset(asset_id: str) -> dict | None:
    """
    Retrieve one asset by APEX ID (case-insensitive).
    Returns asset dict or None.
    Examples: get_asset("APEX-001"), get_asset("apex-007")
    """

def filter_by_ta(therapeutic_area: str) -> list[dict]:
    """
    Filter assets by therapeutic area (case-insensitive).
    Valid values: "Oncology", "Immunology", "Neuroscience"
    """

def filter_by_stage(lifecycle_stage: str) -> list[dict]:
    """
    Filter assets by lifecycle stage (case-insensitive).
    Valid values: "PRE-LAUNCH", "LAUNCH", "POST-LAUNCH"
    """

def format_asset_context_for_prompt(asset_id: str) -> str:
    """
    Primary Claude API integration point.
    Returns a structured text block for prompt injection.
    Returns "" if asset_id not found (caller proceeds with generic context).
    """
```

---

## Asset Schema (each entry in apex_assets.json)

```json
{
  "asset_id":           "APEX-001",
  "brand_name":         "Darzalex",
  "generic_name":       "daratumumab",
  "indication":         "Multiple Myeloma",
  "therapeutic_area":   "Oncology",
  "lifecycle_stage":    "POST-LAUNCH",
  "formulations":       ["IV", "SC (Darzalex Faspro)"],
  "regulatory_status":  { "FDA": "Approved", "EMA": "Approved", "NICE": "..." },
  "key_competitors":    ["..."],
  "comm_ex_priorities": ["..."],
  "medical_affairs_focus": ["..."],
  "market_access_focus":   ["..."],
  "key_messages":       ["..."],
  "notes":              "..."
}
```

---

## Quick Verification

Run these from `06_AI_DIGITAL_TRANSFORM/`:

```bash
# Test 1 — module imports
python -c "from asset_registry.asset_registry import load_assets; r = load_assets(); print(f'{len(r[\"assets\"])} assets loaded')"

# Test 2 — get single asset
python -c "from asset_registry.asset_registry import get_asset; a = get_asset('APEX-002'); print(a['brand_name'], a['lifecycle_stage'])"

# Test 3 — filter by TA
python -c "from asset_registry.asset_registry import filter_by_ta; print([a['brand_name'] for a in filter_by_ta('Oncology')])"

# Test 4 — prompt injection
python -c "from asset_registry.asset_registry import format_asset_context_for_prompt; print(format_asset_context_for_prompt('APEX-005'))"

# Test 5 — CLI
python asset-registry/asset_registry.py --list
```

---

## Codex Task

If you are Codex picking up this file:

1. Run the 5 verification commands above — all should pass cleanly
2. If any fail, check `sys.path` and that `asset-registry/` is in the Python path from the working directory
3. No new code needed for Day 1 — implementation is complete
4. Day 2 task: Wire `asset_id` parameter into `run_comm_ex.py` CLI (`--asset APEX-001` flag)
