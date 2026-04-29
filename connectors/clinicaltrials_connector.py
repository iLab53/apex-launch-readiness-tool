"""
connectors/clinicaltrials_connector.py
=======================================
Queries ClinicalTrials.gov API v2 for competitor trials relevant to
each APEX asset and patches comm_ex_dashboard_ready.json with:
  - competitor trial updates appended to competitive_intel
  - upcoming completion dates appended to milestone_alerts

Uses only Python standard library (no extra dependencies).

Run from repo root:
    python connectors/clinicaltrials_connector.py --verbose
    python connectors/clinicaltrials_connector.py --dry-run --verbose
"""

import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).parent.parent
DASHBOARD_PATH = ROOT / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"
REGISTRY_PATH  = ROOT / "asset-registry" / "apex_assets.json"
DEBUG_DIR      = ROOT / "agents" / "outputs"

CT_API_BASE  = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT_SECS = 15
PAGE_SIZE    = 15
RATE_LIMIT_S = 0.6   # seconds between asset queries (be polite)

# Fallback condition search terms used when indication is "[TO BE FILLED]"
INDICATION_FALLBACK = {
    "APEX-001": "multiple myeloma",
    "APEX-002": "multiple myeloma CAR-T",
    "APEX-003": "non-small cell lung cancer EGFR exon 20",
    "APEX-004": "psoriasis inflammatory bowel disease",
    "APEX-005": "generalized myasthenia gravis",
    "APEX-006": "treatment-resistant depression",
    "APEX-007": "multiple sclerosis",
}

# Sponsor name fragments that belong to J&J / Janssen — skip these
JNJ_FRAGMENTS = {
    "janssen", "johnson & johnson", "johnson and johnson",
    "j&j", "cilag", "ortho-mcneil",
}

# Only flag milestone alerts within this window
MILESTONE_HORIZON_DAYS = 180


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def fetch_trials(cond_query: str, page_size: int = PAGE_SIZE) -> list:
    """
    Query ClinicalTrials.gov API v2 for studies matching cond_query.
    Returns a list of raw study dicts (protocolSection structure).
    Returns [] on any error — never raises.
    """
    params = {
        "query.cond":          cond_query,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED",
        "pageSize":             str(page_size),
        "format":               "json",
    }
    url = CT_API_BASE + "?" + urllib.parse.urlencode(params)

    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "APEX-PIPELINE/1.0"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        return raw.get("studies", [])
    except urllib.error.URLError as exc:
        print(f"  WARNING: ClinicalTrials API request failed: {exc}", file=sys.stderr)
        return []
    except json.JSONDecodeError as exc:
        print(f"  WARNING: ClinicalTrials JSON parse error: {exc}", file=sys.stderr)
        return []
    except Exception as exc:
        print(f"  WARNING: Unexpected error fetching trials: {exc}", file=sys.stderr)
        return []


def extract_study_fields(study: dict) -> dict:
    """Flatten relevant fields from the API v2 nested protocolSection."""
    ps        = study.get("protocolSection", {})
    id_mod    = ps.get("identificationModule", {})
    status    = ps.get("statusModule", {})
    sponsor   = ps.get("sponsorCollaboratorsModule", {})
    conds     = ps.get("conditionsModule", {})
    design    = ps.get("designModule", {})
    arms      = ps.get("armsInterventionsModule", {})

    interventions = [
        i.get("name", "")
        for i in arms.get("interventions", [])
        if i.get("type", "").upper() in (
            "DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT", "GENETIC"
        )
    ]

    return {
        "nct_id":                  id_mod.get("nctId", ""),
        "brief_title":             id_mod.get("briefTitle", ""),
        "sponsor":                 sponsor.get("leadSponsor", {}).get("name", ""),
        "phase":                   ", ".join(design.get("phases", [])) or "N/A",
        "overall_status":          status.get("overallStatus", ""),
        "start_date":              status.get("startDateStruct", {}).get("date", ""),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date", ""),
        "last_update_submit_date": status.get("lastUpdateSubmitDate", ""),
        "interventions":           interventions,
        "conditions":              conds.get("conditions", []),
    }


