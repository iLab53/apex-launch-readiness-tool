"""
connectors/nice_connector.py
=============================
Fetches NICE Technology Appraisal (TA) decisions relevant to each APEX
asset from nice.org.uk and patches comm_ex_dashboard_ready.json with
hta_signals entries.

Strategy
--------
1. Fetch the NICE published guidance list (HTML), filtered to type=ta,
   sorted by most-recently updated.  One page fetch covers all assets.
2. Parse TA reference, title, published date, and URL from the HTML.
3. For each APEX asset, keyword-match the TA title/URL against the
   asset's condition terms and emit an hta_signal if the TA was
   published/updated within LOOKBACK_DAYS.

Uses only Python standard library (no extra dependencies).

Run from repo root:
    python connectors/nice_connector.py --verbose
    python connectors/nice_connector.py --dry-run --verbose
"""

import argparse
import datetime
import html.parser
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT           = pathlib.Path(__file__).parent.parent
DASHBOARD_PATH = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
REGISTRY_PATH  = ROOT / "asset-registry" / "apex_assets.json"
DEBUG_DIR      = ROOT / "agents" / "outputs"

NICE_BASE         = "https://www.nice.org.uk"
# Published guidance list — type=ta, most recently updated first
NICE_LIST_URL     = (
    "https://www.nice.org.uk/guidance/published"
    "?type=ta&sort=DateUpdated&pageSize=50"
)

TIMEOUT_SECS  = 20
RATE_LIMIT_S  = 1.0   # polite scraping

# Look back this many days for relevant TAs (NICE TAs are infrequent)
LOOKBACK_DAYS = 365

# Condition keyword sets per asset (matched case-insensitively against TA title)
CONDITION_KEYWORDS = {
    "APEX-001": ["multiple myeloma", "myeloma", "daratumumab", "darzalex"],
    "APEX-002": ["multiple myeloma", "myeloma", "car-t", "ciltacabtagene", "carvykti"],
    "APEX-003": ["non-small cell lung", "nsclc", "egfr", "amivantamab", "rybrevant"],
    "APEX-004": ["psoriasis", "psoriatic arthritis", "guselkumab", "tremfya",
                 "inflammatory bowel", "crohn", "ulcerative colitis"],
    "APEX-005": ["myasthenia gravis", "nipocalimab"],
    "APEX-006": ["depression", "treatment.resistant depression", "esketamine",
                 "spravato", "suicidal"],
    "APEX-007": ["multiple sclerosis", "relapsing", "ponesimod", "ponvory"],
}

# Decision inference from TA title (checked in order, more specific first)
DECISION_PATTERNS = [
    (r"not recommended",                 "NOT_RECOMMENDED"),
    (r"do not recommend",                "NOT_RECOMMENDED"),
    (r"only in research",                "ONLY_IN_RESEARCH"),
    (r"recommended.*managed access",     "MANAGED_ACCESS"),
    (r"optimis",                         "OPTIMISED"),
    (r"\brecommended\b",                 "RECOMMENDED"),
    (r"appraisal consultation",          "IN_CONSULTATION"),
    (r"terminated",                      "TERMINATED"),
    (r"review",                          "REVIEW"),
]


# ---------------------------------------------------------------------------
# HTML parser
# ---------------------------------------------------------------------------

class NiceGuidanceListParser(html.parser.HTMLParser):
    """
    Extracts TA entries from the NICE published guidance list HTML page.
    Captures:
        href="/guidance/ta<N>"  → guidance_id, url
        link text               → title
        <time datetime="...">   → date (nearest time tag after a TA link)
    Falls back to regex extraction if structured parsing yields nothing.
    """

    def __init__(self):
        super().__init__()
        self._in_ta_link  = False
        self._current     = {}
        self.entries      = []          # list of {guidance_id, title, url, date_str}
        self._last_href   = ""
        self._capture_text = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            href = attrs.get("href", "")
            m = re.match(r"^/guidance/(ta\d+)$", href, re.IGNORECASE)
            if m:
                self._current     = {
                    "guidance_id": m.group(1).upper(),
                    "url":         NICE_BASE + href,
                    "title":       "",
                    "date_str":    "",
                }
                self._in_ta_link   = True
                self._capture_text = True
        if tag == "time" and self._current:
            dt = attrs.get("datetime", "")
            if dt and not self._current.get("date_str"):
                self._current["date_str"] = dt[:10]   # keep YYYY-MM-DD part

    def handle_endtag(self, tag):
        if tag == "a" and self._in_ta_link:
            self._in_ta_link  = False
            self._capture_text = False
            if self._current.get("guidance_id") and self._current.get("title"):
                self.entries.append(dict(self._current))
            self._current = {}

    def handle_data(self, data):
        if self._capture_text:
            self._current["title"] = (self._current.get("title", "") + data).strip()


