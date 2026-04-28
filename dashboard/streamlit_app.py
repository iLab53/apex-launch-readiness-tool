import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent.parent
ASSET_REG_PATH = ROOT_DIR / "asset-registry" / "apex_assets.json"
DASHBOARD_PATH = ROOT_DIR / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "agents"))

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="APEX Commercial Intelligence",
    page_icon="favicon.ico" if Path("favicon.ico").exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

if "selected_assets" not in st.session_state:
    st.session_state["selected_assets"] = []

# ---------------------------------------------------------------------------
# Session state initialisation  (must happen before any widget renders)
# ---------------------------------------------------------------------------
def load_asset_registry():
    try:
        raw = json.loads(ASSET_REG_PATH.read_text(encoding="utf-8"))
        return raw.get("assets", raw)
    except Exception:
        return []


def init_session_state():
    # Load asset registry
    if "asset_registry" not in st.session_state:
        st.session_state["asset_registry"] = load_asset_registry()

    # Load dashboard JSON
    if "dashboard" not in st.session_state:
        try:
            st.session_state["dashboard"] = json.loads(
                DASHBOARD_PATH.read_text(encoding="utf-8")
            )
        except Exception:
            st.session_state["dashboard"] = {}

init_session_state()

# ---------------------------------------------------------------------------
# Helper: last-run timestamp from meta.generated_at
# ---------------------------------------------------------------------------
def last_run_timestamp():
    return (
        st.session_state["dashboard"]
        .get("meta", {})
        .get("generated_at", "N/A")
    )


def get_selected_assets() -> list[dict]:
    selected = set(st.session_state.get("selected_assets", []))
    assets = st.session_state.get("asset_registry", [])
    if not selected:
        return assets
    return [asset for asset in assets if asset.get("brand_name") in selected]


def has_upcoming_milestone(asset: dict, days: int = 30) -> bool:
    apex_id = asset.get("asset_id") or asset.get("apex_id")
    if not apex_id:
        return False
    milestone_alerts = st.session_state.get("dashboard", {}).get("milestone_alerts", {})
    milestones = milestone_alerts.get(apex_id, [])
    return any(m.get("days_to_event", 999) <= days for m in milestones)


def get_next_milestone_type(asset: dict) -> str | None:
    apex_id = asset.get("asset_id") or asset.get("apex_id")
    if not apex_id:
        return None
    milestone_alerts = st.session_state.get("dashboard", {}).get("milestone_alerts", {})
    milestones = milestone_alerts.get(apex_id, [])
    upcoming = sorted(
        (m for m in milestones if m.get("days_to_event", 999) >= 0),
        key=lambda m: m.get("days_to_event", 999),
    )
    if not upcoming:
        return None
    return upcoming[0].get("milestone_type")

# ---------------------------------------------------------------------------
# Stub renderers  (Days 9-11 will fill these in via Codex)
# ---------------------------------------------------------------------------
def render_module_1():
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
            f"No scorecard data found in agents/outputs/ ({len(sc_files)} file(s) present).\n\n"
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
            f"Missing scorecards for: {', '.join(missing)}.\n"
            "Run:  python generate_all_scorecards.py"
        )

def render_module_2():
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
            "No recommendation data available.\n\n"
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
            st.error(f"{label}\n\n{risk.get('risk','')}")

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

def render_module_3():
    """HTA & Market Access -- HTA event feed per asset."""
    st.subheader("HTA & Market Access")
    st.caption(f"Data as of: {last_run_timestamp()}")
    st.info("Module 3 body coming in Day 9. Stub active.")


def render_module_4():
    """Competitive Response -- 30-day cross-functional action plans."""
    st.subheader("Competitive Response")
    st.caption(f"Data as of: {last_run_timestamp()}")
    st.info("Module 4 body coming in Day 9. Stub active.")


