"""Shared fixtures.

`tiny` is a hand-built dataset whose KPI values are computed by hand in
test_kpis.py from the formulas of docs/kpi-definitions.md.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from qa_dashboard.data.db import save_dataset
from qa_dashboard.data.generator import generate_dataset
from qa_dashboard.models import Dataset, Filters

T = pd.Timestamp
NAT = pd.NaT


def _issue(key, project, team, issue_type, status, category, priority, created, resolved=NAT, resolution=None,
           due=NAT, env=None, repro=False, attach=False, linked=None):
    return dict(issue_key=key, project_key=project, team_id=team, issue_type=issue_type, summary=key, status=status,
                status_category=category, priority=priority, assignee_id="D1", reporter_id="Q1", created=T(created),
                updated=T(resolved) if resolved is not NAT else T(created), resolved=T(resolved), due_date=T(due),
                resolution=resolution, labels=[], environment=env, fix_version=None, linked_execution_id=None,
                linked_issue_key=linked, has_repro_steps=repro, has_attachment=attach)


def _exec(eid, cycle, tc, project, team, status, executed_on=NAT, mode="Manual", reason=None):
    return dict(execution_id=eid, cycle_id=cycle, test_case_key=tc, project_key=project, team_id=team, status=status,
                executed_on=T(executed_on), executed_by=None if executed_on is NAT else "Q1", execution_mode=mode,
                failure_reason=reason, defect_keys=[])


def make_tiny() -> Dataset:
    teams = pd.DataFrame({"team_id": ["T1", "T2"], "team_name": ["Team One", "Team Two"], "location": ["X", "Y"]})
    projects = pd.DataFrame({"project_key": ["P1", "P2"], "project_name": ["Project 1", "Project 2"],
                             "team_id": ["T1", "T2"], "project_type": ["Web", "Data"], "criticality": ["High", "Low"]})
    users = pd.DataFrame({
        "user_id": ["Q1", "D1", "C1", "C2", "C3"],
        "display_name": ["Qa One", "Dev One", "Coord One", "Coord Two", "Coord Three"],
        "role": ["QA Engineer", "Developer", "QA Coordinator", "QA Coordinator", "QA Coordinator"],
        "team_id": ["T1", None, "T1", "T2", "T2"],
        "start_date": pd.to_datetime(["2025-01-01"] * 5),
        "end_date": pd.to_datetime([None, None, None, "2026-03-15", None]),
    })
    assignments = pd.DataFrame({
        "assignment_id": ["A1", "A2", "A3"], "team_id": ["T1", "T2", "T2"], "user_id": ["C1", "C2", "C3"],
        "start_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-03-16"]),
        "end_date": pd.to_datetime([None, "2026-03-15", None]),
    })
    issues = pd.DataFrame([
        _issue("B1", "P1", "T1", "Bug", "Closed", "Done", "High", "2026-02-01 10:00", "2026-02-05 10:00", "Fixed",
               "2026-02-06", "PROD", True, True),
        _issue("B2", "P1", "T1", "Bug", "Open", "To Do", "Medium", "2026-02-10 09:00", due="2026-02-25", env="UAT",
               repro=True),
        _issue("B3", "P2", "T2", "Bug", "Resolved", "Done", "Low", "2026-03-01 08:00", "2026-03-11 08:00", "Duplicate",
               env="SIT", repro=True, attach=True),
        _issue("B4", "P2", "T2", "Bug", "In Progress", "In Progress", "Highest", "2026-04-01 12:00", env="PROD"),
        _issue("B5", "P1", "T1", "Bug", "Closed", "Done", "High", "2025-12-15 10:00", "2026-02-02 10:00", "Fixed",
               env="DEV", repro=True, attach=True),
        _issue("S1", "P1", "T1", "Story", "Done", "Done", "Medium", "2026-01-05", "2026-01-20", "Done"),
        _issue("S2", "P1", "T1", "Story", "To Do", "To Do", "Medium", "2026-01-06"),
        _issue("S3", "P2", "T2", "Story", "In Progress", "In Progress", "Medium", "2026-01-07"),
        _issue("I1", "P1", "T1", "Incident", "Closed", "Done", "Highest", "2026-02-02 08:00", "2026-02-03 08:00",
               "Fixed", env="PROD", linked="B1"),
    ])
    test_cases = pd.DataFrame({
        "test_case_key": ["TC1", "TC2", "TC3", "TC4", "TC5"],
        "project_key": ["P1", "P1", "P1", "P1", "P2"], "team_id": ["T1", "T1", "T1", "T1", "T2"],
        "name": ["a", "b", "c", "d", "e"], "test_type": ["Regression", "Functional", "E2E", "Smoke", "Functional"],
        "is_nrt": [True, False, True, True, False], "priority": ["High"] * 5,
        "status": ["Approved", "Draft", "Approved", "Deprecated", "Approved"],
        "automation_status": ["Automated", "To Automate", "Not Automatable", "Automated", "To Automate"],
        "automated_since": pd.to_datetime(["2025-06-01", None, None, "2025-06-01", None]),
        "covered_story_key": ["S1", "S2", None, None, None],
        "created": pd.to_datetime(["2025-05-01"] * 5), "owner_id": ["Q1"] * 5,
    })
    cycles = pd.DataFrame({
        "cycle_id": ["CY1", "CY2", "CY3"], "project_key": ["P1", "P2", "P1"],
        "name": ["P1 1.0 NRT", "P2 1.0 Functional", "P1 0.9 Functional"], "cycle_type": ["NRT", "Functional", "Functional"],
        "version": ["P1 1.0", "P2 1.0", "P1 0.9"],
        "planned_start": pd.to_datetime(["2026-02-01", "2026-03-01", "2025-12-01"]),
        "planned_end": pd.to_datetime(["2026-02-05", "2026-03-05", "2025-12-05"]),
    })
    executions = pd.DataFrame([
        _exec("E1", "CY1", "TC1", "P1", "T1", "Pass", "2026-02-02 10:00", "Automated"),
        _exec("E2", "CY1", "TC1", "P1", "T1", "Fail", "2026-02-03 10:00", "Automated", "Test script issue"),
        _exec("E3", "CY1", "TC3", "P1", "T1", "Not Executed"),
        _exec("E4", "CY1", "TC3", "P1", "T1", "Blocked", "2026-02-04 10:00"),
        _exec("E5", "CY2", "TC5", "P2", "T2", "Fail", "2026-03-02 10:00", reason="Product defect"),
        _exec("E6", "CY2", "TC5", "P2", "T2", "Pass", "2026-03-03 10:00"),
        _exec("E7", "CY3", "TC1", "P1", "T1", "Pass", "2025-12-02 10:00"),
    ])
    reports = pd.DataFrame({
        "report_id": ["R1", "R2", "R3", "R4"], "team_id": ["T1", "T1", "T2", "T2"],
        "week_start": pd.to_datetime(["2026-01-05", "2026-01-12", "2026-01-12", "2025-12-22"]),
        "due_date": pd.to_datetime(["2026-01-12 12:00", "2026-01-19 12:00", "2026-01-19 12:00", "2025-12-29 12:00"]),
        "submitted_at": pd.to_datetime(["2026-01-12 09:00", "2026-01-20 09:00", None, "2025-12-29 08:00"]),
        "author_id": ["C1", "C1", "C2", "C2"],
    })
    return Dataset(teams=teams, projects=projects, users=users, coordinator_assignments=assignments, issues=issues,
                   test_cases=test_cases, test_cycles=cycles, test_executions=executions, qa_reports=reports,
                   reference_date=date(2026, 6, 30))


@pytest.fixture()
def tiny() -> Dataset:
    return make_tiny()


@pytest.fixture()
def tiny_range() -> Filters:
    return Filters(date(2026, 1, 1), date(2026, 6, 30))


@pytest.fixture(scope="session")
def synthetic() -> Dataset:
    return generate_dataset()


@pytest.fixture(scope="session")
def synthetic_db(synthetic, tmp_path_factory):
    path = tmp_path_factory.mktemp("db") / "qa.sqlite"
    save_dataset(synthetic, path)
    return path
