# streamlit_app.py
# AI & Digital Transformation Tool — Johnson & Johnson Innovative Medicine
"""
Pharma commercial intelligence dashboard for J&J Innovative Medicine.
Wraps the multi-agent strategist engine and Comm Ex recommendations layer.

Tabs:
  1. Dashboard     — KPI summary cards + distribution charts
  2. Signals       — Filtered signal table with detail panel
  3. Briefing      — Full executive briefing (HTML)
  4. Comm Ex       — Commercialization recommendations by function / stage
  5. History       — Trend view across pipeline runs
  6. Export        — Download JSON, CSV, or copy summary text

Run:
  cd 06_AI_DIGITAL_TRANSFORM/dashboard
  streamlit run streamlit_app.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
DASH_DIR   = Path(__file__).parent
ROOT_DIR   = DASH_DIR.parent
ENGINE_DIR = ROOT_DIR / "strategist-engine"
COMM_EX_DIR = ROOT_DIR / "comm-ex"
REPORTS_DIR = ENGINE_DIR / "reports"
COMM_EX_OUT = COMM_EX_DIR / "outputs"

sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(COMM_EX_DIR))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="J&J Innovative Medicine | Commercial Intelligence",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .kpi-card {
    background: #f8f9fa;
    border-left: 4px solid #cc0000;
    padding: 12px 16px;
    border-radius: 4px;
    margin-bottom: 8px;
  }
  .kpi-value { font-size: 2rem; font-weight: 700; color: #cc0000; }
  .kpi-label { font-size: 0.8rem; color: #555; text-transform: uppercase; letter-spacing: 0.5px; }
  .stage-badge {
    display: inline-block; padding: 2px 8px; border-radius: 12px;
    font-size: 0.75rem; font-weight: 600;
  }
  .pre-launch  { background: #fff3cd; color: #856404; }
  .launch      { background: #d1ecf1; color: #0c5460; }
  .post-launch { background: #d4edda; color: #155724; }
  .conf-high   { background: #d4edda; color: #155724; }
  .conf-medium { background: #fff3cd; color: #856404; }
  .conf-low    { background: #f8d7da; color: #721c24; }
  .rec-card {
    border: 1px solid #dee2e6; border-radius: 6px;
    padding: 14px 16px; margin-bottom: 12px;
    background: #fff;
  }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Data loaders
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=60)
def load_latest_run() -> dict:
    """Load the most recent strategist_run JSON."""
    files = sorted(REPORTS_DIR.glob("strategist_run_*.json"), reverse=True)
    if not files:
        return {}
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(ttl=60)
def load_comm_ex_dashboard() -> dict:
    """Load latest comm_ex_dashboard_ready.json."""
    p = COMM_EX_OUT / "comm_ex_dashboard_ready.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(ttl=60)
def load_latest_comm_ex_recs() -> list[dict]:
    """Load the most recent comm_ex_recommendations JSON."""
    files = sorted(COMM_EX_OUT.glob("comm_ex_recommendations_*.json"), reverse=True)
    if not files:
        return []
    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return []


@st.cache_data(ttl=60)
def load_latest_summary() -> str:
    """Load the most recent executive summary text."""
    files = sorted(COMM_EX_OUT.glob("comm_ex_summary_*.txt"), reverse=True)
    if not files:
        return ""
    try:
        return files[0].read_text(encoding="utf-8")
    except Exception:
        return ""


@st.cache_data(ttl=60)
def load_signals() -> list[dict]:
    """Return final_signals from latest run."""
    run = load_latest_run()
    return run.get("final_signals", [])


@st.cache_data(ttl=60)
def load_briefing_html() -> str:
    """Return latest HTML briefing content."""
    files = sorted(REPORTS_DIR.glob("strategist_briefing_*.html"), reverse=True)
    if not files:
        return "<p>No briefing found. Run the pipeline first.</p>"
    try:
        return files[0].read_text(encoding="utf-8")
    except Exception:
        return "<p>Could not read briefing file.</p>"


@st.cache_data(ttl=60)
def build_history() -> list[dict]:
    """Reconstruct run history from all strategist_run_*.json files."""
    history = []
    for f in sorted(REPORTS_DIR.glob("strategist_run_*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            analytics = d.get("analytics", {})
            history.append({
                "run_id":            d.get("run_id", f.stem)[:8],
                "run_date":          d.get("run_date", ""),
                "total_signals":     analytics.get("total_raw_signals", 0),
                "approved":          analytics.get("hitl_approved", 0),
                "rejected":          analytics.get("hitl_rejections", 0),
                "final_signals":     len(d.get("final_signals", [])),
                "duration_s":        analytics.get("pipeline_duration_s", 0),
                "dq_score":          d.get("decision_quality_review", {}).get("overall_score", 0),
            })
        except Exception:
            continue
    return history


def invalidate_cache():
    load_latest_run.clear()
    load_comm_ex_dashboard.clear()
    load_latest_comm_ex_recs.clear()
    load_latest_summary.clear()
    load_signals.clear()
    load_briefing_html.clear()
    build_history.clear()


# ══════════════════════════════════════════════════════════════════════════════
#  Sidebar
# ══════════════════════════════════════════════════════════════════════════════

def render_sidebar():
    st.sidebar.markdown("## 💊 Commercial Intelligence")
    st.sidebar.markdown("**Johnson & Johnson Innovative Medicine**")
    st.sidebar.divider()

    run_data = load_latest_run()
    if run_data:
        run_date = run_data.get("run_date", "—")
        run_id   = run_data.get("run_id", "—")[:8]
        st.sidebar.markdown(f"**Last run:** {run_date}  \n**ID:** `{run_id}`")
    else:
        st.sidebar.warning("No pipeline runs found.")

    st.sidebar.divider()

    # ── Run pipeline button ───────────────────────────────────────────────────
    st.sidebar.markdown("### Run Pipeline")
    col1, col2 = st.sidebar.columns(2)

    with col1:
        full_run = st.button("▶ Full Run", use_container_width=True, type="primary")
    with col2:
        comm_only = st.button("⚡ Comm Ex Only", use_container_width=True)

    if full_run or comm_only:
        mode_flag = "--comm-ex-only" if comm_only else ""
        cmd = [sys.executable, str(ROOT_DIR / "run_comm_ex.py")]
        if mode_flag:
            cmd.append(mode_flag)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        with st.sidebar:
            with st.spinner("Running pipeline..."):
                res = subprocess.run(
                    cmd,
                    cwd=str(ROOT_DIR),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    env=env,
                )

        invalidate_cache()

        if res.returncode == 0:
            st.sidebar.success("Pipeline complete.")
        else:
            st.sidebar.error("Pipeline failed.")
            with st.sidebar.expander("Error details"):
                st.code(res.stderr[-3000:] or res.stdout[-3000:])

    st.sidebar.divider()

    # ── Signal filters ────────────────────────────────────────────────────────
    st.sidebar.markdown("### Signal Filters")

    signals = load_signals()
    regions  = sorted({s.get("region","") for s in signals if s.get("region")})
    countries= sorted({s.get("country","") for s in signals if s.get("country")})

    sel_regions  = st.sidebar.multiselect("Region",  regions,  default=[])
    sel_countries= st.sidebar.multiselect("Country", countries, default=[])
    min_conf     = st.sidebar.slider("Min confidence score", 0.0, 1.0, 0.0, 0.05)

    st.sidebar.divider()

    # ── Comm Ex filters ───────────────────────────────────────────────────────
    st.sidebar.markdown("### Comm Ex Filters")

    recs = load_latest_comm_ex_recs()
    ta_opts    = sorted({r.get("therapeutic_area","") for r in recs if r.get("therapeutic_area")})
    stage_opts = sorted({r.get("asset_stage","") for r in recs if r.get("asset_stage")})
    func_opts  = sorted({r.get("function_owner","") for r in recs if r.get("function_owner")})
    conf_opts  = ["HIGH", "MEDIUM", "LOW"]

    sel_ta     = st.sidebar.multiselect("Therapeutic Area", ta_opts, default=[])
    sel_stage  = st.sidebar.multiselect("Asset Stage",      stage_opts, default=[])
    sel_func   = st.sidebar.multiselect("Function Owner",   func_opts, default=[])
    sel_conf   = st.sidebar.multiselect("Confidence",       conf_opts, default=[])

    return {
        "regions":    sel_regions,
        "countries":  sel_countries,
        "min_conf":   min_conf,
        "ta":         sel_ta,
        "stage":      sel_stage,
        "function":   sel_func,
        "confidence": sel_conf,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Filter helpers
# ══════════════════════════════════════════════════════════════════════════════

def apply_signal_filters(signals: list[dict], f: dict) -> list[dict]:
    out = signals
    if f["regions"]:
        out = [s for s in out if s.get("region") in f["regions"]]
    if f["countries"]:
        out = [s for s in out if s.get("country") in f["countries"]]
    if f["min_conf"] > 0:
        out = [s for s in out if s.get("confidence_score", 0) >= f["min_conf"]]
    return out


def apply_rec_filters(recs: list[dict], f: dict) -> list[dict]:
    out = recs
    if f["ta"]:
        out = [r for r in out if r.get("therapeutic_area") in f["ta"]]
    if f["stage"]:
        out = [r for r in out if r.get("asset_stage") in f["stage"]]
    if f["function"]:
        out = [r for r in out if r.get("function_owner") in f["function"]]
    if f["confidence"]:
        out = [r for r in out if r.get("confidence") in f["confidence"]]
    return out


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════

def render_dashboard():
    run_data  = load_latest_run()
    dash      = load_comm_ex_dashboard()
    analytics = run_data.get("analytics", {})

    st.markdown("## Commercial Intelligence Dashboard")

    if not run_data:
        st.info("No pipeline run found. Click **▶ Full Run** in the sidebar to start.")
        return

    # ── KPI row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    total_sigs  = analytics.get("total_raw_signals", 0)
    approved    = analytics.get("hitl_approved", 0)
    final_sigs  = len(run_data.get("final_signals", []))
    total_recs  = dash.get("meta", {}).get("total_recs", 0)
    high_conf   = dash.get("coverage_check", {}).get("high_confidence", 0)

    for col, val, label in [
        (c1, total_sigs, "Raw Signals"),
        (c2, approved,   "HITL Approved"),
        (c3, final_sigs, "Final Signals"),
        (c4, total_recs, "Comm Ex Recs"),
        (c5, high_conf,  "High Confidence"),
    ]:
        col.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-value">{val}</div>
          <div class="kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Charts row ────────────────────────────────────────────────────────────
    dist = dash.get("distribution", {})

    col_l, col_m, col_r = st.columns(3)

    with col_l:
        st.markdown("**Recs by Asset Stage**")
        stage_data = dist.get("by_asset_stage", {})
        if stage_data:
            colors = {"PRE-LAUNCH":"#ffc107","LAUNCH":"#17a2b8","POST-LAUNCH":"#28a745"}
            fig = go.Figure(go.Bar(
                x=list(stage_data.keys()),
                y=list(stage_data.values()),
                marker_color=[colors.get(k,"#999") for k in stage_data],
                text=list(stage_data.values()),
                textposition="auto",
            ))
            fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=220,
                              plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data yet.")

    with col_m:
        st.markdown("**Recs by Function**")
        func_data = dist.get("by_function", {})
        if func_data:
            fig = go.Figure(go.Pie(
                labels=list(func_data.keys()),
                values=list(func_data.values()),
                hole=0.4,
                marker_colors=["#cc0000","#003087","#00a651","#ff6b00"],
            ))
            fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=220,
                              showlegend=True, paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data yet.")

    with col_r:
        st.markdown("**Recs by Therapeutic Area**")
        ta_data = dist.get("by_therapeutic_area", {})
        if ta_data:
            fig = go.Figure(go.Bar(
                y=list(ta_data.keys()),
                x=list(ta_data.values()),
                orientation="h",
                marker_color="#003087",
                text=list(ta_data.values()),
                textposition="auto",
            ))
            fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=220,
                              plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("No data yet.")

    st.divider()

    # ── Top risks + opportunities ─────────────────────────────────────────────
    col_risk, col_opp = st.columns(2)

    with col_risk:
        st.markdown("**Top Risks (if no action)**")
        for r in dash.get("top_risks", [])[:3]:
            with st.container():
                stage = r.get("asset_stage","")
                fn    = r.get("function","")
                tl    = r.get("timeline","")
                risk  = r.get("risk","")
                st.markdown(f"""
                <div class="rec-card">
                  <strong>{r.get("rec_id","")}</strong>
                  &nbsp;·&nbsp; <span class="stage-badge">{stage}</span>
                  &nbsp;·&nbsp; {fn} &nbsp;·&nbsp; {tl}<br/>
                  <small>{risk}</small>
                </div>""", unsafe_allow_html=True)

    with col_opp:
        st.markdown("**Top Opportunities**")
        for r in dash.get("top_opportunities", [])[:3]:
            with st.container():
                impact = r.get("expected_impact","")
                kpi    = r.get("kpi","")
                fn     = r.get("function","")
                st.markdown(f"""
                <div class="rec-card">
                  <strong>{r.get("rec_id","")}</strong>
                  &nbsp;·&nbsp; {r.get("target","")} &nbsp;·&nbsp; {fn}<br/>
                  <small><b>Impact:</b> {impact}</small><br/>
                  <small><b>KPI:</b> {kpi}</small>
                </div>""", unsafe_allow_html=True)

    # ── Immediate actions ─────────────────────────────────────────────────────
    imm = dash.get("immediate_actions", [])
    if imm:
        st.divider()
        st.markdown(f"**Immediate Actions (0-30 days) — {len(imm)} items**")
        for a in imm:
            st.markdown(f"""
            <div class="rec-card">
              <strong>{a.get("rec_id","")}</strong>
              &nbsp;·&nbsp; {a.get("function_owner","")}<br/>
              {a.get("recommended_action","")}<br/>
              <small><b>KPI:</b> {a.get("kpi","")}</small>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 2 — Signals
