"""KPI formulas checked against hand-computed values (see conftest.make_tiny)."""

from __future__ import annotations

from datetime import date

import pytest

from qa_dashboard import kpi_settings as s
from qa_dashboard import kpis as k
from qa_dashboard.models import Filters


# --- A. Defect management ---------------------------------------------------

def test_bug_counts(tiny, tiny_range):
    assert k.dm01_total_bugs(tiny, tiny_range).value == 4  # B1-B4; B5 created before range
    assert k.dm02_open_bugs(tiny, tiny_range).value == 2  # B2, B4
    assert k.dm03_resolved_bugs(tiny, tiny_range).value == 2  # B1, B3


def test_groupings_sum_to_total(tiny, tiny_range):
    total = k.dm01_total_bugs(tiny, tiny_range).value
    by_priority = k.dm04_bugs_by_priority(tiny, tiny_range)
    assert by_priority["count"].sum() == total
    assert list(by_priority["priority"]) == list(s.ISSUE_PRIORITIES)
    assert k.dm05_bugs_by_status(tiny, tiny_range)["count"].sum() == total
    assert k.dm06_bugs_by_project(tiny, tiny_range).set_index("project_key")["count"].to_dict() == {"P1": 2, "P2": 2}
    assert k.dm06_bugs_by_team(tiny, tiny_range)["count"].sum() == total


def test_trends_use_their_own_dates(tiny, tiny_range):
    assert k.dm07_creation_trend(tiny, tiny_range)["created"].sum() == 4
    # B5 was created before the range but resolved inside it.
    assert k.dm08_resolution_trend(tiny, tiny_range)["resolved"].sum() == 3


def test_average_resolution_time(tiny, tiny_range):
    result = k.dm09_avg_resolution_time(tiny, tiny_range)
    assert result.value == pytest.approx((4 + 10 + 49) / 3)  # B1, B3, B5 resolved in range
    assert result.status == "Provisional"


def test_average_resolution_time_excluding_duplicates(tiny, tiny_range, monkeypatch):
    monkeypatch.setattr(s, "RESOLUTION_TIME_EXCLUDED_RESOLUTIONS", ("Duplicate",))
    assert k.dm09_avg_resolution_time(tiny, tiny_range).value == pytest.approx((4 + 49) / 2)


def test_average_resolution_time_business_days(tiny, tiny_range, monkeypatch):
    monkeypatch.setattr(s, "RESOLUTION_TIME_BUSINESS_DAYS", True)
    # B1 Sun 1 Feb -> Thu 5 Feb: 3, B3 Sun 1 Mar -> Wed 11 Mar: 7, B5 Mon 15 Dec -> Mon 2 Feb: 35
    assert k.dm09_avg_resolution_time(tiny, tiny_range).value == pytest.approx((3 + 7 + 35) / 3)


def test_overdue_ignores_missing_due_dates(tiny, tiny_range):
    assert k.dm10_overdue_bugs(tiny, tiny_range).value == 1  # B2 only; B4 has no due date


def test_critical_bugs_unresolved_until_defined(tiny, tiny_range, monkeypatch):
    result = k.critical_bugs(tiny, tiny_range)
    assert result.status == "Unresolved" and result.value is None
    monkeypatch.setattr(s, "CRITICAL_PRIORITIES", ("Highest",))
    assert k.critical_bugs(tiny, tiny_range).value == 1


# --- B. Test execution ------------------------------------------------------

def test_execution_kpis(tiny, tiny_range):
    assert k.te01_total_executions(tiny, tiny_range).value == 6  # E7 is out of range
    assert k.te02_results_breakdown(tiny, tiny_range).set_index("status")["count"].to_dict() == {
        "Pass": 2, "Fail": 2, "Blocked": 1, "In Progress": 0, "Not Executed": 1}
    rate = k.te03_execution_rate(tiny, tiny_range)
    assert (rate.numerator, rate.denominator, rate.value) == (4, 6, pytest.approx(4 / 6))
    assert k.te04_pass_rate(tiny, tiny_range).value == pytest.approx(0.5)
    assert k.te05_fail_rate(tiny, tiny_range).value == pytest.approx(0.5)
    assert k.te06_blocked_tests(tiny, tiny_range).value == 1
    assert k.te07_nrt_execution_rate(tiny, tiny_range).value == pytest.approx(2 / 4)


def test_blocked_as_executed_setting(tiny, tiny_range, monkeypatch):
    monkeypatch.setattr(s, "EXECUTED_STATUSES", ("Pass", "Fail", "Blocked"))
    assert k.te03_execution_rate(tiny, tiny_range).value == pytest.approx(5 / 6)


def test_results_by_team(tiny, tiny_range):
    table = k.te09_results_by(tiny, tiny_range, "team_id").set_index("team_id")
    assert table.loc["T1", "Planned"] == 4 and table.loc["T1", "Executed"] == 2
    assert table.loc["T2", "Pass rate"] == pytest.approx(0.5)


