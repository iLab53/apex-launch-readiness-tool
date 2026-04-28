# patch_modules_1_2.py -- run from repo root inside your venv
# python patch_modules_1_2.py
# Replaces render_module_1() and render_module_2() in dashboard/streamlit_app.py
# with implementations that use the actual dashboard JSON structure.

import re
from pathlib import Path

APP = Path("dashboard") / "streamlit_app.py"
if not APP.exists():
    print("ERROR: dashboard/streamlit_app.py not found")
    raise SystemExit(1)

src = APP.read_text(encoding="utf-8")

# ── Replacement for render_module_1 ──────────────────────────────────────────
NEW_M1 = '''def render_module_1():
    """Launch Intelligence -- portfolio LRS scores from agents/outputs scorecard files."""
    import plotly.graph_objects as go

    st.subheader("Launch Intelligence")
    st.caption(f"Data as of: {last_run_timestamp()}")

    TIER_COLORS = {
        "LAUNCH-READY": "#2ecc71",
        "ON-TRACK":     "#3498db",
        "AT-RISK":      "#e67e22",
        "NOT-READY":    "#e74c3c",
    }

    # Load scorecard files from agents/outputs
    scorecard_dir = ROOT_DIR / "agents" / "outputs"
    sc_files = sorted(scorecard_dir.glob("launch_readiness_scorecard_APEX-*.json")) if scorecard_dir.exists() else []

    scorecards = {}
    for f in sc_files:
        try:
            import json as _json
            sc = _json.loads(f.read_text(encoding="utf-8"))
            aid = sc.get("asset_id")
            if aid:
                scorecards[aid] = sc
        except Exception:
            pass

    assets = st.session_state.get("asset_registry", [])
    selected = st.session_state.get("selected_assets", [])
    if selected:
        assets = [a for a in assets if a.get("brand_name") in selected]

    if not assets:
        st.info("No assets selected. Use the sidebar filter to choose assets.")
        return

    # Build chart data
    brand_names = [a.get("brand_name", "?") for a in assets]
    asset_ids   = [a.get("apex_id", a.get("asset_id", "?")) for a in assets]
    scores, tiers, colors = [], [], []

    for aid in asset_ids:
        sc = scorecards.get(aid)
        if sc:
            score = sc.get("overall_score", 0)
            tier  = sc.get("overall_tier", "N/A")
        else:
            score = 0
            tier  = "No Scorecard"
        scores.append(score)
        tiers.append(tier)
        colors.append(TIER_COLORS.get(tier, "#95a5a6"))

    if not any(s > 0 for s in scores):
        st.warning(
            f"No scorecard data found in agents/outputs/ ({len(sc_files)} file(s) present).\\n\\n"
            "Run:  **python generate_all_scorecards.py**  to generate scores for all assets."
        )

    # Plotly bar chart
    fig = go.Figure(go.Bar(
        x=brand_names,
        y=scores,
        marker_color=colors,
        text=[f"{s}<br>{t}" for s, t in zip(scores, tiers)],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Score: %{y}<br>Tier: %{customdata}<extra></extra>",
        customdata=tiers,
    ))
    fig.update_layout(
        title="Launch Readiness Score (LRS) by Asset",
        xaxis_title="Asset",
        yaxis_title="Score (0-100)",
        yaxis_range=[0, 115],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#fafafa",
        showlegend=False,
        height=420,
        margin=dict(t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Scorecard detail table
    rows = []
    for a, aid, score, tier in zip(assets, asset_ids, scores, tiers):
        rows.append({
            "Asset":    a.get("brand_name", aid),
            "Apex ID":  aid,
            "Stage":    a.get("lifecycle_stage", a.get("asset_stage", "?")),
            "Score":    score if score > 0 else "--",
            "Tier":     tier,
        })
    st.dataframe(rows, use_container_width=True)

    missing = [a.get("brand_name") for a, aid in zip(assets, asset_ids) if aid not in scorecards]
    if missing:
        st.info(
            f"Missing scorecards for: {', '.join(missing)}.\\n"
            "Run:  python generate_all_scorecards.py"
        )

'''

