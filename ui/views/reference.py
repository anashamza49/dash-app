from __future__ import annotations

import pandas as pd
import streamlit as st

from qa_dashboard import kpi_settings as s
from qa_dashboard.kpis import KPI_CATALOG
from qa_dashboard.models import Dataset, Filters

from ..components import page_header, section

OPEN_QUESTIONS = [
    "Which date did the Power BI model use for issue KPIs: created, resolved or both?",
    "What are the exact definitions and targets of SLI-02 and SLI-04?",
    "Does the test execution rate count Blocked as executed?",
    "How was bug reporting quality measured: a checklist, a score or rejected bugs?",
    "Is defect escape rate based on environment, on found-after-release or on a dedicated Jira field?",
    "Which source held weekly report submissions and coordinator assignments?",
    "Were overdue bugs based on a Jira due date or on SLA targets by priority?",
]
POC_GAPS = [
    ("Critical / Blocker bugs", "Requested in the brief, but the Jira priority scale (Highest to Lowest) has no "
     "Critical/Blocker value and no mapping is documented. Displayed as 'Not defined' (setting CRITICAL_PRIORITIES)."),
    ("Date rule for not-executed tests", "The KPI document says 'cycle planned dates'. The POC uses planned_end "
     "(setting NOT_EXECUTED_DATE_FIELD)."),
    ("QQ-01 / QQ-04 date range", "No date rule documented: shown as current snapshots."),
    ("Automation coverage trend", "Test case status has no history, so Deprecated is applied as of today."),
    ("Due dates after the reference date", "Data model rule 12 forbids future dates, but due = created + target days "
     "can exceed it. Treated as a documented exception."),
]


def render(ds: Dataset, f: Filters) -> None:
    page_header("KPI reference", "Definitions, status, active settings and open business questions.", ds, f)

    section("KPI catalogue (docs/kpi-definitions.md)")
    catalog = pd.DataFrame([(kid, name, status) for kid, (name, status) in KPI_CATALOG.items()],
                           columns=["ID", "KPI", "Status"])
    st.dataframe(catalog, hide_index=True, width="stretch", height=420)
    st.caption("Standard: plain Jira/Zephyr count or ratio. Provisional: placeholder formula to confirm. "
               "Proxy: computed from an assumed supporting dataset. Unresolved: no definition, no value displayed.")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        section("Unresolved items and POC decisions")
        for title, text in POC_GAPS:
            st.markdown(f"**{title}** — {text}")
    with c2:
        section("Open questions for the business")
        for i, q in enumerate(OPEN_QUESTIONS, 1):
            st.markdown(f"{i}. {q}")

    section("Active KPI settings (qa_dashboard/kpi_settings.py)")
    settings = {name: getattr(s, name) for name in dir(s) if name.isupper()}
    st.json(settings, expanded=False)
