# APEX Coordinator — Architecture Document
# Version: 1.0  |  Day 7 of 12
# ─────────────────────────────────────────────────────────────────────────────
# This is the canonical design artifact for apex_coordinator.py.
# Commit this file BEFORE giving any implementation task to Codex.
# If Codex drifts, this document is the ground truth to reset from.
# ─────────────────────────────────────────────────────────────────────────────

## Overview

`apex_coordinator.py` is the master orchestrator for the APEX commercial
intelligence platform.  It replaces the simple `coordinator()` call in
`run_apex.py` with a fully orchestrated 6-phase pipeline that:

1. Collects pharma regulatory and market signals
2. Validates signals through HITL and adversarial stress-testing
3. Scores each J&J asset against the latest signals
4. Generates Comm Ex recommendations and updates longitudinal memory
5. Auto-triggers milestone prep documents for imminent events
6. Writes a unified dashboard JSON consumed by the Streamlit dashboard

**CRITICAL**: `apex_coordinator.py` does NOT replace `strategist_hello.py`.
Phase 1 imports `coordinator()` from `strategist_hello` and calls it.
APEX builds on top of STRATEGIST.

---

## File Location

```
06_AI_DIGITAL_TRANSFORM/apex_coordinator.py
```

---

## Path Setup

```python
ROOT_DIR    = Path(__file__).parent                          # repo root
ENGINE_DIR  = ROOT_DIR / "strategist-engine"
COMM_EX_DIR = ROOT_DIR / "comm-ex"
AGENTS_DIR  = ROOT_DIR / "agents"
MEMORY_DIR  = ROOT_DIR / "memory"

sys.path.insert(0, str(ENGINE_DIR))    # for strategist_hello
sys.path.insert(0, str(COMM_EX_DIR))   # for comm_ex_generator
sys.path.insert(0, str(AGENTS_DIR))    # for all APEX agents

DASHBOARD_PATH = COMM_EX_DIR / "outputs" / "comm_ex_dashboard_ready.json"
ASSET_REG_PATH = ROOT_DIR / "asset-registry" / "apex_assets.json"
```

---

## Error Handling Pattern

Every phase function must follow this pattern.  A failing agent MUST NOT
abort the pipeline.  Log to stderr and return a safe empty value.

```python
try:
    from some_agent import run_something
    result = run_something(...)
    if verbose: _ok("Phase N complete")
    return result
except ImportError:
    if verbose: _info("agent not available — skipping")
    return {}    # graceful skip — agent not yet installed
except Exception as exc:
    _warn(f"Phase N failed: {exc}")
    traceback.print_exc(file=sys.stderr)
    return {}    # never raise from a phase
```

---

## Phase Sequence

### Phase 1 — `run_intelligence_engine(verbose) → Optional[dict]`

- Imports `coordinator` from `strategist_hello`
- Calls `coordinator()` and returns the result dict
- On failure: logs warning, returns `None`
- Return type: engine result dict with keys `final_signals`, `briefing`,
  `report_path`, `hitl_output`, `adversarial_output` (structure mirrors
  existing `strategist_hello` output)

### Phase 2 — `run_hitl_and_adversarial(engine_result, verbose) → Optional[dict]`

- Surfaces `hitl_output` and `adversarial_output` from engine_result
- These are already computed inside `coordinator()` — Phase 2 extracts and
  reports them
- Always returns `engine_result` unchanged (pass-through)
- Never aborts the pipeline regardless of what it finds

### Phase 3 — `run_asset_scoring(briefing, assets, verbose) → dict`

- Iterates assets **sequentially** (no parallelism — API rate limit risk)
  - TODO comment: `# TODO: parallelise once API rate limits confirmed`
- For each asset:
  - Always calls `launch_readiness_agent.score_asset(asset, briefing=briefing)`
  - If HTA keywords in briefing → calls `hta_strategy_agent.run_hta_analysis()`
  - If RISK keywords in briefing → calls `competitive_response_agent.run_competitive_response()`
- HTA keywords: `["NICE", "HTA", "ICER", "cost-effectiveness", "QALY", "EUnetHTA"]`
- Risk keywords: `["competitor", "biosimilar", "PDUFA", "competitive threat", "rival"]`
- Return type: `{apex_id: {launch_readiness, hta, competitive_response, status}}`

### Phase 4 — `run_recommendations(briefing, assets, scoring_results, verbose) → dict`

- Calls `comm_ex_generator.run(briefing=briefing, verbose=verbose)`
- After Comm Ex: calls `memory_agent.run_memory_report(asset_id, verbose=False)` per asset
- Return type: `{recs: [...], paths: {...}, memory_deltas: {apex_id: {new, escalated, resolved, stable, trend}}}`

