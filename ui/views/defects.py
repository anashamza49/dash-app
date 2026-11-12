from __future__ import annotations

import plotly.express as px
import streamlit as st

from qa_dashboard import kpis as k
from qa_dashboard.filters import scope_bugs
from qa_dashboard.models import Dataset, Filters

from ..components import chart, empty_state, has_data, kpi_row, page_header, records_table, section, with_names
from ..theme import ISSUE_STATUS_COLORS, PRIORITY_COLORS, TEAM_COLORS
from .overview import trend_figure

BUG_COLUMNS = ["issue_key", "project_key", "team_id", "summary", "status", "status_category", "priority", "environment",
               "created", "resolved", "due_date", "resolution", "assignee_id", "reporter_id", "fix_version"]


def _bar(df, x, y, color_col, colors, key, horizontal=False, custom=None):
    fig = px.bar(df, x=y if horizontal else x, y=x if horizontal else y, color=color_col,
                 color_discrete_map=colors, custom_data=[custom or x], text=y, orientation="h" if horizontal else "v")
    fig.update_traces(textposition="outside", cliponaxis=False)
    if horizontal:
        fig.update_yaxes(categoryorder="total ascending")
    return chart(fig, key, legend=False, selectable=True)


def render(ds: Dataset, f: Filters) -> None:
    page_header("Defect Management", "Jira bugs: volumes, distribution, trends and resolution performance.", ds, f)

    kpi_row([k.dm01_total_bugs(ds, f), k.dm02_open_bugs(ds, f), k.dm03_resolved_bugs(ds, f),
             k.dm09_avg_resolution_time(ds, f), k.dm10_overdue_bugs(ds, f)])
    st.caption("Click bars to drill down into the bug records below. Double-click a chart to clear its selection.")

    selections: dict[str, set] = {}
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        section("Bugs by status (DM-05)")
        df = k.dm05_bugs_by_status(ds, f)
        selections["status"] = _bar(df, "status", "count", "status", ISSUE_STATUS_COLORS, "dm-status") if has_data(df, "count") else empty_state()
    with c2:
        section("Bugs by priority (DM-04)")
        df = k.dm04_bugs_by_priority(ds, f)
        selections["priority"] = _bar(df, "priority", "count", "priority", PRIORITY_COLORS, "dm-priority") if has_data(df, "count") else empty_state()

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        section("Bugs by project (DM-06)")
        df = k.dm06_bugs_by_project(ds, f)
        selections["project_key"] = _bar(df, "project_key", "count", "team_id", TEAM_COLORS, "dm-project", horizontal=True) if has_data(df, "count") else empty_state()
    with c4:
        section("Bugs by team (DM-06)")
        df = k.dm06_bugs_by_team(ds, f)
        selections["team_id"] = _bar(df, "team_name", "count", "team_id", TEAM_COLORS, "dm-team", horizontal=True, custom="team_id") if has_data(df, "count") else empty_state()

    c5, c6 = st.columns([3, 2], gap="medium")
    with c5:
        section("Bug creation and resolution trend (DM-07, DM-08)")
        fig = trend_figure(ds, f)
        chart(fig, "dm-trend") if fig else empty_state()
    with c6:
        section("Average resolution time by priority (DM-09)")
        df = k.dm09_resolution_time_by_priority(ds, f)
        if has_data(df, "avg_days"):
            fig = px.bar(df, x="priority", y="avg_days", color="priority", color_discrete_map=PRIORITY_COLORS,
                         text=df["avg_days"].map("{:.1f} d".format), hover_data={"bugs": True})
            fig.update_traces(textposition="outside", cliponaxis=False)
            chart(fig, "dm-restime", legend=False)
        else:
            empty_state()
        st.caption(k.dm09_avg_resolution_time(ds, f).note)

    section("Bug records")
    bugs = scope_bugs(ds, f)
    active = {col: vals for col, vals in selections.items() if vals}
    for col, vals in active.items():
        bugs = bugs.loc[bugs[col].isin(vals)]
    if active:
        st.caption("Drill-down: " + " · ".join(f"{c} = {', '.join(sorted(map(str, v)))}" for c, v in active.items()))
    overdue_only = st.toggle("Overdue bugs only (DM-10)", key="dm-overdue")
    if overdue_only:
        bugs = bugs.loc[bugs.index.isin(k.overdue_bug_records(ds, f).index)]
    table = with_names(bugs[BUG_COLUMNS].sort_values("created", ascending=False), ds)
    records_table(table, "bugs.csv", "dm-bugs", column_config={
        "created": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
        "resolved": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
        "due_date": st.column_config.DateColumn(format="YYYY-MM-DD"),
    })
