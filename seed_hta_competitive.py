"""
seed_hta_competitive.py
=======================
Patches comm-ex/outputs/comm_ex_dashboard_ready.json with realistic demo
data for hta_events and competitive_intel across all 7 APEX assets.

Run from the repo root:
    python seed_hta_competitive.py

Safe to re-run: existing hta_events / competitive_intel keys are replaced.
All other keys in the JSON are preserved untouched.
"""

import json
import pathlib
import sys

DASHBOARD_PATH = pathlib.Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"


# ---------------------------------------------------------------------------
# HTA Events  (apex_id -> list of event dicts)
# ---------------------------------------------------------------------------
HTA_EVENTS = {
    "APEX-001": [
        {
            "apex_id": "APEX-001",
            "hta_body": "NICE",
            "decision_type": "POSITIVE",
            "indication": "Relapsed/Refractory Multiple Myeloma (3L+)",
            "decision_date": "2025-Q3",
            "reimbursement_strategy": (
                "Recommended for use within NHS England via Cancer Drugs Fund. "
                "Managed access agreement in place with annual clinical review. "
                "Subcutaneous formulation approved for home administration pathway."
            ),
            "evidence_gap": "Long-term OS data pending 5-year POLLUX/CASTOR follow-up",
        },
        {
            "apex_id": "APEX-001",
            "hta_body": "EUnetHTA",
            "decision_type": "POSITIVE",
            "indication": "Multiple Myeloma (2L+, transplant-ineligible)",
            "decision_date": "2025-Q2",
            "reimbursement_strategy": (
                "Joint clinical assessment concluded added therapeutic benefit "
                "versus bortezomib-based SoC. National P&R negotiations ongoing "
                "in DE, FR, IT. Risk-share arrangements expected in price-sensitive markets."
            ),
            "evidence_gap": "Comparative OS data vs. KRd needed for DE AMNOG dossier",
        },
    ],
    "APEX-002": [
        {
            "apex_id": "APEX-002",
            "hta_body": "NICE",
            "decision_type": "RESTRICTED",
            "indication": "RRMM (4L+ post ASCT and prior IMiD/PI/anti-CD38)",
            "decision_date": "2026-Q1",
            "reimbursement_strategy": (
                "Recommended only within a CDF managed access scheme due to ICER "
                "threshold breach at list price. Patient Access Scheme (confidential "
                "discount) submitted. Mandatory patient-level outcome data collection "
                "required for continuation review in 24 months."
            ),
            "evidence_gap": "OS maturity insufficient at data cut; PFS2 data requested by committee",
        },
        {
            "apex_id": "APEX-002",
            "hta_body": "ICER",
            "decision_type": "RESTRICTED",
            "indication": "RRMM (3L+)",
            "decision_date": "2026-Q2",
            "reimbursement_strategy": (
                "ICER found ciltacabtagene autoleucel cost-effective only at a "
                "net price of ~$380,000–$410,000 (vs. WAC ~$465,000). Negotiated "
                "outcomes-based contracts with 3 major PBMs in discussion. "
                "Manufacturing throughput constraints limiting access independently."
            ),
            "evidence_gap": "Real-world durability data post 24 months; CARTITUDE-4 longer follow-up",
        },
    ],
    "APEX-003": [
        {
            "apex_id": "APEX-003",
            "hta_body": "NICE",
            "decision_type": "POSITIVE",
            "indication": "NSCLC with EGFR Exon 20 insertion mutations (1L+)",
            "decision_date": "2026-Q2",
            "reimbursement_strategy": (
                "Recommended as routine commissioning within NHS England. "
                "Companion diagnostic (OncomineDx) funded through NHSE molecular "
                "testing programme. CMAP registry enrolment required for continued access."
            ),
            "evidence_gap": "OS data immature at approval; 36-month landmark analysis expected 2027",
        },
        {
            "apex_id": "APEX-003",
            "hta_body": "EUnetHTA",
            "decision_type": "RESTRICTED",
            "indication": "2L+ NSCLC post-platinum (Exon 20 insertion)",
            "decision_date": "2026-Q3",
            "reimbursement_strategy": (
                "Joint assessment concluded 'added benefit — non-quantifiable' "
                "due to absence of head-to-head versus osimertinib in this setting. "
                "National negotiations in FR, ES expected to require registry-linked "
                "outcomes data. DE AMNOG review requesting ITC submission."
            ),
            "evidence_gap": "No direct comparison vs. osimertinib; ITC quality disputed by GBA",
        },
    ],
    "APEX-004": [
        {
            "apex_id": "APEX-004",
            "hta_body": "NICE",
            "decision_type": "POSITIVE",
            "indication": "Moderate-to-severe plaque psoriasis (biologic-naive and experienced)",
            "decision_date": "2025-Q1",
            "reimbursement_strategy": (
                "Recommended as a treatment option within the IL-23 inhibitor class. "
                "NICE confirmed superiority versus ustekinumab and non-inferiority "
                "versus other IL-23s. List price accepted; no patient access scheme required."
            ),
            "evidence_gap": "Long-term cardiovascular safety follow-up (VOYAGE 5-year extension)",
        },
        {
            "apex_id": "APEX-004",
            "hta_body": "EUnetHTA",
            "decision_type": "POSITIVE",
            "indication": "Psoriatic Arthritis (biologic-naive)",
            "decision_date": "2025-Q4",
            "reimbursement_strategy": (
                "Joint assessment confirmed added benefit in PsA with predominant "
                "skin involvement. Accepted across majority of EU5 markets. "
                "Spain requires AEMPS registry. Italy requires cost-sharing agreement."
            ),
            "evidence_gap": "Radiographic progression data at 2-year mark not yet mature",
        },
    ],
    "APEX-005": [
        {
            "apex_id": "APEX-005",
            "hta_body": "EUnetHTA",
            "decision_type": "RESTRICTED",
            "indication": "Generalised Myasthenia Gravis (anti-AChR+ or anti-MuSK+)",
            "decision_date": "2026-Q3",
            "reimbursement_strategy": (
                "Early assessment (Article 5(1)) initiated pre-approval. Preliminary "
                "opinion acknowledges unmet need but requests comparative evidence "
                "versus eculizumab and efgartigimod. Adaptive pathway designation "
                "under discussion with EMA. Risk-sharing model expected."
            ),
            "evidence_gap": "No head-to-head vs. FcRn class competitors; OS/QoL endpoints needed",
        },
        {
            "apex_id": "APEX-005",
            "hta_body": "ICER",
            "decision_type": "RESTRICTED",
            "indication": "gMG — refractory, anti-AChR+",
            "decision_date": "2026-Q4",
            "reimbursement_strategy": (
                "ICER pre-launch economic model review suggests cost-effectiveness "
                "threshold likely exceeded at anticipated WAC unless outcomes-based "
                "contract structured around MGFA-PIS responder rates. "
                "J&J Market Access is modelling 3 pricing scenarios for ICER submission."
            ),
            "evidence_gap": "ICER requesting blinded 6-month remission rate from Phase 3 FJORD trial",
        },
    ],
    "APEX-006": [
        {
            "apex_id": "APEX-006",
            "hta_body": "NICE",
            "decision_type": "RESTRICTED",
            "indication": "Treatment-Resistant Depression (TRD) — add-on to oral antidepressant",
            "decision_date": "2025-Q2",
            "reimbursement_strategy": (
                "Recommended only within a managed access programme for patients "
                "who have failed ≥2 antidepressants. Administered in certified "
                "healthcare settings only. Cost-per-responder model with NHS England; "
                "outcomes collected via Optimise registry."
            ),
            "evidence_gap": "Long-term relapse prevention data >52 weeks; real-world dissociation rates",
        },
        {
            "apex_id": "APEX-006",
            "hta_body": "ICER",
            "decision_type": "POSITIVE",
            "indication": "TRD and MDD with acute suicidal ideation (MDSI)",
            "decision_date": "2024-Q4",
            "reimbursement_strategy": (
                "ICER 2024 review concluded esketamine is cost-effective in MDSI "
                "at current net price. TRD indication remains borderline; outcomes-based "
                "contracts with major payers tied to 6-month remission rates."
            ),
            "evidence_gap": "Comparative durability vs. emerging oral TRD agents (zuranolone, Auvelity)",
        },
    ],
    "APEX-007": [
        {
            "apex_id": "APEX-007",
            "hta_body": "NICE",
            "decision_type": "POSITIVE",
            "indication": "Relapsing Multiple Sclerosis (RMS)",
            "decision_date": "2026-Q1",
            "reimbursement_strategy": (
                "Recommended as a treatment option for adults with active RMS. "
                "Positioned within NHS treatment algorithm between high-efficacy "
                "oral agents and IV anti-CD20 therapies. No patient access scheme; "
                "SMC Scotland review pending Q3 2026."
            ),
            "evidence_gap": "Long-term lymphocyte recovery data post-discontinuation; 5-year follow-up",
        },
        {
            "apex_id": "APEX-007",
            "hta_body": "EUnetHTA",
            "decision_type": "POSITIVE",
            "indication": "Relapsing-Remitting MS (RRMS)",
            "decision_date": "2026-Q2",
            "reimbursement_strategy": (
                "Joint assessment confirmed moderate added benefit vs. teriflunomide "
                "and dimethyl fumarate. Accepted across DE, FR, IT at submitted price. "
                "ES requires post-marketing registry. Reimbursement in NL pending "
                "ZIN guidance expected Q4 2026."
            ),
            "evidence_gap": "Comparative MRI activity data vs. ofatumumab at 2-year mark",
        },
    ],
}