### Phase 5 — `run_milestone_prep_phase(assets, verbose) → dict`

- For each asset: checks `asset["upcoming_milestones"]` list
- Triggers `milestone_prep_agent.run_milestone_prep(apex_id, m_type)` for
  milestones within 30 days
- Milestone date parsing:
  - YYYY-MM-DD → direct parse
  - YYYY-QN → Q1→03-31, Q2→06-30, Q3→09-30, Q4→12-31
- Return type: `{apex_id: [{milestone_type, milestone_label, milestone_date, document_id}]}`

### Phase 6 — `refresh_dashboard(rec_result, scoring_results, milestone_result, verbose) → Path`

- Loads existing `comm_ex_dashboard_ready.json` (preserves legacy keys)
- Writes merged dict with **new keys**:
  - `meta` — `{generated_at, schema_version: "2.0", pipeline: "apex_coordinator"}`
  - `launch_readiness` — `{apex_id: scorecard_summary, ...}`
  - `hta_events` — `{apex_id: hta_result, ...}`
  - `competitive_intel` — `{apex_id: comp_result, ...}`
  - `memory_deltas` — `{apex_id: {new, escalated, resolved, stable, trend}}`
  - `milestone_alerts` — `{apex_id: [triggered_docs]}`
- Preserves legacy keys: `distribution`, `top_risks`, `top_opportunities`
- Returns `Path` to the written file

---

## `apex_run()` Entry Point

```python
def apex_run(
    full:         bool = True,
    comm_ex_only: bool = False,
    engine_only:  bool = False,
    verbose:      bool = True,
) -> dict:
```

**Modes:**

| Flag combination       | Phases run   | Description                         |
|------------------------|-------------|-------------------------------------|
| `full=True` (default)  | 1, 2, 3, 4, 5, 6 | Full 6-phase pipeline            |
| `comm_ex_only=True`    | 3, 4, 5, 6  | Skip signal collection; use latest briefing on disk |
| `engine_only=True`     | 1 only      | Collect signals; no recommendations |

**Return type:**
```python
{
    "run_timestamp":    str,       # "2026-04-28 09:00 UTC"
    "elapsed_seconds":  float,
    "mode":             str,       # "full" | "comm-ex-only" | "engine-only"
    "assets_processed": int,
    "engine_result":    dict | None,
    "scoring_results":  dict,
    "rec_result":       dict,
    "milestone_result": dict,
    "dashboard_path":   str,
}
```

---

## Helper Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `load_assets` | `() → list[dict]` | Load apex_assets.json; return asset list |
| `extract_briefing` | `(engine_result) → Optional[str]` | Pull briefing text from engine dict |
| `load_latest_briefing` | `() → Optional[str]` | Load most recent HTML/JSON briefing from disk |
| `_parse_milestone_date` | `(date_str) → Optional[date]` | Parse YYYY-MM-DD or YYYY-QN |
| `_milestone_within_days` | `(milestone, days=30) → bool` | True if date is between today and today+30 |

---

## Console Output Helpers

```python
def _phase(n: int, name: str) -> None:   # === PHASE N — Name ===
def _ok(text: str) -> None:              # [OK]  text
def _warn(text: str) -> None:            # [!!]  text  (stderr)
def _info(text: str) -> None:            # ···   text
```

---

## Verification Commands

```bash
# 1. Import test
python -c "from apex_coordinator import apex_run, load_assets; print('Import OK')"

# 2. Score specific asset
python run_apex.py --score-asset APEX-004

# 3. Full comm-ex-only run (all 6 phases, no signal collection)
python run_apex.py --comm-ex-only

# 4. Confirm dashboard JSON keys
python -c "import json; d=json.load(open('comm-ex/outputs/comm_ex_dashboard_ready.json')); print(list(d.keys()))"
# Expected: [..., 'launch_readiness', 'hta_events', 'memory_deltas', 'milestone_alerts']
```

---

## Codex Handoff Prompt

> "Implement apex_coordinator.py from apex_coordinator_architecture.md.
> Import coordinator() from strategist_hello for Phase 1.
> Each phase wrapped in try/except logging failures to stderr but continuing.
> Helper functions: load_assets(), extract_briefing(), load_latest_briefing().
> Use pathlib.Path for all file operations.
> Sequential asset scoring in Phase 3 — no asyncio or threading.
> Do not delete or modify strategist_hello.py.
> Also update run_apex.py to call apex_coordinator.apex_run() instead of
> the old phase functions, passing all existing CLI flags through."

---

*APEX Coordinator Architecture v1.0 — Day 7 of 12*
*Update this document when: phase sequence changes, new agents added, return types change*
