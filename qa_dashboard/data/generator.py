"""Reproducible synthetic Jira/Zephyr-like dataset (docs/data-model.md).

Every name is fictional. No real client data, person or credential is used.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd

from .. import kpi_settings as s
from ..config import HISTORY_START, RANDOM_SEED, REFERENCE_DATE
from ..models import Dataset

QA_ROLES = ("QA Coordinator", "QA Engineer", "Automation Engineer")

TEAMS = [
    ("TEAM-A", "QA Team Atlas", "Paris"),
    ("TEAM-B", "QA Team Boreal", "Lyon"),
    ("TEAM-C", "QA Team Cobalt", "Nantes"),
    ("TEAM-D", "QA Team Delta", "Lille"),
    ("TEAM-E", "QA Team Equinox", "Bordeaux"),
]
STRONG_TEAM, WEAK_TEAM = "TEAM-B", "TEAM-D"

# key, name, team, type, criticality, domain features
PROJECTS = [
    ("ECOM", "E-commerce Platform", "TEAM-A", "Web", "High", ["checkout", "voucher code", "basket", "product page"]),
    ("PAY", "Payment Gateway", "TEAM-A", "Integration", "High", ["card payment", "refund", "3-D Secure", "settlement file"]),
    ("CRM", "Customer Relationship Hub", "TEAM-B", "Back office", "Medium", ["contact search", "lead import", "account merge", "activity log"]),
    ("MOB", "Mobile Banking App", "TEAM-B", "Mobile", "High", ["login", "transfer", "push notification", "statement download"]),
    ("HRP", "HR Self-service Portal", "TEAM-C", "Web", "Low", ["leave request", "payslip view", "profile update", "approval flow"]),
    ("DWH", "Data Warehouse", "TEAM-C", "Data", "Medium", ["nightly load", "sales mart", "currency conversion", "data quality check"]),
    ("LOG", "Logistics Tracking", "TEAM-D", "Integration", "High", ["shipment status", "carrier API", "label printing", "delivery slot"]),
    ("INV", "Inventory Management", "TEAM-D", "Back office", "Medium", ["stock count", "reorder rule", "warehouse transfer", "barcode scan"]),
    ("MKT", "Marketing Website", "TEAM-E", "Web", "Low", ["landing page", "newsletter form", "cookie banner", "store locator"]),
    ("BIR", "BI Reporting", "TEAM-E", "Data", "Medium", ["KPI export", "dashboard filter", "scheduled report", "row-level security"]),
]
CRITICALITY_WEIGHT = {"High": 1.6, "Medium": 1.0, "Low": 0.6}
PROD_RATE = {"High": 0.10, "Medium": 0.07, "Low": 0.05}

# user_id, name, role, team, start, end
USERS = [
    ("U001", "Camille Laurent", "QA Coordinator", "TEAM-A", "2023-02-01", None),
    ("U002", "Hugo Bernard", "QA Coordinator", "TEAM-B", "2022-09-01", None),
    ("U003", "Lea Dubois", "QA Coordinator", "TEAM-C", "2023-06-01", "2026-06-30"),
    ("U004", "Nathan Moreau", "QA Coordinator", "TEAM-D", "2024-01-15", "2026-03-13"),
    ("U005", "Chloe Petit", "QA Coordinator", "TEAM-E", "2023-11-01", None),
    ("U006", "Lucas Girard", "QA Coordinator", "TEAM-D", "2026-03-16", None),
    ("U007", "Emma Roux", "QA Coordinator", "TEAM-C", "2026-07-01", None),
    ("U008", "Alex Martin", "QA Engineer", "TEAM-A", "2023-04-03", None),
    ("U009", "Sarah Lambert", "QA Engineer", "TEAM-B", "2022-11-14", None),
    ("U010", "Yanis Fontaine", "QA Engineer", "TEAM-C", "2023-09-04", None),
    ("U011", "Julie Mercier", "QA Engineer", "TEAM-D", "2024-02-05", None),
    ("U012", "Tom Garnier", "QA Engineer", "TEAM-E", "2023-03-20", None),
    ("U013", "Ines Faure", "QA Engineer", "TEAM-A", "2024-05-02", None),
    ("U014", "Victor Chevalier", "Automation Engineer", "TEAM-B", "2023-01-09", None),
    ("U015", "Manon Blanc", "Automation Engineer", "TEAM-E", "2023-10-02", None),
    ("U016", "Paul Henry", "Developer", None, "2022-03-01", None),
    ("U017", "Sofia Rousseau", "Developer", None, "2022-06-13", None),
    ("U018", "Adam Leroy", "Developer", None, "2023-01-16", None),
    ("U019", "Clara Perrin", "Developer", None, "2023-05-22", None),
    ("U020", "Leo Gauthier", "Developer", None, "2023-08-28", None),
    ("U021", "Zoe Masson", "Developer", None, "2024-01-08", None),
    ("U022", "Noah Brunet", "Developer", None, "2024-03-18", None),
]

COORDINATOR_ASSIGNMENTS = [
    ("CA-01", "TEAM-A", "U001", "2023-02-01", None),
    ("CA-02", "TEAM-B", "U002", "2022-09-01", None),
    ("CA-03", "TEAM-C", "U003", "2023-06-01", "2026-06-30"),
    ("CA-04", "TEAM-D", "U004", "2024-01-15", "2026-03-13"),
    ("CA-05", "TEAM-E", "U005", "2023-11-01", None),
    ("CA-06", "TEAM-D", "U006", "2026-03-16", None),
    ("CA-07", "TEAM-C", "U007", "2026-07-01", None),
]

BUG_TEMPLATES = [
    "{f} fails when input contains special characters",
    "Error 500 on {f} after session timeout",
    "{f} shows wrong totals after refresh",
    "{f} not updated after user action",
    "Slow response on {f} under load",
    "Validation message missing on {f}",
    "{f} layout broken on small screens",
    "Duplicate records created by {f}",
]
STORY_TEMPLATES = ["As a user I can use {f}", "Improve {f} experience", "Add audit trail to {f}", "Support new rules in {f}"]
TASK_TEMPLATES = ["Upgrade library used by {f}", "Configure monitoring for {f}", "Clean up test data for {f}"]
INCIDENT_TEMPLATES = ["Production outage on {f}", "Customers report errors on {f}", "Degraded service on {f}"]
TEST_TEMPLATES = ["Verify {f} nominal flow", "Verify {f} with invalid data", "Verify {f} permissions", "Verify {f} end to end"]

BUG_PRIORITY_P = [0.05, 0.20, 0.45, 0.22, 0.08]
PROD_BUG_PRIORITY_P = [0.20, 0.35, 0.30, 0.10, 0.05]
RESOLUTION_MEAN_DAYS = {"Highest": 2, "High": 5, "Medium": 12, "Low": 25, "Lowest": 35}
TEAM_SPEED = {STRONG_TEAM: 0.7, WEAK_TEAM: 1.6}
OPEN_STATUSES = (["Open", "Reopened", "In Progress", "Blocked", "In Testing"], [0.35, 0.05, 0.30, 0.08, 0.22])
STATUS_CATEGORY = {
    "Open": "To Do", "Reopened": "To Do", "To Do": "To Do",
    "In Progress": "In Progress", "Blocked": "In Progress", "In Testing": "In Progress",
    "Resolved": "Done", "Closed": "Done", "Done": "Done",
}
RESOLUTIONS = (["Fixed", "Won't Fix", "Duplicate", "Cannot Reproduce", "Not a Bug"], [0.75, 0.06, 0.07, 0.07, 0.05])
WEAK_RESOLUTIONS_P = [0.62, 0.06, 0.12, 0.11, 0.09]

TOTAL_BUGS, STORIES_PER_PROJECT, TASKS_PER_PROJECT, TOTAL_INCIDENTS = 850, 20, 8, 70
TEST_CASES_PER_PROJECT = {"High": 70, "Medium": 60, "Low": 50}


class _Generator:
    def __init__(self, seed: int, history_start: date, reference_date: date):
        self.rng = np.random.default_rng(seed)
        self.start = pd.Timestamp(history_start)
        self.ref = pd.Timestamp(reference_date)
        self.cap = self.ref + pd.Timedelta(hours=18)  # latest timestamp allowed

    # ------------------------------------------------------------------ helpers
    def choice(self, values, p=None):
        return values[int(self.rng.choice(len(values), p=p))]

    def rand_ts(self, lo: pd.Timestamp, hi: pd.Timestamp, business: bool = True) -> pd.Timestamp:
        hi = min(hi, self.cap)
        days = pd.date_range(lo.normalize(), hi.normalize(), freq="D")
        if business and (days.dayofweek < 5).any():
            days = days[days.dayofweek < 5]
        ts = days[int(self.rng.integers(len(days)))] + pd.Timedelta(minutes=int(self.rng.integers(8 * 60 + 30, 18 * 60 + 30)))
        return min(max(ts, lo), hi)

    def qa_members(self, team: str, on: pd.Timestamp, roles=QA_ROLES) -> list[str]:
        u = self.users
        mask = (u["team_id"] == team) & u["role"].isin(roles) & (u["start_date"] <= on)
        mask &= u["end_date"].isna() | (u["end_date"] >= on.normalize())
        found = list(u.loc[mask, "user_id"])
        if not found:
            found = list(u.loc[(u["team_id"] == team) & u["role"].isin(QA_ROLES), "user_id"])
        return found

    def coordinator_on(self, team: str, on: pd.Timestamp) -> str:
        ca = self.assignments
        rows = ca.loc[(ca["team_id"] == team) & (ca["start_date"] <= on)]
        rows = rows.loc[rows["end_date"].isna() | (rows["end_date"] >= on.normalize())]
        if rows.empty:
            rows = ca.loc[ca["team_id"] == team].sort_values("start_date")
        return rows.iloc[-1]["user_id"]

    # -------------------------------------------------------------- reference
    def reference_tables(self):
        self.teams = pd.DataFrame(TEAMS, columns=["team_id", "team_name", "location"])
        self.projects = pd.DataFrame([p[:5] for p in PROJECTS],
                                     columns=["project_key", "project_name", "team_id", "project_type", "criticality"])
        self.features = {p[0]: p[5] for p in PROJECTS}
        self.users = pd.DataFrame(USERS, columns=["user_id", "display_name", "role", "team_id", "start_date", "end_date"])
        self.assignments = pd.DataFrame(COORDINATOR_ASSIGNMENTS, columns=["assignment_id", "team_id", "user_id", "start_date", "end_date"])
        for df in (self.users, self.assignments):
            df["start_date"] = pd.to_datetime(df["start_date"])
            df["end_date"] = pd.to_datetime(df["end_date"])
        self.developers = list(self.users.loc[self.users["role"] == "Developer", "user_id"])
        self.team_of = dict(zip(self.projects["project_key"], self.projects["team_id"]))
        self.crit_of = dict(zip(self.projects["project_key"], self.projects["criticality"]))

    # --------------------------------------------------------- releases/cycles
    def releases_and_cycles(self):
        releases, cycles = [], []
        for key in self.projects["project_key"]:
            major = int(self.rng.integers(2, 6))
            minor = 0
            day = self.start + pd.Timedelta(days=int(self.rng.integers(28, 50)))
            while day <= self.ref:
                if day.dayofweek >= 5:
                    day -= pd.Timedelta(days=day.dayofweek - 3)  # move weekend releases to Thursday
                version = f"{key} {major}.{minor}"
                releases.append({"project_key": key, "version": version, "release_date": day})
                plan = [("NRT", 8, 2)]
                if self.rng.random() < 0.45:
                    plan.append(("Functional", 24, 10))
                if self.rng.random() < 0.15:
                    plan.append(("Smoke", 1, 0))
                for cycle_type, before_start, before_end in plan:
                    p_start, p_end = day - pd.Timedelta(days=before_start), day - pd.Timedelta(days=before_end)
                    if p_start >= self.start and p_end <= self.ref:
                        cycles.append({"project_key": key, "name": f"{version} {cycle_type}", "cycle_type": cycle_type,
                                       "version": version, "planned_start": p_start, "planned_end": p_end})
                minor += 1
                day += pd.Timedelta(days=int(self.rng.integers(50, 71)))
        self.releases = pd.DataFrame(releases)
        cycles = pd.DataFrame(cycles).sort_values(["project_key", "planned_start", "cycle_type"], ignore_index=True)
        cycles.insert(0, "cycle_id", cycles["project_key"] + "-R" + (cycles.groupby("project_key").cumcount() + 1).astype(str))
        self.cycles = cycles

    # ----------------------------------------------------------------- issues
    def _issue(self, tmp_id, key, issue_type, summary, status, priority, created, resolved, resolution, reporter,
               assignee, environment=None, labels=None, due_date=None, fix_version=None, linked_execution_id=None,
               linked_issue_key=None, has_repro_steps=False, has_attachment=False):
        if resolved is not None:
            updated = min(resolved + pd.Timedelta(hours=float(self.rng.uniform(0, 72))), self.cap)
        else:
            updated = created + (self.cap - created) * float(self.rng.uniform(0, 1))
        return {
            "tmp_id": tmp_id, "project_key": key, "team_id": self.team_of[key], "issue_type": issue_type,
            "summary": summary, "status": status, "status_category": STATUS_CATEGORY[status], "priority": priority,
            "assignee_id": assignee, "reporter_id": reporter, "created": created, "updated": max(updated, created),
            "resolved": resolved, "due_date": due_date, "resolution": resolution, "labels": labels or [],
            "environment": environment, "fix_version": fix_version, "linked_execution_id": linked_execution_id,
            "linked_issue_key": linked_issue_key, "has_repro_steps": has_repro_steps, "has_attachment": has_attachment,
        }

    def work_items(self):
        """Stories and tasks (stories are needed before test cases can cover them)."""
        items = []
        for key in self.projects["project_key"]:
            team = self.team_of[key]
            for issue_type, count, templates in (("Story", STORIES_PER_PROJECT, STORY_TEMPLATES),
                                                 ("Task", TASKS_PER_PROJECT, TASK_TEMPLATES)):
                for _ in range(count):
                    created = self.rand_ts(self.start, self.ref - pd.Timedelta(days=5))
                    done_at = created + pd.Timedelta(days=float(self.rng.uniform(7, 70)))
                    if done_at <= self.cap and self.rng.random() < 0.9:
                        status, resolved, resolution = "Done", done_at, "Done"
                    else:
                        status, resolved, resolution = self.choice(["To Do", "In Progress"], [0.4, 0.6]), None, None
                    items.append(self._issue(
                        f"W{len(items)}", key, issue_type,
                        self.choice(templates).format(f=self.choice(self.features[key])),
                        status, self.choice(s.ISSUE_PRIORITIES, [0.05, 0.25, 0.5, 0.15, 0.05]), created, resolved,
                        resolution, self.coordinator_on(team, created),
                        None if status == "To Do" and self.rng.random() < 0.5 else self.choice(self.developers),
                    ))
        self.work = pd.DataFrame(items)

    # ------------------------------------------------------------- test cases
    def test_cases(self):
        rows = []
        stories = self.work.loc[self.work["issue_type"] == "Story"]
        for key in self.projects["project_key"]:
            team = self.team_of[key]
            proj_stories = stories.loc[stories["project_key"] == key].sample(frac=1, random_state=int(self.rng.integers(1e9)))
            cover_pool = list(proj_stories.itertuples(index=False))
            cover_pool = cover_pool[: math.ceil(len(cover_pool) * 0.8)]
            next_story = 0
            for _ in range(TEST_CASES_PER_PROJECT[self.crit_of[key]]):
                test_type = self.choice(["Functional", "Regression", "Smoke", "E2E"], [0.45, 0.30, 0.10, 0.15])
                is_nrt = test_type in ("Regression", "Smoke") or (test_type == "E2E" and self.rng.random() < 0.5) \
                    or (test_type == "Functional" and self.rng.random() < 0.1)
                covered = None
                if test_type in ("Functional", "E2E") and self.rng.random() < 0.6 and cover_pool:
                    story = cover_pool[next_story % len(cover_pool)]
                    next_story += 1
                    covered = story.tmp_id
                    created = min(story.created.normalize() + pd.Timedelta(days=int(self.rng.integers(1, 11))), self.ref)
                elif self.rng.random() < 0.7:
                    created = self.rand_ts(pd.Timestamp("2024-06-01"), self.start - pd.Timedelta(days=1)).normalize()
                else:
                    created = self.rand_ts(self.start, self.ref - pd.Timedelta(days=20)).normalize()

                not_auto_p = 0.15 if test_type in ("Functional", "E2E") else 0.05
                auto_p = {"Functional": 0.30, "Regression": 0.60, "Smoke": 0.70, "E2E": 0.40}[test_type]
                r = self.rng.random()
                automation = "Not Automatable" if r < not_auto_p else "Automated" if r < not_auto_p + auto_p else "To Automate"
                automated_since = None
                if automation == "Automated":
                    if created < self.start - pd.Timedelta(days=1) and self.rng.random() < 0.6:
                        automated_since = self.rand_ts(created, self.start - pd.Timedelta(days=1), business=False).normalize()
                    else:
                        automated_since = self.rand_ts(max(created, self.start), self.ref, business=False).normalize()
                rows.append({
                    "project_key": key, "team_id": team,
                    "name": self.choice(TEST_TEMPLATES).format(f=self.choice(self.features[key])),
                    "test_type": test_type, "is_nrt": bool(is_nrt),
                    "priority": self.choice(["High", "Normal", "Low"], [0.25, 0.60, 0.15]),
                    "status": self.choice(["Approved", "Draft", "Deprecated"], [0.85, 0.08, 0.07]),
                    "automation_status": automation, "automated_since": automated_since, "covered_story_key": covered,
                    "created": created, "owner_id": self.choice(self.qa_members(team, created)),
                })
        tc = pd.DataFrame(rows).sort_values(["project_key", "created"], kind="stable", ignore_index=True)
        tc.insert(0, "test_case_key", tc["project_key"] + "-T" + (tc.groupby("project_key").cumcount() + 1).astype(str))
        self.tc = tc

    # ------------------------------------------------------------- executions
    def executions(self):
        rows = []
        pass_p = {STRONG_TEAM: 0.94, WEAK_TEAM: 0.76}
        for cycle in self.cycles.itertuples(index=False):
            team = self.team_of[cycle.project_key]
            pool = self.tc.loc[(self.tc["project_key"] == cycle.project_key) & (self.tc["status"] != "Draft")
                               & (self.tc["created"] <= cycle.planned_start)]
            if cycle.cycle_type == "NRT":
                pool = pool.loc[pool["is_nrt"]]
            elif cycle.cycle_type == "Smoke":
                pool = pool.loc[pool["test_type"] == "Smoke"]
            else:
                pool = pool.sample(n=min(len(pool), int(self.rng.integers(35, 56))), random_state=int(self.rng.integers(1e9)))
            weak = team == WEAK_TEAM
            not_exec = float(self.rng.uniform(0.02, 0.14) if weak else self.rng.uniform(0.0, 0.07))
            if cycle.cycle_type == "Functional":
                not_exec += 0.04
            blocked = 0.04 if weak else 0.02
            slip = int(self.rng.integers(1, 8)) if self.rng.random() < 0.25 else 0
            for t in pool.itertuples(index=False):
                r = self.rng.random()
                if r < not_exec:
                    status = "Not Executed"
                elif r < not_exec + blocked:
                    status = "Blocked"
                elif r < not_exec + blocked + 0.01:
                    status = "In Progress"
                else:
                    status = "Pass" if self.rng.random() < pass_p.get(team, 0.88) else "Fail"
                executed_on = None
                if status != "Not Executed":
                    executed_on = self.rand_ts(cycle.planned_start, cycle.planned_end + pd.Timedelta(days=slip, hours=23))
                ref_day = (executed_on or cycle.planned_start).normalize()
                automated = t.automated_since is not None and not pd.isna(t.automated_since) and t.automated_since <= ref_day
                mode = "Automated" if automated and self.rng.random() < 0.92 else "Manual"
                executed_by = None
                if executed_on is not None:
                    roles = ("Automation Engineer", "QA Engineer") if mode == "Automated" else ("QA Engineer", "QA Coordinator")
                    executed_by = self.choice(self.qa_members(team, executed_on, roles))
                reason = None
                if status == "Fail":
                    if mode == "Automated":
                        p = [0.35, 0.40, 0.15, 0.10] if weak else [0.50, 0.25, 0.15, 0.10]
                    else:
                        p = [0.65, 0.10, 0.15, 0.10]
                    reason = self.choice(["Product defect", "Test script issue", "Environment", "Test data"], p)
                rows.append({
                    "cycle_id": cycle.cycle_id, "test_case_key": t.test_case_key, "project_key": cycle.project_key,
                    "team_id": team, "status": status, "executed_on": executed_on, "executed_by": executed_by,
                    "execution_mode": mode, "failure_reason": reason, "defect_keys": [],
                    "_sort": executed_on if executed_on is not None else cycle.planned_end,
                    "_cycle_type": cycle.cycle_type,
                })
        ex = pd.DataFrame(rows).sort_values("_sort", kind="stable", ignore_index=True)
        ex.insert(0, "execution_id", [f"EX-{i:06d}" for i in range(1, len(ex) + 1)])
        self.ex = ex

    # ------------------------------------------------------------------- bugs
    def _bug(self, tmp_id, key, created, environment, labels, linked_execution_id=None):
        team = self.team_of[key]
        weak = team == WEAK_TEAM
        priority = self.choice(s.ISSUE_PRIORITIES, PROD_BUG_PRIORITY_P if environment == "PROD" else BUG_PRIORITY_P)
        age_ratio = (self.ref - created).days / max((self.ref - self.start).days, 1)
        resolved = None
        if self.rng.random() >= 0.12 + 0.2 * (1 - age_ratio):
            mean = RESOLUTION_MEAN_DAYS[priority] * TEAM_SPEED.get(team, 1.0)
            days = mean * float(self.rng.lognormal(0, 0.6)) / math.exp(0.18)
            candidate = created + pd.Timedelta(days=days)
            if candidate <= self.cap:
                resolved = candidate
        if resolved is not None:
            status = self.choice(["Closed", "Resolved"], [0.6, 0.4])
            resolution = self.choice(RESOLUTIONS[0], WEAK_RESOLUTIONS_P if weak else RESOLUTIONS[1])
        else:
            status, resolution = self.choice(*OPEN_STATUSES), None
        fix_version = None
        if resolution == "Fixed":
            nxt = self.releases.loc[(self.releases["project_key"] == key) & (self.releases["release_date"] >= resolved.normalize())]
            if not nxt.empty and nxt.iloc[0]["release_date"] <= self.ref:
                fix_version = nxt.iloc[0]["version"]
        due = None
        if self.rng.random() < 0.85:
            due = created.normalize() + pd.Timedelta(days=s.DUE_DATE_TARGET_DAYS[priority])
        return self._issue(
            tmp_id, key, "Bug", self.choice(BUG_TEMPLATES).format(f=self.choice(self.features[key]).capitalize()),
            status, priority, created, resolved, resolution, self.choice(self.qa_members(team, created)),
            None if status == "Open" and self.rng.random() < 0.3 else self.choice(self.developers),
            environment=environment, labels=labels, due_date=due, fix_version=fix_version,
            linked_execution_id=linked_execution_id,
            has_repro_steps=bool(self.rng.random() < (0.65 if weak else 0.88)),
            has_attachment=bool(self.rng.random() < (0.50 if weak else 0.72)),
        )

    def bugs(self):
        bugs = []
        defect_keys: dict[int, list[str]] = {}
        product_fails = self.ex.index[(self.ex["status"] == "Fail") & (self.ex["failure_reason"] == "Product defect")]
        env_by_cycle = {"NRT": (["PREPROD", "UAT"], [0.6, 0.4]), "Functional": (["SIT", "UAT"], [0.5, 0.5]),
                        "Smoke": (["PREPROD"], [1.0])}
        for idx in product_fails:
            row = self.ex.loc[idx]
            keys = []
            for _ in range(2 if self.rng.random() < 0.15 else 1):
                created = min(row["executed_on"] + pd.Timedelta(hours=float(self.rng.uniform(0.5, 48))), self.cap)
                tmp = f"B{len(bugs)}"
                labels = [self.features[row["project_key"]][0].split()[0].lower()]
                if row["_cycle_type"] == "NRT":
                    labels.insert(0, "regression")
                bugs.append(self._bug(tmp, row["project_key"], created, self.choice(*env_by_cycle[row["_cycle_type"]]),
                                      labels, linked_execution_id=row["execution_id"]))
                keys.append(tmp)
            defect_keys[idx] = keys
        self.ex["defect_keys"] = [defect_keys.get(i, []) for i in self.ex.index]

        # Free bugs: release peaks, quiet weekends and Christmas break.
        days = pd.date_range(self.start, self.ref, freq="D")
        base = np.where(days.dayofweek >= 5, 0.15, 1.0)
        xmas = ((days.month == 12) & (days.day >= 22)) | ((days.month == 1) & (days.day <= 2))
        base = np.where(xmas, base * 0.2, base)
        keys = list(self.projects["project_key"])
        weights = np.array([CRITICALITY_WEIGHT[self.crit_of[k]] * (1.3 if self.team_of[k] == WEAK_TEAM else 1.0) for k in keys])
        remaining = max(TOTAL_BUGS - len(bugs), 0)
        per_project = self.rng.multinomial(remaining, weights / weights.sum())
        for key, n in zip(keys, per_project):
            w = base.copy()
            for rel in self.releases.loc[self.releases["project_key"] == key, "release_date"]:
                w[(days >= rel - pd.Timedelta(days=14)) & (days < rel)] *= 3
            chosen = self.rng.choice(len(days), size=n, p=w / w.sum())
            prod_rate = PROD_RATE[self.crit_of[key]] * (1.4 if self.team_of[key] == WEAK_TEAM else 1.0)
            for d in chosen:
                created = days[d] + pd.Timedelta(minutes=int(self.rng.integers(8 * 60, 19 * 60)))
                env_p = np.array([0.15, 0.25, 0.30, 0.15]) * (1 - prod_rate) / 0.85
                env = self.choice(["DEV", "SIT", "UAT", "PREPROD", "PROD"], list(env_p) + [prod_rate])
                bugs.append(self._bug(f"B{len(bugs)}", key, min(created, self.cap), env,
                                      [self.features[key][0].split()[0].lower()]))
        self.bug_df = pd.DataFrame(bugs)

    def incidents(self):
        prod = self.bug_df.loc[self.bug_df["environment"] == "PROD"]
        w = prod["project_key"].map(lambda k: CRITICALITY_WEIGHT[self.crit_of[k]]).to_numpy()
        picks = self.rng.choice(len(prod), size=TOTAL_INCIDENTS, p=w / w.sum())
        rows = []
        for i, p in enumerate(picks):
            bug = prod.iloc[p]
            key, team = bug["project_key"], bug["team_id"]
            created = min(bug["created"] + pd.Timedelta(hours=float(self.rng.uniform(0, 24))), self.cap)
            resolved = created + pd.Timedelta(days=float(self.rng.uniform(0.1, 6)))
            if resolved > self.cap or self.rng.random() < 0.08:
                resolved, status, resolution = None, self.choice(["Open", "In Progress"], [0.4, 0.6]), None
            else:
                status, resolution = "Closed", "Fixed"
            rows.append(self._issue(
                f"I{i}", key, "Incident", self.choice(INCIDENT_TEMPLATES).format(f=self.choice(self.features[key])),
                status, self.choice(["Highest", "High"], [0.6, 0.4]), created, resolved, resolution,
                self.coordinator_on(team, created), self.choice(self.developers), environment="PROD",
                labels=["incident"], linked_issue_key=bug["tmp_id"],
            ))
        self.incident_df = pd.DataFrame(rows)

    # -------------------------------------------------------------- reporting
    def qa_reports(self):
        rows = []
        week = self.start + pd.Timedelta(days=(7 - self.start.dayofweek) % 7)
        while week + pd.Timedelta(days=7, hours=12) <= self.cap:
            due = week + pd.Timedelta(days=7, hours=12)
            for team in self.teams["team_id"]:
                on_time_p = {STRONG_TEAM: 0.99, WEAK_TEAM: 0.70}.get(team, 0.93)
                missing_p = 0.06 if team == WEAK_TEAM else 0.015
                r = self.rng.random()
                if r < missing_p:
                    submitted = None
                elif r < missing_p + on_time_p * (1 - missing_p):
                    submitted = due - pd.Timedelta(hours=float(self.rng.uniform(0.5, 72)))
                else:
                    submitted = min(due + pd.Timedelta(hours=float(self.rng.uniform(1, 96))), self.cap)
                rows.append({"report_id": f"QR-{len(rows) + 1:04d}", "team_id": team, "week_start": week, "due_date": due,
                             "submitted_at": submitted, "author_id": self.coordinator_on(team, week)})
            week += pd.Timedelta(days=7)
        self.reports = pd.DataFrame(rows)

    # ---------------------------------------------------------------- finalise
    def finalise_issues(self) -> pd.DataFrame:
        issues = pd.concat([self.work, self.bug_df, self.incident_df], ignore_index=True)
        issues = issues.sort_values(["project_key", "created"], kind="stable", ignore_index=True)
        issues["issue_key"] = issues["project_key"] + "-" + (issues.groupby("project_key").cumcount() + 1).astype(str)
        key_map = dict(zip(issues["tmp_id"], issues["issue_key"]))
        issues["linked_issue_key"] = issues["linked_issue_key"].map(key_map)
        self.ex["defect_keys"] = self.ex["defect_keys"].map(lambda ks: [key_map[k] for k in ks])
        self.tc["covered_story_key"] = self.tc["covered_story_key"].map(key_map)
        cols = ["issue_key", "project_key", "team_id", "issue_type", "summary", "status", "status_category", "priority",
                "assignee_id", "reporter_id", "created", "updated", "resolved", "due_date", "resolution", "labels",
                "environment", "fix_version", "linked_execution_id", "linked_issue_key", "has_repro_steps", "has_attachment"]
        return issues[cols]


def _as_datetime(df: pd.DataFrame, cols) -> pd.DataFrame:
    # Whole seconds, like Jira/Zephyr timestamps. Flooring keeps every ordering rule intact.
    for c in cols:
        df[c] = pd.to_datetime(df[c]).dt.floor("s")
    return df


def generate_dataset(seed: int = RANDOM_SEED, history_start: date = HISTORY_START,
                     reference_date: date = REFERENCE_DATE) -> Dataset:
    g = _Generator(seed, history_start, reference_date)
    g.reference_tables()
    g.releases_and_cycles()
    g.work_items()
    g.test_cases()
    g.executions()
    g.bugs()
    g.incidents()
    g.qa_reports()
    issues = g.finalise_issues()

    return Dataset(
        teams=g.teams,
        projects=g.projects,
        users=g.users,
        coordinator_assignments=g.assignments,
        issues=_as_datetime(issues, ["created", "updated", "resolved", "due_date"]),
        test_cases=_as_datetime(g.tc, ["automated_since", "created"]),
        test_cycles=g.cycles,
        test_executions=_as_datetime(g.ex.drop(columns=["_sort", "_cycle_type"]), ["executed_on"]),
        qa_reports=_as_datetime(g.reports, ["week_start", "due_date", "submitted_at"]),
        reference_date=reference_date,
    )
