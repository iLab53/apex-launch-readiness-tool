"""
STRATEGIST -- Adversarial Reviewer
Receives an APPROVED signal and looks for reasons to downgrade it.
Returns CONFIRM, CHALLENGE, or REJECT with reasoning.
"""
import anthropic, json

client = anthropic.Anthropic()

ADVERSARIAL_PROMPT = """You are the Adversarial Reviewer for STRATEGIST.
Your job is to find weaknesses in the following intelligence signal.
Be skeptical. Look for:
  - Source credibility issues (is this domain actually authoritative for this claim?)
  - Missing corroboration (a single source making a significant claim)
  - Implausible statistics or claims that are suspiciously precise
  - Logical inconsistencies in the excerpt
  - Domain mismatch (signal classified as REGULATION but excerpt is about something else)

Signal to review:
  region:        {region}
  source_domain: {source_domain}
  source_tier:   {source_tier}
  evidence_grade:{evidence_grade}
  classification:{classification}
  signal_subtype:{signal_subtype}
  raw_excerpt:   {raw_excerpt}

Return ONLY valid JSON in this exact format:
{{"verdict": "CONFIRM" or "CHALLENGE" or "REJECT", "reasoning": "one sentence explanation"}}

Use CONFIRM if the signal is credible and well-supported.
Use CHALLENGE if there are notable weaknesses worth a second human look.
Use REJECT only for critical flaws (fabricated data, clear domain mismatch, internally contradictory).
No markdown. No explanation outside the JSON."""


def adversarial_review(signal: dict) -> dict:
    prompt = ADVERSARIAL_PROMPT.format(
        region        = signal.get("region", "?"),
        source_domain = signal.get("source_domain", "?"),
        source_tier   = signal.get("source_tier", "?"),
        evidence_grade= signal.get("evidence_grade", "?"),
        classification= signal.get("classification", "?"),
        signal_subtype= signal.get("signal_subtype", "?"),
        raw_excerpt   = signal.get("raw_excerpt", "?")[:300],
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"verdict": "CHALLENGE", "reasoning": "Reviewer returned malformed JSON -- flagging for human review"}
    verdict   = result.get("verdict",   "CHALLENGE").upper()
    reasoning = result.get("reasoning", "No reasoning provided")
    if verdict not in ("CONFIRM", "CHALLENGE", "REJECT"):
        verdict = "CHALLENGE"
    signal["adversarial_verdict"] = verdict
    signal["adversarial_notes"]   = reasoning
    return signal
