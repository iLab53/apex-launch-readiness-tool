"""
connectors/fda_connector.py
============================
Queries the openFDA drug approvals (drugsfda) and drug label (drug/label)
endpoints for regulatory signals relevant to each APEX asset.

Patches comm_ex_dashboard_ready.json with:
  - New drug approvals / supplement type actions → regulatory_signals
  - Competitor label updates                     → competitive_intel

Uses only Python standard library (no extra dependencies).
API key optional — public rate limit is 240 req/min without a key; set
OPENFDA_API_KEY env var to raise the limit.

Run from repo root:
    python connectors/fda_connector.py --verbose
    python connectors/fda_connector.py --dry-run --verbose
"""

import argparse
import datetime
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT           = pathlib.Path(__file__).parent.parent
DASHBOARD_PATH = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
REGISTRY_PATH  = ROOT / "asset-registry" / "apex_assets.json"
DEBUG_DIR      = ROOT / "agents" / "outputs"

# openFDA endpoints
OPENFDA_DRUGS    = "https://api.fda.gov/drug/drugsfda.json"
OPENFDA_LABEL    = "https://api.fda.gov/drug/label.json"

TIMEOUT_SECS   = 15
PAGE_SIZE      = 10      # results per query
RATE_LIMIT_S   = 0.5    # seconds between requests

# How far back to look for approvals / label changes (days)
LOOKBACK_DAYS  = 180

# Action types that represent significant regulatory milestones
APPROVAL_ACTIONS = {
    "N", "NP", "NDF", "NDA", "BLA",         # new applications / biologics
    "SE", "SEB",                             # supplemental efficacy
    "TE",                                    # new indication
    "SNDA", "SBLA",                          # supplemental NDA/BLA
}

# Sponsor name fragments belonging to J&J / Janssen — skip
JNJ_FRAGMENTS = {
    "janssen", "johnson & johnson", "johnson and johnson",
    "j&j", "cilag", "ortho-mcneil",
}

# Search terms for each asset's active ingredient / INN
# Used when the registry does not have an explicit field
INGREDIENT_MAP = {
    "APEX-001": "daratumumab",
    "APEX-002": "ciltacabtagene autoleucel",
    "APEX-003": "amivantamab",
    "APEX-004": "guselkumab",
    "APEX-005": "nipocalimab",
    "APEX-006": "esketamine",
    "APEX-007": "ponesimod",
}

