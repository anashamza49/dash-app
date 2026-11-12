"""Filter behaviour from docs/kpi-definitions.md, section "Filter behaviour"."""

from __future__ import annotations

from datetime import date

from qa_dashboard import kpis as k
from qa_dashboard.filters import projects_in_scope, scope_executions, teams_in_scope
from qa_dashboard.models import Filters


def test_date_range_is_inclusive_on_calendar_days(tiny):
    f = Filters(date(2026, 2, 1), date(2026, 2, 1))
    assert k.dm01_total_bugs(tiny, f).value == 1  # B1 created 2026-02-01 10:00


def test_not_executed_rows_use_cycle_planned_end(tiny):
    f = Filters(date(2026, 2, 5), date(2026, 2, 5))
    assert list(scope_executions(tiny, f)["execution_id"]) == ["E3"]


def test_team_filter_changes_kpis(tiny, tiny_range):
    f = tiny_range.with_(teams=("T1",))
    assert k.dm01_total_bugs(tiny, f).value == 2
    assert k.te01_total_executions(tiny, f).value == 4
    assert k.qq07_reporting_timeliness(tiny, f).value == 0.5
    assert k.qq08_coordinator_retention(tiny, f).value == 1.0


def test_project_filter_selects_owning_team_for_team_datasets(tiny, tiny_range):
    f = tiny_range.with_(projects=("P2",))
    assert teams_in_scope(tiny, f) == {"T2"}
    assert k.qq07_reporting_timeliness(tiny, f).value == 0.0  # R3 not submitted


def test_priority_and_status_apply_to_bugs_only(tiny, tiny_range):
    f = tiny_range.with_(priorities=("High",), statuses=("Closed",))
    assert k.dm01_total_bugs(tiny, f).value == 1  # B1
    assert k.te01_total_executions(tiny, f).value == 6  # tests unaffected
    assert k.qq06_production_incidents(tiny, f).value == 1  # incidents unaffected
    assert k.qq04_automation_coverage(tiny, f).value == k.qq04_automation_coverage(tiny, tiny_range).value


def test_scope_intersection(tiny):
    f = Filters(date(2026, 1, 1), date(2026, 1, 2), teams=("T1",), projects=("P1", "P2"))
    assert projects_in_scope(tiny, f) == {"P1"}


def test_filters_change_synthetic_results(synthetic):
    full = Filters(date(2025, 11, 1), date(2026, 10, 31))
    one_team = full.with_(teams=("TEAM-D",))
    teams_total = sum(k.dm01_total_bugs(synthetic, full.with_(teams=(t,))).value for t in synthetic.teams["team_id"])
    assert teams_total == k.dm01_total_bugs(synthetic, full).value
    assert k.te04_pass_rate(synthetic, one_team).value != k.te04_pass_rate(synthetic, full).value
