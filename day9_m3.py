def render_module_3():
    """HTA & Market Access -- HTA event feed per asset."""
    import json as _json

    st.subheader("HTA & Market Access")
    st.caption(f"Data as of: {last_run_timestamp()}")

    hta_events = st.session_state.get("dashboard", {}).get("hta_events", {})

    if not hta_events:
        st.info("No HTA events on record.")
        return

    def hta_body_badge(hta_body):
        colours = {"NICE": "#003865", "EUnetHTA": "#6A0DAD", "ICER": "#C9960C"}
        colour = colours.get(hta_body, "#374649")
        return (
            "<span style='background:" + colour
            + ";color:white;padding:3px 10px;"
            + "border-radius:4px;font-size:12px;font-weight:bold;'>"
            + hta_body + "</span>"
        )

    def decision_badge(decision_type):
        colours = {"POSITIVE": "#375623", "RESTRICTED": "#974706", "NEGATIVE": "#7B0000"}
        colour = colours.get(decision_type, "#374649")
        return (
            "<span style='background:" + colour
            + ";color:white;padding:3px 10px;"
            + "border-radius:4px;font-size:12px;font-weight:bold;'>"
            + decision_type + "</span>"
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
        label="Export HTA Events (JSON)",
        data=_json.dumps(events, indent=2),
        file_name=f"hta_{selected_id}.json",
        mime="application/json",
    )
