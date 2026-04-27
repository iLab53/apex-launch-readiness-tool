# output_formatter.py
import json, os, time, uuid
from datetime import datetime, timezone
from pathlib import Path
import anthropic
from decision_quality_reviewer import review_decision_quality
from partner_editor import partner_editor
from business_impact_scorer import business_impact_scorer
from run_memory import save_run_memory, build_trend_summary
# Comm Ex layer (pharma commercialization recommendations)
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent / "comm-ex"))
try:
    from comm_ex_generator import run as run_comm_ex, OUTPUT_DIR as COMM_EX_OUT
    COMM_EX_ENABLED = True
except ImportError:
    COMM_EX_ENABLED = False

REPORTS_DIR   = Path(__file__).parent / 'reports'
MODEL_SUMMARY = 'claude-sonnet-4-6'

# ─────────────────────────────────────────────────────────────────────────────
#  Analytics helper
# ─────────────────────────────────────────────────────────────────────────────

def _build_analytics(coordinator_result: dict, duration_s: float) -> dict:
    phase1_raw   = coordinator_result.get('phase1_raw', {})
    hitl_results = coordinator_result.get('hitl_results', {})
    final_sigs   = coordinator_result.get('final_signals', [])
    dedup_log    = coordinator_result.get('dedup_log', [])

    all_hitl = [s for sigs in hitl_results.values() for s in sigs]
    iters    = [s.get('iterations', 1) for s in final_sigs]

    return {
        'total_regions'          : len(phase1_raw),
        'total_raw_signals'      : sum(len(v) for v in phase1_raw.values()),
        'hitl_approved'          : sum(1 for s in all_hitl if s.get('hitl_decision') == 'APPROVED'),
        'hitl_rejections'        : sum(1 for s in all_hitl if s.get('hitl_decision') == 'REJECTED'),
        'hitl_modified'          : sum(1 for s in all_hitl if s.get('hitl_decision') == 'MODIFIED'),
        'dedup_removed'          : len(dedup_log),
        'adversarial_approved'   : sum(1 for s in final_sigs if s.get('adversarial_verdict') == 'APPROVED'),
        'adversarial_rejections' : sum(1 for s in final_sigs if s.get('adversarial_verdict') == 'REJECTED'),
        'challenge_count'        : sum(1 for s in final_sigs if s.get('adversarial_verdict') == 'CHALLENGE'),
        'avg_iterations'         : round(sum(iters) / len(iters), 2) if iters else 0.0,
        'pipeline_duration_s'    : round(duration_s, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Signal digest builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_signal_digest(signals: list[dict]) -> str:
    by_region: dict[str, list[str]] = {}

    for s in signals:
        region   = s.get('region', 'Global')
        country  = s.get('country', '')
        source   = s.get('source', '')
        headline = s.get('headline', '').strip()
        date     = s.get('publication_date', '')[:10]
        url      = s.get('source_url', '')

        if not headline:
            continue

        label = f"{country} ({source})" if country else source
        line  = f"  - [{date}] {label}: {headline}"
        if url:
            line += f"  -> {url}"

        by_region.setdefault(region, []).append(line)

    sections = []
    for region in sorted(by_region):
        items = by_region[region]
        sections.append(f"### {region} ({len(items)} signals)\n" + "\n".join(items[:40]))

    return "\n\n".join(sections)


# ─────────────────────────────────────────────────────────────────────────────
#  Strategic briefing generator
# ─────────────────────────────────────────────────────────────────────────────

BRIEFING_SYSTEM = """You are a senior McKinsey partner specializing in pharmaceutical \
commercialization, regulatory strategy, and market access.
You advise Chief Commercial Officers, Heads of Market Access, and Global Brand teams \
at top-10 pharmaceutical companies — with deep expertise in Oncology, Immunology, \
and Neuroscience.
You do not summarize regulatory news — you:
- identify what signals mean for drug approvals, label changes, and competitive positioning
- translate HTA decisions and payer signals into access strategy
- surface pipeline threats and launch timing risks before they are consensus
- recommend concrete actions for Marketing, Medical Affairs, and Market Access teams
Your output must be decisive, specific to pharma commercialization, and free of jargon."""

# Use PLACEHOLDER tokens instead of {format} variables so that any { } characters
# inside the digest (common in URLs and JSON snippets) never cause a KeyError.
BRIEFING_PROMPT = """\
Today is DATE_PLACEHOLDER. You have received pharma regulatory and market intelligence \
signals from NREGIONS_PLACEHOLDER regions covering NCOUNTRIES_PLACEHOLDER markets.

You are a senior McKinsey partner preparing a commercial intelligence briefing for the \
Chief Commercial Officer, Head of Global Market Access, and Global Brand leads at \
Johnson & Johnson Innovative Medicine (Oncology, Immunology, Neuroscience).

Your job is NOT to summarize regulatory news. Your job is to:
- identify what signals mean for drug launches, label changes, and competitive positioning
- translate HTA and payer decisions into access strategy implications
- surface pipeline threats before they become consensus
- tell the commercial leadership team what to do differently this week

This briefing must enable real decisions: launch sequencing, access negotiation, \
label strategy, and competitive response.

---
## HEADLINE (ONE SENTENCE ONLY)
- The single most commercially significant development across all signals today
- Must name a specific drug class, regulator, or market — no generics

---
## EXECUTIVE SUMMARY
Maximum 3 sentences:
1. What changed in the regulatory or competitive environment?
2. What is the direct commercial consequence for pharma?
3. What must leadership act on immediately?

---
## TOP 3 COMMERCIAL DECISIONS FOR LEADERSHIP
Exactly 3 decisions the commercial leadership team must make this week.
Each as a decision question:
1. Should we...
2. Should we...
3. Should we...

For each:
- Recommended answer
- Why now (not next quarter)
- Owner: CCO | Head of Market Access | Global Brand Lead | Medical Affairs | Regulatory

---
## TOP PRIORITIES THIS WEEK
The 2-3 most important developments. For each:
- **Priority**: Critical (7 days) | High (30 days) | Monitor
- What happened (1 sentence, name the agency or competitor)
- Commercial implication (access, pricing, launch timing, competitive share)
- **Who is most affected**: Oncology portfolio | Immunology assets | Neuroscience pipeline
- **Action (imperative verb + owner + timeframe)**

---
## KEY THEMES (3-5 ONLY)
Each theme must follow this structure exactly:
**Theme Title — insight-driven, not descriptive**
- What is happening (2 sentences, name agencies and assets)
- Commercial implication (launch risk, access barrier, pricing pressure, or opportunity)
- **Winners / Losers**: which companies or asset classes benefit vs. are disadvantaged

Do NOT restate signals. Synthesize across markets.

---
## MARKET ACCESS & PRICING SIGNALS
Only include if a material access or pricing signal occurred.
For each:
- Agency / payer / HTA body
- Decision or signal
- Impact on reimbursement, formulary position, or price negotiation

---
## PIPELINE & COMPETITIVE SIGNALS
Only include if a competitor NDA/BLA/MAA, trial readout, or label change affects J&J TAs.
For each:
- Competitor asset and indication
- Regulatory or clinical event
- Competitive response required

---
## SIGNALS REQUIRING IMMEDIATE ACTION
Maximum 5. For each:
- Event (1 line, name the regulator and drug class)
- Why commercially urgent
- **Action (imperative + function owner + timeframe)**

---
## COMMERCIAL RECOMMENDATIONS
3-5 total. Each:
**Verb + specific action + timeframe**
1 sentence explaining rationale tied to a named signal.
Example:
**Accelerate NICE submission for [asset] (30 days)**
ICER draft report signals pricing pressure will intensify; early HTA engagement \
reduces access delay by an estimated 2-3 months.

---
## TIME HORIZON
- **Immediate (0-30 days)**: launch or access decisions with hard deadlines
- **Near-term (1-3 months)**: label strategy, payer contracting, competitive response
- **Structural (6-18 months)**: pipeline sequencing, platform investment, TA positioning

---
## GUIDELINES (STRICT)
- Name drugs, agencies, and competitors — never be generic
- Do NOT treat all signals equally — most are noise
- Every section must enable a decision, not just inform
- Prioritise signals that affect J&J's three core TAs: Oncology, Immunology, Neuroscience

---
Signal Digest:
DIGEST_PLACEHOLDER
"""


def _generate_briefing(analytics: dict, signals: list[dict], run_date: str) -> str:
    if not signals:
        return "No signals were collected in this run. Check that RSS feeds are enabled and reachable."

    digest      = _build_signal_digest(signals)
    n_regions   = len(set(s.get('region', '?') for s in signals))
    n_countries = len(set(s.get('country', '?') for s in signals))

    # Use plain string replacement so { } chars in the digest never cause KeyError.
    prompt = (
        BRIEFING_PROMPT
        .replace('DATE_PLACEHOLDER',       run_date)
        .replace('NREGIONS_PLACEHOLDER',   str(n_regions))
        .replace('NCOUNTRIES_PLACEHOLDER', str(n_countries))
        .replace('DIGEST_PLACEHOLDER',     digest)
    )

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL_SUMMARY,
        max_tokens=4000,
        system=BRIEFING_SYSTEM,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return msg.content[0].text.strip()


# ─────────────────────────────────────────────────────────────────────────────
#  HTML report builder
# ─────────────────────────────────────────────────────────────────────────────

def _briefing_to_html(briefing_md: str, run_date: str, analytics: dict, signals: list[dict], decision_review: dict = None) -> str:
    import re

    # Strip any LLM preamble before the first ## section heading.
    # The model sometimes prepends "# STRATEGIC INTELLIGENCE BRIEFING" + a date
    # line, which are redundant with the HTML header and render as raw text.
    first_section = briefing_md.find('\n## ')
    if first_section != -1:
        briefing_md = briefing_md[first_section:].lstrip()

    def md_to_html(text: str) -> str:
        lines = text.split('\n')
        html_lines = []
        in_ul = False

        for line in lines:
            if line.startswith('## '):
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                html_lines.append('<h2>' + line[3:].strip() + '</h2>')
            elif line.startswith('### '):
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                html_lines.append('<h3>' + line[4:].strip() + '</h3>')
            elif re.match(r'^\d+\.', line.strip()):
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                content = re.sub(r'^\d+\.\s*', '', line.strip())
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                content = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', content)
                html_lines.append('<p class="numbered">' + content + '</p>')
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_ul:
                    html_lines.append('<ul>'); in_ul = True
                content = line.strip().lstrip('-').lstrip('*').strip()
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                content = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', content)
                html_lines.append('<li>' + content + '</li>')
            elif line.strip() == '---':
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                html_lines.append('<hr>')
            elif not line.strip():
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                html_lines.append('')
            else:
                if in_ul:
                    html_lines.append('</ul>'); in_ul = False
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line.strip())
                content = re.sub(r'\*([^*]+?)\*', r'<em>\1</em>', content)
                if content:
                    html_lines.append('<p>' + content + '</p>')

        if in_ul:
            html_lines.append('</ul>')
        return '\n'.join(html_lines)

    region_counts = {}
    for s in signals:
        r = s.get('region', 'Other')
        region_counts[r] = region_counts.get(r, 0) + 1

    region_rows = ''.join(
        '<tr><td>' + r + '</td><td>' + str(c) + '</td></tr>'
        for r, c in sorted(region_counts.items(), key=lambda x: -x[1])
    )

    max_region_count = max(region_counts.values()) if region_counts else 1

    region_bars = ''.join(
        '<div class="bar-row">'
        + '<div class="bar-label">' + r + '</div>'
        + '<div class="bar-track"><div class="bar-fill" style="width:'
        + str(round((c / max_region_count) * 100)) + '%"></div></div>'
        + '<div class="bar-value">' + str(c) + '</div>'
        + '</div>'
        for r, c in sorted(region_counts.items(), key=lambda x: -x[1])
    )

    raw_count       = str(analytics.get('total_raw_signals', 0))
    validated_count = str(len(signals))
    flagged_count   = str(analytics.get('challenge_count', 0))

    _dr             = decision_review or {}
    _dq_score       = _dr.get('decision_quality_score', 0)
    decision_score  = str(_dq_score) if _dq_score else 'N/A'
    decision_label  = 'Decision-ready' if _dq_score >= 85 else 'Needs improvement'
    decision_gap    = _dr.get('top_gaps', ['—'])[0] if _dr.get('top_gaps') else '—'

    body_html = md_to_html(briefing_md)

    n_total_regions = str(analytics['total_regions'])
    n_total_raw     = str(analytics['total_raw_signals'])
    n_validated     = str(len(signals))
    n_dedup         = str(analytics['dedup_removed'])
    n_challenge     = str(analytics['challenge_count'])
    n_duration      = str(analytics['pipeline_duration_s']) + 's'

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>STRATEGIST Intelligence Briefing - ' + run_date + '</title>\n'
        '<style>\n'
        '  * { box-sizing: border-box; margin: 0; padding: 0; }\n'
        '  body { font-family: Georgia, serif; font-size: 15px; line-height: 1.7;\n'
        '          color: #1a1a2e; background: #f2f4f8; }\n'
        '  .page { max-width: 900px; margin: 40px auto; background: #fff;\n'
        '           box-shadow: 0 4px 20px rgba(0,0,0,0.08); }\n'
        '  .header { background: #1a1a2e; color: #fff; padding: 40px 48px 32px; }\n'
        '  .header .label { font-family: Arial, sans-serif; font-size: 11px;\n'
        '                    letter-spacing: 3px; text-transform: uppercase;\n'
        '                    color: #8899bb; margin-bottom: 10px; }\n'
        '  .header h1 { font-size: 28px; font-weight: normal; letter-spacing: 0.5px; }\n'
        '  .header .meta { margin-top: 16px; font-family: Arial, sans-serif;\n'
        '                   font-size: 13px; color: #8899bb; }\n'
        '  .header .meta span { margin-right: 24px; }\n'
        '  .stats { background: #16213e; padding: 16px 48px;\n'
        '            display: flex; gap: 32px; flex-wrap: wrap; }\n'
        '  .stat { text-align: center; }\n'
        '  .stat .val { font-size: 24px; font-weight: bold; color: #e8c97e; font-family: Arial; }\n'
        '  .stat .lbl { font-size: 11px; color: #8899bb; font-family: Arial;\n'
        '                letter-spacing: 1px; text-transform: uppercase; }\n'
        '  .body { padding: 48px; }\n'
        '  h2 { font-family: Arial, sans-serif; font-size: 13px; font-weight: bold;\n'
        '        letter-spacing: 2px; text-transform: uppercase; color: #8899bb;\n'
        '        border-bottom: 1px solid #e0e4f0; padding-bottom: 8px;\n'
        '        margin-top: 40px; margin-bottom: 16px; }\n'
        '  h2:first-child { margin-top: 0; }\n'
        '  h3 { font-family: Arial, sans-serif; font-size: 15px; font-weight: bold;\n'
        '        color: #1a1a2e; margin-top: 24px; margin-bottom: 8px; }\n'
        '  p { margin-bottom: 12px; }\n'
        '  p.numbered { padding-left: 20px; margin-bottom: 14px; }\n'
        '  ul { padding-left: 24px; margin-bottom: 12px; }\n'
        '  li { margin-bottom: 6px; }\n'
        '  strong { color: #1a1a2e; }\n'
        '  em { font-style: italic; color: #444; }\n'
        '  hr { border: none; border-top: 1px solid #e0e4f0; margin: 32px 0; }\n'
        '  .region-table { width: 100%; border-collapse: collapse; margin-top: 8px;\n'
        '                   font-family: Arial; font-size: 13px; }\n'
        '  .region-table td { padding: 6px 12px; border-bottom: 1px solid #f0f0f0; }\n'
        '  .region-table tr:last-child td { border-bottom: none; }\n'
        '  .region-table td:last-child { text-align: right; font-weight: bold; color: #1a1a2e; }\n'
        '  .footer { background: #f8f9fa; border-top: 1px solid #e0e4f0;\n'
        '             padding: 20px 48px; font-family: Arial; font-size: 12px;\n'
        '             color: #999; display: flex; justify-content: space-between; }\n'
        '  @media print {\n'
        '    body { background: white; }\n'
        '    .page { box-shadow: none; margin: 0; }\n'
        '  }\n'
        '  .visual-grid { display: grid; grid-template-columns: 1.4fr 1fr 1fr;\n'
        '                  gap: 18px; margin-bottom: 36px; }\n'
        '  .visual-card { border: 1px solid #e5e7eb; background: #f9fafb;\n'
        '                  padding: 18px; border-radius: 10px; }\n'
        '  .visual-card h4 { font-family: Arial, sans-serif; font-size: 11px;\n'
        '                     letter-spacing: 1.5px; text-transform: uppercase;\n'
        '                     color: #6b7280; margin-bottom: 14px; }\n'
        '  .bar-row { display: grid; grid-template-columns: 72px 1fr 32px;\n'
        '              gap: 10px; align-items: center; margin-bottom: 9px;\n'
        '              font-family: Arial, sans-serif; font-size: 12px; }\n'
        '  .bar-track { height: 8px; background: #e5e7eb; border-radius: 999px; overflow: hidden; }\n'
        '  .bar-fill { height: 100%; background: #1a1a2e; border-radius: 999px; }\n'
        '  .bar-value { text-align: right; font-weight: bold; }\n'
        '  .funnel-step { margin-bottom: 12px; }\n'
        '  .funnel-number { font-family: Arial, sans-serif; font-size: 24px;\n'
        '                    font-weight: bold; color: #1a1a2e; }\n'
        '  .funnel-label { font-family: Arial, sans-serif; font-size: 11px;\n'
        '                   text-transform: uppercase; letter-spacing: 1px; color: #6b7280; }\n'
        '  .score-big { font-family: Arial, sans-serif; font-size: 42px;\n'
        '                font-weight: bold; color: #1a1a2e; }\n'
        '  .score-note { font-family: Arial, sans-serif; font-size: 12px; color: #6b7280; }\n'
        '  @media (max-width: 800px) { .visual-grid { grid-template-columns: 1fr; } }\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="page">\n'
        '  <div class="header">\n'
        '    <div class="label">Strategic Intelligence Briefing</div>\n'
        '    <h1>STRATEGIST Daily Report</h1>\n'
        '    <div class="meta">\n'
        '      <span>Date: ' + run_date + '</span>\n'
        '      <span>Regions: ' + n_total_regions + '</span>\n'
        '      <span>Signals collected: ' + n_total_raw + '</span>\n'
        '      <span>Validated: ' + n_validated + '</span>\n'
        '    </div>\n'
        '  </div>\n'
        '  <div class="stats">\n'
        '    <div class="stat"><div class="val">' + n_total_raw + '</div><div class="lbl">Raw Signals</div></div>\n'
        '    <div class="stat"><div class="val">' + n_validated + '</div><div class="lbl">Validated</div></div>\n'
        '    <div class="stat"><div class="val">' + n_dedup + '</div><div class="lbl">Duplicates Removed</div></div>\n'
        '    <div class="stat"><div class="val">' + n_challenge + '</div><div class="lbl">Flagged</div></div>\n'
        '    <div class="stat"><div class="val">' + n_duration + '</div><div class="lbl">Run Time</div></div>\n'
        '  </div>\n'
        '  <div class="body">\n'
        '  <div class="visual-grid">\n'
        '    <div class="visual-card"><h4>Signals by Region</h4>\n'
        + region_bars + '\n'
        '    </div>\n'
        '    <div class="visual-card"><h4>Pipeline Funnel</h4>\n'
        '      <div class="funnel-step"><div class="funnel-number">' + raw_count + '</div>'
        '<div class="funnel-label">Raw Signals</div></div>\n'
        '      <div class="funnel-step"><div class="funnel-number">' + validated_count + '</div>'
        '<div class="funnel-label">Validated</div></div>\n'
        '      <div class="funnel-step"><div class="funnel-number">' + flagged_count + '</div>'
        '<div class="funnel-label">Flagged</div></div>\n'
        '    </div>\n'
        '    <div class="visual-card"><h4>Decision Quality</h4>\n'
        '      <div class="score-big">' + decision_score + '</div>\n'
        '      <div class="score-note">' + decision_label + '</div>\n'
        '      <div class="score-note" style="margin-top:10px;color:#9ca3af;">Top gap: ' + decision_gap + '</div>\n'
        '    </div>\n'
        '  </div>\n'
        + body_html + '\n'
        '    <h2>Signal Coverage by Region</h2>\n'
        '    <table class="region-table">\n'
        '      <tr style="background:#f8f9fa; font-weight:bold;">\n'
        '        <td>Region</td><td style="text-align:right">Signals</td>\n'
        '      </tr>\n'
        + region_rows + '\n'
        '    </table>\n'
        '  </div>\n'
        '  <div class="footer">\n'
        '    <span>STRATEGIST v1.0 - Automated Regulatory Intelligence Pipeline</span>\n'
        '    <span>Generated ' + run_date + ' - Confidential</span>\n'
        '  </div>\n'
        '</div>\n'
        '</body>\n'
        '</html>'
    )
    return html


