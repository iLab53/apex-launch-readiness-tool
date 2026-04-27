# AI & Digital Transformation Tool
## Johnson & Johnson Innovative Medicine — Commercial Intelligence Platform

A pharma-specific intelligence pipeline that translates regulatory and market signals into structured commercialization recommendations for J&J's 3M teams: **Marketing**, **Medical Affairs**, and **Market Access**.

---

## What This Tool Does

1. **Collects** live intelligence from 15+ regulatory and market sources (FDA, EMA, NICE, CMS, ICER, ClinicalTrials.gov, WHO, and more)
2. **Processes** signals through a multi-agent quality pipeline: source validation → confidence scoring → evidence grading → HITL review → adversarial challenge → deduplication
3. **Generates** a pharma executive briefing covering market access signals, pipeline/competitive signals, and HTA decisions
4. **Produces** Comm Ex recommendations — structured, executable commercialization actions with named owners, measurable KPIs, and risk-if-no-action consequences
5. **Surfaces** everything in a Streamlit dashboard built for GCSO leadership

---

## Folder Structure

```
06_AI_DIGITAL_TRANSFORM/
│
├── run_comm_ex.py              ← Main entry point (full pipeline or phase-by-phase)
├── requirements.txt
├── README.md
│
├── strategist-engine/          ← Multi-agent intelligence pipeline (pharma-adapted)
│   ├── strategist_hello.py     ← Coordinator: Phase 1 (collect) → Phase 2 (HITL) → Phase 3 (adversarial)
│   ├── sources.py              ← Pharma source registry (FDA, EMA, NICE, CMS, ICER, etc.)
│   ├── output_formatter.py     ← Briefing generation + JSON report + comm ex hook
│   ├── hitl_gate.py            ← Human-in-the-loop quality gate (Claude-powered)
│   ├── adversarial_reviewer.py ← Adversarial challenge agent
│   ├── deduplicator.py         ← Cross-region signal deduplication
│   ├── confidence_scorer.py    ← Signal confidence scoring
│   ├── evidence_grader.py      ← Evidence quality grading
│   ├── source_validator.py     ← Source credibility validation
│   ├── decision_quality_reviewer.py ← DQ review of final briefing
│   ├── partner_editor.py       ← Editorial polish pass
│   ├── business_impact_scorer.py    ← Business impact assessment
│   ├── run_memory.py           ← Run history persistence
│   └── reports/                ← Output: strategist_run_*.json, strategist_briefing_*.html
│
├── comm-ex/                    ← Commercialization Excellence layer
│   ├── comm_ex_generator.py    ← Director of Comm Ex AI persona + recommendation engine
│   └── outputs/                ← Output: comm_ex_recommendations_*.json, comm_ex_summary_*.txt,
│                                          comm_ex_dashboard_ready.json
│
└── dashboard/
    └── streamlit_app.py        ← Pharma intelligence dashboard (6 tabs)
```

---

## What Was Adapted from the STRATEGIST Project

| Component | STRATEGIST (Anthropic Project) | AI & Digital Transform (J&J) |
|-----------|-------------------------------|------------------------------|
| **Sources** | ~69 financial regulators (SEC, ESMA, FCA, etc.) | 15+ pharma agencies (FDA, EMA, NICE, CMS, ICER, etc.) |
| **Briefing persona** | McKinsey partner for macro hedge fund CIO | McKinsey partner for pharma CCO / Market Access / Brand |
| **Briefing sections** | Regulatory enforcement, systemic risk, macro | Market access & pricing, pipeline & competitive, HTA |
| **Recommendation layer** | Investment recs (OPEN/ACTIVE/CLOSED lifecycle, PnL tracking) | Comm Ex recs (PRE-LAUNCH/LAUNCH/POST-LAUNCH, 3M function owners) |
| **Dashboard** | 7 tabs incl. financial investment rec review | 6 tabs focused on pharma signals and Comm Ex |
| **Multi-agent pipeline** | Identical — all quality agents reused | Identical — all quality agents reused |

The core multi-agent engine (HITL gate, adversarial reviewer, deduplicator, confidence scorer, evidence grader, decision quality reviewer, partner editor) is **shared and unchanged**. Only the sources, briefing prompts, and recommendation layer are pharma-specific.

---

## Setup

### 1. Create a virtual environment

```bash
cd "06_AI_DIGITAL_TRANSFORM"
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your Anthropic API key

```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Mac/Linux
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Running the Pipeline

### Full pipeline (engine + Comm Ex)
```bash
python run_comm_ex.py
```

