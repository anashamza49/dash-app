"""KPI parameters. Every value here is documented in docs/kpi-definitions.md.

Change a business rule here (and in the document), never in the dashboard pages.
"""

from __future__ import annotations

# --- Issue types and categories -------------------------------------------
BUG_TYPE = "Bug"
STORY_TYPE = "Story"
INCIDENT_TYPE = "Incident"
DONE_CATEGORY = "Done"

ISSUE_PRIORITIES = ("Highest", "High", "Medium", "Low", "Lowest")
BUG_STATUSES = ("Open", "Reopened", "In Progress", "Blocked", "In Testing", "Resolved", "Closed")

# "Critical / Blocker bugs" (dashboard brief) has no documented mapping onto the
# Jira priority scale above. Leave as None until the business confirms it, for
# example ("Highest",). While None, the KPI is displayed as unresolved.
CRITICAL_PRIORITIES: tuple[str, ...] | None = None

# --- DM-09 Average resolution time ----------------------------------------
RESOLUTION_TIME_BUSINESS_DAYS = False
RESOLUTION_TIME_EXCLUDED_RESOLUTIONS: tuple[str, ...] = ()

# --- DM-10 Overdue bugs (placeholder targets, see data model) ---------------
DUE_DATE_TARGET_DAYS = {"Highest": 2, "High": 5, "Medium": 15, "Low": 30, "Lowest": 45}

# --- Test execution --------------------------------------------------------
EXECUTION_STATUSES = ("Pass", "Fail", "Blocked", "In Progress", "Not Executed")
# Add "Blocked" to count blocked runs as executed (open question 3).
EXECUTED_STATUSES: tuple[str, ...] = ("Pass", "Fail")
NRT_CYCLE_TYPE = "NRT"
# Date used by the date-range filter for Not Executed rows (no executed_on).
# The KPI document says "the cycle planned dates"; the POC uses planned_end.
NOT_EXECUTED_DATE_FIELD = "planned_end"

# --- Quality and coverage --------------------------------------------------
COVERAGE_TEST_CASE_STATUS = "Approved"  # QQ-01
INVALID_RESOLUTIONS = ("Duplicate", "Cannot Reproduce", "Not a Bug")  # QQ-02
COMPLETENESS_FIELDS = ("has_repro_steps", "has_attachment")  # QQ-02
ESCAPED_ENVIRONMENTS = ("PROD",)  # QQ-03
DEPRECATED_TEST_STATUS = "Deprecated"  # QQ-04
AUTOMATION_EXCLUDE_NOT_AUTOMATABLE = False  # QQ-04
STABILITY_FAILURE_REASONS = ("Test script issue", "Environment")  # QQ-05

# --- Targets and thresholds (placeholders) ---------------------------------
# "green"/"amber" are lower bounds when higher is better, upper bounds otherwise.
THRESHOLDS = {
    "TE-03": {"higher_is_better": True, "green": 0.95, "amber": 0.85},
    "TE-07": {"higher_is_better": True, "green": 0.95, "amber": 0.90},
    "TE-04": {"higher_is_better": True, "green": 0.90, "amber": 0.80},
    "QQ-03": {"higher_is_better": False, "green": 0.05, "amber": 0.10},
    "QQ-05": {"higher_is_better": True, "green": 0.95, "amber": 0.90},
    "QQ-07": {"higher_is_better": True, "green": 0.95, "amber": 0.85},
}
NRT_EXECUTION_TARGET = 0.95
