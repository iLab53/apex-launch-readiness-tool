"""
NAVIGATOR -- Evidence Grader (full)
Evaluates source_tier, confidence_score, and validation_status.
Produces a diagnostic feedback prompt when grade is LOW.
No LLM calls -- deterministic rules only.
"""

HIGH_SCORE_THRESHOLD   = 0.80
MEDIUM_SCORE_THRESHOLD = 0.60

def grade_signal(signal: dict) -> dict:
    tier   = signal.get("source_tier", "TIER_3")
    score  = signal.get("confidence_score", 0.0)
    status = signal.get("validation_status", "FAILED")

    issues = []

    # LOW wins if any criterion is at the lowest level
    if status == "FAILED":
        issues.append(f"validation_status is FAILED ({signal.get('validation_notes', '')})")
    if tier == "TIER_3":
        issues.append(f"source_domain '{signal.get('source_domain', '?')}' is TIER_3")
    if score < MEDIUM_SCORE_THRESHOLD:
        issues.append(f"confidence_score {score:.3f} is below MEDIUM threshold ({MEDIUM_SCORE_THRESHOLD})")

    if issues:
        grade = "LOW"
    elif tier in ("TIER_1", "TIER_2") and score >= HIGH_SCORE_THRESHOLD and status in ("PASSED",):
        grade = "HIGH"
    else:
        # MEDIUM: no LOW triggers, but not all HIGH criteria met
        if tier == "TIER_2":
            issues.append("source is TIER_2 (not TIER_1)")
        if score < HIGH_SCORE_THRESHOLD:
            issues.append(f"confidence_score {score:.3f} below HIGH threshold ({HIGH_SCORE_THRESHOLD})")
        if status == "FLAGGED":
            issues.append("validation_status is FLAGGED")
        grade = "MEDIUM"

    signal["evidence_grade"] = grade
    signal["grader_notes"]   = "; ".join(issues) if issues else "All criteria met"
    return signal


def build_feedback_prompt(signal: dict) -> str:
    """
    Returns a diagnostic feedback string appended to the collector prompt on retry.
    Names exactly which criteria failed so the collector can target a better source.
    """
    parts = ["FEEDBACK: The previous signal did not meet evidence quality standards."]

    tier   = signal.get("source_tier", "TIER_3")
    score  = signal.get("confidence_score", 0.0)
    status = signal.get("validation_status", "FAILED")
    notes  = signal.get("validation_notes", "")
    domain = signal.get("source_domain", "unknown")

    if tier == "TIER_3":
        parts.append(
            f"Source domain '{domain}' was classified as TIER_3 (unrecognized). "
            "Please use a government body (.gov), international organization, or established news outlet."
        )
    if status == "FAILED":
        parts.append(
            f"Validation failed: {notes}. "
            "Ensure the source_url is present, the publication_date is within 90 days, "
            "and RISK signals include at least one corroboration_url."
        )
    if score < MEDIUM_SCORE_THRESHOLD:
        parts.append(
            f"Confidence score was {score:.3f}, below the minimum threshold of {MEDIUM_SCORE_THRESHOLD}. "
            "Use a higher-tier source and include corroboration_urls to improve the score."
        )

    parts.append("Please return a revised signal that addresses the issues above.")
    return " ".join(parts)
