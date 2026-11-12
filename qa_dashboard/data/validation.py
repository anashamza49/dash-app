"""Consistency rules 1-12 of docs/data-model.md.

Documented exception to rule 12: issues.due_date may be after the reference
date (a bug created near the reference date gets created + target days).
"""

from __future__ import annotations

import pandas as pd

from ..models import Dataset

QA_ROLES = {"QA Coordinator", "QA Engineer", "Automation Engineer"}
SLIP = pd.Timedelta(days=7)


def _fk(errors: list[str], label: str, values: pd.Series, valid, nullable: bool = True) -> None:
    values = values.dropna() if nullable else values
    bad = values.loc[~values.isin(set(valid))]
    if len(bad):
        errors.append(f"Rule 1: {label} has {len(bad)} unknown reference(s), e.g. {bad.iloc[0]!r}")


def validate(ds: Dataset) -> list[str]:
    """Return the list of broken rules (empty when the dataset is consistent)."""
    e: list[str] = []
    teams, projects, users = set(ds.teams["team_id"]), ds.projects, ds.users
    issues, tc, cycles, ex = ds.issues, ds.test_cases, ds.test_cycles, ds.test_executions
    user_ids = set(users["user_id"])
    ref_end = pd.Timestamp(ds.reference_date) + pd.Timedelta(days=1)

    # 1. Foreign keys
    _fk(e, "projects.team_id", projects["team_id"], teams, nullable=False)
    _fk(e, "users.team_id", users["team_id"], teams)
    _fk(e, "coordinator_assignments.team_id", ds.coordinator_assignments["team_id"], teams, nullable=False)
    _fk(e, "coordinator_assignments.user_id", ds.coordinator_assignments["user_id"], user_ids, nullable=False)
    _fk(e, "issues.project_key", issues["project_key"], projects["project_key"], nullable=False)
    _fk(e, "issues.assignee_id", issues["assignee_id"], user_ids)
    _fk(e, "issues.reporter_id", issues["reporter_id"], user_ids, nullable=False)
    _fk(e, "issues.linked_issue_key", issues["linked_issue_key"], issues["issue_key"])
    _fk(e, "issues.linked_execution_id", issues["linked_execution_id"], ex["execution_id"])
    _fk(e, "test_cases.project_key", tc["project_key"], projects["project_key"], nullable=False)
    _fk(e, "test_cases.owner_id", tc["owner_id"], user_ids, nullable=False)
    _fk(e, "test_cycles.project_key", cycles["project_key"], projects["project_key"], nullable=False)
    _fk(e, "test_executions.cycle_id", ex["cycle_id"], cycles["cycle_id"], nullable=False)
    _fk(e, "test_executions.test_case_key", ex["test_case_key"], tc["test_case_key"], nullable=False)
    _fk(e, "test_executions.executed_by", ex["executed_by"], user_ids)
    _fk(e, "qa_reports.team_id", ds.qa_reports["team_id"], teams, nullable=False)
    _fk(e, "qa_reports.author_id", ds.qa_reports["author_id"], user_ids, nullable=False)
    all_defects = pd.Series([k for ks in ex["defect_keys"] for k in ks], dtype=object)
    _fk(e, "test_executions.defect_keys", all_defects, issues.loc[issues["issue_type"] == "Bug", "issue_key"])
    stories = issues.loc[issues["issue_type"] == "Story"].set_index("issue_key")["project_key"]
    covered = tc.dropna(subset=["covered_story_key"])
    if (covered["covered_story_key"].map(stories) != covered["project_key"]).any():
        e.append("Rule 1: a test case covers something that is not a Story of its project")

    # 2. Same team as the project
    team_of = projects.set_index("project_key")["team_id"]
    for name, df in (("issues", issues), ("test_cases", tc), ("test_executions", ex)):
        if (df["project_key"].map(team_of) != df["team_id"]).any():
            e.append(f"Rule 2: {name} with a team different from its project's team")

    # 3. resolved / resolution iff Done
    done = issues["status_category"] == "Done"
    if (issues["resolved"].notna() != done).any() or (issues["resolution"].notna() != done).any():
        e.append("Rule 3: resolved/resolution not set if and only if status_category is Done")

    # 4. created <= updated, created <= resolved <= reference date, updated >= resolved
    if (issues["created"] > issues["updated"]).any():
        e.append("Rule 4: created after updated")
    res = issues.dropna(subset=["resolved"])
    if ((res["resolved"] < res["created"]) | (res["resolved"] >= ref_end) | (res["updated"] < res["resolved"])).any():
        e.append("Rule 4: resolved outside [created, reference date] or after updated")

    # 5. Bug reporter is QA, assignee is a developer
    role = users.set_index("user_id")["role"]
    bugs = issues.loc[issues["issue_type"] == "Bug"]
    if (~bugs["reporter_id"].map(role).isin(QA_ROLES)).any():
        e.append("Rule 5: bug reporter is not a QA member")
    if (bugs["assignee_id"].dropna().map(role) != "Developer").any():
        e.append("Rule 5: bug assignee is not a developer")

    # 6. executed_on/by iff executed, close to cycle dates
    not_exec = ex["status"] == "Not Executed"
    if (ex["executed_on"].isna() != not_exec).any() or (ex["executed_by"].isna() != not_exec).any():
        e.append("Rule 6: executed_on/executed_by not null if and only if executed")
    cyc = cycles.set_index("cycle_id")
    run = ex.loc[~not_exec]
    lo = run["cycle_id"].map(cyc["planned_start"]) - SLIP
    hi = run["cycle_id"].map(cyc["planned_end"]) + SLIP + pd.Timedelta(days=1)
    if ((run["executed_on"] < lo) | (run["executed_on"] >= hi)).any():
        e.append("Rule 6: executed_on outside cycle dates plus 7-day slip")

    # 7. Execution, test case and cycle in the same project
    tc_project = tc.set_index("test_case_key")["project_key"]
    if ((ex["test_case_key"].map(tc_project) != ex["project_key"]) | (ex["cycle_id"].map(cyc["project_key"]) != ex["project_key"])).any():
        e.append("Rule 7: execution, test case and cycle not in the same project")

    # 8. Automated runs only for test cases automated on that date
    auto = ex.loc[ex["execution_mode"] == "Automated"]
    day = auto["executed_on"].fillna(auto["cycle_id"].map(cyc["planned_start"])).dt.normalize()
    since = auto["test_case_key"].map(tc.set_index("test_case_key")["automated_since"])
    if (since.isna() | (since > day)).any():
        e.append("Rule 8: automated execution before the test case was automated")

    # 9. failure_reason only for Fail, defect_keys only for product defects, bugs created after execution
    if (ex["failure_reason"].notna() & (ex["status"] != "Fail")).any():
        e.append("Rule 9: failure_reason set on a non-Fail execution")
    has_defects = ex["defect_keys"].map(len) > 0
    if (has_defects & (ex["failure_reason"] != "Product defect")).any():
        e.append("Rule 9: defect_keys set without a product defect")
    created = issues.set_index("issue_key")["created"]
    pairs = ex.loc[has_defects, ["executed_on", "defect_keys"]].explode("defect_keys")
    if (pairs["defect_keys"].map(created) < pairs["executed_on"]).any():
        e.append("Rule 9: linked bug created before the execution")

    # 10. Incident linked to a PROD bug of the same project
    inc = issues.loc[issues["issue_type"] == "Incident"].dropna(subset=["linked_issue_key"])
    linked = issues.set_index("issue_key").loc[inc["linked_issue_key"]]
    if ((linked["issue_type"].to_numpy() != "Bug") | (linked["environment"].to_numpy() != "PROD")
            | (linked["project_key"].to_numpy() != inc["project_key"].to_numpy())).any():
        e.append("Rule 10: incident not linked to a PROD bug of the same project")

    # 11. Coordinator assignments do not overlap, assignee is a coordinator
    ca = ds.coordinator_assignments
    if (ca["user_id"].map(role) != "QA Coordinator").any():
        e.append("Rule 11: assignment to a user who is not a QA Coordinator")
    for team, rows in ca.sort_values("start_date").groupby("team_id"):
        ends = rows["end_date"].fillna(pd.Timestamp.max).to_numpy()
        starts = rows["start_date"].to_numpy()
        if (starts[1:] <= ends[:-1]).any():
            e.append(f"Rule 11: overlapping coordinator assignments for {team}")

    # 12. No date after the reference date (except issues.due_date)
    checks = {
        "users": ["start_date", "end_date"], "coordinator_assignments": ["start_date", "end_date"],
        "issues": ["created", "updated", "resolved"], "test_cases": ["created", "automated_since"],
        "test_cycles": ["planned_start", "planned_end"], "test_executions": ["executed_on"],
        "qa_reports": ["week_start", "due_date", "submitted_at"],
    }
    for name, cols in checks.items():
        df = getattr(ds, name)
        for col in cols:
            if (df[col].dropna() >= ref_end).any():
                e.append(f"Rule 12: {name}.{col} after the reference date")
    return e
