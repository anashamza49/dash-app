"""Scoping rules from docs/kpi-definitions.md, section "Filter behaviour".

Every KPI goes through these functions so that filters change the actual
calculations, not just the charts.
"""

from __future__ import annotations

import pandas as pd

from . import kpi_settings as s
from .models import Dataset, Filters


def in_date_range(values: pd.Series, f: Filters) -> pd.Series:
    """Inclusive [start, end] on calendar days. Missing dates are out of range."""
    start = pd.Timestamp(f.start)
    end_exclusive = pd.Timestamp(f.end) + pd.Timedelta(days=1)
    return values.notna() & (values >= start) & (values < end_exclusive)


def projects_in_scope(ds: Dataset, f: Filters) -> set[str]:
    projects = ds.projects
    mask = pd.Series(True, index=projects.index)
    if f.teams:
        mask &= projects["team_id"].isin(f.teams)
    if f.projects:
        mask &= projects["project_key"].isin(f.projects)
    return set(projects.loc[mask, "project_key"])


def teams_in_scope(ds: Dataset, f: Filters) -> set[str]:
    """Teams owning at least one project in scope (for team-level datasets)."""
    keys = projects_in_scope(ds, f)
    return set(ds.projects.loc[ds.projects["project_key"].isin(keys), "team_id"])


def scope_issues(
    ds: Dataset,
    f: Filters,
    issue_type: str,
    date_field: str | None = "created",
    bug_filters: bool = True,
) -> pd.DataFrame:
    """Issues of one type in the project/team scope.

    date_field: issue date the range applies to (None = no date restriction).
    bug_filters: apply the priority and status filters (bug-based KPIs only).
    """
    issues = ds.issues
    mask = (issues["issue_type"] == issue_type) & issues["project_key"].isin(projects_in_scope(ds, f))
    if date_field is not None:
        mask &= in_date_range(issues[date_field], f)
    if bug_filters:
        if f.priorities:
            mask &= issues["priority"].isin(f.priorities)
        if f.statuses:
            mask &= issues["status"].isin(f.statuses)
    return issues.loc[mask]


def scope_bugs(ds: Dataset, f: Filters, date_field: str | None = "created") -> pd.DataFrame:
    return scope_issues(ds, f, s.BUG_TYPE, date_field=date_field, bug_filters=True)


def execution_filter_date(ds: Dataset) -> pd.Series:
    """executed_on, or the cycle planned date for rows that were not executed."""
    executions = ds.test_executions
    planned = executions["cycle_id"].map(ds.test_cycles.set_index("cycle_id")[s.NOT_EXECUTED_DATE_FIELD])
    return executions["executed_on"].fillna(planned)


def scope_executions(ds: Dataset, f: Filters, nrt_only: bool = False) -> pd.DataFrame:
    """Executions in scope. Priority and status filters do not apply (see document)."""
    executions = ds.test_executions
    mask = executions["project_key"].isin(projects_in_scope(ds, f))
    mask &= in_date_range(execution_filter_date(ds), f)
    if nrt_only:
        nrt_cycles = ds.test_cycles.loc[ds.test_cycles["cycle_type"] == s.NRT_CYCLE_TYPE, "cycle_id"]
        mask &= executions["cycle_id"].isin(nrt_cycles)
    return executions.loc[mask]


def scope_test_cases(ds: Dataset, f: Filters) -> pd.DataFrame:
    """Test cases in the project/team scope. They have no date filter."""
    return ds.test_cases.loc[ds.test_cases["project_key"].isin(projects_in_scope(ds, f))]
