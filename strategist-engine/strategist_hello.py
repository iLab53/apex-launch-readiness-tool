# strategist_hello.py  (complete coordinator — Day 4, live data update)

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse
import hashlib
import time
import traceback

import feedparser

from output_formatter import format_output
from source_validator import validate_signal
from confidence_scorer import score_signal
from evidence_grader import grade_signal
from hitl_gate import hitl_gate
from adversarial_reviewer import adversarial_review
from deduplicator import deduplicate
from sources import get_sources_for_country, FETCH_TIMEOUT_SECONDS, MAX_ENTRIES_PER_FEED


# ── Region → country mapping ──────────────────────────────────────────────────
# To skip a region, remove it from ENABLED_REGIONS in sources.py.
# To add a country, add it here AND add its sources block in sources.py.

REGIONS = {
    "NA": [
        "United States",
        "Canada",
        "Mexico",
    ],
    "LATAM": [
        "Brazil",
        "Argentina",
        "Chile",
        "Colombia",
        "Peru",
        "Ecuador",
        "Uruguay",
        "Panama",
    ],
    "Europe": [
        "EU Overlay",       # ECB, ESMA, EBA, EIOPA — run once for all of Europe
        "United Kingdom",
        "Germany",
        "France",
        "Italy",
        "Spain",
        "Netherlands",
        "Switzerland",
        "Sweden",
        "Norway",
        "Denmark",
        "Ireland",
        "Poland",
        "Austria",
        "Belgium",
        "Portugal",
        "Turkey",
    ],
    "Middle East": [
        "Saudi Arabia",
        "UAE",
        "Qatar",
        "Israel",
    ],
    "APAC": [
        "China",
        "Japan",
        "India",
        "South Korea",
        "Australia",
        "New Zealand",
        "Indonesia",
        "Thailand",
        "Malaysia",
        "Philippines",
        "Vietnam",
        "Pakistan",
        "Bangladesh",
        "Singapore",
        "Hong Kong",
        "Taiwan",
    ],
    "Africa": [
        "South Africa",
        "Nigeria",
        "Kenya",
        "Egypt",
        "Morocco",
        "Ghana",
    ],
}

MAX_ITERATIONS = 3


# ── Live signal collection ─────────────────────────────────────────────────────

def _entry_to_signal(entry: dict, source_meta: dict, country: str, region: str) -> dict:
    """
    Convert a single feedparser entry into the standard 19-field signal dict.
    Called once per RSS item — you shouldn't need to edit this.
    """
    title    = entry.get("title", "").strip()
    link     = entry.get("link", "")
    summary  = entry.get("summary", entry.get("description", ""))[:2000]
    pub_raw  = entry.get("published", entry.get("updated", ""))

    # Parse date — fall back to today if unparseable
    try:
        pub_date = datetime(*entry.published_parsed[:3]).strftime("%Y-%m-%d")
    except Exception:
        pub_date = datetime.today().strftime("%Y-%m-%d")

    domain = urlparse(link).netloc or urlparse(source_meta["url"]).netloc

    # Stable ID based on URL so duplicates across runs are caught by deduplicator
    sig_id = hashlib.md5(link.encode()).hexdigest()[:8] if link else \
             hashlib.md5((title + pub_date).encode()).hexdigest()[:8]

    return {
        "signal_id":          sig_id,
        "headline":           title,
        "source":             source_meta["name"],
        "signal_type":        "regulatory",   # will be re-classified by grade_signal
        "raw_text":           summary,
        "raw_excerpt":        summary[:500],
        "publication_date":   pub_date,
        "source_url":         link,
        "source_domain":      domain,
        "classification":     "UNKNOWN",      # set by validate_signal / grade_signal
        "signal_subtype":     "UNCLASSIFIED",
        "corroboration_urls": [],
        "feedback_iteration": 0,
        "iterations":         0,
        "signal_date":        pub_date,
        "market_impact":      "UNKNOWN",
        "recommended_action": "Review",
        "tags":               [country, region, source_meta["type"]],
        "region":             region,
        "country":            country,
    }


def collect_signals(country: str, region: str = "") -> list[dict]:
    """
    Fetch live signals for one country.

    • Loops over every enabled source in sources.py for that country.
    • RSS feeds  → parsed with feedparser (automatic).
    • API sources → skipped for now with a clear log message (add wrappers later).
    • Scrape sources → skipped (flagged in sources.py; build scrapers on Day 5+).
    • Any single feed failure is caught and logged — it never crashes the run.
    """
    sources = get_sources_for_country(country)

    if not sources:
        print(f"  [{country}] No enabled sources — skipping")
        return []

    signals: list[dict] = []

    for src in sources:
        src_type = src["type"]
        src_name = src["name"]

        # ── RSS feeds ──────────────────────────────────────────────────────
        if src_type == "rss":
            try:
                print(f"  [{country}] Fetching RSS: {src_name}")
                feed = feedparser.parse(src["url"], request_headers={"User-Agent": "STRATEGIST/1.0"})

                entries = feed.entries[:MAX_ENTRIES_PER_FEED]
                print(f"  [{country}] → {len(entries)} entries from {src_name}")

                for entry in entries:
                    sig = _entry_to_signal(entry, src, country, region)
                    signals.append(sig)

            except Exception as e:
                print(f"  [{country}] ERROR fetching {src_name}: {e}")

        # ── API sources ────────────────────────────────────────────────────
        elif src_type == "api":
            # API wrappers go here — see sources.py for which ones need keys.
            # For now we log and skip so the run stays clean.
            print(f"  [{country}] SKIP API source '{src_name}' — no wrapper yet (add in sources_api.py)")

        # ── Scrape sources ─────────────────────────────────────────────────
        elif src_type == "scrape":
            print(f"  [{country}] SKIP scrape source '{src_name}' — add a scraper to unlock it")

    print(f"  [{country}] Collected {len(signals)} raw signals")
    return signals


