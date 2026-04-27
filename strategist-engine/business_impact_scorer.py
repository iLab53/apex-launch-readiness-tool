def business_impact_scorer(signals: list[dict]) -> list[dict]:
    """
    Adds simple business impact metadata to each signal.
    Minimum viable version: rule-based, no LLM cost.
    """

    high_impact_terms = [
        "crypto", "capital", "settlement", "enforcement",
        "prosecution", "digital euro", "Basel", "sanctions",
        "liquidity", "systemic", "market structure"
    ]

    urgent_terms = [
        "consultation", "effective", "deadline", "prosecution",
        "enforcement", "settlement", "framework", "final rule"
    ]

    for signal in signals:
        text = " ".join([
            str(signal.get("headline", "")),
            str(signal.get("summary", "")),
            str(signal.get("source", "")),
            str(signal.get("country", "")),
        ]).lower()

        impact_score = 3
        urgency_score = 3

        if any(term in text for term in high_impact_terms):
            impact_score += 1

        if any(term in text for term in urgent_terms):
            urgency_score += 1

        if "enforcement" in text or "prosecution" in text:
            impact_score += 1
            urgency_score += 1

        signal["business_impact_score"] = min(5, impact_score)
        signal["urgency_score"] = min(5, urgency_score)

        affected_firms = []

        if "crypto" in text:
            affected_firms += ["crypto firms", "fintechs", "banks"]
        if "capital" in text or "basel" in text:
            affected_firms += ["banks", "asset managers"]
        if "settlement" in text or "fpi" in text:
            affected_firms += ["asset managers", "custodians", "prime brokers"]
        if "digital euro" in text or "payments" in text:
            affected_firms += ["banks", "payment providers", "technology vendors"]

        signal["affected_firms"] = list(set(affected_firms)) or ["regulated financial institutions"]

    return signals
