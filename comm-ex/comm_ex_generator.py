# comm_ex_generator.py
# AI & Digital Transformation Tool Ã¢â‚¬â€ Johnson & Johnson Innovative Medicine
"""
Translates pharma regulatory and market intelligence into structured,
executable commercialization recommendations for J&J 3M teams:
  Marketing | Medical Affairs | Market Access

Therapeutic focus: Oncology | Immunology | Neuroscience
Asset coverage:    PRE-LAUNCH Ã¢â€ â€™ LAUNCH Ã¢â€ â€™ POST-LAUNCH

Outputs (per run):
  comm_ex_recommendations_{DATE}_{RUN_ID}.json  Ã¢â‚¬â€ full structured recs
  comm_ex_summary_{DATE}_{RUN_ID}.txt           Ã¢â‚¬â€ executive summary
  comm_ex_dashboard_ready.json                  Ã¢â‚¬â€ aggregated KPIs (always latest)
"""

import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
import os

import anthropic

# Ã¢â€â‚¬Ã¢â€â‚¬ Asset Registry (Day 1 addition) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬ 
import sys as _sys
import os as _os
_sys.path.insert(0, str(_os.path.join(_os.path.dirname(__file__), "..", "asset-registry")))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
from memory_agent import update_memory
try:
    from asset_registry import format_asset_context_for_prompt as _fmt_asset
except ImportError:
    def _fmt_asset(asset_id: str) -> str:  # graceful fallback if registry missing
        return ""

MODEL      = "claude-sonnet-4-6"
OUTPUT_DIR = Path(__file__).parent / "outputs"

# Path to the intelligence engine (sibling folder)
ENGINE_REPORTS = Path(__file__).parent.parent / "strategist-engine" / "reports"


# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
#  Director of Comm Ex persona
# Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

SYSTEM = """\
You are the Director of Commercialization Excellence AI & Digital Transformation \
at Johnson & Johnson Innovative Medicine.

Your mandate: translate pharma regulatory and market intelligence into concrete, \
cross-functional commercial strategy for J&J's 3M teams Ã¢â‚¬â€ Marketing, Medical Affairs, \
and Market Access Ã¢â‚¬â€ across Oncology, Immunology, and Neuroscience portfolios.

You think like a business product leader building enterprise-grade commercial \
intelligence tools, not like an analyst writing reports.

Your non-negotiable standards:
- Every recommendation drives a real commercial decision with a named owner
- Every recommendation has a measurable KPI Ã¢â‚¬â€ not a vague aspiration
- You NEVER produce generic actions ("monitor", "assess", "consider impact")
- You ALWAYS connect a regulatory or market signal to a specific asset stage consequence
- You think in terms of launch sequencing, access barriers, physician behavior, \
  payer dynamics, label strategy, and competitive positioning

Output only valid JSON arrays. No preamble, no markdown fences."""

QUALITY_RUBRIC = """\
QUALITY BAR Ã¢â‚¬â€ STRICT

REJECT any recommendation that:
  Ã¢Å“â€” Could apply to any industry (must be pharma-specific)
  Ã¢Å“â€” Lacks a named function owner
  Ã¢Å“â€” Lacks a concrete, quantifiable KPI
  Ã¢Å“â€” Is not tied to a named signal, agency, or regulatory event
  Ã¢Å“â€” Uses passive or hedged language ("may", "consider", "explore")

STRONG recommendations:
  Ã¢Å“â€œ Name a specific drug class, asset type, or commercial capability
  Ã¢Å“â€œ Link to a named agency decision, trial readout, or payer signal
  Ã¢Å“â€œ State exactly what a top-performing 3M team does THIS WEEK
  Ã¢Å“â€œ Quantify the cost of delay (lost access, market share, launch velocity)

THINKING FRAMEWORK Ã¢â‚¬â€ for each signal:
  1. Does this affect: pricing | access | physician behavior | launch timing | competitive positioning?
  2. Which asset stage is most exposed: PRE-LAUNCH | LAUNCH | POST-LAUNCH?
  3. Which function owns the decision: Marketing | Medical Affairs | Market Access | Cross-functional?
  4. What is the 30-day action window before this risk or opportunity compounds?"""

