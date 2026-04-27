# sources.py — Pharma Intelligence Source Registry
# AI & Digital Transformation Tool — Johnson & Johnson Innovative Medicine
#
# Covers the regulatory and market intelligence sources that drive
# commercial decisions across Oncology, Immunology, and Neuroscience.
#
# ─────────────────────────────────────────────────────────────────────────────
#  QUICK START
#  1. Toggle entire regions via ENABLED_REGIONS below
#  2. Set "enabled": False on any source to skip it without deleting it
#  3. type="rss"    → auto-fetched via feedparser
#     type="scrape" → not yet automated; logged as skipped
# ─────────────────────────────────────────────────────────────────────────────

import os

ENABLED_REGIONS = [
    "Global",
    "US",
    "Europe",
    "APAC",
    "Canada",
]

API_KEYS = {}

FETCH_TIMEOUT_SECONDS = 15
MAX_ENTRIES_PER_FEED  = 20

# ─────────────────────────────────────────────────────────────────────────────
#  SOURCE REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

COUNTRY_SOURCES: dict[str, list[dict]] = {

    # ══════════════════════════════════════════════════════════════════════════
    # GLOBAL — Multi-agency and cross-market signals
    # ══════════════════════════════════════════════════════════════════════════
    "Global": [
        {
            "name": "WHO — News",
            "url": "https://www.who.int/rss-feeds/news-english.xml",
            "type": "rss",
            "description": "WHO public health guidance — affects global launch sequencing",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "ICH — Guidelines",
            "url": "https://www.ich.org/page/rss",
            "type": "rss",
            "description": "International Council for Harmonisation — global drug development standards",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "ClinicalTrials.gov — Recent Results",
            "url": "https://clinicaltrials.gov/ct2/results/rss.xml?sel_rss=new14400&rcv_d=&lup_d=14&no_unk=Y&show_rss=Y",
            "type": "rss",
            "description": "New trial results — competitive pipeline visibility for Oncology/Immunology/Neuroscience",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "IQVIA Institute — Reports",
            "url": "https://www.iqvia.com/insights/the-iqvia-institute/reports.rss",
            "type": "rss",
            "description": "Global pharma market data — forecasts, access, adherence trends",
            "requires_key": None,
            "enabled": True,
        },
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # US — FDA, CMS, ICER, and payer signals
    # ══════════════════════════════════════════════════════════════════════════
    "United States": [
        {
            "name": "FDA — Drug Approvals",
            "url": "https://www.fda.gov/drugs/resources-information-approved-drugs/rss",
            "type": "rss",
            "description": "NDA/BLA approvals and CRLs — competitive approvals and label decisions",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "FDA — Press Announcements",
            "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
            "type": "rss",
            "description": "High-priority FDA actions including safety communications and accelerated approvals",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "FDA — Warning Letters",
            "url": "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters/rss",
            "type": "rss",
            "description": "Manufacturing and promotional warning letters — supply chain and compliance risk",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "FDA — MedWatch Safety Alerts",
            "url": "https://www.fda.gov/safety/medwatch-fda-safety-information-and-adverse-event-reporting-program/rss",
            "type": "rss",
            "description": "Post-market safety signals — label change risk for in-line products",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "CMS — Coverage Decisions",
            "url": "https://www.cms.gov/medicare-coverage-database/downloads/lcd-rss.xml",
            "type": "rss",
            "description": "Medicare coverage decisions — market access and reimbursement signals",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "ICER — Evidence Reports",
            "url": "https://icer.org/feed/",
            "type": "rss",
            "description": "Independent drug pricing assessments — value-based access and payer negotiation signals",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "NIH — Research News",
            "url": "https://www.nih.gov/news-events/rss",
            "type": "rss",
            "description": "NIH-funded research — early signal on emerging science in J&J therapeutic areas",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "SEC EDGAR — Pharma Filings",
            "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=8-K&dateb=&owner=include&count=40&search_text=&SIC=2836&output=atom",
            "type": "rss",
            "description": "8-K filings from pharma companies — pipeline updates, trial results, M&A signals",
            "requires_key": None,
            "enabled": True,
        },
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # EUROPE — EMA, HTA, and national agency signals
    # ══════════════════════════════════════════════════════════════════════════
    "EU Overlay": [
        {
            "name": "EMA — News",
            "url": "https://www.ema.europa.eu/en/news-events/rss/news.xml",
            "type": "rss",
            "description": "EMA approvals, opinions, referrals — European label and access decisions",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "EMA — Press Releases",
            "url": "https://www.ema.europa.eu/en/news-events/rss/press-releases.xml",
            "type": "rss",
            "description": "High-priority EMA actions — CHMP positive opinions, safety reviews",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "NICE — Technology Appraisals",
            "url": "https://www.nice.org.uk/guidance/published?type=ta&niceResultsPageSize=10&nicePublishedDateFrom=&nicePublishedDateTo=&niceGuidanceStatusList=&niceProductList=&niceGuidanceTypeList=TA&niceCollectionList=&niceAuthoringOrganisationList=&niceAreaOfInterestList=&niceNationsList=&niceKeyword=&_=1&format=rss",
            "type": "rss",
            "description": "NICE HTA decisions — UK market access and reimbursement outcomes",
            "requires_key": None,
            "enabled": True,
        },
        {
            "name": "EUnetHTA — Joint Clinical Assessments",
            "url": "https://www.ema.europa.eu/en/news-events/rss/news.xml",
            "type": "rss",
            "description": "EU-wide joint HTA — multi-market access signal under HTA Regulation",
            "requires_key": None,
            "enabled": True,
        },
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # APAC — PMDA, TGA, MFDS signals
    # ══════════════════════════════════════════════════════════════════════════
    "Japan": [
        {
            "name": "PMDA — New Drug Approvals",
            "url": "https://www.pmda.go.jp/english/rs-sb-std/rs/0001.html",
            "type": "scrape",
            "description": "Japan PMDA approvals — Asia-Pacific launch sequencing signal",
            "requires_key": None,
            "enabled": False,
        },
    ],
    "Australia": [
        {
            "name": "TGA — Approvals",
            "url": "https://www.tga.gov.au/rss.xml",
            "type": "rss",
            "description": "Therapeutic Goods Administration — Australia approval and safety signals",
            "requires_key": None,
            "enabled": True,
        },
    ],

    # ══════════════════════════════════════════════════════════════════════════
    # CANADA
    # ══════════════════════════════════════════════════════════════════════════
    "Canada": [
        {
            "name": "Health Canada — Drug Approvals",
            "url": "https://www.canada.ca/en/health-canada/services/drugs-health-products/drug-products/applications-submissions/guidance-documents.atom",
            "type": "rss",
            "description": "Health Canada decisions — North American launch sequencing and label alignment",
            "requires_key": None,
            "enabled": True,
        },
    ],
}


def get_sources_for_country(country: str) -> list[dict]:
    """Return enabled sources for a given country, plus Global sources."""
    sources = []
    for src in COUNTRY_SOURCES.get("Global", []):
        if src.get("enabled", True):
            sources.append(src)
    for src in COUNTRY_SOURCES.get(country, []):
        if src.get("enabled", True):
            sources.append(src)
    return sources
