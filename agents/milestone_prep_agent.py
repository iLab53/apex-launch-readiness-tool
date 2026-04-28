# agents/milestone_prep_agent.py
# APEX Milestone Prep Agent
# ─────────────────────────────────────────────────────────────────────────────
# Generates governance-ready milestone documents for a given asset + milestone
# type.  Produces a structured 5-section JSON document that can be committed as
# a governance artifact or used as a Codex prompt payload for prose generation.
#
# Milestone types:
#   ADP_REVIEW          — Asset Development Plan Review (senior leadership)
#   LRR                 — Launch Readiness Review (90–120 days pre-launch)
#   LRP                 — Launch Readiness Plan (final launch sign-off)
#   INVESTMENT_DECISION — Portfolio investment gate / budget allocation
#   GOVERNANCE          — Quarterly governance / board-level update
#
# 5-section output schema:
#   1. executive_summary   — posture + decision required + headline rec
#   2. asset_readiness     — per-dimension scores + trend
#   3. risk_register       — top 3–5 risks with owner + mitigation
#   4. financial_snapshot  — revenue at stake + access risk quantification
#   5. recommendation      — Proceed / Proceed with conditions / Pause / Stop
#
# Usage:
#   python run_comm_ex.py --milestone-prep APEX-001 LRR
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

MILESTONE_TYPES: dict[str, str] = {
    "ADP_REVIEW":          "Asset Development Plan Review",
    "LRR":                 "Launch Readiness Review",
    "LRP":                 "Launch Readiness Plan",
    "INVESTMENT_DECISION": "Investment Decision Gate",
    "GOVERNANCE":          "Governance / Board Update",
}

# ── Paths ─────────────────────────────────────────────────────────────────────
# milestone_prep_agent.py lives at  <repo>/agents/milestone_prep_agent.py

_REPO_ROOT     = Path(__file__).parent.parent
AGENTS_DIR     = Path(__file__).parent
OUTPUT_DIR     = AGENTS_DIR / "outputs"
ASSET_REG_PATH = _REPO_ROOT / "asset-registry" / "apex_assets.json"
PROMPT_PATH    = AGENTS_DIR / "milestone_prep_prompt.txt"


# ── 1. load_milestone_prompt ──────────────────────────────────────────────────

def load_milestone_prompt() -> str:
    """
    Load the system prompt from agents/milestone_prep_prompt.txt.

    If the file does not exist, writes the embedded default and returns it.
    This ensures the prompt file is always present on disk after the first call.
    """
    if PROMPT_PATH.exists():
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()

    prompt = _default_prompt()
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROMPT_PATH, "w", encoding="utf-8") as f:
        f.write(prompt)
    return prompt


def _default_prompt() -> str:
    return """\
# APEX Milestone Prep Agent — System Prompt
# Version: 1.0

You are the APEX Milestone Preparation Agent for J&J Innovative Medicine.
Your role is to generate governance-ready milestone documents that prepare
commercial and medical affairs leadership for critical asset decision gates.

You produce structured, evidence-based documents for five milestone types:
  ADP_REVIEW          — Asset Development Plan Review
  LRR                 — Launch Readiness Review (90-120 days pre-launch)
  LRP                 — Launch Readiness Plan (final launch sign-off)
  INVESTMENT_DECISION — Portfolio investment gate or budget allocation
  GOVERNANCE          — Quarterly governance or board-level update

For each milestone document, produce exactly five sections:

  1. Executive Summary     — 3-5 sentences: state the milestone, asset posture,
                             and single most important decision required.
                             Flag any launch-blocking gap in the first sentence.

  2. Asset Readiness       — Current readiness state across Market Access,
                             Medical Affairs, Marketing, Commercial Ops,
                             Regulatory, and Patient Support dimensions.
                             For each dimension: score (1-5), trend, confidence,
                             and top gap with owner.

  3. Risk Register         — Top 3-5 risks with: likelihood, impact, owner,
                             and mitigation action + target close date.
                             Cite regulatory signals (FDA/EMA/NICE/CMS) where
                             applicable. Escalate launch-blocking risks to the
                             Executive Summary.

  4. Financial Snapshot    — Revenue at stake, Year 1 forecast, launch
                             investment required, and payer/access risk
                             quantification in dollar terms (base + downside).

  5. Recommendation        — Single, unambiguous governance recommendation:
                             Proceed / Proceed with conditions / Pause / Stop.
                             If conditional: name each condition with owner and
                             target close date.
                             State the next review trigger.

Rules:
  - Write in imperative, decision-ready language
  - Cite specific signals (FDA/EMA/NICE/CMS/competitive) for every risk
  - Every risk and gap must have a named owner
  - Do not hedge — state best assessment with explicit confidence level
  - Never recommend Proceed when a launch-blocking gap exists
  - Cap at 5 risks in the risk register — prioritise ruthlessly
"""


