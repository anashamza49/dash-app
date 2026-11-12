"""KPI formulas of docs/kpi-definitions.md. One function per KPI ID.

Pure pandas: no Streamlit import. Every function takes the full Dataset and
the global Filters, and applies the scoping rules itself.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import kpi_settings as s
from .filters import (
    in_date_range,
    projects_in_scope,
    scope_bugs,
    scope_executions,
    scope_issues,
    scope_test_cases,
    teams_in_scope,
)
from .models import Dataset, Filters

STANDARD, PROVISIONAL, PROXY, UNRESOLVED = "Standard", "Provisional", "Proxy", "Unresolved"

KPI_CATALOG: dict[str, tuple[str, str]] = {
    "DM-01": ("Total bugs", STANDARD),
    "DM-02": ("Open bugs", STANDARD),
    "DM-03": ("Resolved bugs", STANDARD),
    "DM-04": ("Bugs by priority", STANDARD),
    "DM-05": ("Bugs by status", STANDARD),
    "DM-06": ("Bugs by project and team", STANDARD),
    "DM-07": ("Bug creation trend", STANDARD),
    "DM-08": ("Bug resolution trend", STANDARD),
    "DM-09": ("Average resolution time", PROVISIONAL),
    "DM-10": ("Overdue bugs", PROVISIONAL),
    "TE-01": ("Total test executions", STANDARD),
    "TE-02": ("Results breakdown", STANDARD),
    "TE-03": ("Test execution rate", PROVISIONAL),
    "TE-04": ("Pass rate", STANDARD),
    "TE-05": ("Fail rate", STANDARD),
    "TE-06": ("Blocked tests", STANDARD),
    "TE-07": ("NRT execution rate", PROVISIONAL),
    "TE-08": ("Execution trend", STANDARD),
    "TE-09": ("Results by project and team", STANDARD),
    "QQ-01": ("Test coverage", PROVISIONAL),
    "QQ-02": ("Bug reporting quality", PROVISIONAL),
    "QQ-03": ("Defect escape rate", PROVISIONAL),
    "QQ-04": ("Automation coverage", PROVISIONAL),
    "QQ-05": ("Automation stability", PROVISIONAL),
    "QQ-06": ("Production incidents", STANDARD),
    "QQ-07": ("Reporting timeliness", PROXY),
    "QQ-08": ("QA coordinator retention", PROXY),
}


@dataclass(frozen=True)
class KpiResult:
    kpi_id: str
    name: str
    status: str
    value: float | None
    unit: str = "count"  # count | ratio | days
    numerator: int | None = None
    denominator: int | None = None
    note: str = ""


def _result(kpi_id: str, value, unit: str = "count", numerator=None, denominator=None, note: str = "") -> KpiResult:
    name, status = KPI_CATALOG[kpi_id]
    return KpiResult(kpi_id, name, status, value, unit, numerator, denominator, note)


def _ratio_result(kpi_id: str, numerator: int, denominator: int, note: str = "") -> KpiResult:
    value = numerator / denominator if denominator else None
    return _result(kpi_id, value, "ratio", int(numerator), int(denominator), note)


def _period_start(values: pd.Series, freq: str) -> pd.Series:
    """Week (Monday) or month start of each timestamp."""
    period = "W-SUN" if freq == "W" else "M"
    return values.dt.to_period(period).dt.start_time


def _all_periods(f: Filters, freq: str) -> pd.DatetimeIndex:
    bounds = _period_start(pd.Series([pd.Timestamp(f.start), pd.Timestamp(f.end)]), freq)
    return pd.date_range(bounds.iloc[0], bounds.iloc[1], freq="W-MON" if freq == "W" else "MS")


def _count_by_period(values: pd.Series, f: Filters, freq: str = "W", name: str = "count") -> pd.DataFrame:
    counts = _period_start(values, freq).value_counts()
    counts = counts.reindex(_all_periods(f, freq), fill_value=0)
    return counts.rename_axis("period").rename(name).reset_index()


def _ordered_counts(values: pd.Series, order, label: str) -> pd.DataFrame:
    counts = values.value_counts()
    order = list(order) + sorted(set(counts.index) - set(order))
    return counts.reindex(order, fill_value=0).rename_axis(label).rename("count").reset_index()


def _is_done(issues: pd.DataFrame) -> pd.Series:
    return issues["status_category"] == s.DONE_CATEGORY


# ---------------------------------------------------------------------------
# A. Defect management
# ---------------------------------------------------------------------------

def dm01_total_bugs(ds: Dataset, f: Filters) -> KpiResult:
    return _result("DM-01", len(scope_bugs(ds, f)))


def dm02_open_bugs(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f)
    return _result("DM-02", int((~_is_done(bugs)).sum()), note="Current status, not status at end of range.")


def dm03_resolved_bugs(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f)
    return _result("DM-03", int(_is_done(bugs).sum()), note="Current status, not status at end of range.")


def critical_bugs(ds: Dataset, f: Filters) -> KpiResult:
    """'Critical / Blocker bugs' from the brief: no documented definition yet."""
    if s.CRITICAL_PRIORITIES is None:
        return KpiResult(
            "Not in KPI doc", "Critical / Blocker bugs", UNRESOLVED, None,
            note="Not defined: the Jira priority scale has no Critical/Blocker value. "
                 "Set CRITICAL_PRIORITIES once the business confirms the mapping.",
        )
    bugs = scope_bugs(ds, f)
    return KpiResult(
        "Not in KPI doc", "Critical / Blocker bugs", PROVISIONAL, int(bugs["priority"].isin(s.CRITICAL_PRIORITIES).sum()),
        note=f"Priorities counted: {', '.join(s.CRITICAL_PRIORITIES)}.",
    )


def dm04_bugs_by_priority(ds: Dataset, f: Filters) -> pd.DataFrame:
    return _ordered_counts(scope_bugs(ds, f)["priority"], s.ISSUE_PRIORITIES, "priority")


def dm05_bugs_by_status(ds: Dataset, f: Filters) -> pd.DataFrame:
    return _ordered_counts(scope_bugs(ds, f)["status"], s.BUG_STATUSES, "status")


def dm06_bugs_by_project(ds: Dataset, f: Filters) -> pd.DataFrame:
    bugs = scope_bugs(ds, f)
    keys = sorted(projects_in_scope(ds, f))
    counts = bugs.groupby("project_key").size().reindex(keys, fill_value=0)
    out = counts.rename("count").rename_axis("project_key").reset_index()
    out = out.merge(ds.projects[["project_key", "project_name", "team_id"]], on="project_key", how="left")
    return out.sort_values("count", ascending=False, ignore_index=True)


def dm06_bugs_by_team(ds: Dataset, f: Filters) -> pd.DataFrame:
    bugs = scope_bugs(ds, f)
    teams = sorted(teams_in_scope(ds, f))
    counts = bugs.groupby("team_id").size().reindex(teams, fill_value=0)
    out = counts.rename("count").rename_axis("team_id").reset_index()
    out = out.merge(ds.teams[["team_id", "team_name"]], on="team_id", how="left")
    return out.sort_values("count", ascending=False, ignore_index=True)


def dm07_creation_trend(ds: Dataset, f: Filters) -> pd.DataFrame:
    return _count_by_period(scope_bugs(ds, f)["created"], f, "W", "created")


def dm08_resolution_trend(ds: Dataset, f: Filters) -> pd.DataFrame:
    """Bugs resolved in range, by week of `resolved` (inactive-relationship exception)."""
    return _count_by_period(scope_bugs(ds, f, date_field="resolved")["resolved"], f, "W", "resolved")


def _resolution_days(bugs: pd.DataFrame) -> pd.Series:
    if s.RESOLUTION_TIME_BUSINESS_DAYS:
        start = bugs["created"].dt.date.to_numpy(dtype="datetime64[D]")
        end = bugs["resolved"].dt.date.to_numpy(dtype="datetime64[D]")
        return pd.Series(np.busday_count(start, end), index=bugs.index, dtype=float)
    return (bugs["resolved"] - bugs["created"]).dt.total_seconds() / 86400


def dm09_avg_resolution_time(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f, date_field="resolved")
    bugs = bugs.loc[~bugs["resolution"].isin(s.RESOLUTION_TIME_EXCLUDED_RESOLUTIONS)]
    unit_note = "business days" if s.RESOLUTION_TIME_BUSINESS_DAYS else "calendar days"
    value = float(_resolution_days(bugs).mean()) if len(bugs) else None
    return _result("DM-09", value, "days", denominator=len(bugs), note=f"Bugs resolved in range, {unit_note}.")


def dm09_resolution_time_by_priority(ds: Dataset, f: Filters) -> pd.DataFrame:
    bugs = scope_bugs(ds, f, date_field="resolved")
    bugs = bugs.loc[~bugs["resolution"].isin(s.RESOLUTION_TIME_EXCLUDED_RESOLUTIONS)]
    days = _resolution_days(bugs).rename("days")
    out = days.groupby(bugs["priority"]).agg(["mean", "count"]).reindex(list(s.ISSUE_PRIORITIES))
    return out.rename(columns={"mean": "avg_days", "count": "bugs"}).rename_axis("priority").reset_index().dropna(subset=["avg_days"])


def dm10_overdue_bugs(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f)
    overdue = (~_is_done(bugs)) & bugs["due_date"].notna() & (bugs["due_date"] < pd.Timestamp(ds.reference_date))
    return _result("DM-10", int(overdue.sum()), note=f"Not Done and due before {ds.reference_date:%Y-%m-%d}.")


def overdue_bug_records(ds: Dataset, f: Filters) -> pd.DataFrame:
    bugs = scope_bugs(ds, f)
    overdue = (~_is_done(bugs)) & bugs["due_date"].notna() & (bugs["due_date"] < pd.Timestamp(ds.reference_date))
    return bugs.loc[overdue]


# ---------------------------------------------------------------------------
# B. Test execution and NRT
# ---------------------------------------------------------------------------

def _executed_mask(executions: pd.DataFrame) -> pd.Series:
    return executions["status"].isin(s.EXECUTED_STATUSES)


def te01_total_executions(ds: Dataset, f: Filters) -> KpiResult:
    return _result("TE-01", len(scope_executions(ds, f)))


def te02_results_breakdown(ds: Dataset, f: Filters) -> pd.DataFrame:
    return _ordered_counts(scope_executions(ds, f)["status"], s.EXECUTION_STATUSES, "status")


def executed_count(ds: Dataset, f: Filters) -> KpiResult:
    """Numerator of TE-03, displayed as 'Executed tests'."""
    ex = scope_executions(ds, f)
    return KpiResult("TE-03 numerator", "Executed tests", STANDARD, int(_executed_mask(ex).sum()),
                     note=f"Statuses counted as executed: {', '.join(s.EXECUTED_STATUSES)}.")


def te03_execution_rate(ds: Dataset, f: Filters) -> KpiResult:
    ex = scope_executions(ds, f)
    return _ratio_result("TE-03", int(_executed_mask(ex).sum()), len(ex),
                         note=f"Executed = {', '.join(s.EXECUTED_STATUSES)}.")


def te04_pass_rate(ds: Dataset, f: Filters) -> KpiResult:
    ex = scope_executions(ds, f)
    return _ratio_result("TE-04", int((ex["status"] == "Pass").sum()), int(_executed_mask(ex).sum()))


def te05_fail_rate(ds: Dataset, f: Filters) -> KpiResult:
    ex = scope_executions(ds, f)
    return _ratio_result("TE-05", int((ex["status"] == "Fail").sum()), int(_executed_mask(ex).sum()))


def failed_tests(ds: Dataset, f: Filters) -> KpiResult:
    ex = scope_executions(ds, f)
    return KpiResult("TE-02 Fail", "Failed tests", STANDARD, int((ex["status"] == "Fail").sum()), note="TE-02, status Fail.")


def te06_blocked_tests(ds: Dataset, f: Filters) -> KpiResult:
    return _result("TE-06", int((scope_executions(ds, f)["status"] == "Blocked").sum()))


def te07_nrt_execution_rate(ds: Dataset, f: Filters) -> KpiResult:
    ex = scope_executions(ds, f, nrt_only=True)
    return _ratio_result("TE-07", int(_executed_mask(ex).sum()), len(ex),
                         note=f"Placeholder for SLI-02/SLI-04. Target {s.NRT_EXECUTION_TARGET:.0%}.")


def te07_nrt_by_cycle(ds: Dataset, f: Filters) -> pd.DataFrame:
    """TE-07 per NRT cycle, to compare each release against the target."""
    ex = scope_executions(ds, f, nrt_only=True)
    if ex.empty:
        return pd.DataFrame(columns=["cycle_id", "name", "project_key", "planned_end", "planned", "executed", "rate"])
    grouped = ex.assign(executed=_executed_mask(ex)).groupby("cycle_id").agg(planned=("status", "size"), executed=("executed", "sum"))
    grouped["rate"] = grouped["executed"] / grouped["planned"]
    cycles = ds.test_cycles.set_index("cycle_id")[["name", "project_key", "planned_end"]]
    return grouped.join(cycles).reset_index().sort_values("planned_end", ignore_index=True)


def te08_execution_trend(ds: Dataset, f: Filters) -> pd.DataFrame:
    """TE-02 by week of executed_on. Not Executed rows have no execution date."""
    ex = scope_executions(ds, f)
    ex = ex.loc[ex["executed_on"].notna()]
    periods = _all_periods(f, "W")
    if ex.empty:
        return pd.DataFrame(columns=["period", "status", "count"])
    table = pd.crosstab(_period_start(ex["executed_on"], "W"), ex["status"])
    table = table.reindex(index=periods, fill_value=0)
    table = table.reindex(columns=[c for c in s.EXECUTION_STATUSES if c in table.columns])
    return table.rename_axis(index="period", columns=None).reset_index().melt(id_vars="period", var_name="status", value_name="count")


def te09_results_by(ds: Dataset, f: Filters, by: str) -> pd.DataFrame:
    """TE-02, TE-03 and TE-04 grouped by 'project_key' or 'team_id'."""
    ex = scope_executions(ds, f)
    keys = sorted(projects_in_scope(ds, f)) if by == "project_key" else sorted(teams_in_scope(ds, f))
    table = pd.crosstab(ex[by], ex["status"]).reindex(index=keys, columns=list(s.EXECUTION_STATUSES), fill_value=0)
    planned = table.sum(axis=1)
    executed = table[list(s.EXECUTED_STATUSES)].sum(axis=1)
    table.insert(0, "Planned", planned)
    table["Executed"] = executed
    table["Execution rate"] = (executed / planned.replace(0, np.nan))
    table["Pass rate"] = (table["Pass"] / executed.replace(0, np.nan))
    return table.rename_axis(index=by, columns=None).reset_index()


def execution_mode_split(ds: Dataset, f: Filters) -> pd.DataFrame:
    """TE-01 grouped by execution_mode (automated versus manual runs)."""
    return _ordered_counts(scope_executions(ds, f)["execution_mode"], ("Automated", "Manual"), "execution_mode")


# ---------------------------------------------------------------------------
# C. QA quality and coverage
# ---------------------------------------------------------------------------

def qq01_test_coverage(ds: Dataset, f: Filters) -> KpiResult:
    stories = scope_issues(ds, f, s.STORY_TYPE, date_field=None, bug_filters=False)
    tc = ds.test_cases
    covering = tc.loc[tc["status"] == s.COVERAGE_TEST_CASE_STATUS, "covered_story_key"].dropna()
    covered = int(stories["issue_key"].isin(covering).sum())
    return _ratio_result("QQ-01", covered, len(stories),
                         note="Current snapshot: the date range is not applied (not specified for stories).")


def _bug_validity(bugs: pd.DataFrame) -> pd.Series:
    valid = ~bugs["resolution"].isin(s.INVALID_RESOLUTIONS)
    complete = bugs[list(s.COMPLETENESS_FIELDS)].astype(bool).all(axis=1)
    return valid & complete


def qq02_bug_reporting_quality(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f)
    return _ratio_result("QQ-02", int(_bug_validity(bugs).sum()), len(bugs),
                         note="Valid (resolution not invalid) and complete (repro steps and attachment).")


def _escaped(bugs: pd.DataFrame) -> pd.Series:
    return bugs["environment"].isin(s.ESCAPED_ENVIRONMENTS)


def qq03_defect_escape_rate(ds: Dataset, f: Filters) -> KpiResult:
    bugs = scope_bugs(ds, f)
    return _ratio_result("QQ-03", int(_escaped(bugs).sum()), len(bugs), note="Every PROD bug counts as escaped.")


def production_bugs(ds: Dataset, f: Filters) -> pd.DataFrame:
    """Records behind the QQ-03 numerator, for distribution charts and drill-down."""
    bugs = scope_bugs(ds, f)
    return bugs.loc[_escaped(bugs)]


def bugs_by_environment(ds: Dataset, f: Filters) -> pd.DataFrame:
    return _ordered_counts(scope_bugs(ds, f)["environment"], ("DEV", "SIT", "UAT", "PREPROD", "PROD"), "environment")


def _automation_population(tc: pd.DataFrame) -> pd.DataFrame:
    active = tc.loc[tc["status"] != s.DEPRECATED_TEST_STATUS]
    if s.AUTOMATION_EXCLUDE_NOT_AUTOMATABLE:
        active = active.loc[active["automation_status"] != "Not Automatable"]
    return active


def qq04_automation_coverage(ds: Dataset, f: Filters) -> KpiResult:
    active = _automation_population(scope_test_cases(ds, f))
    return _ratio_result("QQ-04", int((active["automation_status"] == "Automated").sum()), len(active),
                         note="Current snapshot of active test cases: the date range is not applied.")


def automation_status_split(ds: Dataset, f: Filters) -> pd.DataFrame:
    active = _automation_population(scope_test_cases(ds, f))
    return _ordered_counts(active["automation_status"], ("Automated", "To Automate", "Not Automatable"), "automation_status")


def qq04_automation_trend(ds: Dataset, f: Filters) -> pd.DataFrame:
    """QQ-04 at each month end of the range.

    Approximation: test case status has no history, so Deprecated is taken as of today.
    """
    active = _automation_population(scope_test_cases(ds, f))
    rows = []
    for month in _all_periods(f, "M"):
        month_end = month + pd.offsets.MonthEnd(0) + pd.Timedelta(days=1)
        existing = active.loc[active["created"] < month_end]
        automated = existing["automated_since"].notna() & (existing["automated_since"] < month_end)
        rows.append({"period": month, "automated": int(automated.sum()), "active": len(existing),
                     "rate": automated.sum() / len(existing) if len(existing) else np.nan})
    return pd.DataFrame(rows, columns=["period", "automated", "active", "rate"])


def _automated_runs(ds: Dataset, f: Filters) -> pd.DataFrame:
    ex = scope_executions(ds, f)
    return ex.loc[(ex["execution_mode"] == "Automated") & _executed_mask(ex)]


def _unstable(runs: pd.DataFrame) -> pd.Series:
    return (runs["status"] == "Fail") & runs["failure_reason"].isin(s.STABILITY_FAILURE_REASONS)


def qq05_automation_stability(ds: Dataset, f: Filters) -> KpiResult:
    runs = _automated_runs(ds, f)
    unstable = int(_unstable(runs).sum())
    value = 1 - unstable / len(runs) if len(runs) else None
    return _result("QQ-05", value, "ratio", len(runs) - unstable, len(runs),
                   note="Failures from test scripts or environment count against stability.")


def qq06_production_incidents(ds: Dataset, f: Filters) -> KpiResult:
    return _result("QQ-06", len(scope_issues(ds, f, s.INCIDENT_TYPE, bug_filters=False)))


def incidents(ds: Dataset, f: Filters) -> pd.DataFrame:
    return scope_issues(ds, f, s.INCIDENT_TYPE, bug_filters=False)


def _reports_in_scope(ds: Dataset, f: Filters) -> pd.DataFrame:
    reports = ds.qa_reports
    mask = reports["team_id"].isin(teams_in_scope(ds, f)) & in_date_range(reports["due_date"], f)
    return reports.loc[mask]


def _on_time(reports: pd.DataFrame) -> pd.Series:
    return reports["submitted_at"].notna() & (reports["submitted_at"] <= reports["due_date"])


def qq07_reporting_timeliness(ds: Dataset, f: Filters) -> KpiResult:
    reports = _reports_in_scope(ds, f)
    return _ratio_result("QQ-07", int(_on_time(reports).sum()), len(reports),
                         note="Reports are per team: the project filter selects the owning teams.")


def qq08_coordinator_retention(ds: Dataset, f: Filters) -> KpiResult:
    ca = ds.coordinator_assignments
    ca = ca.loc[ca["team_id"].isin(teams_in_scope(ds, f))]

    def assigned_on(day) -> set[str]:
        ts = pd.Timestamp(day)
        active = (ca["start_date"] <= ts) & (ca["end_date"].isna() | (ca["end_date"] >= ts))
        return set(ca.loc[active, "user_id"])

    at_start = assigned_on(f.start)
    retained = at_start & assigned_on(f.end)
    return _ratio_result("QQ-08", len(retained), len(at_start), note="Headcount at the start and end of the range.")


def coordinator_timeline(ds: Dataset, f: Filters) -> pd.DataFrame:
    ca = ds.coordinator_assignments
    ca = ca.loc[ca["team_id"].isin(teams_in_scope(ds, f))].copy()
    ca["end_display"] = ca["end_date"].fillna(pd.Timestamp(ds.reference_date))
    ca = ca.merge(ds.users[["user_id", "display_name"]], on="user_id", how="left")
    return ca.merge(ds.teams[["team_id", "team_name"]], on="team_id", how="left")


def quality_trend(ds: Dataset, f: Filters) -> pd.DataFrame:
    """Monthly QQ-03, QQ-05, QQ-06 and QQ-07, each with its own date rule."""
    periods = _all_periods(f, "M")
    out = pd.DataFrame(index=periods)

    bugs = scope_bugs(ds, f)
    month = _period_start(bugs["created"], "M")
    out["Defect escape rate"] = _escaped(bugs).groupby(month).mean()

    runs = _automated_runs(ds, f)
    out["Automation stability"] = 1 - _unstable(runs).groupby(_period_start(runs["executed_on"], "M")).mean()

    reports = _reports_in_scope(ds, f)
    out["Reporting timeliness"] = _on_time(reports).groupby(_period_start(reports["due_date"], "M")).mean()

    inc = incidents(ds, f)
    out["Production incidents"] = inc.groupby(_period_start(inc["created"], "M")).size().reindex(periods, fill_value=0)
    return out.rename_axis("period").reset_index()


# ---------------------------------------------------------------------------
# Composite views (overview comparison tables)
# ---------------------------------------------------------------------------

COMPOSITE_KPIS = (
    ("DM-01", dm01_total_bugs),
    ("DM-02", dm02_open_bugs),
    ("DM-09", dm09_avg_resolution_time),
    ("DM-10", dm10_overdue_bugs),
    ("TE-03", te03_execution_rate),
    ("TE-04", te04_pass_rate),
    ("QQ-03", qq03_defect_escape_rate),
)


def performance_table(ds: Dataset, f: Filters, by: str) -> pd.DataFrame:
    """'QA performance by team' (by='team') or 'Project performance comparison' (by='project')."""
    if by == "team":
        keys = sorted(teams_in_scope(ds, f))
        names = ds.teams.set_index("team_id")["team_name"]
        narrow = lambda k: f.with_(teams=(k,))  # noqa: E731
    else:
        keys = sorted(projects_in_scope(ds, f))
        names = ds.projects.set_index("project_key")["project_name"]
        narrow = lambda k: f.with_(projects=(k,))  # noqa: E731

    rows = []
    for key in keys:
        row = {"key": key, "name": names.get(key, key)}
        for kpi_id, func in COMPOSITE_KPIS:
            row[kpi_id] = func(ds, narrow(key)).value
        rows.append(row)
    return pd.DataFrame(rows, columns=["key", "name", *[k for k, _ in COMPOSITE_KPIS]])


def rag_status(kpi_id: str, value: float | None) -> str | None:
    """'green', 'amber', 'red' or None when no threshold or no value."""
    rule = s.THRESHOLDS.get(kpi_id)
    if rule is None or value is None or pd.isna(value):
        return None
    if rule["higher_is_better"]:
        return "green" if value >= rule["green"] else "amber" if value >= rule["amber"] else "red"
    return "green" if value <= rule["green"] else "amber" if value <= rule["amber"] else "red"
