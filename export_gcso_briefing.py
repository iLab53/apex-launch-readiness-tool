"""
export_gcso_briefing.py
=======================
Generates a single-page HTML executive briefing from
comm-ex/outputs/comm_ex_dashboard_ready.json.

Three sections:
  1. Top 3 Immediate Comm Ex Recommendations
  2. Milestone Alerts (next 90 days, sorted by days_to_event)
  3. Portfolio Readiness Summary with colour-coded LRS scores

Output: comm-ex/outputs/gcso_briefing_YYYYMMDD.html

Run from the repo root:
    python export_gcso_briefing.py
"""

import json
import pathlib
import sys
from datetime import datetime, timezone

DASHBOARD_PATH = pathlib.Path("comm-ex") / "outputs" / "comm_ex_dashboard_ready.json"
OUTPUT_DIR     = pathlib.Path("comm-ex") / "outputs"


def score_colour(score):
    if score >= 75:
        return "#d4edda"   # green tint
    if score >= 50:
        return "#fff3cd"   # amber tint
    return "#f8d7da"       # red tint


def score_text_colour(score):
    if score >= 75:
        return "#155724"
    if score >= 50:
        return "#856404"
    return "#721c24"


def build_html(data, generated_at):
    # ---- Section 1: Immediate Recommendations ----
    # Try 'recs' first (seeded by seed_milestone_data.py), fall back to immediate_actions
    recs = [r for r in data.get("recs", []) if r.get("urgency") == "Immediate"][:3]
    if not recs:
        recs = data.get("immediate_actions", [])[:3]

    if recs:
        rec_rows = ""
        for r in recs:
            rec_id = r.get("rec_id", r.get("action_id", "N/A"))
            func   = r.get("function_owner", r.get("function", "N/A"))
            action = r.get("recommended_action", r.get("action", str(r)))
            urgency = r.get("urgency", "Immediate")
            rec_rows += (
                "<tr>"
                "<td><strong>{rec_id}</strong></td>"
                "<td>{func}</td>"
                "<td>{action}</td>"
                "<td><span class='badge bg-danger'>{urgency}</span></td>"
                "</tr>"
            ).format(rec_id=rec_id, func=func, action=action, urgency=urgency)
        section1 = """
        <h2 class="mt-4">1. Top Immediate Recommendations</h2>
        <table class="table table-bordered table-sm">
          <thead class="table-dark">
            <tr>
              <th>Rec ID</th><th>Function</th>
              <th>Recommended Action</th><th>Urgency</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>""".format(rows=rec_rows)
    else:
        section1 = """
        <h2 class="mt-4">1. Top Immediate Recommendations</h2>
        <div class="alert alert-secondary">No immediate recommendations in current run.</div>"""

    # ---- Section 2: Milestone Alerts ----
    milestone_alerts = data.get("milestone_alerts", {})
    all_milestones = []
    for apex_id, ms_list in milestone_alerts.items():
        for ms in ms_list:
            ms["_apex_id"] = apex_id
            all_milestones.append(ms)
    all_milestones.sort(key=lambda m: m.get("days_to_event", 9999))

    if all_milestones:
        ms_rows = ""
        for ms in all_milestones:
            days = ms.get("days_to_event", "?")
            row_class = "table-warning" if isinstance(days, int) and days <= 30 else ""
            ms_rows += (
                "<tr class='{cls}'>"
                "<td>{apex_id}</td>"
                "<td><span class='badge' style='background:#003865'>{ms_type}</span></td>"
                "<td>{label}</td>"
                "<td>{date}</td>"
                "<td>{days}</td>"
                "</tr>"
            ).format(
                cls=row_class,
                apex_id=ms.get("_apex_id", ms.get("apex_id", "")),
                ms_type=ms.get("milestone_type", ""),
                label=ms.get("milestone_label", ""),
                date=ms.get("milestone_date", ""),
                days=days,
            )
        section2 = """
        <h2 class="mt-4">2. Milestone Alerts (Next 90 Days)</h2>
        <p class="text-muted small">Rows highlighted in amber are within 30 days.</p>
        <table class="table table-bordered table-sm">
          <thead class="table-dark">
            <tr>
              <th>Asset</th><th>Type</th><th>Milestone</th>
              <th>Date</th><th>Days Out</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>""".format(rows=ms_rows)
    else:
        section2 = """
        <h2 class="mt-4">2. Milestone Alerts (Next 90 Days)</h2>
        <div class="alert alert-secondary">No milestone alerts in current run.</div>"""

    # ---- Section 3: Portfolio Readiness ----
    launch_readiness = data.get("launch_readiness", {})
    memory_deltas    = data.get("memory_deltas", {})

    if launch_readiness:
        lr_rows = ""
        for apex_id, info in sorted(
            launch_readiness.items(),
            key=lambda x: x[1].get("launch_readiness_score", 0),
            reverse=True
        ):
            score  = info.get("launch_readiness_score", 0)
            brand  = info.get("brand_name", apex_id)
            status = info.get("status", "")
            trend  = memory_deltas.get(apex_id, {}).get("trend", "N/A")
            bg     = score_colour(score)
            fg     = score_text_colour(score)
            lr_rows += (
                "<tr>"
                "<td>{apex_id}</td>"
                "<td>{brand}</td>"
                "<td style='background:{bg};color:{fg};font-weight:bold;text-align:center'>"
                "{score:.0f}</td>"
                "<td>{status}</td>"
                "<td>{trend}</td>"
                "</tr>"
            ).format(
                apex_id=apex_id, brand=brand, score=score,
                status=status, trend=trend, bg=bg, fg=fg
            )
        section3 = """
        <h2 class="mt-4">3. Portfolio Readiness Summary</h2>
        <table class="table table-bordered table-sm">
          <thead class="table-dark">
            <tr>
              <th>Asset ID</th><th>Brand</th><th>LRS Score</th>
              <th>Status</th><th>Trend</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        <p class="text-muted small">
          Score colour: green &ge;75 (Launch Ready), amber 50&ndash;74 (On Track),
          red &lt;50 (At Risk)
        </p>""".format(rows=lr_rows)
    else:
        section3 = """
        <h2 class="mt-4">3. Portfolio Readiness Summary</h2>
        <div class="alert alert-secondary">
          No launch readiness data available. Run seed_milestone_data.py or the full pipeline.
        </div>"""

    html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>GCSO Commercial Intelligence Briefing</title>
  <link rel="stylesheet"
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 14px; }}
    .header-bar {{ background: #003865; color: white; padding: 20px 30px; }}
    .footer-bar {{ background: #f8f9fa; border-top: 1px solid #dee2e6;
                   padding: 10px 30px; font-size: 12px; color: #6c757d; }}
    table td, table th {{ vertical-align: middle; }}
  </style>
</head>
<body>
  <div class="header-bar">
    <h1 class="h4 mb-0">GCSO Commercial Intelligence Briefing &mdash; APEX Pipeline</h1>
    <p class="mb-0 mt-1 small">
      J&amp;J Innovative Medicine &bull; Commercialization Excellence
    </p>
  </div>

  <div class="container-fluid px-4 py-2">
    {section1}
    {section2}
    {section3}
  </div>

  <div class="footer-bar">
    Generated: {generated_at} &nbsp;|&nbsp; <strong>CONFIDENTIAL</strong>
    &nbsp;|&nbsp; APEX Pipeline v1.0
    &nbsp;|&nbsp; J&amp;J Innovative Medicine
  </div>
</body>
</html>""".format(
        section1=section1,
        section2=section2,
        section3=section3,
        generated_at=generated_at,
    )
    return html


def main():
    if not DASHBOARD_PATH.exists():
        print("ERROR: Dashboard JSON not found at: {0}".format(DASHBOARD_PATH))
        sys.exit(1)

    with open(DASHBOARD_PATH, encoding="utf-8") as f:
        data = json.load(f)

    generated_at = data.get("meta", {}).get("generated_at", datetime.now(timezone.utc).isoformat())
    today = datetime.now().strftime("%Y%m%d")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "gcso_briefing_{0}.html".format(today)

    html = build_html(data, generated_at)
    out_path.write_text(html, encoding="utf-8")

    print("SUCCESS: Briefing written to {0}".format(out_path))
    print("Open in browser: Start-Process {0}".format(out_path))


if __name__ == "__main__":
    main()
