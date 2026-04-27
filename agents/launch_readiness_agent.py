import json
import re
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from agents.output_validator import validate_output


MODEL = "claude-sonnet-4-6"

THIS_FILE = Path(__file__).resolve()
AGENTS_DIR = THIS_FILE.parent
PROJECT_ROOT = AGENTS_DIR.parent
ASSET_REGISTRY_PATH = PROJECT_ROOT / "asset-registry" / "asset_registry.py"
PROMPT_PATH = AGENTS_DIR / "launch_readiness_prompt.txt"
SCHEMA_PATH = AGENTS_DIR / "launch_readiness_schema.md"
STRATEGIST_REPORTS_DIR = PROJECT_ROOT / "strategist-engine" / "reports"
AGENT_OUTPUT_DIR = AGENTS_DIR / "outputs"
COMM_EX_OUTPUT_DIR = PROJECT_ROOT / "comm-ex" / "outputs"

SYSTEM_PROMPT = """\
You are the Director of Commercialization Excellence AI & Digital Transformation
at Johnson & Johnson Innovative Medicine.

Return exactly one valid JSON object matching the provided schema.
Do not wrap the JSON in markdown fences.
Do not invent placeholder values, mock scores, or dummy evidence.
If evidence is limited, lower confidence and explain why in the rationale fields.
Return ONLY this exact top-level shape:
{
  "asset_id": "...",
  "brand_name": "...",
  "run_date": "...",
  "overall_score": 0,
  "overall_tier": "...",
  "dimensions": [
    {
      "dimension": "...",
      "score": 0,
      "rationale": "...",
      "gap_closing_action": "..."
    }
  ]
}
Do not nest asset under "asset".
Do not use "scorecard_id".
Do not add extra top-level objects.
"""


