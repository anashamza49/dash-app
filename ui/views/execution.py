from __future__ import annotations

import plotly.express as px
import streamlit as st

from qa_dashboard import kpi_settings as s
from qa_dashboard import kpis as k
from qa_dashboard.filters import scope_executions
from qa_dashboard.models import Dataset, Filters

from ..components import chart, empty_state, has_data, kpi_row, page_header, rag_styler, records_table, section, with_names
from ..theme import EXECUTION_COLORS, RAG_COLORS

EXECUTION_COLUMNS = ["execution_id", "cycle_id", "cycle_name", "cycle_type", "test_case_key", "test_case_name", "project_key",
                     "team_id", "status", "executed_on", "executed_by", "execution_mode", "failure_reason", "defect_keys"]
RATE_FORMATS = {"Execution rate": "{:.1%}", "Pass rate": "{:.1%}"}
RAG_COLUMNS = {"Execution rate": "TE-03", "Pass rate": "TE-04"}


def _results_by(ds: Dataset, f: Filters, by: str) -> None:
    table = k.te09_results_by(ds, f, by)
    if table.empty:
        empty_state()
        return
    if by == "team_id":
        table.insert(1, "Name", table["team_id"].map(ds.teams.set_index("team_id")["team_name"]))
    else:
        table.insert(1, "Name", table["project_key"].map(ds.projects.set_index("project_key")["project_name"]))
    table = table.rename(columns={"team_id": "Team", "project_key": "Project"})
    st.dataframe(rag_styler(table, RAG_COLUMNS, RATE_FORMATS), hide_index=True, width="stretch")


def render(ds: Dataset, f: Filters) -> None:
    page_header("Test Execution", "Zephyr test runs: execution progress, results and NRT campaigns.", ds, f)

    kpi_row([
        (k.te01_total_executions(ds, f), "Planned tests"),
        k.executed_count(ds, f),
        k.te03_execution_rate(ds, f),
        k.te04_pass_rate(ds, f),
        k.te05_fail_rate(ds, f),
        k.te06_blocked_tests(ds, f),
    ])
    st.caption(f"Executed = {', '.join(s.EXECUTED_STATUSES)} (setting EXECUTED_STATUSES). "
               "Date range applies to the execution date, or to the cycle planned end for runs not executed. "
               "Priority and status filters do not apply to tests.")

    c1, c2 = st.columns([2, 3], gap="medium")
    with c1:
        section("Results breakdown (TE-02)")
        breakdown = k.te02_results_breakdown(ds, f)
        status_sel = set()
        if has_data(breakdown, "count"):
            fig = px.bar(breakdown, x="status", y="count", color="status", color_discrete_map=EXECUTION_COLORS,
                         custom_data=["status"], text="count")
            fig.update_traces(textposition="outside", cliponaxis=False)
            status_sel = chart(fig, "te-breakdown", legend=False, selectable=True)
        else:
            empty_state()
    with c2:
        section("Execution trend by week (TE-08)")
        trend = k.te08_execution_trend(ds, f)
        if has_data(trend, "count"):
            fig = px.bar(trend, x="period", y="count", color="status", color_discrete_map=EXECUTION_COLORS)
            fig.update_layout(barmode="stack", hovermode="x unified")
            chart(fig, "te-trend")
        else:
            empty_state()

    section("NRT execution (TE-07)")
    nrt = k.te07_nrt_execution_rate(ds, f)
    c3, c4 = st.columns([1, 3], gap="medium")
    with c3:
        kpi_row([(nrt, "NRT execution rate")])
        st.caption(f"Placeholder for SLI-02 / SLI-04 (definitions not available). Target {s.NRT_EXECUTION_TARGET:.0%} (placeholder).")
    cycle_sel = set()
    with c4:
        cycles = k.te07_nrt_by_cycle(ds, f)
        if not cycles.empty:
            cycles["rag"] = cycles["rate"].map(lambda v: k.rag_status("TE-07", v) or "green")
            fig = px.bar(cycles, x="name", y="rate", color="rag", color_discrete_map=RAG_COLORS, custom_data=["cycle_id"],
                         hover_data={"planned": True, "executed": True, "planned_end": "|%Y-%m-%d", "rag": False})
            fig.add_hline(y=s.NRT_EXECUTION_TARGET, line_dash="dash", line_color="#0F172A",
                          annotation_text=f"Target {s.NRT_EXECUTION_TARGET:.0%}", annotation_position="top left")
            fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
            fig.update_xaxes(tickangle=-45)
            cycle_sel = chart(fig, "te-nrt", height=300, legend=False, selectable=True)
        else:
            empty_state("No NRT cycle in the current scope.")

    c5, c6 = st.columns(2, gap="medium")
    with c5:
        section("Results by team (TE-09)")
        _results_by(ds, f, "team_id")
    with c6:
        section("Results by project (TE-09)")
        _results_by(ds, f, "project_key")

    section("Execution records")
    ex = scope_executions(ds, f)
    cyc = ds.test_cycles.set_index("cycle_id")
    ex = ex.assign(cycle_name=ex["cycle_id"].map(cyc["name"]), cycle_type=ex["cycle_id"].map(cyc["cycle_type"]),
                   test_case_name=ex["test_case_key"].map(ds.test_cases.set_index("test_case_key")["name"]))
    notes = []
    if status_sel:
        ex = ex.loc[ex["status"].isin(status_sel)]
        notes.append("status = " + ", ".join(sorted(status_sel)))
    if cycle_sel:
        ex = ex.loc[ex["cycle_id"].isin(cycle_sel)]
        notes.append("cycle = " + ", ".join(sorted(cycle_sel)))
    if notes:
        st.caption("Drill-down: " + " · ".join(notes))
    table = with_names(ex[EXECUTION_COLUMNS].sort_values("execution_id", ascending=False), ds)
    table["defect_keys"] = table["defect_keys"].map(", ".join)
    records_table(table, "test_executions.csv", "te-ex", column_config={
        "executed_on": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm"),
    })