def test_execution_trend_excludes_not_executed(tiny, tiny_range):
    assert k.te08_execution_trend(tiny, tiny_range)["count"].sum() == 5


# --- C. Quality and coverage ------------------------------------------------

def test_quality_kpis(tiny, tiny_range):
    assert k.qq01_test_coverage(tiny, tiny_range).value == pytest.approx(1 / 3)  # S1 only (TC2 is Draft)
    assert k.qq02_bug_reporting_quality(tiny, tiny_range).value == pytest.approx(1 / 4)  # B1 only
    assert k.qq03_defect_escape_rate(tiny, tiny_range).value == pytest.approx(2 / 4)  # B1, B4
    assert k.qq04_automation_coverage(tiny, tiny_range).value == pytest.approx(1 / 4)  # TC1 of TC1-3, TC5 (TC4 deprecated)
    assert k.qq05_automation_stability(tiny, tiny_range).value == pytest.approx(0.5)  # E2 script failure
    assert k.qq06_production_incidents(tiny, tiny_range).value == 1
    assert k.qq07_reporting_timeliness(tiny, tiny_range).value == pytest.approx(1 / 3)  # R1 on time, R2 late, R3 missing
    assert k.qq08_coordinator_retention(tiny, tiny_range).value == pytest.approx(1 / 2)  # C2 replaced by C3


def test_automation_coverage_excluding_not_automatable(tiny, tiny_range, monkeypatch):
    monkeypatch.setattr(s, "AUTOMATION_EXCLUDE_NOT_AUTOMATABLE", True)
    assert k.qq04_automation_coverage(tiny, tiny_range).value == pytest.approx(1 / 3)  # TC3 excluded


def test_product_defect_failures_do_not_reduce_stability(tiny):
    f = Filters(date(2026, 3, 1), date(2026, 3, 31))  # only E5 (manual product defect) and E6
    assert k.qq05_automation_stability(tiny, f).value is None  # no automated run in range


def test_quality_trend_and_composites(tiny, tiny_range):
    trend = k.quality_trend(tiny, tiny_range)
    assert len(trend) == 6 and trend["Production incidents"].sum() == 1
    perf = k.performance_table(tiny, tiny_range, "team").set_index("key")
    assert perf.loc["T1", "DM-01"] == 2 and perf.loc["T2", "QQ-03"] == pytest.approx(0.5)


def test_rag_status():
    assert k.rag_status("TE-04", 0.95) == "green"
    assert k.rag_status("TE-04", 0.85) == "amber"
    assert k.rag_status("TE-04", 0.5) == "red"
    assert k.rag_status("QQ-03", 0.04) == "green"
    assert k.rag_status("QQ-03", 0.2) == "red"
    assert k.rag_status("DM-01", 10) is None
    assert k.rag_status("TE-04", None) is None


# --- Edge cases -------------------------------------------------------------

def test_empty_scope_returns_zero_or_none(tiny):
    f = Filters(date(2020, 1, 1), date(2020, 12, 31))
    assert k.dm01_total_bugs(tiny, f).value == 0
    for func in (k.dm09_avg_resolution_time, k.te03_execution_rate, k.te04_pass_rate, k.te07_nrt_execution_rate,
                 k.qq02_bug_reporting_quality, k.qq03_defect_escape_rate, k.qq05_automation_stability,
                 k.qq07_reporting_timeliness, k.qq08_coordinator_retention):
        assert func(tiny, f).value is None, func.__name__
    assert k.dm07_creation_trend(tiny, f)["created"].sum() == 0
    assert k.te08_execution_trend(tiny, f).empty
    assert k.te07_nrt_by_cycle(tiny, f).empty
    assert len(k.performance_table(tiny, f, "project")) == 2


def test_conflicting_team_and_project_filters_give_empty_scope(tiny, tiny_range):
    f = tiny_range.with_(teams=("T1",), projects=("P2",))
    assert k.dm01_total_bugs(tiny, f).value == 0
    assert k.te01_total_executions(tiny, f).value == 0
    assert k.qq04_automation_coverage(tiny, f).value is None
    assert k.performance_table(tiny, f, "team").empty


def test_kpis_on_synthetic_data_are_bounded(synthetic):
    f = Filters(date(2025, 11, 1), date(2026, 10, 31))
    for func in (k.te03_execution_rate, k.te04_pass_rate, k.te07_nrt_execution_rate, k.qq01_test_coverage,
                 k.qq02_bug_reporting_quality, k.qq03_defect_escape_rate, k.qq04_automation_coverage,
                 k.qq05_automation_stability, k.qq07_reporting_timeliness, k.qq08_coordinator_retention):
        value = func(synthetic, f).value
        assert value is not None and 0 <= value <= 1, func.__name__
    assert k.dm02_open_bugs(synthetic, f).value + k.dm03_resolved_bugs(synthetic, f).value == k.dm01_total_bugs(synthetic, f).value
