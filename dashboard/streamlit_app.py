import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Kai CommEx Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Kai CommEx Insights")
st.caption("Commercial Intelligence for Launch Readiness")
st.markdown(
    "Integrating regulatory, HTA, and competitive signals to assess launch readiness and strategic risk."
)

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
ASSET_REG_PATH = ROOT_DIR / "asset-registry" / "apex_assets.json"
DASHBOARD_PATH = ROOT_DIR / "comm-ex" / "outputs" / "comm_ex_dashboard_ready.json"

sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "agents"))

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "selected_assets" not in st.session_state:
    st.session_state["selected_assets"] = []


def load_asset_registry():
    try:
        raw = json.loads(ASSET_REG_PATH.read_text(encoding="utf-8"))
        return raw.get("assets", raw)
    except Exception as e:
        st.warning(f"Could not load asset registry: {e}")
        return []


def load_dashboard():
    try:
        return json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        st.warning(f"Could not load dashboard data: {e}")
        return {}


def init_session_state():
    if "asset_registry" not in st.session_state:
        st.session_state["asset_registry"] = load_asset_registry()

    if "dashboard" not in st.session_state:
        st.session_state["dashboard"] = load_dashboard()


init_session_state()


def last_run_timestamp():
    return st.session_state["dashboard"].get("meta", {}).get("generated_at", "N/A")


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
# Module 1: Launch Intelligence
# ---------------------------------------------------------------------------
def render_module_1():
    st.subheader("Launch Intelligence")
    st.caption(f"Data as of: {last_run_timestamp()}")

    tier_colors = {
        "LAUNCH-READY": "#2ecc71",
        "ON-TRACK": "#3498db",
        "AT-RISK": "#e67e22",
        "NOT-READY": "#e74c3c",
    }

    scorecard_dir = ROOT_DIR / "agents" / "outputs"
    sc_files = (
        sorted(scorecard_dir.glob("launch_readiness_scorecard_APEX-*.json"))
        if scorecard_dir.exists()
        else []
    )

    scorecards = {}
    for f in sc_files:
        try:
            sc = json.loads(f.read_text(encoding="utf-8"))
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

    brand_names = [a.get("brand_name", "?") for a in assets]
    asset_ids = [a.get("apex_id", a.get("asset_id", "?")) for a in assets]

    scores = []
    tiers = []
    colors = []

    for aid in asset_ids:
        sc = scorecards.get(aid)
        if sc:
            score = sc.get("overall_score", 0)
            tier = sc.get("overall_tier", "N/A")
        else:
            score = 0
            tier = "No Scorecard"

        scores.append(score)
        tiers.append(tier)
        colors.append(tier_colors.get(tier, "#95a5a6"))

    if not any(s > 0 for s in scores):
        st.warning(
            f"No scorecard data found in agents/outputs/ ({len(sc_files)} file(s) present).\n\n"
            "Run: python generate_all_scorecards.py to generate scores for all assets."
        )

    fig = go.Figure(
        go.Bar(
            x=brand_names,
            y=scores,
            marker_color=colors,
            text=[f"{s}<br>{t}" for s, t in zip(scores, tiers)],
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Score: %{y}<br>Tier: %{customdata}<extra></extra>",
            customdata=tiers,
        )
    )

    fig.update_layout(
        title="Launch Readiness Score by Asset",
        xaxis_title="Asset",
        yaxis_title="Score",
        yaxis_range=[0, 115],
        showlegend=False,
        height=420,
        margin=dict(t=60, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

    rows = []
    for asset, aid, score, tier in zip(assets, asset_ids, scores, tiers):
        rows.append(
            {
                "Asset": asset.get("brand_name", aid),
                "Apex ID": aid,
                "Stage": asset.get("lifecycle_stage", asset.get("asset_stage", "?")),
                "Score": score if score > 0 else "--",
                "Tier": tier,
            }
        )

    st.dataframe(rows, use_container_width=True)

    missing = [
        a.get("brand_name")
        for a, aid in zip(assets, asset_ids)
        if aid not in scorecards
    ]

    if missing:
        st.info(
            f"Missing scorecards for: {', '.join(missing)}.\n"
            "Run: python generate_all_scorecards.py"
        )


# ---------------------------------------------------------------------------
# Module 2: Asset Strategy
# ---------------------------------------------------------------------------
def render_module_2():
    st.subheader("Asset Strategy")
    st.caption(f"Data as of: {last_run_timestamp()}")

    d = st.session_state.get("dashboard", {})

    immediate = d.get("immediate_actions", [])
    top_risks = d.get("top_risks", [])
    top_opps = d.get("top_opportunities", [])
    kpis = d.get("kpis_by_function", {})
    coverage = d.get("coverage_check", {})

    if not immediate and not top_risks:
        st.info(
            "No recommendation data available.\n\n"
            "Run: python run_comm_ex.py --comm-ex-only"
        )
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Recommendations", d.get("rec_count", 0))
    col2.metric("Immediate Actions", coverage.get("immediate_actions", 0))
    col3.metric("High Confidence", coverage.get("high_confidence", 0))
    col4.metric("% High Confidence", f"{coverage.get('pct_high_confidence', 0)}%")

    st.divider()

    if immediate:
        st.markdown("### Immediate Actions")
        for rec in immediate:
            with st.expander(
                f"{rec.get('rec_id', '?')} | {rec.get('function_owner', '?')}",
                expanded=False,
            ):
                st.write(rec.get("recommended_action", ""))
                if rec.get("kpi"):
                    st.caption(f"KPI: {rec.get('kpi')}")

    if top_risks:
        st.divider()
        st.markdown("### Top Strategic Risks")
        for risk in top_risks:
            label = (
                f"**{risk.get('rec_id', '')}** "
                f"[{risk.get('asset_stage', '')}] | "
                f"{risk.get('timeline', '')} | "
                f"{risk.get('function', '')}"
            )
            st.error(f"{label}\n\n{risk.get('risk', '')}")

    if top_opps:
        st.divider()
        st.markdown("### Top Opportunities")
        for opp in top_opps:
            with st.expander(
                f"{opp.get('rec_id', '?')} | {opp.get('function', '?')}",
                expanded=False,
            ):
                st.write(f"**Target:** {opp.get('target', '')}")
                st.write(f"**Expected Impact:** {opp.get('expected_impact', '')}")
                if opp.get("kpi"):
                    st.caption(f"KPI: {opp.get('kpi')}")

    if kpis:
        st.divider()
        st.markdown("### KPIs by Function")
        for func, kpi_list in kpis.items():
            if kpi_list:
                st.markdown(f"**{func}**")
                for kpi_item in kpi_list:
                    st.write(f"- {kpi_item}")


# ---------------------------------------------------------------------------
# Module 3: HTA & Market Access
# ---------------------------------------------------------------------------
def render_module_3():
    st.subheader("HTA & Market Access")
    st.caption(f"Data as of: {last_run_timestamp()}")

    hta_events = st.session_state.get("dashboard", {}).get("hta_events", {})

    if not hta_events:
        st.info("No HTA events on record.")
        return

    def hta_body_badge(hta_body):
        colors = {"NICE": "#003865", "EUnetHTA": "#6A0DAD", "ICER": "#C9960C"}
        color = colors.get(hta_body, "#374649")
        return (
            f"<span style='background:{color};color:white;padding:3px 10px;"
            f"border-radius:4px;font-size:12px;font-weight:bold;'>{hta_body}</span>"
        )

    def decision_badge(decision_type):
        colors = {
            "POSITIVE": "#375623",
            "RESTRICTED": "#974706",
            "NEGATIVE": "#7B0000",
        }
        color = colors.get(decision_type, "#374649")
        return (
            f"<span style='background:{color};color:white;padding:3px 10px;"
            f"border-radius:4px;font-size:12px;font-weight:bold;'>{decision_type}</span>"
        )

    apex_ids = list(hta_events.keys())
    selected_id = st.selectbox("Select Asset", apex_ids, key="hta_asset_selector")
    events = hta_events.get(selected_id, [])

    if not events:
        st.info("No HTA events on record.")
        return

    for event in events:
        hta_body = event.get("hta_body", "")
        decision_type = event.get("decision_type", "")
        indication = event.get("indication", "")
        label = f"{hta_body} | {decision_type} | {indication}"

        with st.expander(label, expanded=False):
            st.markdown(
                hta_body_badge(hta_body) + "&nbsp;&nbsp;" + decision_badge(decision_type),
                unsafe_allow_html=True,
            )
            st.write("")

            col_left, col_right = st.columns(2)

            with col_left:
                st.metric("Decision Date", event.get("decision_date", "N/A"))
                st.metric("HTA Body", hta_body)

            with col_right:
                st.subheader("Reimbursement Strategy")
                st.write(event.get("reimbursement_strategy", "N/A"))
                st.caption("Evidence gap: " + event.get("evidence_gap", "N/A"))

    st.download_button(
        label="Export HTA Events JSON",
        data=json.dumps(events, indent=2),
        file_name=f"hta_{selected_id}.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------------
# Module 4: Competitive Response
# ---------------------------------------------------------------------------
def render_module_4():
    st.subheader("Competitive Response")
    st.caption(f"Data as of: {last_run_timestamp()}")

    competitive_intel = st.session_state.get("dashboard", {}).get(
        "competitive_intel", {}
    )

    all_plans = []
    for apex_id, plans in competitive_intel.items():
        for plan in plans:
            entry = dict(plan)
            entry.setdefault("apex_id", apex_id)
            all_plans.append(entry)

    if not all_plans:
        st.warning("No action plans match the selected filters.")
        return

    all_apex_ids = sorted({p.get("apex_id", "") for p in all_plans})
    all_functions = sorted({p.get("function_owner", "") for p in all_plans})

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        selected_assets = st.multiselect(
            "Asset", options=all_apex_ids, default=[], key="comp_asset_filter"
        )

    with col_f2:
        selected_functions = st.multiselect(
            "Function", options=all_functions, default=[], key="comp_function_filter"
        )

    filtered = all_plans

    if selected_assets:
        filtered = [p for p in filtered if p.get("apex_id") in selected_assets]

    if selected_functions:
        filtered = [p for p in filtered if p.get("function_owner") in selected_functions]

    st.metric("Action Plans Displayed", len(filtered))

    if not filtered:
        st.warning("No action plans match the selected filters.")
        return

    def priority_badge(priority):
        colors = {
            "IMMEDIATE": "#7B0000",
            "STRATEGIC": "#003865",
            "MONITOR": "#374649",
        }
        color = colors.get(priority, "#374649")
        return (
            f"<span style='background:{color};color:white;padding:3px 8px;"
            f"border-radius:4px;font-size:11px;font-weight:bold;'>{priority}</span>"
        )

    def function_badge(function_owner):
        colors = {
            "Market Access": "#1F3864",
            "Marketing": "#C9960C",
            "Medical Affairs": "#375623",
            "Regulatory": "#4A235A",
        }
        color = colors.get(function_owner, "#374649")
        return (
            f"<span style='background:{color};color:white;padding:3px 8px;"
            f"border-radius:4px;font-size:11px;'>{function_owner}</span>"
        )

    def asset_badge(apex_id):
        return (
            f"<span style='background:#003865;color:white;padding:3px 8px;"
            f"border-radius:4px;font-size:11px;font-weight:bold;'>{apex_id}</span>"
        )

    for plan in filtered:
        apex_id = plan.get("apex_id", "")
        func = plan.get("function_owner", "")
        priority = plan.get("priority", "")
        escalation = plan.get("escalation_flag", False)

        flag_html = (
            " &nbsp;<span style='color:red;font-size:16px;' "
            "title='Escalation Required'>🚩</span>"
            if escalation
            else ""
        )

        badges = (
            asset_badge(apex_id)
            + "&nbsp;"
            + function_badge(func)
            + "&nbsp;"
            + priority_badge(priority)
            + flag_html
        )

        with st.container(border=True):
            st.markdown(badges, unsafe_allow_html=True)
            st.subheader(plan.get("threat_event", ""))
            st.write(plan.get("action_30d", ""))
            st.caption("KPI: " + plan.get("kpi", ""))

    export_fields = [
        "apex_id",
        "threat_event",
        "function_owner",
        "priority",
        "action_30d",
        "kpi",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=export_fields, extrasaction="ignore")
    writer.writeheader()

    for plan in filtered:
        writer.writerow({k: plan.get(k, "") for k in export_fields})

    st.download_button(
        label="Export Playbook CSV",
        data=output.getvalue().encode("utf-8"),
        file_name="competitive_playbook.csv",
        mime="text/csv",
    )


# ---------------------------------------------------------------------------
# Module 5: GCSO Feed
# ---------------------------------------------------------------------------
def render_module_5():
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
        logo_path = ROOT_DIR / "assets" / "logo.png"

        if logo_path.exists():
            st.image(str(logo_path))
        else:
            st.markdown("## Kai CommEx Insights")

        st.divider()

        if st.button("Refresh Dashboard Data"):
            for key in ("dashboard", "asset_registry", "selected_assets"):
                st.session_state.pop(key, None)

            init_session_state()
            st.success("Data refreshed.")
            st.rerun()

        st.divider()

        all_assets = [a.get("brand_name", "Unknown") for a in load_asset_registry()]

        st.session_state["selected_assets"] = st.multiselect(
            "Filter by Asset",
            all_assets,
            default=st.session_state["selected_assets"],
        )

        st.divider()

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

        with st.expander("GCSO Intelligence Feed", expanded=False):
            d = st.session_state.get("dashboard", {})
            st.caption(f"Generated: {d.get('meta', {}).get('generated_at', 'N/A')}")

            imm = [r for r in d.get("recs", []) if r.get("urgency") == "Immediate"][:3]

            if imm:
                st.markdown("**Immediate Actions**")
                for r in imm:
                    st.write(
                        f"{r.get('rec_id', '')} | {r.get('function_owner', '')} | "
                        f"{str(r.get('recommended_action', ''))[:80]}..."
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
                        f"{apex_id} | {m.get('milestone_type', '')} | "
                        f"{m.get('milestone_date', '')}"
                    )

            det = [
                k
                for k, v in d.get("memory_deltas", {}).items()
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