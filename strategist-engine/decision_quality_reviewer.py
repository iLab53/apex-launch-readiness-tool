# decision_quality_reviewer.py
"""Phase 4 agent: Decision Quality Reviewer."""

import json
import re
import anthropic

MODEL = "claude-sonnet-4-6"

DECISION_QUALITY_CRITERIA = {
    "decisiveness":        "Does it clearly say what to do?",
    "resource_allocation": "Does it support budget/headcount/timeline decisions?",
    "prioritization":      "Does it rank what matters most?",
    "business_context":    "Does it say which firms/functions are affected?",
    "non_obvious_insight": "Does it surface patterns beyond aggregation?",
}

_CRITERIA_BLOCK = "\n".join(
    "  - {}: {}".format(k, v) for k, v in DECISION_QUALITY_CRITERIA.items()
)

# Schema of the dict returned by review_decision_quality().
OUTPUT_SCHEMA = {
    "decision_quality_score": "0-100",
    "pass":               "true/false",
    "top_gaps":           "[...]",
    "required_revisions": "[...]",
}

DQ_SYSTEM = (
    "You are a Chief Risk Officer reviewing strategic intelligence briefings "
    "before they reach the Board. Your only job: determine whether this briefing enables real executive decisions (budget, risk, or strategy).\n\n"
    "Full marks only when:\n"
    "- Every priority has an imperative action + timeframe\n"
    "- Priorities are ranked (Critical / High / Monitor)\n"
    "- Business impact is specified (revenue at risk, fine exposure, market shift)\n"
    "- Each section ends with a decision, not a summary\n"
    "- Language is executive-grade: no hedges, no passive voice, no filler\n"
    "- Insights go beyond listing signals -- patterns named\n\n"
    "Respond ONLY with valid JSON -- no preamble, no text outside the JSON."
)

DQ_PROMPT_TEMPLATE = (
    "A decision-quality briefing must satisfy ALL of the following:\n"
    "{criteria_block}\n\n"
    "Score each dimension 0-20:\n"
    "1. actionability       -- imperative verb + explicit timeframe on every recommendation?\n"
    "2. prioritization      -- priorities ranked with Critical/High/Monitor labels?\n"
    "3. impact_specificity  -- business impact (cost, revenue, regulatory risk) specified?\n"
    "4. decision_forcing    -- each section forces a leadership decision vs merely informs?\n"
    "5. executive_brevity   -- free of analyst filler, passive voice, over-hedging?\n"
    "6. non_obvious_insight -- surfaces patterns or connections beyond aggregating signals?\n\n"
    "For each dimension provide one quoted example (or 'not found').\n\n"
    "Also identify:\n"
    "- strengths: 2-3 things done well (15 words max each)\n"
    "- gaps: 2-4 specific weaknesses (15 words max each), or []\n"
    "- required_revisions: concrete 'add X to Y section' actions, or []\n"
    "- reviewer_notes: one-sentence overall assessment\n\n"
    "Return ONLY this JSON (no markdown fences):\n\n"
    "{{\n"
    "  \"dimension_scores\": {{\n"
    "    \"actionability\": 0, \"prioritization\": 0, \"impact_specificity\": 0,\n"
    "    \"decision_forcing\": 0, \"executive_brevity\": 0, \"non_obvious_insight\": 0\n"
    "  }},\n"
    "  \"dimension_evidence\": {{\n"
    "    \"actionability\": \"\", \"prioritization\": \"\", \"impact_specificity\": \"\",\n"
    "    \"decision_forcing\": \"\", \"executive_brevity\": \"\", \"non_obvious_insight\": \"\"\n"
    "  }},\n"
    "  \"strengths\": [],\n"
    "  \"gaps\": [],\n"
    "  \"required_revisions\": [],\n"
    "  \"reviewer_notes\": \"\"\n"
    "}}\n\n"
    "BRIEFING TO EVALUATE:\n"
    "{briefing}"
)


