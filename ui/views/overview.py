from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from qa_dashboard import kpi_settings as s
from qa_dashboard import kpis as k
from qa_dashboard.models import Dataset, Filters

from ..components import chart, empty_state, has_data, kpi_row, page_header, rag_styler, section
from ..theme import EXECUTION_COLORS, TREND_COLORS

COMPOSITE_LABELS = {
    "DM-01": "Bugs", "DM-02": "Open", "DM-09": "Avg resolution (d)", "DM-10": "Overdue",
    "TE-03": "Execution rate", "TE-04": "Pass rate", "QQ-03": "Escape rate",
}
FORMATS = {"Avg resolution (d)": "{:.1f}", "Execution rate": "{:.1%}", "Pass rate": "{:.1%}", "Escape rate": "{:.1%}"}
RAG_COLUMNS = {"Execution rate": "TE-03", "Pass rate": "TE-04", "Escape rate": "QQ-03"}


def trend_figure(ds: Dataset, f: Filters) -> go.Figure | None:
    created, resolved = k.dm07_creation_trend(ds, f), k.dm08_resolution_trend(ds, f)
    if not (has_data(created, "created") or has_data(resolved, "resolved")):
        return None
    fig = go.Figure()
    fig.add_bar(x=created["period"], y=created["created"], name="Created (DM-07)", marker_color=TREND_COLORS["created"])
    fig.add_scatter(x=resolved["period"], y=resolved["resolved"], name="Resolved (DM-08)", mode="lines+markers",
                    line=dict(color=TREND_COLORS["resolved"], width=2.5), marker=dict(size=5))
    fig.update_layout(hovermode="x unified")
    return fig


def performance(ds: Dataset, f: Filters, by: str) -> None:
    table = k.performance_table(ds, f, by).rename(columns=COMPOSITE_LABELS)
    if table.empty:
        empty_state()
        return
    table = table.rename(columns={"key": "Team" if by == "team" else "Project", "name": "Name"})
    st.dataframe(rag_styler(table, RAG_COLUMNS, FORMATS), hide_index=True, width="stretch")


def render(ds: Dataset, f: Filters) -> None:
    page_header("QA KPI Overview", "Defect, test execution and NRT health across teams and projects.", ds, f)

    section("Defects")
    kpi_row([k.dm01_total_bugs(ds, f), k.dm02_open_bugs(ds, f), k.dm03_resolved_bugs(ds, f), k.critical_bugs(ds, f)])
    section("Test execution")
    nrt = k.te07_nrt_execution_rate(ds, f)
    kpi_row([
        k.te03_execution_rate(ds, f),
        k.te04_pass_rate(ds, f),
        k.failed_tests(ds, f),
        (nrt, "NRT execution rate", f"{nrt.numerator or 0:,} / {nrt.denominator or 0:,} · target {s.NRT_EXECUTION_TARGET:.0%}"),
    ])

    left, right = st.columns([3, 2], gap="medium")
    with left:
        section("Bug creation vs resolution (weekly)")
        fig = trend_figure(ds, f)
        chart(fig, "ov-trend") if fig else empty_state()
    with right:
        section("Test results (TE-02)")
        breakdown = k.te02_results_breakdown(ds, f)
        if has_data(breakdown, "count"):
            fig = px.pie(breakdown, names="status", values="count", hole=0.62, color="status",
                         color_discrete_map=EXECUTION_COLORS)
            fig.update_traces(textinfo="percent", sort=False)
            total = int(breakdown["count"].sum())
            fig.add_annotation(text=f"<b>{total:,}</b><br>runs", showarrow=False, font=dict(size=15))
            chart(fig, "ov-results", legend="bottom")
        else:
            empty_state()

    section("QA performance by team")
    performance(ds, f, "team")
    section("Project performance comparison")
    performance(ds, f, "project")
    st.caption("Tables show DM-01, DM-02, DM-09, DM-10, TE-03, TE-04 and QQ-03 per row. "
               "Cell colours use the placeholder thresholds of the KPI document.")
