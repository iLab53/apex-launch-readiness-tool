# comm_ex_generator.py — Day 1 Diff (Codex Handoff)

**Day 1 | APEX Build Roadmap**  
Generated: 2026-04-27 | Status: IMPLEMENTED — edits live in file

---

## Summary of Changes

Three surgical edits to `comm_ex_generator.py`. No logic removed. All existing tests still pass.

---

## Edit 1 — Asset Registry Import (after `import anthropic`)

```python
# ── Asset Registry (Day 1 addition) ───────────────────────────────────────────
import sys as _sys
import os as _os
_sys.path.insert(0, str(_os.path.join(_os.path.dirname(__file__), "..", "asset-registry")))
try:
    from asset_registry import format_asset_context_for_prompt as _fmt_asset
except ImportError:
    def _fmt_asset(asset_id: str) -> str:  # graceful fallback if registry missing
        return ""
```

**Why:** Adds the asset-registry package to sys.path relative to comm_ex_generator.py's location. The try/except ensures the generator still works if the registry is missing (graceful degradation).

---

## Edit 2 — ASSET_CONTEXT_PLACEHOLDER in PROMPT_TEMPLATE

```python
PROMPT_TEMPLATE = """\
Today is DATE_PLACEHOLDER.

ASSET_CONTEXT_PLACEHOLDER        # ← NEW LINE

You have received the following pharmaceutical regulatory and market intelligence briefing:
...
```

**Why:** Asset context is injected at the top of the prompt, before the briefing, so the model sees the specific asset's stage, competitors, and priorities first. This anchors all 6-10 recommendations to that asset.

---

## Edit 3 — generate_recommendations() signature update

```python
# BEFORE
def generate_recommendations(briefing: str, run_id: str, run_date: str) -> list[dict]:

# AFTER
def generate_recommendations(
    briefing: str,
    run_id: str,
    run_date: str,
    asset_id: str | None = None,   # ← NEW optional parameter
) -> list[dict]:
```

New body logic (added before the `prompt = ...` line):

```python
# ── Asset context injection (Day 1 addition) ───────────────────────────────
if asset_id:
    asset_context = _fmt_asset(asset_id)
    if not asset_context:
        asset_context = f"[Asset context unavailable for {asset_id} — proceeding with portfolio-level analysis]"
else:
    asset_context = "[No specific asset selected — generating portfolio-level recommendations across all 7 APEX assets]"
```

And one additional `.replace()` in the prompt assembly:

```python
prompt = (PROMPT_TEMPLATE
          .replace("DATE_PLACEHOLDER",           run_date)
          .replace("ASSET_CONTEXT_PLACEHOLDER",  asset_context)   # ← NEW
          .replace("BRIEFING_PLACEHOLDER",        briefing)
          ...
```

---

## Edit 4 — run() signature update

```python
# BEFORE
def run(briefing=None, out_dir=OUTPUT_DIR, verbose=True) -> dict:

# AFTER
def run(briefing=None, out_dir=OUTPUT_DIR, verbose=True, asset_id=None) -> dict:
```

`asset_id` is forwarded to `generate_recommendations()`:

```python
recs = generate_recommendations(briefing, run_id, run_date, asset_id=asset_id)
```

---

## Backward Compatibility

- `asset_id` defaults to `None` in both functions → existing callers are unaffected
- When `asset_id=None`, the prompt receives `[No specific asset selected — generating portfolio-level recommendations...]` — still valid
- The `try/except ImportError` on the registry import means the file works even without Day 1 asset-registry/ present

---

## Day 2 Next Step

Wire `--asset APEX-001` flag into `run_comm_ex.py`:

```python
# In run_comm_ex.py argument parser, add:
parser.add_argument("--asset", default=None,
    help="APEX asset ID to scope recommendations (e.g. APEX-002)")

# In main(), pass to run():
result = generator.run(briefing=briefing, asset_id=args.asset)
```