def _parse_verdict(raw):
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    brace_end = cleaned.rfind("}")
    if brace_end != -1:
        cleaned = cleaned[: brace_end + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "decision_quality_score": 0,
            "pass": False,
            "top_gaps": ["DQ reviewer returned unparseable JSON"],
            "required_revisions": [],
            "verdict": "PARSE-ERROR",
            "overall_score": 0,
            "dimension_scores": {},
            "dimension_evidence": {},
            "strengths": [],
            "gaps": ["DQ reviewer returned unparseable JSON"],
            "reviewer_notes": "Reviewer response could not be parsed.",
            "_raw_response": raw[:500],
        }

    scores = data.get("dimension_scores", {})
    raw_total = sum(scores.values())
    max_raw = len(scores) * 20 if scores else 120
    total = round(raw_total / max_raw * 100) if max_raw else 0

    if total >= 80:
        verdict = "DECISION-READY"
    elif total >= 60:
        verdict = "NEEDS-REVISION"
    else:
        verdict = "INSUFFICIENT"

    # Hard failure: weak actions poison the whole briefing regardless of other scores
    if scores.get("actionability", 0) < 10:
        verdict = "INSUFFICIENT"

    gaps = data.get("gaps", [])
    required_revisions = data.get("required_revisions", [])

    return {
        # OUTPUT_SCHEMA fields
        "decision_quality_score": total,
        "pass": verdict == "DECISION-READY",
        "top_gaps": gaps[:3],
        "required_revisions": required_revisions,
        # Full detail
        "verdict": verdict,
        "overall_score": total,
        "dimension_scores": scores,
        "dimension_evidence": data.get("dimension_evidence", {}),
        "strengths": data.get("strengths", []),
        "gaps": gaps,
        "reviewer_notes": data.get("reviewer_notes", ""),
    }


def review_decision_quality(briefing_md, signals):
    """Evaluate whether the briefing supports CFO/CRO decisions.

    Returns a dict conforming to OUTPUT_SCHEMA plus full dimension detail.
    """
    if not briefing_md or briefing_md.startswith("No signals"):
        return {
            "decision_quality_score": 0,
            "pass": False,
            "top_gaps": ["No briefing -- pipeline produced no signals"],
            "required_revisions": [],
            "verdict": "SKIPPED",
            "overall_score": 0,
            "dimension_scores": {},
            "dimension_evidence": {},
            "strengths": [],
            "gaps": ["No briefing -- pipeline produced no signals"],
            "reviewer_notes": "Review skipped: empty briefing.",
        }

    excerpt = briefing_md[:6000]
    if len(briefing_md) > 6000:
        excerpt += "\n\n[... truncated ...]"

    prompt = DQ_PROMPT_TEMPLATE.format(
        criteria_block=_CRITERIA_BLOCK,
        briefing=excerpt,
    )

    print("[DQ Reviewer] Evaluating decision quality...")
    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=DQ_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
    except Exception as e:
        err = str(e)
        return {
            "decision_quality_score": 0,
            "pass": False,
            "top_gaps": ["API call failed: " + err],
            "required_revisions": [],
            "verdict": "ERROR",
            "overall_score": 0,
            "dimension_scores": {},
            "dimension_evidence": {},
            "strengths": [],
            "gaps": ["API call failed: " + err],
            "reviewer_notes": err,
        }

    return _parse_verdict(raw)


if __name__ == "__main__":
    import sys
    from pathlib import Path

    reports = sorted(
        (Path(__file__).parent / "reports").glob("strategist_run_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        print("No JSON reports found -- run the pipeline first.")
        sys.exit(1)

    latest = reports[0]
    print("Reviewing: " + latest.name + "\n")

    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    v = review_decision_quality(
        data.get("executive_briefing", ""),
        data.get("signals", []),
    )

    print("\n" + "=" * 60)
    print("  DECISION QUALITY: {}  ({}/100)  PASS: {}".format(
        v["verdict"], v["decision_quality_score"], v["pass"]))
    print("=" * 60)

    for dim, score in v["dimension_scores"].items():
        bar = "#" * int(score / 2) + "-" * (10 - int(score / 2))
        print("  {:<22} [{}]  {}/20".format(dim, bar, score))

    if v["strengths"]:
        print("\nStrengths:")
        for s in v["strengths"]:
            print("  + " + s)

    if v["top_gaps"]:
        print("\nTop gaps:")
        for g in v["top_gaps"]:
            prin