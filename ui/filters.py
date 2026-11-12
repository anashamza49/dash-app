"""Global sidebar filters, shared by every page."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from qa_dashboard import kpi_settings as s
from qa_dashboard.config import HISTORY_START
from qa_dashboard.models import Dataset, Filters

PRESETS = {
    "Full history": None,
    "Last 30 days": 30,
    "Last 90 days": 90,
    "Last 6 months": 182,
    "Custom range": "custom",
}
FILTER_KEYS = ("f_preset", "f_range", "f_teams", "f_projects", "f_priorities", "f_statuses")


def _reset() -> None:
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)


def render_filters(ds: Dataset) -> Filters:
    ref = ds.reference_date
    st.sidebar.markdown("**Filters**")

    preset = st.sidebar.selectbox("Period", list(PRESETS), key="f_preset")
    days = PRESETS[preset]
    if days == "custom":
        picked = st.sidebar.date_input("Date range", value=(HISTORY_START, ref), min_value=date(2024, 1, 1),
                                       max_value=ref, key="f_range", format="DD/MM/YYYY")
        start, end = (picked[0], picked[-1]) if isinstance(picked, (list, tuple)) and picked else (HISTORY_START, ref)
    elif days is None:
        start, end = HISTORY_START, ref
    else:
        start, end = ref - timedelta(days=days - 1), ref

    team_names = dict(zip(ds.teams["team_id"], ds.teams["team_name"]))
    teams = st.sidebar.multiselect("QA team", list(team_names), format_func=team_names.get, key="f_teams",
                                   placeholder="All teams")

    projects = ds.projects if not teams else ds.projects.loc[ds.projects["team_id"].isin(teams)]
    project_names = dict(zip(projects["project_key"], projects["project_name"]))
    if "f_projects" in st.session_state:
        st.session_state["f_projects"] = [p for p in st.session_state["f_projects"] if p in project_names]
    selected_projects = st.sidebar.multiselect("Project", list(project_names), key="f_projects", placeholder="All projects",
                                               format_func=lambda k: f"{k} · {project_names[k]}")

    priorities = st.sidebar.multiselect("Priority", list(s.ISSUE_PRIORITIES), key="f_priorities", placeholder="All priorities")
    statuses = st.sidebar.multiselect("Bug status", list(s.BUG_STATUSES), key="f_statuses", placeholder="All statuses")
    st.sidebar.caption("Priority and status apply to bug-based KPIs only (test priorities and statuses use other scales).")
    st.sidebar.button("Reset filters", on_click=_reset, icon=":material/restart_alt:", width="stretch")

    return Filters(start=start, end=end, teams=tuple(teams), projects=tuple(selected_projects),
                   priorities=tuple(priorities), statuses=tuple(statuses))