# ---------------------------------------------------------------------------
# Competitive Intel  (apex_id -> list of action_plan dicts)
# ---------------------------------------------------------------------------
COMPETITIVE_INTEL = {
    "APEX-001": [
        {
            "apex_id": "APEX-001",
            "threat_event": "Biosimilar Daratumumab PDUFA 2026-Q3",
            "function_owner": "Market Access",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Initiate renegotiation of top-5 payer contracts with volume-based "
                "rebate guarantees before biosimilar entry. Quantify formulary "
                "displacement risk per plan and escalate to GCSO for pricing authority."
            ),
            "kpi": "Maintain formulary position in >90% of commercial plans",
            "escalation_flag": True,
        },
        {
            "apex_id": "APEX-001",
            "threat_event": "Elrexfio (elranatamab) BCMA BiTE 1L approval filing",
            "function_owner": "Medical Affairs",
            "priority": "STRATEGIC",
            "action_30d": (
                "Commission rapid evidence synthesis comparing MAJESTAD-B vs. "
                "POLLUX/CASSINI outcomes. Develop clinical differentiation narrative "
                "for KOL engagement: depth/duration of response, MRD negativity rates, "
                "and admin convenience of Darzalex SC vs. IV bispecific."
            ),
            "kpi": "KOL differentiation deck deployed to top-50 accounts by end of month",
            "escalation_flag": False,
        },
        {
            "apex_id": "APEX-001",
            "threat_event": "Talquetamab (Talvey) share expansion in 3L+ MM",
            "function_owner": "Marketing",
            "priority": "MONITOR",
            "action_30d": (
                "Track real-world prescribing shift data from IQVIA monthly. "
                "Prepare patient support programme enhancements (co-pay card refresh) "
                "for Q3 counter-detailing campaign if share erosion exceeds 3 pts."
            ),
            "kpi": "Market share erosion <3 pts in 3L+ segment Q3 2026",
            "escalation_flag": False,
        },
    ],
    "APEX-002": [
        {
            "apex_id": "APEX-002",
            "threat_event": "Ide-cel (Abecma) label expansion to 2L+",
            "function_owner": "Market Access",
            "priority": "IMMEDIATE",
            "action_30d": (
                "File differentiation dossier with top-10 IDN formulary committees "
                "within 30 days of ide-cel label update. Emphasise CARTITUDE-4 "
                "ORR and durability superiority. Secure preferred formulary tier "
                "before ide-cel contracting cycle opens."
            ),
            "kpi": "Preferred formulary status retained in top-10 IDN accounts",
            "escalation_flag": True,
        },
        {
            "apex_id": "APEX-002",
            "threat_event": "CAR-T manufacturing slot scarcity driving share loss",
            "function_owner": "Marketing",
            "priority": "STRATEGIC",
            "action_30d": (
                "Deploy Carvykti cell therapy coordinator resources to top-30 "
                "treatment centres to reduce slot-request-to-infusion cycle time. "
                "Develop slot availability dashboard for MSL use. Liaise with "
                "Operations on Ghent site capacity expansion timeline."
            ),
            "kpi": "Vein-to-vein time <6 weeks in 80% of treated patients",
            "escalation_flag": False,
        },
    ],
    "APEX-003": [
        {
            "apex_id": "APEX-003",
            "threat_event": "Osimertinib label expansion into Exon 20 insertion NSCLC",
            "function_owner": "Medical Affairs",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Initiate rapid ITC vs. osimertinib in Exon 20 population using "
                "individual patient data from PAPILLON. Brief top-30 thoracic oncology "
                "KOLs on mechanistic differentiation (bispecific EGFR-MET vs. mono EGFR TKI). "
                "Submit ITC to GBA for AMNOG dossier."
            ),
            "kpi": "ITC manuscript submitted within 45 days; KOL brief completed in 30",
            "escalation_flag": True,
        },
        {
            "apex_id": "APEX-003",
            "threat_event": "Furmonertinib (new EGFR TKI) EU filing — Q3 2026",
            "function_owner": "Market Access",
            "priority": "STRATEGIC",
            "action_30d": (
                "Model payer impact scenarios for furmonertinib entry. Prepare "
                "value dossier update emphasising Rybrevant+chemo OS advantage "
                "and Exon 20-specific biomarker testing pathway investment. "
                "Brief NHS England on testing programme expansion."
            ),
            "kpi": "Updated value dossier distributed to EU5 payers before furmonertinib filing",
            "escalation_flag": False,
        },
    ],
    "APEX-004": [
        {
            "apex_id": "APEX-004",
            "threat_event": "Biosimilar secukinumab (Cosentyx) US entry 2026-Q2",
            "function_owner": "Market Access",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Activate IL-17 vs. IL-23 class differentiation messaging with "
                "managed care partners. Deploy updated co-pay programme to close "
                "OOP gap vs. biosimilar IL-17. Renew multi-year payer contracts "
                "with step-therapy exclusion clauses before biosimilar launch."
            ),
            "kpi": "Step-therapy exclusion maintained in plans covering >40% of commercial lives",
            "escalation_flag": True,
        },
        {
            "apex_id": "APEX-004",
            "threat_event": "Bimekizumab (Bimzelx) IL-17A/F penetration in biologic-naive",
            "function_owner": "Marketing",
            "priority": "STRATEGIC",
            "action_30d": (
                "Reposition Tremfya in biologic-naive segment with safety-first "
                "messaging: superior CV safety profile, no new-onset Crohn's signal. "
                "Develop 3-year durability data package for dermatologists. "
                "Launch 'Total Skin Clearance' campaign update."
            ),
            "kpi": "Biologic-naive new patient share held above 22% through Q3",
            "escalation_flag": False,
        },
    ],
    "APEX-005": [
        {
            "apex_id": "APEX-005",
            "threat_event": "Efgartigimod SC (Vyvgart Hytrulo) penetration in gMG",
            "function_owner": "Market Access",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Develop health-economic model comparing nipocalimab vs. efgartigimod "
                "on cost-per-responder basis using Phase 3 FJORD data. Pre-brief "
                "top-5 US neuromuscular payers on mechanism differentiation "
                "(neonatal FcRn half-life extension vs. IgG degradation)."
            ),
            "kpi": "HE model approved by HEOR team; payer pre-brief deck ready by Day 30",
            "escalation_flag": True,
        },
        {
            "apex_id": "APEX-005",
            "threat_event": "Rozanolixizumab (Rystiggo) label broadening to seronegative gMG",
            "function_owner": "Medical Affairs",
            "priority": "STRATEGIC",
            "action_30d": (
                "Commission systematic review of anti-MuSK+ and seronegative gMG "
                "response data across FcRn inhibitor class. Develop scientific platform "
                "for ASN 2026 abstract. Brief gMG KOL advisory board on sub-group "
                "analysis from FJORD."
            ),
            "kpi": "ASN abstract submitted; KOL advisory board convened with ≥8 key accounts",
            "escalation_flag": False,
        },
        {
            "apex_id": "APEX-005",
            "threat_event": "Pre-launch label scope — narrow vs. broad gMG population",
            "function_owner": "Regulatory",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Confirm FDA labelling strategy for anti-AChR+ vs. pan-antibody-positive "
                "populations. Submit labelling negotiations briefing to GCSO. "
                "Assess label breadth impact on ICER economic model and "
                "patient access programme design."
            ),
            "kpi": "Regulatory labelling position paper finalised and shared with Commercial team",
            "escalation_flag": True,
        },
    ],
    "APEX-006": [
        {
            "apex_id": "APEX-006",
            "threat_event": "Zuranolone (Zurzuvae) oral GABA TRD penetration",
            "function_owner": "Marketing",
            "priority": "STRATEGIC",
            "action_30d": (
                "Develop Spravato vs. zuranolone clinical differentiation toolkit "
                "for psychiatrists: rapid onset in SI, in-clinic administration model, "
                "maintenance dosing protocol. Refresh HCP-facing digital assets with "
                "SUSTAIN-3 long-term remission data."
            ),
            "kpi": "Updated HCP toolkit deployed to field force; adoption rate tracked at 30 days",
            "escalation_flag": False,
        },
        {
            "apex_id": "APEX-006",
            "threat_event": "Payer restriction tightening — TRD step-edit to ≥3 prior agents",
            "function_owner": "Market Access",
            "priority": "IMMEDIATE",
            "action_30d": (
                "Engage top-10 commercial payers to resist step-edit escalation from "
                "≥2 to ≥3 prior agents. Provide real-world evidence from Optimise "
                "registry on outcomes at ≥2 failure. File appeal with CVS/ESI and "
                "present to Express Scripts P&T committee."
            ),
            "kpi": "Step-edit criteria held at ≥2 agents in plans covering >50% of TRD patients",
            "escalation_flag": True,
        },
    ],
    "APEX-007": [
        {
            "apex_id": "APEX-007",
            "threat_event": "Ofatumumab (Kesimpta) self-injection convenience advantage",
            "function_owner": "Medical Affairs",
            "priority": "STRATEGIC",
            "action_30d": (
                "Commission comparative adherence analysis Ponvory vs. ofatumumab "
                "using specialty pharmacy data. Develop MSL briefing on lymphocyte "
                "recovery advantages of Ponvory (no B-cell depletion; faster immune "
                "reconstitution post-stop). Target neuro KOLs at ECTRIMS 2026."
            ),
            "kpi": "Adherence analysis completed; MSL briefing deployed to top-25 MS centres",
            "escalation_flag": False,
        },
        {
            "apex_id": "APEX-007",
            "threat_event": "BTK inhibitor pipeline (fenebrutinib Phase 3 readout 2026-Q4)",
            "function_owner": "Marketing",
            "priority": "MONITOR",
            "action_30d": (
                "Monitor FENWAY Phase 3 topline results. Prepare scenario-based "
                "response plans for positive, neutral, and negative BTK readout. "
                "Develop 'established oral efficacy' messaging platform for Ponvory "
                "as proven alternative vs. investigational pipeline."
            ),
            "kpi": "BTK response scenarios approved by brand team before Q4 data readout",
            "escalation_flag": False,
        },
        {
            "apex_id": "APEX-007",
            "threat_event": "Ublituximab (Briumvi) anti-CD20 IV gaining KOL preference",
            "function_owner": "Market Access",
            "priority": "STRATEGIC",
            "action_30d": (
                "Develop formulary access strategy positioning Ponvory as preferred "
                "oral option for patients declining IV therapy or at elevated infection "
                "risk. Engage IDN pharmacy directors with cost-of-care model "
                "(no pre-medication, no infusion suite cost)."
            ),
            "kpi": "Formulary preferred oral tier secured in 5 additional IDNs this quarter",
            "escalation_flag": False,
        },
    ],
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not DASHBOARD_PATH.exists():
        print(f"ERROR: Dashboard JSON not found at: {DASHBOARD_PATH}")
        print("Run the APEX pipeline first to generate comm_ex_dashboard_ready.json")
        sys.exit(1)

    print(f"Reading: {DASHBOARD_PATH}")
    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        data = json.load(f)

    # Patch in the seed data
    data["hta_events"] = HTA_EVENTS
    data["competitive_intel"] = COMPETITIVE_INTEL

    with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("SUCCESS: Dashboard JSON patched.")
    print(f"  hta_events   : {sum(len(v) for v in HTA_EVENTS.values())} events across {len(HTA_EVENTS)} assets")
    print(f"  competitive_intel: {sum(len(v) for v in COMPETITIVE_INTEL.values())} plans across {len(COMPETITIVE_INTEL)} assets")

    # Quick verification
    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        check = json.load(f)
    assert check.get("hta_events"), "hta_events empty after write"
    assert check.get("competitive_intel"), "competitive_intel empty after write"
    print("Verification passed: both keys present and non-empty.")


if __name__ == "__main__":
    main()