# ── 2. build_milestone_document ───────────────────────────────────────────────

def build_milestone_document(
    asset_id:       str,
    milestone_type: str,
    scorecard_path: Optional[Path] = None,
    verbose:        bool = True,
) -> dict:
    """
    Build a structured 5-section milestone document.

    Loads asset context from apex_assets.json and (optionally) the latest
    scorecard JSON for pre-populated readiness scores.

    Returns a fully populated document dict.  Does not call the LLM — this
    is a scaffold that becomes either a governance artifact or a Codex/LLM
    prompt payload for prose generation.

    Args:
        asset_id:       APEX asset ID, e.g. "APEX-004"
        milestone_type: One of MILESTONE_TYPES keys (case-insensitive)
        scorecard_path: Optional explicit path to a scorecard JSON;
                        if None, searches agents/outputs/ and comm-ex/outputs/
        verbose:        Print progress to stdout
    """
    milestone_type = milestone_type.upper()
    if milestone_type not in MILESTONE_TYPES:
        raise ValueError(
            f"Unknown milestone type '{milestone_type}'. "
            f"Valid: {', '.join(MILESTONE_TYPES)}"
        )

    asset_ctx  = _load_asset(asset_id)
    scorecard  = (
        json.loads(scorecard_path.read_text(encoding="utf-8"))
        if scorecard_path
        else _load_latest_scorecard(asset_id)
    )

    ts         = datetime.now(timezone.utc).isoformat()
    doc_id     = (
        f"MILESTONE-{asset_id}-{milestone_type}-"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    asset_name = (asset_ctx or {}).get("brand_name", asset_id)
    ta         = (asset_ctx or {}).get("therapeutic_area", "Unknown")

    document = {
        "document_id":     doc_id,
        "asset_id":        asset_id,
        "asset_name":      asset_name,
        "therapeutic_area": ta,
        "milestone_type":  milestone_type,
        "milestone_label": MILESTONE_TYPES[milestone_type],
        "generated_at":    ts,
        "schema_version":  "1.0",
        "asset_context":   asset_ctx,
        "scorecard_ref":   (scorecard or {}).get("scorecard_id"),
        "sections": {
            "executive_summary":  _exec_summary(asset_ctx, milestone_type, scorecard),
            "asset_readiness":    _asset_readiness(asset_ctx, scorecard),
            "risk_register":      _risk_register(asset_ctx, milestone_type, scorecard),
            "financial_snapshot": _financial_snapshot(asset_ctx, milestone_type),
            "recommendation":     _recommendation(asset_ctx, milestone_type, scorecard),
        },
    }

    if verbose:
        print(f"  [OK]  Milestone document built: {doc_id}")
        print(f"        Asset:     {asset_name} ({asset_id}) | TA: {ta}")
        print(f"        Milestone: {MILESTONE_TYPES[milestone_type]}")

    return document


# ── Section builders ──────────────────────────────────────────────────────────

def _exec_summary(
    asset_ctx:  Optional[dict],
    m_type:     str,
    scorecard:  Optional[dict],
) -> dict:
    asset_name    = (asset_ctx or {}).get("brand_name", "Asset")
    indication    = (asset_ctx or {}).get("primary_indication", "")
    launch_phase  = (asset_ctx or {}).get("launch_phase", "")
    tier          = (scorecard or {}).get("overall", {}).get("readiness_tier", "Scorecard not available")
    m_label       = MILESTONE_TYPES.get(m_type, m_type)

    # Surface any launch-blocking gaps from scorecard
    blocking_gaps = [
        g.get("gap_description", "")
        for g in (scorecard or {}).get("overall", {}).get("top_gaps", [])
        if g.get("severity") == "Launch-Blocking"
    ]
    blocking_str = (
        f"LAUNCH-BLOCKING GAP IDENTIFIED: {blocking_gaps[0][:150]}. "
        if blocking_gaps else ""
    )

    return {
        "section": "Executive Summary",
        "readiness_tier": tier,
        "milestone_type": m_type,
        "content_scaffold": (
            f"{blocking_str}"
            f"This {m_label} covers {asset_name} ({indication}), "
            f"currently in {launch_phase} phase. "
            f"Overall readiness tier: {tier}. "
            "KEY DECISION REQUIRED: [State the single most important governance decision here]. "
            "RECOMMENDATION HEADLINE: [One sentence — Proceed / Proceed with conditions / Pause / Stop]."
        ),
        "instructions": (
            "Replace bracket placeholders with signal-grounded content before distribution. "
            "Reference specific FDA/EMA/NICE/CMS signals. Max 5 sentences. "
            "If a launch-blocking gap exists, lead with it."
        ),
    }


def _asset_readiness(
    asset_ctx: Optional[dict],
    scorecard: Optional[dict],
) -> dict:
    dimensions = [
        "market_access",
        "medical_affairs",
        "marketing_brand",
        "commercial_operations",
        "regulatory_compliance",
        "patient_support",
    ]
    dim_status: dict[str, dict] = {}

    sc_dims = (scorecard or {}).get("dimensions", {})
    for dim in dimensions:
        d = sc_dims.get(dim, {})
        if d:
            dim_status[dim] = {
                "score":      d.get("score", "N/A"),
                "weight":     d.get("weight", "N/A"),
                "trend":      d.get("trend", "Not enough data"),
                "confidence": d.get("confidence", "Low"),
                "rationale":  d.get("rationale", "[Populate from scorecard or field assessment]"),
            }
        else:
            dim_status[dim] = {
                "score":      "N/A — run --scorecard to populate",
                "trend":      "Not enough data",
                "confidence": "Low",
                "rationale":  "[Run: python run_apex.py --scorecard --asset <ID>]",
            }

    return {
        "section":      "Asset Readiness",
        "dimensions":   dim_status,
        "instructions": (
            "For each dimension: confirm score is current (within 30 days), "
            "update trend vs. prior review, name the top gap and gap owner."
        ),
    }


def _risk_register(
    asset_ctx: Optional[dict],
    m_type:    str,
    scorecard: Optional[dict],
) -> dict:
    risks: list[dict] = []

    # Seed from scorecard top_gaps if available
    for i, gap in enumerate(
        (scorecard or {}).get("overall", {}).get("top_gaps", [])[:5], 1
    ):
        risks.append({
            "risk_id":          f"RISK-{i:02d}",
            "dimension":        gap.get("dimension", "Unknown"),
            "description":      gap.get("gap_description", "[Describe risk]"),
            "likelihood":       "Medium — validate against current signals",
            "impact":           gap.get("severity", "High"),
            "owner":            gap.get("owner", "TBD"),
            "mitigation":       "[Define mitigation action, owner, and close date]",
            "target_close_date": gap.get("target_close_date", "TBD"),
            "signal_source":    "[Cite FDA/EMA/NICE/CMS signal driving this risk]",
        })

    # Template risks if no scorecard
    if not risks:
        templates = [
            ("RISK-01", "Market Access",           "Payer coverage decision delayed beyond launch date",                    "High",   "Market Access"),
            ("RISK-02", "Medical Affairs",          "MSL deployment incomplete in key accounts at launch",                  "Medium", "Medical Affairs"),
            ("RISK-03", "Regulatory Compliance",    "Label negotiation outcome narrower than modelled indication",           "High",   "Regulatory"),
            ("RISK-04", "Marketing Brand",          "Competitive response faster than anticipated — PDUFA threat imminent",  "Medium", "Marketing"),
            ("RISK-05", "Commercial Operations",    "Field force training completion <90% at launch date",                  "Medium", "Commercial Ops"),
        ]
        for risk_id, dim, desc, impact, owner in templates:
            risks.append({
                "risk_id":          risk_id,
                "dimension":        dim,
                "description":      desc,
                "likelihood":       "Medium — validate with current signals",
                "impact":           impact,
                "owner":            owner,
                "mitigation":       "[Define mitigation action, owner, and target close date]",
                "target_close_date": "TBD",
                "signal_source":    "[Cite FDA/EMA/NICE/CMS signal driving this risk]",
            })

    return {
        "section":      "Risk Register",
        "risks":        risks,
        "instructions": (
            "For each risk: cite the specific signal (FDA/EMA/NICE/CMS/Competitive) "
            "driving likelihood and impact. Escalate any launch-blocking risk to "
            "the Executive Summary. Cap at 5 risks — rank by launch impact."
        ),
    }


def _financial_snapshot(
    asset_ctx: Optional[dict],
    m_type:    str,
) -> dict:
    peak_sales = (asset_ctx or {}).get("peak_sales_estimate_usd_bn", "TBD")
    patent_exp = (asset_ctx or {}).get("patent_expiry", "TBD")

    return {
        "section": "Financial Snapshot",
        "revenue_at_stake": {
            "peak_sales_estimate_usd_bn":    peak_sales,
            "revenue_risk_pct":              "[Estimate % of forecast at risk from access/label/competitive gaps]",
            "year_1_forecast_usd_m":         "[Year 1 revenue forecast — confirm with Finance]",
        },
        "investment_required": {
            "launch_investment_usd_m":       "[Total launch investment budget — confirm with Finance]",
            "incremental_ask_this_milestone": "[Any incremental investment decision required at this gate]",
        },
        "access_risk_quantification": {
            "payer_coverage_delay_3mo_usd_m": "[Revenue impact of 3-month payer coverage delay]",
            "payer_coverage_delay_6mo_usd_m": "[Revenue impact of 6-month payer coverage delay]",
            "step_therapy_erosion_pct":       "[Estimated Rx volume lost to step-edit / PA burden]",
        },
        "patent_expiry": patent_exp,
        "instructions": (
            "Populate all brackets with Finance-confirmed figures before governance presentation. "
            "Quantify payer risk in dollar terms — present base case and downside scenario."
        ),
    }


def _recommendation(
    asset_ctx: Optional[dict],
    m_type:    str,
    scorecard: Optional[dict],
) -> dict:
    tier = (scorecard or {}).get("overall", {}).get("readiness_tier", "Not assessed")

    if "Gold" in tier or "Green" in tier:
        preliminary = "PROCEED — readiness tier supports forward motion at this gate"
    elif "Amber" in tier:
        preliminary = "PROCEED WITH CONDITIONS — named gaps must close before next gate"
    elif "Red" in tier:
        preliminary = "PAUSE — launch-blocking gaps require resolution before proceeding"
    else:
        preliminary = "ASSESSMENT REQUIRED — run --scorecard before governance presentation"

    return {
        "section":                   "Recommendation",
        "governance_recommendation": preliminary,
        "readiness_basis":           tier,
        "conditions_if_conditional": [
            "[Condition 1: specific gap, owner, close date]",
            "[Condition 2: specific gap, owner, close date]",
        ],
        "next_review_trigger": (
            f"[Define: what event or date triggers the next "
            f"{MILESTONE_TYPES.get(m_type, 'milestone')} review]"
        ),
        "decision_owner": "[Name the governance body or individual responsible for this gate]",
        "instructions": (
            "Replace all bracket placeholders before distribution. "
            "governance_recommendation must be one of: "
            "Proceed / Proceed with conditions / Pause / Stop. "
            "Conditions must name a specific owner and target close date."
        ),
    }


# ── Asset / scorecard loaders ─────────────────────────────────────────────────

def _load_asset(asset_id: str) -> Optional[dict]:
    if not ASSET_REG_PATH.exists():
        return None
    with open(ASSET_REG_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)
    assets = registry if isinstance(registry, list) else registry.get("assets", [])
    for asset in assets:
        if asset.get("apex_id", "").upper() == asset_id.upper():
            return asset
    return None


def _load_latest_scorecard(asset_id: str) -> Optional[dict]:
    for search_dir in [OUTPUT_DIR, _REPO_ROOT / "comm-ex" / "outputs"]:
        candidates = sorted(search_dir.glob(f"scorecard_{asset_id}_*.json"))
        if candidates:
            with open(candidates[-1], "r", encoding="utf-8") as f:
                return json.load(f)
    return None


# ── 3. save_milestone_doc ─────────────────────────────────────────────────────

def save_milestone_doc(document: dict, verbose: bool = True) -> Path:
    """
    Save the milestone document JSON to agents/outputs/.
    Returns the saved file path.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts       = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    asset_id = document.get("asset_id", "UNKNOWN")
    m_type   = document.get("milestone_type", "UNKNOWN")
    filename = OUTPUT_DIR / f"milestone_{asset_id}_{m_type}_{ts}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(document, f, indent=2, ensure_ascii=False)

    if verbose:
        print(f"  [OK]  Milestone doc saved: {filename.name}")

    return filename


# ── CLI entry point ───────────────────────────────────────────────────────────

def run_milestone_prep(
    asset_id:       str,
    milestone_type: str,
    verbose:        bool = True,
) -> dict:
    """
    Main callable for run_comm_ex.py --milestone-prep.

    Ensures prompt file exists, builds the document, saves it to disk,
    and returns the document dict.
    """
    load_milestone_prompt()   # Ensure agents/milestone_prep_prompt.txt exists
    document  = build_milestone_document(asset_id, milestone_type, verbose=verbose)
    save_path = save_milestone_doc(document, verbose=verbose)

    if verbose:
        print(f"\n  Milestone document ready: {save_path}")

    return document
