from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from qa_dashboard import kpis as k
from qa_dashboard.models import Dataset, Filters

from ..components import chart, empty_state, has_data, kpi_row, page_header, records_table, section, with_names
from ..theme import AUTOMATION_COLORS, ENVIRONMENT_COLORS, PRIORITY_COLORS, TEAM_COLORS

PROD_COLUMNS = ["issue_key", "issue_type", "project_key", "team_id", "summary", "status", "priority", "environment",
                "created", "resolved", "linked_issue_key"]
RATE_SERIES = {"Defect escape rate": "#DC2626", "Automation stability": "#2563EB", "Reporting timeliness": "#0D9488"}


def _donut(df, names, colors, key, center):
    fig = px.pie(df, names=names, values="count", hole=0.62, color=names, color_discrete_map=colors)
    fig.update_traces(textinfo="percent", sort=False)
    fig.add_annotation(text=center, showarrow=False, font=dict(size=14))
    chart(fig, key, height=300, legend="bottom")


def render(ds: Dataset, f: Filters) -> None:
    page_header("Quality & Coverage", "Escaped defects, automation, coverage and QA process indicators.", ds, f)

    kpi_row([k.qq01_test_coverage(ds, f), k.qq02_bug_reporting_quality(ds, f), k.qq03_defect_escape_rate(ds, f),
             k.qq06_production_incidents(ds, f)])
    st.write("")
    kpi_row([k.qq04_automation_coverage(ds, f), k.qq05_automation_stability(ds, f), k.qq07_reporting_timeliness(ds, f),
             k.qq08_coordinator_retention(ds, f)])
    st.caption("QQ-01 and QQ-04 are current snapshots (no date rule documented). QQ-07 and QQ-08 are proxies built on "
               "assumed supporting datasets. Hover a card for its definition notes.")

    section("Production defect distribution (QQ-03 numerator)")
    prod = k.production_bugs(ds, f)
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.caption("PROD bugs by project")
        if not prod.empty:
            df = prod.groupby(["project_key", "team_id"]).size().rename("count").reset_index()
            fig = px.bar(df, x="count", y="project_key", color="team_id", color_discrete_map=TEAM_COLORS, orientation="h", text="count")
            fig.update_yaxes(categoryorder="total ascending")
            chart(fig, "qq-prod-project", height=280, legend=False)
        else:
            empty_state()
    with c2:
        st.caption("PROD bugs by priority")
        if not prod.empty:
            df = prod["priority"].value_counts().reindex(list(PRIORITY_COLORS), fill_value=0).rename_axis("priority").rename("count").reset_index()
            fig = px.bar(df, x="priority", y="count", color="priority", color_discrete_map=PRIORITY_COLORS, text="count")
            chart(fig, "qq-prod-priority", height=280, legend=False)
        else:
            empty_state()
    with c3:
        st.caption("All bugs by detection environment")
        env = k.bugs_by_environment(ds, f)
        if has_data(env, "count"):
            _donut(env, "environment", ENVIRONMENT_COLORS, "qq-env", "Bugs by<br>env.")
        else:
            empty_state()

    section("Automated versus manual testing")
    c4, c5, c6 = st.columns([1, 1, 2], gap="medium")
    with c4:
        st.caption("Active test cases by automation status (QQ-04)")
        split = k.automation_status_split(ds, f)
        _donut(split, "automation_status", AUTOMATION_COLORS, "qq-auto-status", "Test<br>cases") if has_data(split, "count") else empty_state()
    with c5:
        st.caption("Test runs by execution mode (TE-01)")
        modes = k.execution_mode_split(ds, f)
        _donut(modes, "execution_mode", AUTOMATION_COLORS, "qq-auto-mode", "Runs") if has_data(modes, "count") else empty_state()
    with c6:
        st.caption("Automation coverage at month end (QQ-04, approximation: Deprecated status as of today)")
        trend = k.qq04_automation_trend(ds, f)
        if has_data(trend, "active"):
            fig = px.area(trend, x="period", y="rate", hover_data={"automated": True, "active": True})
            fig.update_traces(line_color="#2563EB", fillcolor="rgba(37,99,235,0.12)")
            fig.update_yaxes(tickformat=".0%", rangemode="tozero")
            chart(fig, "qq-auto-trend", height=280, legend=False)
        else:
            empty_state()

    section("Quality trends by month")
    qt = k.quality_trend(ds, f)
    if qt.empty:
        empty_state()
    else:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=qt["period"], y=qt["Production incidents"], name="Production incidents (QQ-06)",
                             marker_color="#CBD5E1"), secondary_y=True)
        for name, color in RATE_SERIES.items():
            fig.add_trace(go.Scatter(x=qt["period"], y=qt[name], name=name, mode="lines+markers", line=dict(color=color, width=2.5),
                                     connectgaps=False), secondary_y=False)
        fig.update_yaxes(tickformat=".0%", secondary_y=False, gridcolor="#EEF2F7", range=[0, 1.05])
        max_incidents = int(qt["Production incidents"].max() or 0)
        fig.update_yaxes(showgrid=False, secondary_y=True, rangemode="tozero", tickformat="d",
                         dtick=max(1, -(-max_incidents // 4)), title_text="Incidents")
        fig.update_layout(hovermode="x unified")
        chart(fig, "qq-trends", height=340)

    section("QA coordinator assignments (QQ-08)")
    timeline = k.coordinator_timeline(ds, f)
    if timeline.empty:
        empty_state()
    else:
        fig = px.timeline(timeline, x_start="start_date", x_end="end_display", y="team_name", color="team_id",
                          color_discrete_map=TEAM_COLORS, text="display_name", hover_data={"end_date": "|%Y-%m-%d"})
        fig.add_vrect(x0=f.start, x1=f.end, fillcolor="#2563EB", opacity=0.06, line_width=0)
        fig.update_yaxes(categoryorder="category descending")
        chart(fig, "qq-coord", height=260, legend=False)

    section("Production defects and incidents")
    records = pd.concat(
        [prod.reindex(columns=PROD_COLUMNS), k.incidents(ds, f).reindex(columns=PROD_COLUMNS)], ignore_index=True
    ).sort_values("created", ascending=False)
    records_table(with_names(records, ds), "production_defects.csv", "qq-prod", column_config={
        "created": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
        "resolved": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
    })