# ══════════════════════════════════════════════════════════════════════════════

def render_signals(filters: dict):
    st.markdown("## Regulatory & Market Signals")

    signals  = load_signals()
    filtered = apply_signal_filters(signals, filters)

    if not filtered:
        if not signals:
            st.info("No signals found. Run the pipeline to collect intelligence.")
        else:
            st.warning(f"No signals match current filters ({len(signals)} total).")
        return

    st.caption(f"Showing {len(filtered)} of {len(signals)} signals")

    # Build display dataframe
    rows = []
    for s in filtered:
        rows.append({
            "Date":       s.get("signal_date","")[:10],
            "Source":     s.get("source",""),
            "Region":     s.get("region",""),
            "Country":    s.get("country",""),
            "Headline":   s.get("headline",""),
            "Confidence": round(s.get("confidence_score", 0), 2),
            "URL":        s.get("source_url",""),
            "_idx":       filtered.index(s),
        })

    df = pd.DataFrame(rows)
    display_df = df.drop(columns=["_idx"])

    selection = st.dataframe(
        display_df,
        use_container_width=True,
        height=340,
        column_config={
            "URL": st.column_config.LinkColumn("URL", display_text="Link"),
            "Confidence": st.column_config.ProgressColumn(
                "Confidence", min_value=0, max_value=1, format="%.2f"
            ),
        },
        on_select="rerun",
        selection_mode="single-row",
    )

    selected = selection.get("selection", {}).get("rows", [])
    if selected:
        idx = df.iloc[selected[0]]["_idx"]
        sig = filtered[idx]

        st.divider()
        st.markdown(f"#### {sig.get('headline','')}")

        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("Confidence",  round(sig.get("confidence_score",0),2))
        dc2.metric("Region",      sig.get("region",""))
        dc3.metric("Country",     sig.get("country",""))
        dc4.metric("Source Tier", sig.get("source_tier",""))

        with st.expander("Full signal content", expanded=True):
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown("**Raw excerpt**")
                st.write(sig.get("raw_excerpt","") or sig.get("raw_text","")[:1000])
            with col_b:
                st.markdown("**Signal metadata**")
                meta_fields = ["signal_id","signal_type","signal_subtype","classification",
                               "market_impact","publication_date","adversarial_verdict"]
                for f_name in meta_fields:
                    val = sig.get(f_name)
                    if val:
                        st.markdown(f"**{f_name}:** {val}")
                url = sig.get("source_url","")
                if url:
                    st.markdown(f"[View source]({url})")


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 3 — Briefing
# ══════════════════════════════════════════════════════════════════════════════

