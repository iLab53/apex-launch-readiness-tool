"""
NAVIGATOR -- Source Validator
Applies 5 trust rules to each Signal Object. No LLM calls.
"""
import datetime

RECENCY_DAYS = 90
SOCIAL_MEDIA  = {"twitter.com","x.com","reddit.com","linkedin.com","facebook.com","instagram.com","tiktok.com"}
TIER_1_DOMAINS = {
    "europa.eu","ec.europa.eu","gov.uk","gov.sg","gov.au",
    "whitehouse.gov","congress.gov","state.gov","un.org","wto.org",
    "oecd.org","worldbank.org","imf.org","apec.org","asean.org",
    "g20.org","au.int","africa-union.org","mci.gov.sg","pdpc.gov.sg",
    "mas.gov.sg","nist.gov","ftc.gov","meti.go.jp",  # Japan Ministry of Economy, Trade and Industry (gov) 
}
TIER_2_DOMAINS = {
    "reuters.com","ft.com","economist.com","bbc.com","bbc.co.uk",
    "nytimes.com","wsj.com","politico.com","theguardian.com",
    "bloomberg.com","techcrunch.com","wired.com","brookings.edu",
    "chathamhouse.org","cfr.org","rand.org","carnegieendowment.org",
    "csis.org","iiss.org"
}

def classify_source_tier(domain: str) -> str:
    domain = domain.lower().strip()

    # Check Tier 1 domains
    for t1 in TIER_1_DOMAINS:
        if domain == t1 or domain.endswith("." + t1):
            return "TIER_1"

    # Check Tier 2 domains
    for t2 in TIER_2_DOMAINS:
        if domain == t2 or domain.endswith("." + t2):
            return "TIER_2"

    return "TIER_3"

def validate_signal(signal: dict) -> dict:
    notes = []; failed = False; flagged = False
    # Rule 1: source_url must exist
    if not signal.get("source_url"):
        notes.append("Rule 1 FAILED: source_url missing"); failed = True
    # Rule 2: recency check
    pub = signal.get("publication_date", "")
    if pub:
        try:
            days_old = (datetime.date.today() - datetime.date.fromisoformat(pub)).days
            if days_old > RECENCY_DAYS:
                notes.append(f"Rule 2 FAILED: source is {days_old} days old"); failed = True
        except ValueError:
            notes.append("Rule 2 FAILED: invalid date format"); failed = True
    else:
        notes.append("Rule 2 FAILED: publication_date missing"); failed = True
    # Rule 3: source tier
    domain = signal.get("source_domain", "")
    tier = classify_source_tier(domain)
    signal["source_tier"] = tier
    if tier == "TIER_3":
        notes.append(f"Rule 3 FLAGGED: {domain} is TIER_3"); flagged = True
    # Rule 4: RISK signals need corroboration
    if signal.get("classification") == "RISK" and not signal.get("corroboration_urls", []):
        notes.append("Rule 4 FAILED: RISK signal has no corroboration_urls"); failed = True
    # Rule 5: no social media
    if signal.get("source_domain", "").lower() in SOCIAL_MEDIA:
        notes.append("Rule 5 FAILED: social media domain"); failed = True
    signal["validation_status"] = "FAILED" if failed else ("FLAGGED" if flagged else "PASSED")
    signal["validation_notes"] = " | ".join(notes) if notes else ""
    return signal
