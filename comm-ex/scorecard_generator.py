"""
APEX -- Launch Readiness Scorecard Generator
Calls the Director of Launch Excellence Claude agent to produce a
validated Launch Readiness Scorecard for a given asset.
"""

import anthropic
import json
import pathlib
import datetime
import sys
import os

# Add the asset-registry folder to the path so we can import it
_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT / "asset-registry"))

from asset_registry import format_asset_context_for_prompt
from scorecard_validator import validate_scorecard

client = anthropic.Anthropic()

# Path to the Director system prompt created on Day 3
_PROMPT_PATH = _REPO_ROOT / "director_system_prompt.md"


def load_director_prompt():
    """
    Load the Director of Launch Excellence system prompt from the
    markdown file created on Day 3. Strip the heading lines (lines
    starting with # or ---) so only the prompt content is sent.
    """
    if not _PROMPT_PATH.exists():
        # Fallback minimal prompt if file is not found
        print("[WARN] director_system_prompt.md not found. Using minimal fallback.")
        return (
            "You are the Director of Launch Excellence for J&J Innovative Medicine. "
            "Assess commercial launch readiness and return a structured JSON scorecard."
        )
    lines = _PROMPT_PATH.read_text(encoding="utf-8").splitlines()
    content = [
        l for l in lines
        if not l.startswith("#") and not l.strip() == "---"
    ]
    return "\n".join(content).strip()


def _parse_json_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        if len(lines) >= 2:
            raw = "\n".join(lines[1:-1]).strip()

    start = raw.find("{")
    end = raw.rfind("}")

    try:
        if start == -1 or end == -1 or end < start:
            raise json.JSONDecodeError("No JSON object found", raw, 0)
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        debug_path = _REPO_ROOT / "agents" / "outputs" / "debug_scorecard_raw_response.txt"
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(raw, encoding="utf-8")
        raise ValueError(
            "Could not parse scorecard JSON. See agents/outputs/debug_scorecard_raw_response.txt"
        ) from exc


def generate_scorecard(asset_id: str) -> dict:
    """
    Ask the Director agent to generate a Launch Readiness Scorecard.

    Args:
        asset_id: APEX asset ID string, e.g. 'APEX-002'

    Returns:
        Validated scorecard dict (status VALID or CORRECTED).

    Raises:
        ValueError if the scorecard fails hard validation.
        KeyError if asset_id is not in the registry.
    """
    # Step 1: load asset context from the registry
    asset_context = format_asset_context_for_prompt(asset_id)
    system_prompt = load_director_prompt()
    today = datetime.date.today().isoformat()

    print(f"[SCORECARD] Generating for {asset_id}...")

    # Step 2: build the user message
    user_message = f"""
ASSET CONTEXT:
{asset_context}

Today's date: {today}

Generate a Launch Readiness Scorecard for this asset as valid JSON.
The JSON must have exactly these top-level fields:
  asset_id        Ã¢â‚¬â€ string, must equal "{asset_id}"
  overall_score   Ã¢â‚¬â€ number 0-100
  overall_tier    Ã¢â‚¬â€ one of: LAUNCH-READY, ON-TRACK, AT-RISK, NOT-READY
  dimensions      Ã¢â‚¬â€ array of exactly 8 objects

Each dimension object must include:
  dimension         Ã¢â‚¬â€ one of the 8 canonical names listed below
  score             Ã¢â‚¬â€ number 0-100
  rationale         Ã¢â‚¬â€ at least 20 characters of signal-grounded reasoning
  gap_closing_action Ã¢â‚¬â€ at least 15 characters describing the action needed

The 8 canonical dimension names (use exactly):
  market_access, medical_affairs, marketing_brand, commercial_operations,
  regulatory_compliance, patient_support, competitive_positioning, supply_distribution

Return ONLY valid JSON. No markdown fences. No explanation outside the JSON.
"""

    # Step 3: call the Claude API with the Director system prompt
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()

    # Step 4: parse the JSON
    scorecard = _parse_json_response(raw)

    # Step 6: guarantee asset_id is set (even if Claude forgot it)
    scorecard["asset_id"] = asset_id

    # Step 7: validate and auto-correct via the validator
    result = validate_scorecard(scorecard)

    if result["status"] == "ERROR":
        print("[SCORECARD] Validation FAILED:")
        for err in result["errors"]:
            print(f"  {err['message']}")
        raise ValueError("Scorecard failed validation — see errors above.")

    if result["status"] == "CORRECTED":
        n = len(result["errors"])
        print(f"[SCORECARD] Auto-corrected {n} issue(s):")
        for err in result["errors"]:
            print(f"  {err['message']}")

    print(f"[SCORECARD] Status: {result['status']}")

    # Step 8: save output (runs for both VALID and CORRECTED)
    output_dir = _REPO_ROOT / "agents" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"launch_readiness_scorecard_{asset_id}_{today}.json"
    filepath = output_dir / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result["scorecard"], f, indent=2)

    print(f"[SCORECARD] Saved -> {filepath}")
    return result["scorecard"]