# Therapeutic area / condition search terms used in label endpoint
CONDITION_MAP = {
    "APEX-001": "multiple myeloma",
    "APEX-002": "multiple myeloma",
    "APEX-003": "non-small cell lung cancer",
    "APEX-004": "psoriasis",
    "APEX-005": "myasthenia gravis",
    "APEX-006": "treatment-resistant depression",
    "APEX-007": "multiple sclerosis",
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _api_key_param() -> str:
    key = os.environ.get("OPENFDA_API_KEY", "")
    return f"&api_key={key}" if key else ""


def fetch_fda_approvals(search_term: str, limit: int = PAGE_SIZE) -> list:
    """
    Query openFDA drug approvals for applications matching search_term
    (searched against openfda.brand_name and openfda.generic_name).
    Date filtering is done in Python (extract_approval_signals) to avoid
    server-side date range syntax issues.
    Returns list of application result dicts. Never raises.
    """
    search = (
        f'openfda.brand_name:"{search_term}"'
        f'+openfda.generic_name:"{search_term}"'
    )
    params = f"search={urllib.parse.quote(search)}&limit={limit}"
    url = OPENFDA_DRUGS + "?" + params + _api_key_param()

    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "APEX-PIPELINE/1.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw.get("results", [])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []   # no results
        print(f"  WARNING: openFDA approvals HTTP {exc.code}: {exc}", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  WARNING: openFDA approvals error: {exc}", file=sys.stderr)
        return []


def fetch_fda_labels(condition_term: str, limit: int = PAGE_SIZE) -> list:
    """
    Query openFDA drug labels for labels in a given condition/indication.
    Date filtering is done in Python (extract_label_signals) to avoid
    server-side date range syntax issues.
    Returns list of label result dicts. Never raises.
    """
    search = f'indications_and_usage:"{condition_term}"'
    params = f"search={urllib.parse.quote(search)}&limit={limit}"
    url = OPENFDA_LABEL + "?" + params + _api_key_param()

    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "APEX-PIPELINE/1.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw.get("results", [])
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        print(f"  WARNING: openFDA labels HTTP {exc.code}: {exc}", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  WARNING: openFDA labels error: {exc}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Field extractors
# ---------------------------------------------------------------------------

def _is_jnj(name: str) -> bool:
    n = (name or "").lower()
    return any(frag in n for frag in JNJ_FRAGMENTS)


def extract_approval_signals(app: dict, apex_id: str, brand_name: str) -> list:
    """
    From one drugsfda application, extract regulatory signal dicts
    for significant submissions within the lookback window.
    Skips J&J applications.
    """
    openfda     = app.get("openfda", {})
    sponsor_raw = app.get("sponsor_name", "") or (openfda.get("manufacturer_name") or [""])[0]
    if _is_jnj(sponsor_raw):
        return []

    app_number  = app.get("application_number", "")
    brand_names = openfda.get("brand_name", [])
    generic_names = openfda.get("generic_name", [])
    brand_str   = ", ".join(brand_names[:2]) if brand_names else "unknown"
    generic_str = ", ".join(generic_names[:1]) if generic_names else ""
    drug_label  = brand_str + (f" ({generic_str})" if generic_str else "")

    cutoff = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
    signals = []

    for sub in app.get("submissions", []):
        action_type  = sub.get("submission_type", "")
        status       = sub.get("submission_status", "")
        status_date  = sub.get("submission_status_date", "")

        if status not in ("AP", "TA"):  # AP = Approved, TA = Tentatively Approved
            continue

        try:
            sub_date = datetime.datetime.strptime(status_date, "%Y%m%d").date()
        except (ValueError, TypeError):
            continue

        if sub_date < cutoff:
            continue

        is_new_app   = action_type in APPROVAL_ACTIONS
        signal_type  = "FDA_APPROVAL" if is_new_app else "FDA_LABEL_CHANGE"

        doc_id = f"FDA-{app_number}-{action_type}-{status_date}"
        date_iso = sub_date.isoformat()

        summary = (
            f"{sponsor_raw} received FDA {status} for {drug_label} "
            f"(application {app_number}, type {action_type}) "
            f"on {date_iso}."
        )

        signals.append({
            "apex_id":             apex_id,
            "asset_id":            apex_id,
            "brand_name":          brand_name,
            "signal_type":         signal_type,
            "source":              "openFDA",
            "doc_id":              doc_id,
            "application_number":  app_number,
            "submission_type":     action_type,
            "title":               f"FDA {status}: {drug_label} ({action_type})",
            "summary":             summary,
            "sponsor":             sponsor_raw,
            "date":                date_iso,
            "confidence":          "HIGH",
            "strategic_relevance": (
                f"Competitor {drug_label} received FDA {status} ({action_type}) "
                f"in {brand_name} indication space. Assess market access impact."
            ),
            "function_owner":      "Market Access",
            "recommended_action":  (
                f"Review FDA {status} for {drug_label} ({app_number}). "
                f"Update competitive positioning for {brand_name}."
            ),
        })

    return signals


def extract_label_signals(label: dict, apex_id: str, brand_name: str) -> dict | None:
    """
    From one openFDA label record, build a competitive_intel entry if
    the drug is not J&J and the label was updated recently.
    """
    openfda         = label.get("openfda", {})
    sponsor_raw     = (openfda.get("manufacturer_name") or [""])[0]
    if _is_jnj(sponsor_raw):
        return None

    brand_names     = openfda.get("brand_name", [])
    generic_names   = openfda.get("generic_name", [])
    brand_str       = ", ".join(brand_names[:2]) if brand_names else "unknown"
    generic_str     = ", ".join(generic_names[:1]) if generic_names else ""
    drug_label      = brand_str + (f" ({generic_str})" if generic_str else "")

    effective_time  = label.get("effective_time", "")
    set_id          = label.get("set_id", "")
    indications_raw = label.get("indications_and_usage", [""])[0]
    indication_short = (indications_raw[:200] + "...") if len(indications_raw) > 200 else indications_raw

    try:
        eff_date = datetime.datetime.strptime(effective_time[:8], "%Y%m%d").date()
        date_iso = eff_date.isoformat()
    except (ValueError, TypeError):
        date_iso = ""
        eff_date = None

    # Only surface labels updated within the lookback window
    if eff_date is None:
        return None
    cutoff = datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)
    if eff_date < cutoff:
        return None

    if not set_id and not brand_str:
        return None

    doc_id = f"FDAL-{set_id or brand_str.replace(' ', '_')}-{effective_time[:8]}"

    return {
        "apex_id":             apex_id,
        "asset_id":            apex_id,
        "brand_name":          brand_name,
        "signal_type":         "FDA_LABEL_UPDATE",
        "source":              "openFDA",
        "doc_id":              doc_id,
        "set_id":              set_id,
        "title":               f"FDA label update: {drug_label}",
        "summary":             (
            f"{sponsor_raw} label for {drug_label} updated "
            f"(effective {date_iso}). Indication: {indication_short}"
        ),
        "sponsor":             sponsor_raw,
        "date":                date_iso,
        "confidence":          "MEDIUM",
        "strategic_relevance": (
            f"Label update for {drug_label} in {brand_name} indication space — "
            f"may reflect new data, warnings, or indication expansion."
        ),
        "function_owner":      "Medical Affairs",
        "recommended_action":  (
            f"Review updated {drug_label} FDA label (set_id {set_id}). "
            f"Assess implications for {brand_name} Medical Affairs messaging."
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

    all_approval_signals = []    # → regulatory_signals and competitive_intel
    all_label_signals    = []    # → competitive_intel
    debug_payload        = {}

    for asset in assets:
        apex_id    = asset.get("apex_id") or asset.get("asset_id", "")
        brand_name = asset.get("brand_name", apex_id)
        ingredient = INGREDIENT_MAP.get(apex_id, brand_name.lower())
        condition  = CONDITION_MAP.get(apex_id, "")

        if verbose:
            print(f"  [{apex_id}] {brand_name}")
            print(f"    -> drugsfda query: '{ingredient}'")

        # 1. Approval signals (drugsfda endpoint — search by ingredient name)
        approval_results = fetch_fda_approvals(ingredient)
        asset_approval_signals = []
        for app in approval_results:
            sigs = extract_approval_signals(app, apex_id, brand_name)
            asset_approval_signals.extend(sigs)
        all_approval_signals.extend(asset_approval_signals)

        if verbose:
            print(f"    -> {len(approval_results)} apps, {len(asset_approval_signals)} approval signals")

        time.sleep(RATE_LIMIT_S)

        # 2. Label signals (drug/label endpoint — search by condition)
        label_results = []
        asset_label_signals = []
        if condition:
            if verbose:
                print(f"    -> label query: '{condition}'")
            label_results = fetch_fda_labels(condition)
            for lbl in label_results:
                sig = extract_label_signals(lbl, apex_id, brand_name)
                if sig:
                    asset_label_signals.append(sig)
            all_label_signals.extend(asset_label_signals)
            if verbose:
                print(f"    -> {len(label_results)} labels, {len(asset_label_signals)} label signals")

        debug_payload[apex_id] = {
            "ingredient_query":     ingredient,
            "condition_query":      condition,
            "approval_results":     len(approval_results),
            "approval_signals":     len(asset_approval_signals),
            "label_results":        len(label_results),
            "label_signals":        len(asset_label_signals),
        }

        time.sleep(RATE_LIMIT_S)

    # Summary counts
    total_approval = len(all_approval_signals)
    total_label    = len(all_label_signals)
    total_signals  = total_approval + total_label

    print(f"\nResults: {total_approval} FDA approval signals, {total_label} label signals ({total_signals} total)")

    # Write debug output
    today_str  = datetime.date.today().isoformat()
    debug_path = DEBUG_DIR / f"fda_debug_{today_str}.json"
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

    # regulatory_signals: dict keyed by apex_id, deduped by doc_id
    existing_reg = dashboard.get("regulatory_signals", {})
    if not isinstance(existing_reg, dict):
        existing_reg = {}

    by_asset_approval: dict = {}
    for sig in all_approval_signals:
        by_asset_approval.setdefault(sig["apex_id"], []).append(sig)

    for aid, new_sigs in by_asset_approval.items():
        existing       = existing_reg.get(aid, [])
        existing_docs  = {s.get("doc_id") for s in existing if s.get("doc_id")}
        deduped        = [s for s in new_sigs if s.get("doc_id") not in existing_docs]
        existing_reg[aid] = existing + deduped

    dashboard["regulatory_signals"] = existing_reg

    # competitive_intel: append label signals, deduped by doc_id
    existing_ci = dashboard.get("competitive_intel", {})
    if not isinstance(existing_ci, dict):
        existing_ci = {}

    by_asset_label: dict = {}
    for sig in all_label_signals:
        by_asset_label.setdefault(sig["apex_id"], []).append(sig)

    for aid, new_sigs in by_asset_label.items():
        existing       = existing_ci.get(aid, [])
        existing_docs  = {s.get("doc_id") for s in existing if s.get("doc_id")}
        # Also check nct_id so we don't shadow ClinicalTrials entries
        existing_ncts  = {s.get("nct_id") for s in existing if s.get("nct_id")}
        deduped        = [
            s for s in new_sigs
            if s.get("doc_id") not in existing_docs
        ]
        existing_ci[aid] = existing + deduped

    dashboard["competitive_intel"] = existing_ci

    # Connector metadata
    dashboard.setdefault("data_sources", {})["fda"] = {
        "last_run":               datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "approval_signals_added": total_approval,
        "label_signals_added":    total_label,
    }

    DASHBOARD_PATH.write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Dashboard patched: {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="openFDA drug approvals + label -> APEX signal connector"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Query API but do NOT write to dashboard JSON",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print per-asset progress",
    )
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run, verbose=args.verbose))