# ---------------------------------------------------------------------------
# Signal converters
# ---------------------------------------------------------------------------

def _is_jnj(sponsor: str) -> bool:
    s = sponsor.lower()
    return any(frag in s for frag in JNJ_FRAGMENTS)


def to_competitive_intel(study: dict, apex_id: str, brand_name: str) -> dict | None:
    """
    Convert a study dict to an APEX competitive_intel entry.
    Returns None if the sponsor is J&J or there is no useful data.
    """
    if _is_jnj(study["sponsor"]):
        return None
    if not study["nct_id"]:
        return None

    intv_str  = ", ".join(study["interventions"]) if study["interventions"] else "undisclosed"
    cond_str  = ", ".join(study["conditions"][:2]) or "related indication"
    date_str  = (
        study["last_update_submit_date"]
        or study["primary_completion_date"]
        or study["start_date"]
        or ""
    )

    summary = (
        f"{study['sponsor']} conducting {study['phase']} trial ({study['nct_id']}) "
        f"in {cond_str}. "
        f"Intervention: {intv_str}. "
        f"Status: {study['overall_status']}. "
        f"Primary completion: {study['primary_completion_date'] or 'TBD'}."
    )

    return {
        "apex_id":            apex_id,
        "asset_id":           apex_id,
        "brand_name":         brand_name,
        "signal_type":        "COMPETITOR_TRIAL",
        "source":             "ClinicalTrials.gov",
        "nct_id":             study["nct_id"],
        "title":              study["brief_title"],
        "summary":            summary,
        "sponsor":            study["sponsor"],
        "phase":              study["phase"],
        "status":             study["overall_status"],
        "date":               date_str,
        "confidence":         "HIGH",
        "strategic_relevance": (
            f"Active {study['phase']} competitor trial in {brand_name} indication space "
            f"({cond_str}). Monitor for data readout."
        ),
        "function_owner":       "Market Access",
        "recommended_action": (
            f"Track {study['sponsor']} trial {study['nct_id']} for data readout. "
            f"Assess competitive impact on {brand_name} positioning."
        ),
    }