def render_briefing():
    st.markdown("## Executive Briefing")

    run_data = load_latest_run()
    if not run_data:
        st.info("No briefing found. Run the pipeline first.")
        return

    run_date = run_data.get("run_date","")
    run_id   = run_data.get("run_id","")[:8]
    st.caption(f"Run {run_id} | {run_date}")

    # Executive briefing text
    briefing_text = run_data.get("executive_briefing","")
    if briefing_text:
        st.markdown("### Intelligence Summary")
        st.markdown(briefing_text[:6000])
        st.divider()

    # Full HTML briefing
    html_content = load_briefing_html()
    if html_content and "<html" in html_content.lower():
        st.markdown("### Full Briefing")
        with st.expander("View formatted briefing", expanded=False):
            import streamlit.components.v1 as components
            components.html(html_content, height=800, scrolling=True)
    elif html_content:
        with st.expander("Full briefing content"):
            st.markdown(html_content[:5000])


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 4 — Comm Ex Recommendations
# ══════════════════════════════════════════════════════════════════════════════

STAGE_CLASS = {
    "PRE-LAUNCH":  "pre-launch",
    "LAUNCH":      "launch",
    "POST-LAUNCH": "post-launch",
}
CONF_CLASS = {
    "HIGH":   "conf-high",
    "MEDIUM": "conf-medium",
    "LOW":    "conf-low",
}