def run_with_feedback(region: str) -> list[dict]:
    print(f"[Phase 1] Starting {region}...")

    countries = REGIONS[region]
    all_signals = []

    for country in countries:
        raw_signals = collect_signals(country, region=region)

        for sig in raw_signals:
            sig = validate_signal(sig)
            sig = score_signal(sig)
            sig = grade_signal(sig)

            all_signals.append(sig)

    print(f"[Phase 1] {region} done — {len(all_signals)} signals")
    return all_signals


def coordinator() -> dict:
    """Three-phase coordinator: fan-out → sequential HITL → parallel adversarial."""
    t0 = time.time()

    # ── Phase 1: parallel collection + grading ───────────────────────────
    print("\n=== PHASE 1: Parallel collection + grading ===")

    phase1: dict[str, list[dict]] = {}

    with ThreadPoolExecutor(max_workers=len(REGIONS)) as ex:
        futures = {
            ex.submit(run_with_feedback, region): region
            for region in REGIONS
        }

        for fut in as_completed(futures):
            region = futures[fut]

            try:
                result = fut.result() or []
                phase1[region] = result
                print(f"[Phase 1] Stored {region}: {len(result)} signals")

            except Exception as e:
                print(f"{region} failed: {e}")
                traceback.print_exc()
                phase1[region] = []

    total_raw = sum(len(v) for v in phase1.values())
    print(f"[Phase 1 complete] {total_raw} signals across {len(REGIONS)} regions")

    # ── Phase 2: sequential HITL ──────────────────────────────────────────
    print("\n=== PHASE 2: Sequential HITL review ===")

    hitl_results: dict[str, list[dict]] = {}

    for region in REGIONS:
        sigs = phase1.get(region, [])

        if not sigs:
            hitl_results[region] = []
            continue

        print(f"[HITL] Reviewing {region} ({len(sigs)} signals)...")
        hitl_results[region] = hitl_gate(sigs, region)

    # ── Deduplication ─────────────────────────────────────────────────────
    all_approved_signals = [
        sig
        for region_signals in hitl_results.values()
        for sig in region_signals
        if sig.get("hitl_decision") == "APPROVED"
    ]

    deduped, dedup_log = deduplicate(all_approved_signals)

    print(
        f"[Dedup] {len(all_approved_signals)} APPROVED → "
        f"{len(deduped)} unique"
    )

    # ── Phase 3: parallel adversarial review ──────────────────────────────
    print("\n=== PHASE 3: Parallel adversarial review ===")

    adversarial_results = []

    if deduped:
        with ThreadPoolExecutor(max_workers=min(len(deduped), 8)) as ex:
            futures = {
                ex.submit(adversarial_review, sig): sig
                for sig in deduped
            }

            for fut in as_completed(futures):
                try:
                    adversarial_results.append(fut.result())

                except Exception as e:
                    sig = futures[fut]
                    sig["adversarial_verdict"] = "ERROR"
                    sig["adversarial_notes"] = str(e)
                    adversarial_results.append(sig)

    elapsed = time.time() - t0

    print(
        f"\n[coordinator] Done in {elapsed:.1f}s — "
        f"{len(adversarial_results)} final signals"
    )

    # ── Format + persist ─────────────────────────────────────────────────
    report_path, exec_summary, analytics = format_output(
        {
            "phase1_raw": phase1,
            "hitl_results": hitl_results,
            "dedup_log": dedup_log,
            "final_signals": adversarial_results,
        },
        duration_s=elapsed,
    )

    # ── Phase 4: Decision quality review (runs inside format_output) ─────
    # The review + optional partner edit happen inside format_output above.
    # We surface the stored verdict here for the final console summary.
    print("\n=== PHASE 4: Decision quality review ===")
    import json as _json
    dq_verdict = {}
    # ── Phase 4: Decision quality review (runs inside format_output) ─────
    # The review + optional partner edit happen inside format_output above.
    # We surface the stored verdict here for the final console summary.
    print("\n=== PHASE 4: Decision quality review ===")
    import json as _json
    dq_verdict = {}
    try:
        with open(report_path, encoding="utf-8") as fh:
            dq_verdict = _json.load(fh).get("decision_quality_review", {})
    except Exception:
        pass

    verdict_label = dq_verdict.get("verdict", "UNKNOWN")
    score = dq_verdict.get("decision_quality_score", dq_verdict.get("overall_score", 0))
    passed = dq_verdict.get("pass", False)
    print("\n" + "=" * 60)
    print("  DECISION QUALITY: {}  ({}/100)  PASS: {}".format(verdict_label, score, passed))
    print("=" * 60)
    for dim, s in dq_verdict.get("dimension_scores", {}).items():
        bar = "#" * int(s / 2) + "-" * (10 - int(s / 2))
        print("  {:<22} [{}]  {}/20".format(dim, bar, s))
    if dq_verdict.get("top_gaps"):
        print("\n  Top gaps:")
        for g in dq_verdict["top_gaps"]:
            print("    \! " + g)
    if dq_verdict.get("reviewer_notes"):
        print("\n  Reviewer: " + dq_verdict["reviewer_notes"])
    print()

    return {
        "phase1_raw": phase1,
        "hitl_results": hitl_results,
        "dedup_log": dedup_log,
        "final_signals": adversarial_results,
        "report_path": report_path,
        "exec_summary": exec_summary,
        "analytics": analytics,
        "dq_verdict": dq_verdict,
    }


if __name__ == "__main__":
    results = coordin