"""
seed_milestone_data.py
======================
Patches comm-ex/outputs/comm_ex_dashboard_ready.json with:

  milestone_alerts  -- upcoming governance/launch milestones per asset
  launch_readiness  -- LRS scores per asset (mirrors scorecard files)
  recs              -- GCSO Feed immediate actions (sourced from
                       existing immediate_actions key so the sidebar
                       Immediate Actions section is non-empty)

Run from the repo root:
    python seed_milestone_data.py

Safe to re-run: existing keys are replaced; all other keys preserved.
"""

import json
import pathlib
import sys

DASHBOARD_PATH = pathlib.Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"

# ---------------------------------------------------------------------------
# Milestone alerts  (apex_id -> list of milestone dicts)
# Dates relative to 2026-04-29.  days_to_event computed from that date.
# ---------------------------------------------------------------------------
MILESTONE_ALERTS = {
    "APEX-001": [
        {
            "apex_id": "APEX-001",
            "milestone_type": "GOVERNANCE",
            "milestone_label": "Annual Commercial Governance Review — Darzalex Portfolio",
            "milestone_date": "2026-06-15",
            "document_id": "MPDF-APEX001-GOV-20260615",
            "days_to_event": 47,
        },
    ],
    "APEX-002": [
        {
            "apex_id": "APEX-002",
            "milestone_type": "LRR",
            "milestone_label": "Launch Readiness Review Q3 — Carvykti",
            "milestone_date": "2026-07-31",
            "document_id": "MPDF-APEX002-LRR-20260731",
            "days_to_event": 93,
        },
        {
            "apex_id": "APEX-002",
            "milestone_type": "INVESTMENT_DECISION",
            "milestone_label": "Ghent Manufacturing Scale-Up Investment Decision",
            "milestone_date": "2026-09-15",
            "document_id": "MPDF-APEX002-INV-20260915",
            "days_to_event": 139,
        },
    ],
    "APEX-003": [
        {
            "apex_id": "APEX-003",
            "milestone_type": "LRP",
            "milestone_label": "Launch Readiness Plan Submission — Rybrevant EGFR Exon20",
            "milestone_date": "2026-06-30",
            "document_id": "MPDF-APEX003-LRP-20260630",
            "days_to_event": 62,
        },
        {
            "apex_id": "APEX-003",
            "milestone_type": "LRR",
            "milestone_label": "Launch Readiness Review Q3 — Rybrevant",
            "milestone_date": "2026-08-31",
            "document_id": "MPDF-APEX003-LRR-20260831",
            "days_to_event": 124,
        },
    ],
    "APEX-004": [
        {
            "apex_id": "APEX-004",
            "milestone_type": "GOVERNANCE",
            "milestone_label": "Immunology Portfolio Governance Review — Tremfya",
            "milestone_date": "2026-07-15",
            "document_id": "MPDF-APEX004-GOV-20260715",
            "days_to_event": 77,
        },
        {
            "apex_id": "APEX-004",
            "milestone_type": "ADP_REVIEW",
            "milestone_label": "Annual Development Plan Review — IBD Indication Expansion",
            "milestone_date": "2026-10-31",
            "document_id": "MPDF-APEX004-ADP-20261031",
            "days_to_event": 185,
        },
    ],
    "APEX-005": [
        {
            "apex_id": "APEX-005",
            "milestone_type": "ADP_REVIEW",
            "milestone_label": "Pre-Launch ADP Review — Nipocalimab gMG Label Strategy",
            "milestone_date": "2026-05-30",
            "document_id": "MPDF-APEX005-ADP-20260530",
            "days_to_event": 31,
        },
        {
            "apex_id": "APEX-005",
            "milestone_type": "LRP",
            "milestone_label": "Launch Readiness Plan — First Submission (gMG)",
            "milestone_date": "2026-06-30",
            "document_id": "MPDF-APEX005-LRP-20260630",
            "days_to_event": 62,
        },
        {
            "apex_id": "APEX-005",
            "milestone_type": "LRR",
            "milestone_label": "Launch Readiness Review — Nipocalimab Q3",
            "milestone_date": "2026-09-30",
            "document_id": "MPDF-APEX005-LRR-20260930",
            "days_to_event": 154,
        },
        {
            "apex_id": "APEX-005",
            "milestone_type": "INVESTMENT_DECISION",
            "milestone_label": "Commercial Investment Decision — gMG Launch Budget",
            "milestone_date": "2026-11-30",
            "document_id": "MPDF-APEX005-INV-20261130",
            "days_to_event": 215,
        },
    ],
    "APEX-006": [
        {
            "apex_id": "APEX-006",
            "milestone_type": "LRR",
            "milestone_label": "Annual Launch Review — Spravato GCSO Q3",
            "milestone_date": "2026-09-30",
            "document_id": "MPDF-APEX006-LRR-20260930",
            "days_to_event": 154,
        },
        {
            "apex_id": "APEX-006",
            "milestone_type": "GOVERNANCE",
            "milestone_label": "Year-End Governance Board — Neuroscience Portfolio",
            "milestone_date": "2026-12-15",
            "document_id": "MPDF-APEX006-GOV-20261215",
            "days_to_event": 230,
        },
    ],
    "APEX-007": [
        {
            "apex_id": "APEX-007",
            "milestone_type": "LRR",
            "milestone_label": "Launch Readiness Review Q2 — Ponvory",
            "milestone_date": "2026-06-30",
            "document_id": "MPDF-APEX007-LRR-20260630",
            "days_to_event": 62,
        },
        {
            "apex_id": "APEX-007",
            "milestone_type": "INVESTMENT_DECISION",
            "milestone_label": "Sales Force Expansion Investment Decision — MS Franchise",
            "milestone_date": "2026-08-15",
            "document_id": "MPDF-APEX007-INV-20260815",
            "days_to_event": 108,
        },
    ],
}