def _stage_badge(stage: str) -> str:
    cls = STAGE_CLASS.get(stage, "")
    return f'<span class="stage-badge {cls}">{stage}</span>'

def _conf_badge(conf: str) -> str:
    cls = CONF_CLASS.get(conf, "")
    return f'<span class="stage-badge {cls}">{conf}</span>'


def render_comm_ex(filters: dict):
    st.markdown("## Commercialization Excellence Recommendations")

    summary = load_latest_summary()
    if summary:
        with st.expander("Executive Summary", expanded=True):
            st.text(summary)
        st.divider()

    recs = load_latest_comm_ex_recs()
    if not recs:
        st.info("No Comm Ex recommendations found. Run the pipeline first.")
        return

    filtered = apply_rec_filters(recs, filters)
    st.caption(f"Showing {len(filtered)} of {len(recs)} recommendations")

    if not filtered:
        st.warning("No recommendations match current filters.")
        return

    # ── View toggle ───────────────────────────────────────────────────────────
    view_mode = st.radio("View", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

    if view_mode == "Table":
        table_rows = []
        for r in filtered:
            table_rows.append({
                "ID":           r.get("rec_id",""),
                "Stage":        r.get("asset_stage",""),
                "Area":         r.get("therapeutic_area",""),
                "Function":     r.get("function_owner",""),
                "Timeline":     r.get("timeline",""),
                "Confidence":   r.get("confidence",""),
                "Target":       r.get("target",""),
                "Action":       r.get("recommended_action","")[:100] + "...",
                "KPI":          r.get("kpi","")[:80] + "...",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, height=400)
        return

    # ── Cards view — group by function ───────────────────────────────────────
    functions = sorted({r.get("function_owner","") for r in filtered})
    func_tabs = st.tabs(functions) if len(functions) > 1 else [st.container()]

    for tab, fn in zip(func_tabs, functions):
        with tab:
            fn_recs = [r for r in filtered if r.get("function_owner","") == fn]

            for r in fn_recs:
                stage = r.get("asset_stage","")
                conf  = r.get("confidence","")
                ta    = r.get("therapeutic_area","")
                tl    = r.get("timeline","")
                rec_id= r.get("rec_id","")

                st.markdown(f"""
                <div class="rec-card">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <strong>{rec_id}</strong>
                    <div>
                      {_stage_badge(stage)}&nbsp;
                      {_conf_badge(conf)}&nbsp;
                      <span style="font-size:0.75rem; color:#555;">{ta} · {tl}</span>
                    </div>
                  </div>
                  <div style="font-size:0.85rem; color:#333; margin-bottom:6px;">
                    <strong>Why it matters:</strong> {r.get("why_this_matters","")}
                  </div>
                  <div style="margin-bottom:6px;">
                    <strong>Action:</strong> {r.get("recommended_action","")}
                  </div>
                </div>""", unsafe_allow_html=True)

                with st.expander(f"Full details — {rec_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Target:** {r.get('target','')}")
                        st.markdown(f"**Expected impact:** {r.get('expected_impact','')}")
                        st.markdown(f"**KPI:** {r.get('kpi','')}")
                        st.markdown(f"**Region:** {r.get('region','')}")
                    with col2:
                        st.markdown(f"**Risk if no action:** {r.get('risk_if_no_action','')}")
                        src = r.get("signal_source","")
                        if src:
                            st.markdown(f"**Signal source:** {src}")

    # ── KPIs by function ──────────────────────────────────────────────────────
    dash = load_comm_ex_dashboard()
    kpis = dash.get("kpis_by_function", {})
    if kpis:
        st.divider()
        st.markdown("### KPI Register by Function")
        for fn, fn_kpis in kpis.items():
            if filters.get("function") and fn not in filters["function"]:
                continue
            with st.expander(fn):
                for item in fn_kpis:
                    st.markdown(f"- **{item.get('rec_id','')}** — {item.get('kpi','')}")


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 5 — History
# ══════════════════════════════════════════════════════════════════════════════

def render_history():
    st.markdown("## Pipeline Run History")

    history = build_history()
    if not history:
        st.info("No run history found.")
        return

    df = pd.DataFrame(history)

    # ── Trend charts ──────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Signals per Run**")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["run_date"], y=df["total_signals"],
            name="Raw", mode="lines+markers", line=dict(color="#999"),
        ))
        fig.add_trace(go.Scatter(
            x=df["run_date"], y=df["approved"],
            name="Approved", mode="lines+markers", line=dict(color="#28a745"),
        ))
        fig.add_trace(go.Scatter(
            x=df["run_date"], y=df["final_signals"],
            name="Final", mode="lines+markers", line=dict(color="#003087"),
        ))
        fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=260,
                          plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("**Decision Quality Score**")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["run_date"], y=df["dq_score"],
            marker_color="#cc0000",
            text=df["dq_score"],
            textposition="auto",
        ))
        fig.add_hline(y=70, line_dash="dash", line_color="green",
                      annotation_text="Pass threshold (70)")
        fig.update_layout(
            margin=dict(l=10,r=10,t=10,b=10), height=260,
            yaxis=dict(range=[0,100]),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── Run table ─────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**All Runs**")
    st.dataframe(
        df[["run_id","run_date","total_signals","approved","final_signals","dq_score","duration_s"]],
        use_container_width=True,
        column_config={
            "dq_score": st.column_config.ProgressColumn(
                "DQ Score", min_value=0, max_value=100, format="%d"
            ),
        },
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Tab 6 — Export
# ══════════════════════════════════════════════════════════════════════════════

def render_export():
    st.markdown("## Export & Download")

    recs     = load_latest_comm_ex_recs()
    signals  = load_signals()
    summary  = load_latest_summary()
    dash     = load_comm_ex_dashboard()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Comm Ex Outputs")

        if recs:
            st.download_button(
                "⬇ Recommendations (JSON)",
                data=json.dumps(recs, indent=2, ensure_ascii=False),
                file_name=f"comm_ex_recommendations_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

            rec_rows = [{
                "rec_id": r.get("rec_id"),
                "asset_stage": r.get("asset_stage"),
                "therapeutic_area": r.get("therapeutic_area"),
                "function_owner": r.get("function_owner"),
                "timeline": r.get("timeline"),
                "confidence": r.get("confidence"),
                "target": r.get("target"),
                "recommended_action": r.get("recommended_action"),
                "kpi": r.get("kpi"),
                "risk_if_no_action": r.get("risk_if_no_action"),
            } for r in recs]
            csv = pd.DataFrame(rec_rows).to_csv(index=False)
            st.download_button(
                "⬇ Recommendations (CSV)",
                data=csv,
                file_name=f"comm_ex_recommendations_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

        if dash:
            st.download_button(
                "⬇ Dashboard Data (JSON)",
                data=json.dumps(dash, indent=2, ensure_ascii=False),
                file_name="comm_ex_dashboard.json",
                mime="application/json",
            )

        if summary:
            st.download_button(
                "⬇ Executive Summary (TXT)",
                data=summary,
                file_name=f"comm_ex_summary_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
            )

    with col2:
        st.markdown("### Signal Intelligence")

        if signals:
            sig_rows = [{
                "signal_id": s.get("signal_id"),
                "date": s.get("signal_date","")[:10],
                "source": s.get("source"),
                "region": s.get("region"),
                "country": s.get("country"),
                "headline": s.get("headline"),
                "confidence_score": s.get("confidence_score"),
                "source_url": s.get("source_url"),
            } for s in signals]
            csv_sigs = pd.DataFrame(sig_rows).to_csv(index=False)
            st.download_button(
                "⬇ Signals (CSV)",
                data=csv_sigs,
                file_name=f"signals_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

            st.download_button(
                "⬇ Signals (JSON)",
                data=json.dumps(signals, indent=2, ensure_ascii=False),
                file_name=f"signals_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
            )

    if summary:
        st.divider()
        st.markdown("### Summary Preview")
        st.text_area("Copy to clipboard", value=summary, height=350, label_visibility="collapsed")


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    filters = render_sidebar()

    st.markdown("""
    <div style='display:flex; align-items:center; gap:12px; margin-bottom:4px;'>
      <span style='font-size:1.6rem; font-weight:700; color:#cc0000;'>
        J&amp;J Innovative Medicine
      </span>
      <span style='font-size:1rem; color:#666;'>AI &amp; Digital Transformation | Commercial Intelligence</span>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard",
        "📡 Signals",
        "📋 Briefing",
        "💼 Comm Ex",
        "📈 History",
        "⬇ Export",
    ])

    with tab1:
        render_dashboard()
    with tab2:
        render_signals(filters)
    with tab3:
        render_briefing()
    with tab4:
        render_comm_ex(filters)
    with tab5:
        render_history()
    with tab6:
        render_export()


if __name__ == "__main__":
    main()
