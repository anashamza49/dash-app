"""QA KPI Dashboard POC. Run with: streamlit run app.py"""

from __future__ import annotations

import streamlit as st

from qa_dashboard.data.repository import build_database, get_dataset
from qa_dashboard.models import Dataset
from ui.filters import render_filters
from ui.theme import CSS
from ui.views import defects, execution, overview, quality, reference

st.set_page_config(page_title="QA KPI Dashboard", page_icon=":material/insights:", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Loading QA data…")
def load_data() -> Dataset:
    return get_dataset()


def regenerate() -> None:
    build_database()
    load_data.clear()


ds = load_data()

st.sidebar.markdown('<div class="brand">QA KPI Dashboard</div><div class="brand-sub">Streamlit POC · synthetic data</div>',
                    unsafe_allow_html=True)

PAGES = [
    (overview.render, "Overview", ":material/dashboard:", "overview"),
    (defects.render, "Defect Management", ":material/bug_report:", "defects"),
    (execution.render, "Test Execution", ":material/fact_check:", "execution"),
    (quality.render, "Quality & Coverage", ":material/verified:", "quality"),
    (reference.render, "KPI reference", ":material/menu_book:", "reference"),
]
holder: dict = {}
pages = [
    st.Page(lambda fn=fn: fn(ds, holder["filters"]), title=title, icon=icon, url_path=path, default=(i == 0))
    for i, (fn, title, icon, path) in enumerate(PAGES)
]
current = st.navigation(pages, position="sidebar")

st.sidebar.divider()
holder["filters"] = render_filters(ds)

with st.sidebar.expander("Data"):
    st.caption(f"Synthetic Jira/Zephyr-like dataset (seed 42), reference date {ds.reference_date:%d %b %Y}. "
               "Stored in data/qa_dashboard.sqlite.")
    st.button("Regenerate data", on_click=regenerate, icon=":material/refresh:", width="stretch")

current.run()