def to_milestone_alert(study: dict, apex_id: str, brand_name: str) -> dict | None:
    """
    Convert a study with an upcoming primary completion date into an
    APEX milestone_alert entry. Returns None if out of horizon or J&J.
    """
    if _is_jnj(study["sponsor"]):
        return None

    pcd = (study.get("primary_completion_date") or "").strip()
    if not pcd:
        return None

    try:
        completion = datetime.date.fromisoformat(pcd[:10])
        today      = datetime.date.today()
        days_out   = (completion - today).days
        if days_out < 0 or days_out > MILESTONE_HORIZON_DAYS:
            return None
    except ValueError:
        return None

    return {
        "apex_id":          apex_id,
        "milestone_type":   "COMPETITOR_READOUT",
        "milestone_label":  (
            f"Competitor trial readout — {study['sponsor']} "
            f"({study['nct_id']}) in {brand_name} space"
        ),
        "milestone_date":   pcd[:10],
        "document_id":      f"CT-{study['nct_id']}",
        "days_to_event":    days_out,
        "source":           "ClinicalTrials.gov",
        "sponsor":          study["sponsor"],
        "phase":            study["phase"],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run: bool = False, verbose: bool = False) -> int:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)

    # Load asset registry
    if not REGISTRY_PATH.exists():
        print(f"ERROR: Registry not found: {REGISTRY_PATH}", file=sys.stderr)
        return 1
    registry_raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assets = (
        registry_raw.get("assets", registry_raw)
        if isinstance(registry_raw, dict) else registry_raw
    )

    # Load dashboard JSON
    if not DASHBOARD_PATH.exists():
        print(f"ERROR: Dashboard JSON not found: {DASHBOARD_PATH}", file=sys.stderr)
        return 1
    dashboard = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))

    all_ci_entries  = []
    all_ms_entries  = {}   # apex_id -> [alerts]
    debug_payload   = {}

    for asset in assets:
        apex_id    = asset.get("apex_id") or asset.get("asset_id", "")
        brand_name = asset.get("brand_name", apex_id)
        indication = asset.get("indication", "")

        cond_query = (
            indication
            if indication and indication not in ("", "[TO BE FILLED]")
            else INDICATION_FALLBACK.get(apex_id, brand_name)
        )

        if verbose:
            print(f"  [{apex_id}] {brand_name}: querying '{cond_query}'")

        studies_raw = fetch_trials(cond_query)
        debug_payload[apex_id] = {
            "query":     cond_query,
            "returned":  len(studies_raw),
            "studies":   studies_raw,
        }

        if verbose:
            print(f"    -> {len(studies_raw)} studies returned")

        asset_ms = []
        for s_raw in studies_raw:
            study = extract_study_fields(s_raw)

            ci_entry = to_competitive_intel(study, apex_id, brand_name)
            if ci_entry:
                all_ci_entries.append(ci_entry)

            ms_entry = to_milestone_alert(study, apex_id, brand_name)
            if ms_entry:
                asset_ms.append(ms_entry)

        if asset_ms:
            all_ms_entries[apex_id] = asset_ms

        time.sleep(RATE_LIMIT_S)

    # Write debug output
    today_str  = datetime.date.today().isoformat()
    debug_path = DEBUG_DIR / f"clinicaltrials_debug_{today_str}.json"
    debug_path.write_text(
        json.dumps(debug_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    total_ci = len(all_ci_entries)
    total_ms = sum(len(v) for v in all_ms_entries.values())

    print(
        f"\nResults: {total_ci} competitor signals, "
        f"{total_ms} milestone alerts"
    )
    if verbose:
        print(f"Debug output written: {debug_path}")

    if dry_run:
        print("Dry run — dashboard JSON not modified.")
        return 0

    # ---- Patch dashboard JSON ----

    # competitive_intel: merge by nct_id to avoid duplicates
    existing_ci = dashboard.get("competitive_intel", {})
    if not isinstance(existing_ci, dict):
        existing_ci = {}

    by_asset = {}
    for entry in all_ci_entries:
        by_asset.setdefault(entry["apex_id"], []).append(entry)

    for aid, new_entries in by_asset.items():
        existing      = existing_ci.get(aid, [])
        existing_ncts = {e.get("nct_id") for e in existing if e.get("nct_id")}
        deduped       = [e for e in new_entries if e["nct_id"] not in existing_ncts]
        existing_ci[aid] = existing + deduped

    dashboard["competitive_intel"] = existing_ci

    # milestone_alerts: merge by document_id to avoid duplicates
    existing_ms = dashboard.get("milestone_alerts", {})
    if not isinstance(existing_ms, dict):
        existing_ms = {}

    for aid, new_alerts in all_ms_entries.items():
        existing    = existing_ms.get(aid, [])
        existing_docs = {a.get("document_id") for a in existing if a.get("document_id")}
        deduped     = [a for a in new_alerts if a["document_id"] not in existing_docs]
        existing_ms[aid] = existing + deduped

    dashboard["milestone_alerts"] = existing_ms

    # Connector metadata
    dashboard.setdefault("data_sources", {})["clinicaltrials"] = {
        "last_run":              datetime.datetime.utcnow().isoformat() + "Z",
        "signals_added":         total_ci,
        "milestone_alerts_added": total_ms,
    }

    DASHBOARD_PATH.write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"Dashboard patched: {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ClinicalTrials.gov -> APEX signal connector"
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