SCHEMA_DESCRIPTION = """\
Each recommendation MUST follow this EXACT schema (no extra fields, no omissions):

{
  "rec_id":              "COMMEX-RUNID_PLACEHOLDER-NN",
  "run_id":              "RUNID_PLACEHOLDER",
  "date":                "DATE_PLACEHOLDER",

  "region":              "US | Europe | APAC | Canada | Global",

  "therapeutic_area":    "Oncology | Immunology | Neuroscience | General",

  "asset_stage":         "PRE-LAUNCH | LAUNCH | POST-LAUNCH",

  "target":              "Specific drug class, portfolio segment, or commercial capability (NOT generic)",

  "why_this_matters":    "One sentence: [named signal] Ã¢â€ â€™ [direct commercial implication]",

  "recommended_action":  "Specific executable action beginning with a strong verb. Ã¢â€°Â¥ 20 words.",

  "function_owner":      "Marketing | Medical Affairs | Market Access | Cross-functional",

  "timeline":            "Immediate (0-30d) | Near-term (30-90d) | Mid-term (90-180d)",

  "expected_impact":     "Specific business outcome: revenue protection | access expansion | \
launch velocity improvement | adherence gain | competitive differentiation",

  "kpi":                 "Measurable metric with a numeric target, e.g.: \
'Tier-2+ formulary coverage across Ã¢â€°Â¥60% of targeted payers within 90 days'",

  "risk_if_no_action":   "Specific consequence within the timeline window if action is not taken",

  "confidence":          "HIGH | MEDIUM | LOW",

  "signal_source":       "Exact section or agency name from the briefing"
}"""

PROMPT_TEMPLATE = """\
Today is DATE_PLACEHOLDER.

ASSET_CONTEXT_PLACEHOLDER

You have received the following pharmaceutical regulatory and market intelligence briefing:

Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
BRIEFING_PLACEHOLDER
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â

QUALITY_RUBRIC_PLACEHOLDER

SCHEMA_PLACEHOLDER

Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
TASK
Ã¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢ÂÃ¢â€¢Â
Generate 6Ã¢â‚¬â€œ10 commercialization recommendations for J&J Innovative Medicine \
3M teams (Marketing, Medical Affairs, Market Access) across Oncology, \
Immunology, and Neuroscience.

MANDATORY DISTRIBUTION Ã¢â‚¬â€ your output WILL be rejected if any of these are missing:
  Ã¢â€°Â¥ 2  PRE-LAUNCH recommendations
  Ã¢â€°Â¥ 2  LAUNCH recommendations
  Ã¢â€°Â¥ 2  POST-LAUNCH recommendations
  Ã¢â€°Â¥ 2  different function owners represented
  Ã¢â€°Â¥ 1  Oncology therapeutic area
  Ã¢â€°Â¥ 1  Immunology therapeutic area

ORDERING: Confidence descending (HIGH first), then timeline ascending \
(Immediate before Near-term before Mid-term).

OUTPUT: JSON array ONLY. No markdown. No explanation. No preamble."""

SUMMARY_SYSTEM = """\
You are the Director of Commercialization Excellence AI & Digital Transformation \
at Johnson & Johnson Innovative Medicine.
Write with authority and commercial urgency for a GCSO leadership audience."""

SUMMARY_PROMPT = """\
Today is DATE_PLACEHOLDER.

Based on these Comm Ex recommendations:

RECS_PLACEHOLDER

Write a concise executive summary for GCSO leadership. Use this exact structure:

---
COMMERCIAL INTELLIGENCE SUMMARY
DATE_PLACEHOLDER | Run RUNID_PLACEHOLDER

STRATEGIC SITUATION
2-3 sentences. What is happening in the regulatory/market environment \
that is commercially material for J&J Innovative Medicine?

TOP 3 RECOMMENDATIONS
For each: rec_id | function_owner | timeline
One sentence: what to do and why now.

LEADERSHIP ACTIONS Ã¢â‚¬â€ NEXT 7 DAYS
3 specific decisions. Each must name a decision-maker (CCO, Head of Market Access, \
Global Brand Lead) and a deadline date.

RISK REGISTER
Top 2 risks of inaction. Each: risk | asset_stage affected | commercial consequence.
---

Plain prose. Decisive. No hedging. Every sentence earns its place."""


