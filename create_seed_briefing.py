# create_seed_briefing.py -- run from repo root inside your venv
# python create_seed_briefing.py
# Creates a minimal seed briefing so --comm-ex-only can run without Phase 1.

import json
from datetime import datetime, timezone
from pathlib import Path

REPORTS_DIR = Path("strategist-engine") / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
briefing_path = REPORTS_DIR / f"strategist_briefing_{timestamp}.json"

briefing = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "source": "seed_briefing",
    "briefing_text": (
        "APEX Pharma Intelligence Briefing -- Seed Document\n\n"

        "REGULATORY SIGNALS\n"
        "FDA has issued updated guidance on biosimilar interchangeability standards. "
        "The agency is accelerating PDUFA review timelines for oncology assets with "
        "breakthrough therapy designation. EMA has published revised HTA cooperation "
        "framework under EUnetHTA 21, affecting joint clinical assessments for oncology "
        "and immunology indications launching after January 2025. "
        "NICE has issued final guidance on cost-effectiveness thresholds, maintaining "
        "the standard QALY threshold at GBP 20,000-30,000 with flexibility for "
        "end-of-life and rare disease modifiers. ICER has published updated evidence "
        "assessment reports for CD38-targeting agents in multiple myeloma.\n\n"

        "MARKET ACCESS SIGNALS\n"
        "CMS has finalized Medicare drug price negotiation selections for 2026, "
        "with implications for post-launch pricing strategy across immunology portfolio. "
        "Payer consolidation continues in commercial markets with three major PBMs "
        "tightening formulary criteria for CAR-T therapies. "
        "European reimbursement delays averaging 18 months post-EMA approval in "
        "key markets including Germany, France, and Italy.\n\n"

        "COMPETITIVE INTELLIGENCE\n"
        "Biosimilar competitor PDUFA date confirmed for Q3 2026 targeting the "
        "multiple myeloma indication. Three anti-CD38 biosimilars in Phase 3 "
        "with expected market entry 2027-2028. "
        "Competitor CAR-T asset received FDA approval for earlier line of therapy, "
        "creating competitive threat in the RRMM segment. "
        "Rival IL-23 inhibitor posted positive Phase 3 data in psoriatic arthritis, "
        "expanding the competitive landscape in immunology.\n\n"

        "HTA AND EVIDENCE GAPS\n"
        "NICE appraisal for Rybrevant in EGFR Exon 20 insertion NSCLC ongoing -- "
        "decision expected Q3 2026. Cost-effectiveness submission requires updated "
        "OS data from PAPILLON trial. EUnetHTA joint clinical assessment for "
        "nipocalimab in fetal and neonatal alloimmune thrombocytopenia in preparation. "
        "ICER review of CAR-T therapies in large B-cell lymphoma raised concerns "
        "about long-term durability evidence and real-world cost-effectiveness.\n\n"

        "CLINICAL AND REGULATORY MILESTONES\n"
        "Nipocalimab Phase 3 readout in generalised myasthenia gravis expected H2 2026. "
        "Rybrevant plus lazertinib combination sNDA submission planned Q2 2026. "
        "Tremfya Phase 3b data in Crohn's disease to be presented at major congress. "
        "Spravato real-world evidence publication planned for peer-reviewed journal Q3 2026. "
        "Ponvory long-term safety extension data available for regulatory submission.\n\n"

        "STRATEGIC PRIORITIES\n"
        "GCSO has identified Market Access readiness as the top commercial risk for "
        "assets entering launch phase in 2026-2027. Medical Affairs evidence generation "
        "plans require acceleration for HTA submissions. Marketing teams are prioritising "
        "disease awareness campaigns ahead of label expansions. "
        "Cross-functional alignment on payer value story for CAR-T portfolio is flagged "
        "as an immediate action item for the GCSO leadership team."
    ),
    "final_signals": [
        {
            "signal_id": "SIG-001",
            "source": "FDA",
            "signal_text": "FDA accelerating PDUFA review for oncology breakthrough therapy designations",
            "signal_type": "regulatory",
            "relevance_score": 0.92
        },
        {
            "signal_id": "SIG-002",
            "source": "NICE",
            "signal_text": "NICE appraisal for Rybrevant in EGFR Exon 20 NSCLC -- decision Q3 2026",
            "signal_type": "HTA",
            "relevance_score": 0.95
        },
        {
            "signal_id": "SIG-003",
            "source": "EUnetHTA",
            "signal_text": "EUnetHTA joint clinical assessment framework active for new oncology launches",
            "signal_type": "HTA",
            "relevance_score": 0.88
        },
        {
            "signal_id": "SIG-004",
            "source": "competitor",
            "signal_text": "Biosimilar PDUFA date Q3 2026 for multiple myeloma indication -- competitive threat",
            "signal_type": "competitive",
            "relevance_score": 0.94
        },
        {
            "signal_id": "SIG-005",
            "source": "CMS",
            "signal_text": "CMS Medicare drug price negotiation selections finalised for 2026",
            "signal_type": "market_access",
            "relevance_score": 0.87
        },
        {
            "signal_id": "SIG-006",
            "source": "ICER",
            "signal_text": "ICER cost-effectiveness review of CAR-T therapies raises long-term durability concerns",
            "signal_type": "HTA",
            "relevance_score": 0.89
        },
        {
            "signal_id": "SIG-007",
            "source": "EMA",
            "signal_text": "EMA HTA cooperation framework requiring joint clinical assessments post-January 2025",
            "signal_type": "regulatory",
            "relevance_score": 0.91
        }
    ],
    "top_risks": [
        {
            "risk_id": "RISK-001",
            "signal_text": "Biosimilar competitive threat in multiple myeloma -- PDUFA Q3 2026",
            "severity": "HIGH"
        },
        {
            "risk_id": "RISK-002",
            "signal_text": "CMS price negotiation impact on post-launch immunology portfolio",
            "severity": "HIGH"
        },
        {
            "risk_id": "RISK-003",
            "signal_text": "HTA evidence gaps for NICE Rybrevant appraisal -- OS data maturity",
            "severity": "MEDIUM"
        }
    ],
    "top_opportunities": [
        {
            "opportunity_id": "OPP-001",
            "signal_text": "FDA breakthrough therapy acceleration for oncology pipeline assets",
            "impact": "HIGH"
        },
        {
            "opportunity_id": "OPP-002",
            "signal_text": "Nipocalimab Phase 3 readout H2 2026 -- first-in-class positioning opportunity",
            "impact": "HIGH"
        }
    ]
}

briefing_path.write_text(json.dumps(briefing, indent=2), encoding="utf-8")
print(f"Seed briefing written: {briefing_path}")
print(f"Signals: {len(briefing['final_signals'])}")
print()
print("Now run:")
print("  python run_comm_ex.py --comm-ex-only")