# ── Replacement for render_module_2 ──────────────────────────────────────────
NEW_M2 = '''def render_module_2():
    """Asset Strategy -- Comm Ex recommendations feed."""
    st.subheader("Asset Strategy")
    st.caption(f"Data as of: {last_run_timestamp()}")

    d = st.session_state.get("dashboard", {})

    immediate      = d.get("immediate_actions", [])
    top_risks      = d.get("top_risks", [])
    top_opps       = d.get("top_opportunities", [])
    kpis           = d.get("kpis_by_function", {})
    coverage       = d.get("coverage_check", {})

    if not immediate and not top_risks:
        st.info(
            "No recommendation data available.\\n\\n"
            "Run:  python run_comm_ex.py --comm-ex-only"
        )
        return

    # Coverage metrics row
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Recommendations", d.get("rec_count", 0))
    col2.metric("Immediate Actions",      coverage.get("immediate_actions", 0))
    col3.metric("High Confidence",        coverage.get("high_confidence", 0))
    col4.metric("% High Confidence",      f"{coverage.get('pct_high_confidence', 0)}%")

    st.divider()

    # Immediate actions
    if immediate:
        st.markdown("### Immediate Actions (0-30 days)")
        for rec in immediate:
            with st.expander(
                f"{rec.get('rec_id','?')}  |  {rec.get('function_owner','?')}",
                expanded=False
            ):
                st.write(rec.get("recommended_action", ""))
                kpi_text = rec.get("kpi", "")
                if kpi_text:
                    st.caption(f"KPI: {kpi_text}")

    # Top risks
    if top_risks:
        st.divider()
        st.markdown("### Top Strategic Risks")
        for risk in top_risks:
            label = (
                f"**{risk.get('rec_id','')}**  "
                f"[{risk.get('asset_stage','')}]  "
                f"| {risk.get('timeline','')}  "
                f"| {risk.get('function','')}"
            )
            st.error(f"{label}\\n\\n{risk.get('risk','')}")

    # Top opportunities
    if top_opps:
        st.divider()
        st.markdown("### Top Opportunities")
        for opp in top_opps:
            with st.expander(
                f"{opp.get('rec_id','?')}  |  {opp.get('function','?')}",
                expanded=False
            ):
                st.write(f"**Target:** {opp.get('target','')}")
                st.write(f"**Expected Impact:** {opp.get('expected_impact','')}")
                kpi_text = opp.get("kpi", "")
                if kpi_text:
                    st.caption(f"KPI: {kpi_text}")

    # KPIs by function
    if kpis:
        st.divider()
        st.markdown("### KPIs by Function")
        for func, kpi_list in kpis.items():
            if kpi_list:
                st.markdown(f"**{func}**")
                for kpi_item in kpi_list:
                    st.write(f"- {kpi_item}")

'''

# ── Regex replace: find each function and replace until the next `def ` ─────
def replace_function(source, func_name, new_body):
    """Replace func_name definition up to (but not including) the next def at column 0."""
    pattern = rf"(^def {re.escape(func_name)}\(.*?)(?=^def |\Z)"
    match = re.search(pattern, source, flags=re.DOTALL | re.MULTILINE)
    if not match:
        print(f"  WARNING: could not find 'def {func_name}' in source")
        return source
    start, end = match.span()
    print(f"  Replacing {func_name}() at chars {start}-{end}")
    return source[:start] + new_body + source[end:]


print("Patching dashboard/streamlit_app.py ...")
src = replace_function(src, "render_module_1", NEW_M1)
src = replace_function(src, "render_module_2", NEW_M2)

APP.write_text(src, encoding="utf-8")
print("Done. Restart Streamlit (Ctrl+C then: streamlit run dashboard/streamlit_app.py)")