def render_module_5():
    """GCSO Feed -- milestone calendar and unified intelligence digest."""
    st.subheader("GCSO Feed")
    st.caption(f"Data as of: {last_run_timestamp()}")
    assets = get_selected_assets()
    if not assets:
        st.info("No assets selected.")
        return

    found_upcoming = False
    for asset in assets:
        if not has_upcoming_milestone(asset, days=30):
            continue

        milestone_type = get_next_milestone_type(asset)
        apex_id = asset.get("asset_id") or asset.get("apex_id")
        brand_name = asset.get("brand_name", apex_id or "Unknown asset")
        if not milestone_type or not apex_id:
            continue

        found_upcoming = True
        st.markdown(f"**{brand_name}**")
        if st.button(
            f"Generate Milestone Prep - {milestone_type}",
            key=f"milestone_prep_{apex_id}_{milestone_type}",
        ):
            with st.spinner("Generating milestone prep document..."):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT_DIR / "run_comm_ex.py"),
                        "--milestone-prep",
                        apex_id,
                        milestone_type,
                    ],
                    cwd=str(ROOT_DIR),
                    capture_output=True,
                    text=True,
                )
            if result.returncode == 0:
                st.success("Milestone prep document generated.")
            else:
                st.error(f"Error: {result.stderr}")

    if not found_upcoming:
        st.info("No milestones within 30 days for the selected assets.")


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.image(str(ROOT_DIR / "assets" / "logo.png")) if (
            ROOT_DIR / "assets" / "logo.png"
        ).exists() else st.markdown("## APEX")

        st.divider()

        # Refresh button
        if st.button("Refresh Dashboard Data"):
            for key in ("dashboard", "asset_registry", "selected_assets"):
                st.session_state.pop(key, None)
            init_session_state()
            st.success("Data refreshed.")
            st.rerun()

        st.divider()

        all_assets = [a["brand_name"] for a in load_asset_registry()]
        st.session_state["selected_assets"] = st.sidebar.multiselect(
            "Filter by Asset",
            all_assets,
            default=st.session_state["selected_assets"],
        )

        st.divider()

        # Module selector
        selected_module = st.radio(
            "Module",
            options=[
                "Launch Intelligence",
                "Asset Strategy",
                "HTA & Market Access",
                "Competitive Response",
                "GCSO Feed",
            ],
            key="selected_module",
        )

        st.divider()

        # GCSO Intelligence Feed (collapsible, always at bottom)
        with st.expander("GCSO Intelligence Feed", expanded=False):
            d = st.session_state.get("dashboard", {})
            st.caption(f"Generated: {d.get('meta', {}).get('generated_at', 'N/A')}")

            imm = [
                r for r in d.get("recs", [])
                if r.get("urgency") == "Immediate"
            ][:3]
            if imm:
                st.markdown("**Immediate Actions**")
                for r in imm:
                    st.write(
                        f"{r.get('rec_id','')} | {r.get('function_owner','')} | "
                        f"{str(r.get('recommended_action',''))[:80]}..."
                    )

            close_ms = []
            for apex_id, ms_list in d.get("milestone_alerts", {}).items():
                for m in ms_list:
                    if m.get("days_to_event", 999) <= 14:
                        close_ms.append((apex_id, m))
            if close_ms:
                st.markdown("**Milestones within 14 days**")
                for apex_id, m in close_ms:
                    st.write(
                        f"{apex_id} | {m.get('milestone_type','')} | "
                        f"{m.get('milestone_date','')}"
                    )

            det = [
                k for k, v in d.get("memory_deltas", {}).items()
                if v.get("trend") == "DETERIORATING"
            ]
            if det:
                st.warning("Trend DETERIORATING: " + ", ".join(det))

            risks = d.get("top_risks", [])
            if risks:
                st.markdown("**Top Strategic Risk**")
                st.caption(str(risks[0].get("signal_text", ""))[:120])

    return selected_module


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    selected_module = render_sidebar()

    # Module router -- session-state / sidebar driven, no query params
    if selected_module == "Launch Intelligence":
        render_module_1()
        return

    if selected_module == "Asset Strategy":
        render_module_2()
        return

    if selected_module == "HTA & Market Access":
        render_module_3()
        return

    if selected_module == "Competitive Response":
        render_module_4()
        return

    if selected_module == "GCSO Feed":
        render_module_5()
        return


if __name__ == "__main__":
    main()
