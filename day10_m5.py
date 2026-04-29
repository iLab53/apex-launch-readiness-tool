def render_module_5():
    """Milestone Prep View -- portfolio readiness chart + milestone calendar."""
    import json as _json
    import pathlib as _pathlib

    st.subheader("Milestone Prep")
    st.caption(f"Data as of: {last_run_timestamp()}")

    dashboard = st.session_state.get("dashboard", {})
    milestone_alerts = dashboard.get("milestone_alerts", {})
    launch_readiness = dashboard.get("launch_readiness", {})

    # ------------------------------------------------------------------ #
    # SECTION A -- Portfolio Readiness Bar Chart                          #
    # ------------------------------------------------------------------ #
    st.markdown("### Portfolio Readiness Overview")

    # Build score data -- prefer launch_readiness dict, fallback to scorecard files
    score_data = {}
    if launch_readiness:
        for apex_id, info in launch_readiness.items():
            score_data[apex_id] = {
                "brand": info.get("brand_name", apex_id),
                "score": float(info.get("launch_readiness_score", 0)),
            }
    else:
        # Fallback: read from agents/outputs/launch_readiness_scorecard_*.json
        scorecard_dir = _pathlib.Path(__file__).parent.parent / "agents" / "outputs"
        for sc_file in sorted(scorecard_dir.glob("launch_readiness_scorecard_APEX-*.json")):
            try:
                sc = _json.loads(sc_file.read_text(encoding="utf-8"))
                apex_id = sc.get("asset_id", sc_file.stem.split("_")[3])
                score_data[apex_id] = {
                    "brand": sc.get("brand_name", apex_id),
                    "score": float(sc.get("overall_score", sc.get("score", 0))),
                }
            except Exception:
                continue

    if score_data:
        try:
            import plotly.express as px
            import pandas as pd

            df = pd.DataFrame([
                {
                    "Asset": v["brand"],
                    "LRS Score": v["score"],
                    "Tier": (
                        "Launch Ready" if v["score"] >= 75
                        else "At Risk" if v["score"] < 50
                        else "On Track"
                    ),
                }
                for v in score_data.values()
            ]).sort_values("LRS Score", ascending=False)

            colour_map = {
                "Launch Ready": "#375623",
                "On Track":     "#C9960C",
                "At Risk":      "#7B0000",
            }

            fig = px.bar(
                df,
                x="Asset",
                y="LRS Score",
                color="Tier",
                color_discrete_map=colour_map,
                range_y=[0, 100],
                text="LRS Score",
            )
            fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
            fig.update_layout(
                showlegend=True,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=0),
                height=320,
            )
            st.plotly_chart(fig, use_container_width=True)

            scores = [v["score"] for v in score_data.values()]
            avg_lrs  = round(sum(scores) / len(scores), 1) if scores else 0
            ready    = sum(1 for s in scores if s >= 75)
            at_risk  = sum(1 for s in scores if s < 50)

            m1, m2, m3 = st.columns(3)
            m1.metric("Average LRS", f"{avg_lrs}")
            m2.metric("Assets \u2265 75", ready)
            m3.metric("Assets < 50", at_risk)

        except ImportError:
            # plotly not installed -- show simple table fallback
            st.info("Install plotly for bar chart. Showing table instead.")
            for apex_id, v in score_data.items():
                st.write(f"**{v['brand']}** — {v['score']:.0f}")
    else:
        st.info("No launch readiness scores available.")

    st.divider()

    # ------------------------------------------------------------------ #
    # SECTION B -- Milestone Calendar                                     #
    # ------------------------------------------------------------------ #
    st.markdown("### Milestone Calendar")

    if not milestone_alerts:
        st.info("No milestones within 30 days.")
        return

    # Build apex_id -> brand_name mapping from asset registry
    brand_map = {
        a.get("apex_id", a.get("asset_id", "")): a.get("brand_name", "")
        for a in st.session_state.get("asset_registry", [])
    }

    type_colours = {
        "LRR":                "#003865",
        "LRP":                "#1F3864",
        "ADP_REVIEW":         "#C9960C",
        "INVESTMENT_DECISION":"#375623",
        "GOVERNANCE":         "#4A235A",
    }

    def type_badge(milestone_type):
        colour = type_colours.get(milestone_type, "#374649")
        label  = milestone_type.replace("_", " ")
        return (
            "<span style='background:" + colour
            + ";color:white;padding:3px 9px;"
            + "border-radius:4px;font-size:11px;font-weight:bold;'>"
            + label + "</span>"
        )

    for apex_id, milestones in milestone_alerts.items():
        brand = brand_map.get(apex_id, apex_id)
        header = f"{brand} ({apex_id})" if brand and brand != apex_id else apex_id

        with st.expander(header, expanded=False):
            for ms in milestones:
                ms_type  = ms.get("milestone_type", "")
                ms_label = ms.get("milestone_label", "")
                ms_date  = ms.get("milestone_date", "")
                ms_days  = ms.get("days_to_event", "?")
                doc_id   = ms.get("document_id", "")

                c1, c2, c3, c4 = st.columns([1, 3, 1.5, 1.5])

                with c1:
                    st.markdown(type_badge(ms_type), unsafe_allow_html=True)

                with c2:
                    st.write(ms_label)

                with c3:
                    st.metric("Date / Days Out", ms_date, delta=f"{ms_days}d")

                with c4:
                    # Look for briefing doc in memory/ folder
                    doc_path = (
                        _pathlib.Path(__file__).parent.parent
                        / "memory"
                        / (doc_id + ".json")
                    )
                    doc_data = (
                        doc_path.read_bytes()
                        if doc_path.exists()
                        else b"{}"
                    )
                    st.download_button(
                        label="Get Briefing Doc",
                        data=doc_data,
                        file_name=(doc_id + ".json") if doc_id else "briefing.json",
                        mime="application/json",
                        key=f"dl_{apex_id}_{ms_type}_{ms_date}",
                    )