def _build_dashboard(recs: list[dict], run_id: str, run_date: str) -> dict:
    total    = len(recs)
    stages   = Counter(r.get("asset_stage", "?")        for r in recs)
    funcs    = Counter(r.get("function_owner", "?")     for r in recs)
    areas    = Counter(r.get("therapeutic_area", "?")   for r in recs)
    timelines= Counter(r.get("timeline", "?")           for r in recs)
    conf     = Counter(r.get("confidence", "?")         for r in recs)
    regions  = Counter(r.get("region", "?")             for r in recs)

    immediate  = [r for r in recs if "Immediate" in r.get("timeline","")]
    high_conf  = [r for r in recs if r.get("confidence") == "HIGH"]

    sort_key = lambda r: (
        {"HIGH":0,"MEDIUM":1,"LOW":2}.get(r.get("confidence","LOW"),2),
        {"Immediate (0-30d)":0,"Near-term (30-90d)":1,"Mid-term (90-180d)":2}.get(r.get("timeline",""),3)
    )

    top_risks = [
        {"rec_id": r["rec_id"], "asset_stage": r.get("asset_stage"),
         "risk": r.get("risk_if_no_action"), "timeline": r.get("timeline"),
         "function": r.get("function_owner")}
        for r in sorted(recs, key=sort_key)[:3]
    ]

    top_opps = [
        {"rec_id": r["rec_id"], "target": r.get("target"),
         "expected_impact": r.get("expected_impact"), "kpi": r.get("kpi"),
         "function": r.get("function_owner")}
        for r in high_conf[:4]
    ]

    kpis_by_function: dict[str, list] = {}
    for r in recs:
        fn = r.get("function_owner","Unknown")
        kpis_by_function.setdefault(fn, []).append(
            {"rec_id": r.get("rec_id"), "kpi": r.get("kpi")}
        )

    return {
        "meta": {
            "run_id": run_id[:8], "date": run_date,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_recs": total,
        },
        "distribution": {
            "by_asset_stage": dict(stages), "by_function": dict(funcs),
            "by_therapeutic_area": dict(areas), "by_timeline": dict(timelines),
            "by_confidence": dict(conf), "by_region": dict(regions),
        },
        "coverage_check": {
            "pre_launch_count":    stages.get("PRE-LAUNCH", 0),
            "launch_count":        stages.get("LAUNCH", 0),
            "post_launch_count":   stages.get("POST-LAUNCH", 0),
            "immediate_actions":   len(immediate),
            "high_confidence":     conf.get("HIGH", 0),
            "pct_high_confidence": round(conf.get("HIGH",0)/total*100) if total else 0,
        },
        "top_risks":         top_risks,
        "top_opportunities": top_opps,
        "kpis_by_function":  kpis_by_function,
        "immediate_actions": [
            {"rec_id": r.get("rec_id"), "recommended_action": r.get("recommended_action"),
             "function_owner": r.get("function_owner"), "kpi": r.get("kpi")}
            for r in immediate
        ],
    }


def _parse_json(text: str) -> list[dict]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    raise ValueError(f"Could not parse JSON:\n{text[:400]}")

REQUIRED = ["rec_id","run_id","date","region","therapeutic_area","asset_stage",
            "target","why_this_matters","recommended_action","function_owner",
            "timeline","expected_impact","kpi","risk_if_no_action","confidence","signal_source"]

def _enforce(recs: list[dict], short_id: str, run_date: str) -> list[dict]:
    out = []
    for i, rec in enumerate(recs):
        rec.setdefault("rec_id", f"COMMEX-{short_id}-{i+1:02d}")
        rec.setdefault("run_id", short_id)
        rec.setdefault("date",   run_date)
        for f in REQUIRED:
            rec.setdefault(f, "Ã¢â‚¬â€")
        out.append(rec)
    return out

def load_latest_briefing() -> str | None:
    if not ENGINE_REPORTS.exists():
        return None
    for f in sorted(ENGINE_REPORTS.glob("strategist_run_*.json"), reverse=True):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            b = d.get("executive_briefing","")
            if b and len(b) > 200:
                return b
        except Exception:
            continue
    return None