# ─────────────────────────────────────────────────────────────────────────────
#  Briefing improvement loop
# ─────────────────────────────────────────────────────────────────────────────

def _improve_briefing_until_ready(briefing: str, signals: list[dict], max_rounds: int = 1) -> tuple[str, dict]:
    """
    Review briefing quality. If weak, revise once using reviewer feedback.
    """
    decision_review = review_decision_quality(briefing, signals)

    rounds = 0
    while decision_review.get('decision_quality_score', 0) < 85 and rounds < max_rounds:
        print('[formatter] Briefing below threshold. Running partner editor...')

        revision_guidance = '\n'.join(
            decision_review.get('required_revisions', [])
            or decision_review.get('top_gaps', [])
            or ['Make the briefing more decisive, prioritized, and actionable.']
        )

        briefing = partner_editor(
            briefing + '\n\nREVISION GUIDANCE:\n' + revision_guidance
        )

        decision_review = review_decision_quality(briefing, signals)
        rounds += 1

    decision_review['revision_rounds'] = rounds
    return briefing, decision_review


# ─────────────────────────────────────────────────────────────────────────────
#  Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def format_output(
    coordinator_result: dict,
    duration_s: float = 0.0
) -> tuple[str, str, dict]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id    = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    run_date  = timestamp[:10]

    analytics = _build_analytics(coordinator_result, duration_s)
    signals   = business_impact_scorer(coordinator_result.get('final_signals', []))

    hitl_decisions = {
        region: [s.get('hitl_decision') for s in sigs]
        for region, sigs in coordinator_result.get('hitl_results', {}).items()
    }
    adversarial_verdicts = {
        s['signal_id']: s.get('adversarial_verdict', 'UNKNOWN')
        for s in signals if 'signal_id' in s
    }

    print('[formatter] Generating strategic intelligence briefing...')
    briefing = _generate_briefing(analytics, signals, run_date)

    print('[formatter] Reviewing and improving briefing...')
    briefing, decision_review = _improve_briefing_until_ready(
        briefing=briefing,
        signals=signals,
        max_rounds=1,
    )

    trend_summary = build_trend_summary(limit=5)

    # ── Comm Ex recommendations (pharma commercialization layer) ─────────────
    if COMM_EX_ENABLED:
        print('[formatter] Generating Comm Ex commercialization recommendations...')
        try:
            run_comm_ex(briefing=briefing, out_dir=COMM_EX_OUT, verbose=False)
            print('[formatter] Comm Ex recommendations saved.')
        except Exception as e:
            print(f'[formatter] WARNING: Comm Ex generation failed: {e}')

    fname_json = 'strategist_run_' + run_date + '_' + run_id[:8] + '.json'
    path_json  = str(REPORTS_DIR / fname_json)

    report = {
        'run_id'                 : run_id,
        'timestamp'              : timestamp,
        'regions'                : list(coordinator_result.get('phase1_raw', {}).keys()),
        'total_raw_signals'      : analytics['total_raw_signals'],
        'signals'                : signals,
        'hitl_decisions'         : hitl_decisions,
        'adversarial_verdicts'   : adversarial_verdicts,
        'dedup_log'              : coordinator_result.get('dedup_log', []),
        'analytics'              : analytics,
        'decision_quality_review': decision_review,
        'dq_verdict'             : decision_review,   # alias for dashboard compatibility
        'trend_summary'          : trend_summary,
        'executive_briefing'     : briefing,
    }

   