def _load_asset_registry_module():
    spec = spec_from_file_location("asset_registry", ASSET_REGISTRY_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load asset registry module from {ASSET_REGISTRY_PATH}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _save_debug_response(text: str) -> Path:
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    debug_path = AGENT_OUTPUT_DIR / "debug_raw_response.txt"
    debug_path.write_text(text, encoding="utf-8")
    return debug_path


def _extract_largest_json_object(text: str) -> str | None:
    start_positions = [match.start() for match in re.finditer(r"\{", text)]
    end_positions = [match.start() for match in re.finditer(r"\}", text)]
    candidates = []

    for start in start_positions:
        for end in reversed(end_positions):
            if end < start:
                break
            candidate = text[start:end + 1].strip()
            if candidate:
                candidates.append(candidate)
                break

    if not candidates:
        return None
    return max(candidates, key=len)


def _parse_json_object(text: str) -> dict:
    debug_path = _save_debug_response(text)
    cleaned = _strip_markdown_fences(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        repaired = _extract_largest_json_object(cleaned)
        if repaired is None:
            raise ValueError(
                f"Could not parse Claude JSON response. See raw response at {debug_path}"
            )
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse Claude JSON response after repair. "
                f"See raw response at {debug_path}"
            ) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Claude returned JSON, but it was not an object.")
    return parsed


def _load_latest_briefing() -> str | None:
    if not STRATEGIST_REPORTS_DIR.exists():
        return None

    for report_path in sorted(STRATEGIST_REPORTS_DIR.glob("strategist_run_*.json"), reverse=True):
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        briefing = payload.get("executive_briefing", "")
        if isinstance(briefing, str) and len(briefing.strip()) > 200:
            return briefing.strip()
    return None


def _quarter_string(dt: datetime) -> str:
    quarter = ((dt.month - 1) // 3) + 1
    return f"{dt.year}Q{quarter}"


def _build_prompt(asset: dict, asset_context: str, briefing: str, today: str, quarter: str) -> str:
    persona_constraints = PROMPT_PATH.read_text(encoding="utf-8").strip()
    schema_text = SCHEMA_PATH.read_text(encoding="utf-8").strip()
    asset_json = json.dumps(asset, indent=2, ensure_ascii=False)

    return f"""Today is {today}.

{persona_constraints}

ASSET CONTEXT
=============
{asset_context}

ASSET RECORD (JSON)
===================
{asset_json}

REGULATORY / MARKET BRIEFING
============================
{briefing}

SCHEMA
======
Ignore any richer or nested scorecard format in the reference material below.
Use it only as business context for scoring logic, not as the response shape.

Validator-required output schema:
{{
  "asset_id": "{asset.get('asset_id', '')}",
  "brand_name": "{asset.get('brand_name', '')}",
  "run_date": "{today}",
  "overall_score": number,
  "overall_tier": "LAUNCH-READY | ON-TRACK | AT-RISK | NOT-READY",
  "dimensions": [
    {{
      "dimension": "market_access",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "medical_affairs",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "marketing_brand",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "commercial_operations",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "regulatory_compliance",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "patient_support",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "competitive_positioning",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }},
    {{
      "dimension": "supply_distribution",
      "score": number,
      "rationale": string,
      "gap_closing_action": string
    }}
  ]
}}

Exactly 8 dimension objects are required, one for each canonical dimension above.
Do not add any other top-level keys.
Do not output nested objects such as "asset", "evaluation", "overall", or "dimensions" as a map.

Reference material:
{schema_text}

OUTPUT RULES
============
- Return exactly one JSON object matching the validator-required schema above.
- Use the asset's real details and the provided briefing as evidence.
- Do not include markdown fences, commentary, or explanatory text outside JSON.
- Set `asset_id` to "{asset.get('asset_id', '')}" and `brand_name` to "{asset.get('brand_name', '')}".
- Set `run_date` to "{today}".
- Ground all rationales, gaps, and recommendations in the supplied signals and asset context.
- Do not use placeholder text, mock data, or hardcoded default scores.
- Do not use `scorecard_id`.
- Do not nest asset information under `asset`.
- Do not add extra top-level objects.
"""


def _save_outputs(scorecard: dict, asset_id: str, run_date: str) -> None:
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    COMM_EX_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dated_path = AGENT_OUTPUT_DIR / f"launch_readiness_scorecard_{asset_id}_{run_date}.json"
    latest_path = COMM_EX_OUTPUT_DIR / f"lrs_{asset_id}_latest.json"
    body = json.dumps(scorecard, indent=2, ensure_ascii=False)

    dated_path.write_text(body, encoding="utf-8")
    latest_path.write_text(body, encoding="utf-8")


def score_launch_readiness(asset_id, briefing=None) -> dict:
    load_dotenv(PROJECT_ROOT / ".env")

    asset_registry = _load_asset_registry_module()
    asset = asset_registry.get_asset(asset_id)
    if asset is None:
        raise ValueError(f"Unknown asset_id: {asset_id}")

    if briefing is None:
        briefing = _load_latest_briefing()
    if not briefing:
        raise RuntimeError("No briefing provided and no strategist briefing could be loaded.")

    asset_context = asset_registry.format_asset_context_for_prompt(asset["asset_id"])
    now = datetime.now(timezone.utc)
    run_date = now.strftime("%Y-%m-%d")
    quarter = _quarter_string(now)
    prompt = _build_prompt(
        asset=asset,
        asset_context=asset_context,
        briefing=briefing,
        today=run_date,
        quarter=quarter,
    )

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=6000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    data = _parse_json_object(message.content[0].text)
    data = validate_output(data)
    _save_outputs(data, asset["asset_id"], run_date)
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate a launch readiness scorecard.")
    parser.add_argument("asset_id", help="APEX asset ID, e.g. APEX-001")
    parser.add_argument("--briefing-file", type=Path, help="Optional path to a briefing text file")
    args = parser.parse_args()

    briefing_text = None
    if args.briefing_file:
        briefing_text = args.briefing_file.read_text(encoding="utf-8")

    result = score_launch_readiness(args.asset_id, briefing=briefing_text)
    print(json.dumps(result, ensure_ascii=False))