### Comm Ex only (uses latest briefing — faster for iteration)
```bash
python run_comm_ex.py --comm-ex-only
```

### Engine only (collect signals + briefing, skip Comm Ex)
```bash
python run_comm_ex.py --engine-only
```

### Launch the dashboard
```bash
cd dashboard
streamlit run streamlit_app.py
```

---

## Output Files

| File | Location | Description |
|------|----------|-------------|
| `strategist_run_*.json` | `strategist-engine/reports/` | Full pipeline run: signals, analytics, briefing text, DQ review |
| `strategist_briefing_*.html` | `strategist-engine/reports/` | Formatted HTML executive briefing |
| `comm_ex_recommendations_*.json` | `comm-ex/outputs/` | Structured Comm Ex recs (one file per run) |
| `comm_ex_summary_*.txt` | `comm-ex/outputs/` | Plain-text executive summary for GCSO leadership |
| `comm_ex_dashboard_ready.json` | `comm-ex/outputs/` | Aggregated KPIs, always overwritten with latest run |

---

## Comm Ex Recommendation Schema

Each recommendation includes:

| Field | Description |
|-------|-------------|
| `rec_id` | Unique ID: `COMMEX-{run_id}-{nn}` |
| `therapeutic_area` | Oncology / Immunology / Neuroscience / General |
| `asset_stage` | PRE-LAUNCH / LAUNCH / POST-LAUNCH |
| `target` | Specific drug class, portfolio segment, or capability |
| `why_this_matters` | Named signal → direct commercial implication |
| `recommended_action` | Specific, executable action with strong verb |
| `function_owner` | Marketing / Medical Affairs / Market Access / Cross-functional |
| `timeline` | Immediate (0-30d) / Near-term (30-90d) / Mid-term (90-180d) |
| `expected_impact` | Revenue protection / access expansion / launch velocity / etc. |
| `kpi` | Measurable target with numeric value |
| `risk_if_no_action` | Specific consequence if action is not taken |
| `confidence` | HIGH / MEDIUM / LOW |
| `signal_source` | Exact source from the intelligence briefing |

### Mandatory distribution per run
- ≥ 2 PRE-LAUNCH recommendations
- ≥ 2 LAUNCH recommendations  
- ≥ 2 POST-LAUNCH recommendations
- ≥ 2 different function owners represented
- ≥ 1 Oncology therapeutic area
- ≥ 1 Immunology therapeutic area

---

## Intelligence Sources

### United States
- FDA Drug Approvals, Press Announcements, Warning Letters, MedWatch Safety Alerts
- CMS Medicare Coverage Decisions
- ICER Evidence Reports (drug pricing / value-based access)
- NIH Research News
- SEC EDGAR Pharma Filings (8-K)

### Europe
- EMA News and Press Releases
- NICE Technology Appraisals (UK HTA)
- EUnetHTA Joint Clinical Assessments

### Global
- WHO News
- ICH Guidelines
- ClinicalTrials.gov Recent Results
- IQVIA Institute Reports

### APAC / Canada
- TGA Approvals (Australia)
- Health Canada Drug Approvals

---

## Adding New Sources

Edit `strategist-engine/sources.py`. Each source entry:

```python
{
    "name":        "Source display name",
    "url":         "https://feed-url.xml",
    "type":        "rss",          # or "scrape", "api"
    "description": "What this source signals commercially",
    "requires_key": None,          # or "API_KEY_NAME"
    "enabled":     True,
}
```

Add to the appropriate country key in `COUNTRY_SOURCES`. Enable/disable entire regions via `ENABLED_REGIONS`.

---

## Architecture

```
RSS Feeds (15+ sources)
        ↓
  [Phase 1] Parallel collection + grading
    source_validator → confidence_scorer → evidence_grader
        ↓
  [Phase 2] Sequential HITL review (Claude)
    hitl_gate → deduplicator
        ↓
  [Phase 3] Parallel adversarial review (Claude)
    adversarial_reviewer
        ↓
  [output_formatter]
    decision_quality_reviewer → partner_editor
    → strategist_run_*.json
    → strategist_briefing_*.html
        ↓
  [comm_ex_generator]
    Director of Comm Ex AI persona (Claude)
    → comm_ex_recommendations_*.json
    → comm_ex_summary_*.txt
    → comm_ex_dashboard_ready.json
        ↓
  [Streamlit Dashboard]
    Dashboard / Signals / Briefing / Comm Ex / History / Export
```
