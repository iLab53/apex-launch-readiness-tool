# partner_editor.py
"""
Partner Editor agent.

Called by output_formatter when the briefing scores below the decision-quality
threshold (default 85/100).  Rewrites the briefing to be more decision-forcing
without changing the underlying facts — just sharpens structure, adds missing
timeframes, hardens recommendations, and removes analyst filler.

Usage:
    from partner_editor import partner_editor
    improved = partner_editor(briefing_md)
"""

import anthropic

MODEL = "claude-sonnet-4-6"

EDITOR_SYSTEM = (
    "You are a senior McKinsey partner doing a final edit pass on a regulatory "
    "intelligence briefing before it goes to the CEO, CFO, and CRO.\n\n"
    "Your job is NOT to add new information. Your job is to make every sentence "
    "force a decision.\n\n"
    "Edit rules (apply all of them):\n"
    "1. Every recommendation must start with an imperative verb and end with a timeframe.\n"
    "   Bad:  'Firms should consider reviewing their capital buffers.'\n"
    "   Good: 'Review Tier 1 capital buffers against the new ECB threshold (5 days).'\n"
    "2. Every priority must carry an explicit label: Critical (7 days), High (30 days), "
    "or Monitor.\n"
    "3. Every 'why it matters' must name a specific business impact: a fine range, "
    "a revenue line, a capital ratio, a market share risk. Not 'this is significant.'\n"
    "4. Cut every sentence that only describes — if it does not drive a decision, delete it.\n"
    "5. Replace all passive voice with active voice.\n"
    "6. Replace hedge phrases ('may', 'could potentially', 'it should be noted') "
    "with direct statements or delete them.\n"
    "7. Preserve all section headers and the overall structure exactly.\n"
    "8. Do NOT add new sections. Do NOT invent facts. Only sharpen what is there.\n\n"
    "Return the complete rewritten briefing — nothing else, no preamble."
)

EDITOR_PROMPT_TEMPLATE = (
    "Edit the following briefing to meet McKinsey partner standard.\n"
    "Apply all edit rules from your instructions.\n"
    "Return the full rewritten briefing.\n\n"
    "BRIEFING:\n"
    "{briefing}"
)


def partner_editor(briefing_md):
    """
    Rewrite a briefing to be more decision-forcing.

    Args:
        briefing_md: The markdown briefing text that failed the DQ threshold.

    Returns:
        str: The improved briefing text (same format, sharper language).
             Falls back to the original if the API call fails.
    """
    if not briefing_md:
        return briefing_md

    prompt = EDITOR_PROMPT_TEMPLATE.format(briefing=briefing_md)

    try:
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=EDITOR_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as e:
        print("[partner_editor] Edit failed ({}), keeping original.".format(e))
        return briefing_md