def generate_recommendations(
    briefing: str,
    run_id: str,
    run_date: str,
    asset_id: str | None = None,
) -> list[dict]:
    short_id = run_id[:8]
    client   = anthropic.Anthropic()
    schema   = (SCHEMA_DESCRIPTION
                .replace("RUNID_PLACEHOLDER", short_id)
                .replace("DATE_PLACEHOLDER",  run_date))

    if asset_id:
        asset_context = _fmt_asset(asset_id)
        if not asset_context:
            asset_context = f"[Asset context unavailable for {asset_id} Ã¢â‚¬â€ proceeding with portfolio-level analysis]"
    else:
        asset_context = "[No specific asset selected Ã¢â‚¬â€ generating portfolio-level recommendations across all 7 APEX assets]"

    prompt = (PROMPT_TEMPLATE
              .replace("DATE_PLACEHOLDER",           run_date)
              .replace("ASSET_CONTEXT_PLACEHOLDER",  asset_context)
              .replace("BRIEFING_PLACEHOLDER",        briefing)
              .replace("QUALITY_RUBRIC_PLACEHOLDER",  QUALITY_RUBRIC)
              .replace("SCHEMA_PLACEHOLDER",          schema)
              .replace("RUNID_PLACEHOLDER",           short_id))
    msg = client.messages.create(
        model=MODEL, max_tokens=6000, system=SYSTEM,
        messages=[{"role":"user","content":prompt}],
    )
    recs = _parse_json(msg.content[0].text.strip())
    return _enforce(recs, short_id, run_date)

def generate_summary(recs: list[dict], run_id: str, run_date: str) -> str:
    short_id = run_id[:8]
    client   = anthropic.Anthropic()
    prompt = (SUMMARY_PROMPT
              .replace("DATE_PLACEHOLDER",  run_date)
              .replace("RUNID_PLACEHOLDER", short_id)
              .replace("RECS_PLACEHOLDER",  json.dumps(recs, indent=2)[:8000]))
    msg = client.messages.create(
        model=MODEL, max_tokens=1200, system=SUMMARY_SYSTEM,
        messages=[{"role":"user","content":prompt}],
    )
    return msg.content[0].text.strip()


def save_outputs(recs, summary, dashboard, run_id, run_date, out_dir=OUTPUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    short_id = run_id[:8]
    paths = {}
    p = out_dir / f"comm_ex_recommendations_{run_date}_{short_id}.json"
    p.write_text(json.dumps(recs, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["recommendations"] = str(p)
    s = out_dir / f"comm_ex_summary_{run_date}_{short_id}.txt"
    s.write_text(summary, encoding="utf-8")
    paths["summary"] = str(s)
    d = out_dir / "comm_ex_dashboard_ready.json"
    d.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding="utf-8")
    paths["dashboard"] = str(d)
    return paths


def run(
    briefing: str | None = None,
    out_dir: Path = OUTPUT_DIR,
    verbose: bool = True,
    asset_id: str | None = None,
) -> dict:
    run_id   = str(uuid.uuid4())
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if briefing is None:
        if verbose: print("[comm_ex] Loading latest briefing from intelligence engine...")
        briefing = load_latest_briefing()
        if not briefing:
            raise RuntimeError("No briefing found. Run the intelligence engine first.")
    if asset_id and verbose:
        print(f"[comm_ex] Asset context: {asset_id}")
    if verbose: print(f"[comm_ex] Generating recommendations (run {run_id[:8]})...")
    recs      = generate_recommendations(briefing, run_id, run_date, asset_id=asset_id)
    if verbose: print(f"[comm_ex] {len(recs)} recommendations generated. Writing summary...")
    summary   = generate_summary(recs, run_id, run_date)
    dashboard = _build_dashboard(recs, run_id, run_date)
    paths     = save_outputs(recs, summary, dashboard, run_id, run_date, out_dir)

    # Ã¢â€â‚¬Ã¢â€â‚¬ Memory update (Day 5) Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
    memory_run_id   = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    memory_run_date = datetime.now().strftime('%Y-%m-%d')

    recs_by_asset = {}
    for rec in recs:
        aid = rec.get("asset_id") or "UNKNOWN"
        recs_by_asset.setdefault(aid, []).append(rec)

    memory_deltas = {}
    for memory_asset_id, asset_recs in recs_by_asset.items():
        if memory_asset_id == "UNKNOWN":
            continue
        delta = update_memory(memory_asset_id, memory_run_id, memory_run_date, asset_recs)
        memory_deltas[memory_asset_id] = delta.get("delta_summary", {})

    result = {
        "recs": recs,
        "summary": summary,
        "dashboard": dashboard,
        "paths": paths,
        "run_id": run_id,
        "run_date": run_date,
    }
    result["memory_deltas"] = memory_deltas

    if verbose:
        print(f"\n{'='*60}")
        print(f"  COMM EX Ã¢â‚¬â€ Complete | Run {run_id[:8]} | {run_date}")
        for label, path in paths.items():
            print(f"  {label:<20}: {path}")
        print(f"{'='*60}\n")
    return result

