"""Reusable Streamlit widgets: KPI cards, charts, drill-down tables."""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from qa_dashboard.kpis import KpiResult, rag_status
from qa_dashboard.models import Dataset, Filters

from .theme import RAG_BACKGROUNDS, style_figure


def format_value(value, unit: str) -> str:
    if value is None or pd.isna(value):
        return "—"
    if unit == "ratio":
        return f"{value:.1%}"
    if unit == "days":
        return f"{value:.1f} d"
    return f"{int(value):,}"


def page_header(title: str, subtitle: str, ds: Dataset, f: Filters) -> None:
    st.markdown(f'<div class="page-title">{html.escape(title)}</div><div class="page-sub">{html.escape(subtitle)}</div>',
                unsafe_allow_html=True)
    team_names = ds.teams.set_index("team_id")["team_name"]
    chips = [f"{f.start:%d %b %Y} → {f.end:%d %b %Y}",
             "Teams: " + (", ".join(team_names.get(t, t) for t in f.teams) if f.teams else "All"),
             "Projects: " + (", ".join(f.projects) if f.projects else "All")]
    if f.priorities:
        chips.append("Priority: " + ", ".join(f.priorities))
    if f.statuses:
        chips.append("Status: " + ", ".join(f.statuses))
    chips.append(f"Data as of {ds.reference_date:%d %b %Y}")
    st.markdown('<div class="chips">' + "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips) + "</div>",
                unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def kpi_card(result: KpiResult, label: str | None = None, sub: str | None = None) -> None:
    label = label or result.name
    status = result.status.lower()
    tooltip = f"{result.kpi_id} · {result.name} ({result.status}). {result.note}".strip()
    if result.status == "Unresolved":
        value_html = '<div class="kpi-value muted">Not defined</div>'
        sub = sub or "Business definition required"
        rag = None
    else:
        value_html = f'<div class="kpi-value">{format_value(result.value, result.unit)}</div>'
        if sub is None:
            sub = result.kpi_id
            if result.unit == "ratio" and result.denominator is not None:
                sub = f"{result.numerator:,} / {result.denominator:,} · {result.kpi_id}"
        rag = rag_status(result.kpi_id, result.value)
    classes = "kpi-card" + (f" rag-{rag}" if rag else "") + (" unresolved" if status == "unresolved" else "")
    st.markdown(
        f'<div class="{classes}" title="{html.escape(tooltip)}">'
        f'<div class="kpi-label">{html.escape(label)}</div>{value_html}'
        f'<div class="kpi-foot"><span class="kpi-sub">{html.escape(sub)}</span>'
        f'<span class="badge badge-{status}">{html.escape(result.status)}</span></div></div>',
        unsafe_allow_html=True,
    )


def kpi_row(results: list[KpiResult | tuple]) -> None:
    """Each item is a KpiResult or (KpiResult, label) or (KpiResult, label, sub)."""
    cols = st.columns(len(results))
    for col, item in zip(cols, results):
        with col:
            if isinstance(item, tuple):
                kpi_card(*item)
            else:
                kpi_card(item)


def has_data(df: pd.DataFrame, value_col: str | None = None) -> bool:
    if df is None or df.empty:
        return False
    if value_col is not None:
        return bool(pd.to_numeric(df[value_col], errors="coerce").fillna(0).abs().sum() > 0)
    return True


def empty_state(message: str = "No data for the current filters.") -> None:
    st.info(message, icon=":material/filter_alt_off:")


def chart(fig: go.Figure, key: str, height: int = 320, legend: bool | str = True, selectable: bool = False):
    """Render a Plotly chart. When selectable, return the selected customdata values."""
    style_figure(fig, height=height, legend=legend)
    config = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}
    if not selectable:
        st.plotly_chart(fig, width="stretch", config=config, key=key)
        return set()
    event = st.plotly_chart(fig, width="stretch", config=config, key=key, on_select="rerun", selection_mode="points")
    values = set()
    try:
        for point in event.selection.points:
            data = point.get("customdata")
            if data is not None:
                values.add(data[0] if isinstance(data, (list, tuple)) else data)
    except AttributeError:
        pass
    return values


def records_table(df: pd.DataFrame, file_name: str, key: str, column_config: dict | None = None, height: int = 360) -> None:
    left, right = st.columns([4, 1])
    left.caption(f"{len(df):,} record(s)")
    right.download_button(
        "Export CSV", df.to_csv(index=False).encode("utf-8"), file_name=file_name, mime="text/csv",
        key=f"dl-{key}", icon=":material/download:", width="stretch", disabled=df.empty,
    )
    st.dataframe(df, hide_index=True, width="stretch", height=height, column_config=column_config, key=f"tbl-{key}")


def rag_styler(df: pd.DataFrame, rag_columns: dict[str, str], formats: dict[str, str]):
    """Colour cells by RAG threshold. rag_columns maps column name to KPI ID."""
    styler = df.style.format(formats, na_rep="—")
    for col, kpi_id in rag_columns.items():
        if col in df.columns:
            styler = styler.map(
                lambda v, k=kpi_id: f"background-color: {RAG_BACKGROUNDS[r]}" if (r := rag_status(k, v)) else "",
                subset=[col],
            )
    return styler


def with_names(df: pd.DataFrame, ds: Dataset) -> pd.DataFrame:
    """Add readable user, team and project names for drill-down tables."""
    out = df.copy()
    names = ds.users.set_index("user_id")["display_name"]
    for col, label in (("assignee_id", "assignee"), ("reporter_id", "reporter"), ("owner_id", "owner")):
        if col in out.columns:
            out.insert(out.columns.get_loc(col), label, out[col].map(names))
            out = out.drop(columns=col)
    if "executed_by" in out.columns:
        out["executed_by"] = out["executed_by"].map(names)
    if "team_id" in out.columns:
        out.insert(out.columns.get_loc("team_id") + 1, "team", out["team_id"].map(ds.teams.set_index("team_id")["team_name"]))
    return out