# ---------------------------------------------------------------------------
# Launch readiness scores  (mirrors scorecard file values from Day 4)
# ---------------------------------------------------------------------------
LAUNCH_READINESS = {
    "APEX-001": {"brand_name": "Darzalex",    "launch_readiness_score": 82, "status": "LAUNCH-READY"},
    "APEX-002": {"brand_name": "Carvykti",    "launch_readiness_score": 62, "status": "ON-TRACK"},
    "APEX-003": {"brand_name": "Rybrevant",   "launch_readiness_score": 72, "status": "ON-TRACK"},
    "APEX-004": {"brand_name": "Tremfya",     "launch_readiness_score": 72, "status": "ON-TRACK"},
    "APEX-005": {"brand_name": "Nipocalimab", "launch_readiness_score": 52, "status": "AT-RISK"},
    "APEX-006": {"brand_name": "Spravato",    "launch_readiness_score": 68, "status": "ON-TRACK"},
    "APEX-007": {"brand_name": "Ponvory",     "launch_readiness_score": 68, "status": "ON-TRACK"},
}


def main():
    if not DASHBOARD_PATH.exists():
        print(f"ERROR: Dashboard JSON not found at: {DASHBOARD_PATH}")
        sys.exit(1)

    print(f"Reading: {DASHBOARD_PATH}")
    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Patch milestone_alerts and launch_readiness
    data["milestone_alerts"] = MILESTONE_ALERTS
    data["launch_readiness"] = LAUNCH_READINESS

    # Fix GCSO Feed: copy immediate_actions into 'recs' so the sidebar
    # Immediate Actions section is non-empty (it reads d.get('recs', [])).
    # Each rec gets a synthetic urgency='Immediate' tag.
    imm_actions = data.get("immediate_actions", [])
    if imm_actions and not data.get("recs"):
        recs = []
        for item in imm_actions:
            rec = dict(item)
            rec.setdefault("urgency", "Immediate")
            rec.setdefault("rec_id", rec.get("action_id", "REC-???"))
            rec.setdefault("function_owner", rec.get("function", "Cross-functional"))
            rec.setdefault("recommended_action", rec.get("action", str(item)))
            recs.append(rec)
        data["recs"] = recs
        print(f"  recs: built {len(recs)} entries from immediate_actions")
    else:
        print("  recs: already present or no immediate_actions to copy")

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Verify
    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        check = json.load(f)

    total_milestones = sum(len(v) for v in MILESTONE_ALERTS.values())
    print("SUCCESS: Dashboard JSON patched.")
    print(f"  milestone_alerts : {total_milestones} milestones across {len(MILESTONE_ALERTS)} assets")
    print(f"  launch_readiness : {len(LAUNCH_READINESS)} assets seeded")
    assert check.get("milestone_alerts"), "milestone_alerts empty after write"
    assert check.get("launch_readiness"), "launch_readiness empty after write"
    print("Verification passed.")


if __name__ == "__main__":
    main()