def fetch_nice_list(verbose: bool = False) -> tuple[list, str]:
    """
    Fetch the NICE published TA list page and return
    (parsed_entries, raw_html).  Never raises.
    """
    try:
        req = urllib.request.Request(
            NICE_LIST_URL,
            headers={
                "Accept":          "text/html,application/xhtml+xml",
                "Accept-Language": "en-GB,en;q=0.9",
                "User-Agent":      (
                    "Mozilla/5.0 (compatible; APEX-PIPELINE/1.0; "
                    "+https://github.com/apex-pipeline)"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            raw_html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"  WARNING: NICE fetch failed: {exc}", file=sys.stderr)
        return [], ""
    except Exception as exc:
        print(f"  WARNING: NICE fetch unexpected error: {exc}", file=sys.stderr)
        return [], ""

    # Primary: HTMLParser
    parser = NiceGuidanceListParser()
    try:
        parser.feed(raw_html)
    except Exception as exc:
        if verbose:
            print(f"  WARNING: HTML parser error (falling back to regex): {exc}",
                  file=sys.stderr)

    entries = parser.entries

    # Fallback: regex if HTMLParser found nothing
    if not entries:
        if verbose:
            print("  INFO: HTMLParser found no entries, trying regex fallback")
        ta_refs = re.findall(r'href="(/guidance/(ta\d+))"[^>]*>([^<]+)<', raw_html, re.IGNORECASE)
        dates   = re.findall(r'<time[^>]+datetime="(\d{4}-\d{2}-\d{2})"', raw_html)
        date_iter = iter(dates)
        for href_path, ta_id, title in ta_refs:
            entries.append({
                "guidance_id": ta_id.upper(),
                "url":         NICE_BASE + href_path,
                "title":       title.strip(),
                "date_str":    next(date_iter, ""),
            })

    if verbose:
        print(f"  NICE list page: {len(entries)} TA entries found")

    return entries, raw_html


# ---------------------------------------------------------------------------
# Signal builder
# ---------------------------------------------------------------------------

def detect_decision(title: str) -> str:
    t = title.lower()
    for pattern, label in DECISION_PATTERNS:
        if re.search(pattern, t):
            return label
    return "PUBLISHED"


def _matches_asset(title: str, keywords: list) -> bool:
    t = title.lower()
    return any(re.search(kw, t) for kw in keywords)


def entry_to_hta_signal(entry: dict, apex_id: str, brand_name: str) -> dict | None:
    """
    Convert a parsed NICE TA entry to an APEX hta_signal dict.
    Returns None if the entry is outside the lookback window.
    """
    date_str = entry.get("date_str", "")
    try:
        pub_date = datetime.date.fromisoformat(date_str[:10])
        cutoff   = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
        if pub_date < cutoff:
            return None
    except (ValueError, TypeError):
        # If no date, include it anyway (better to surface than silently drop)
        pub_date = None

    guidance_id = entry["guidance_id"]
    title       = entry["title"]
    decision    = detect_decision(title)
    url         = entry["url"]
    date_iso    = pub_date.isoformat() if pub_date else ""

    confidence = "HIGH" if decision in ("RECOMMENDED", "NOT_RECOMMENDED",
                                         "MANAGED_ACCESS", "OPTIMISED") else "MEDIUM"

    summary = (
        f"NICE {guidance_id}: {title}. "
        f"Decision: {decision.replace('_', ' ').title()}. "
        f"Published/updated: {date_iso or 'date unknown'}. "
        f"Source: {url}"
    )

    return {
        "apex_id":             apex_id,
        "asset_id":            apex_id,
        "brand_name":          brand_name,
        "signal_type":         "NICE_TA_DECISION",
        "source":              "NICE",
        "guidance_id":         guidance_id,
        "url":                 url,
        "title":               title,
        "summary":             summary,
        "decision":            decision,
        "date":                date_iso,
        "confidence":          confidence,
        "strategic_relevance": (
            f"NICE {guidance_id} decision ({decision.replace('_', ' ').title()}) "
            f"in {brand_name} indication space. "
            f"Impacts UK market access and reimbursement positioning."
        ),
        "function_owner":      "Market Access",
        "recommended_action":  (
            f"Review NICE {guidance_id} ({url}). "
            f"Update {brand_name} UK market access strategy and "
            f"HTA dossier in response to decision: "
            f"{decision.replace('_', ' ').title()}."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run: bool = False, verbose: bool = False) -> int:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found: {REGISTRY_PATH}", file=sys.stderr)
        return 1
    registry_raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assets = (
        registry_raw.get("assets", registry_raw)
        if isinstance(registry_raw, dict) else registry_raw
    )

    if not DASHBOARD_PATH.exists():
        print(f"ERROR: Dashboard JSON not found: {DASHBOARD_PATH}", file=sys.stderr)
        return 1
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    if verbose:
        print(f"Fetching NICE TA list: {NICE_LIST_URL}")

    all_entries, raw_html = fetch_nice_list(verbose=verbose)

    # Per-asset matching
    all_hta_signals = {}   # apex_id -> [signals]
    debug_payload   = {
        "list_url":       NICE_LIST_URL,
        "entries_fetched": len(all_entries),
        "per_asset":       {},
    }

    for asset in assets:
        apex_id    = asset.get("apex_id") or asset.get("asset_id", "")
        brand_name = asset.get("brand_name", apex_id)
        keywords   = CONDITION_KEYWORDS.get(apex_id, [brand_name.lower()])

        matched = []
        for entry in all_entries:
            if _matches_asset(entry["title"], keywords):
                sig = entry_to_hta_signal(entry, apex_id, brand_name)
                if sig:
                    matched.append(sig)

        if verbose:
            print(
                f"  [{apex_id}] {brand_name}: "
                f"{len(matched)} NICE TA signals matched"
            )

        debug_payload["per_asset"][apex_id] = {
            "keywords":      keywords,
            "matched_count": len(matched),
            "matched_titles": [s["title"] for s in matched],
        }

        if matched:
            all_hta_signals[apex_id] = matched

    total = sum(len(v) for v in all_hta_signals.values())
    print(f"\nResults: {total} NICE TA signals across "
          f"{len(all_hta_signals)} assets")

    # Write debug output
    today_str  = datetime.date.today().isoformat()
    debug_path = DEBUG_DIR / f"nice_debug_{today_str}.json"
    debug_payload["raw_html_length"] = len(raw_html)
    debug_path.write_text(
        json.dumps(debug_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if verbose:
        print(f"Debug output written: {debug_path}")

    if dry_run:
        print("Dry run — dashboard JSON not modified.")
        return 0

    # ---- Patch dashboard JSON ----
    existing_hta = dashboard.get("hta_signals", {})
    if not isinstance(existing_hta, dict):
        existing_hta = {}

    for aid, new_sigs in all_hta_signals.items():
        existing      = existing_hta.get(aid, [])
        existing_gids = {s.get("guidance_id") for s in existing if s.get("guidance_id")}
        deduped       = [s for s in new_sigs if s["guidance_id"] not in existing_gids]
        existing_hta[aid] = existing + deduped

    dashboard["hta_signals"] = existing_hta

    # Connector metadata
    dashboard.setdefault("data_sources", {})["nice"] = {
        "last_run":          datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "entries_fetched":   len(all_entries),
        "signals_added":     total,
    }

    DASHBOARD_PATH.write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Dashboard patched: {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NICE TA guidance -> APEX HTA signal connector"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Fetch NICE but do NOT write to dashboard JSON",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-asset progress",
    )
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run, verbose=args.verbose))
