def render_module_4():
    """Competitive Response -- 30-day cross-functional action plans."""
    import io
    import csv as _csv

    st.subheader("Competitive Response")
    st.caption(f"Data as of: {last_run_timestamp()}")

    competitive_intel = st.session_state.get("dashboard", {}).get("competitive_intel", {})

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
        colours = {"IMMEDIATE": "#7B0000", "STRATEGIC": "#003865", "MONITOR": "#374649"}
        colour = colours.get(priority, "#374649")
        return (
            "<span style='background:" + colour
            + ";color:white;padding:3px 8px;"
            + "border-radius:4px;font-size:11px;font-weight:bold;'>"
            + priority + "</span>"
        )

    def function_badge(function_owner):
        colours = {
            "Market Access": "#1F3864", "Marketing": "#C9960C",
            "Medical Affairs": "#375623", "Regulatory": "#4A235A",
        }
        colour = colours.get(function_owner, "#374649")
        return (
            "<span style='background:" + colour
            + ";color:white;padding:3px 8px;"
            + "border-radius:4px;font-size:11px;'>"
            + function_owner + "</span>"
        )

    def asset_badge(apex_id):
        return (
            "<span style='background:#003865;color:white;padding:3px 8px;"
            + "border-radius:4px;font-size:11px;font-weight:bold;'>"
            + apex_id + "</span>"
        )

    for plan in filtered:
        apex_id = plan.get("apex_id", "")
        func = plan.get("function_owner", "")
        priority = plan.get("priority", "")
        escalation = plan.get("escalation_flag", False)
        flag_html = (
            " &nbsp;<span style='color:red;font-size:16px;' "
            "title='Escalation Required'>\U0001f6a9</span>"
            if escalation else ""
        )
        badges = (
            asset_badge(apex_id) + "&nbsp;"
            + function_badge(func) + "&nbsp;"
            + priority_badge(priority) + flag_html
        )
        with st.container(border=True):
            st.markdown(badges, unsafe_allow_html=True)
            st.subheader(plan.get("threat_event", ""))
            st.write(plan.get("action_30d", ""))
            st.caption("KPI: " + plan.get("kpi", ""))

    export_fields = ["apex_id", "threat_event", "function_owner", "priority", "action_30d", "kpi"]
    output = io.StringIO()
    writer = _csv.DictWriter(output, fieldnames=export_fields, extrasaction="ignore")
    writer.writeheader()
    for plan in filtered:
        writer.writerow({k: plan.get(k, "") for k in export_fields})

    st.download_button(
        label="Export Playbook (CSV)",
        data=output.getvalue().encode("utf-8"),
        file_name="competitive_playbook.csv",
        mime="text/csv",
    )
