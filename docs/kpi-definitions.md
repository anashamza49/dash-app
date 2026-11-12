# KPI definitions

This document defines every KPI shown in the QA dashboard POC. The Streamlit POC implements each formula in one module (`qa_dashboard/kpis.py`). Parameters such as status lists, target days and thresholds live in one settings module (`qa_dashboard/kpi_settings.py`). To change a formula, edit those two files and this document. Do not edit the dashboard pages (`ui/views/`).

Status: draft for review (Phase 2).

## Status of each definition

Each KPI has one of these statuses:

| Status | Meaning |
|---|---|
| Standard | Plain count or ratio that follows directly from Jira or Zephyr fields. Little room for interpretation. |
| Provisional | A business definition exists in the original dashboard but was not available for the POC. The formula here is a reasonable placeholder and must be checked. |
| Proxy | The original source data does not exist in the POC. The KPI is computed from a synthetic supporting dataset. |

No official formula from the Power BI dashboard was available while this document was written. Any formula marked Standard only reflects common Jira and Zephyr usage, so it still needs confirming against the original DAX measures.

## Filter behaviour

Global filters are date range, project, QA team, priority and status.

| Filter | Issue KPIs | Test KPIs | Quality KPIs |
|---|---|---|---|
| Date range | Applied to `created`. Exceptions are noted below. | Applied to `executed_on`, or to the cycle planned dates for not-executed rows | Depends on the KPI, see each definition |
| Project | Yes | Yes | Yes |
| QA team | Yes | Yes | Yes |
| Priority | Yes | No. Test priority uses a different scale. | Bug-based KPIs only |
| Status | Yes | No. Test statuses differ from issue statuses. | Bug-based KPIs only |

Assumption: like a typical Power BI model with one active relationship from a date table to `created`, issue KPIs count the bugs created within the selected range. Trend charts are the exception. They plot created bugs by `created` and resolved bugs by `resolved`, which corresponds to a second, inactive relationship activated with USERELATIONSHIP in DAX. Please confirm which date the original model used.

## A. Defect management

All KPIs in this section count issues with `issue_type = Bug`.

| ID | KPI | Formula | Status |
|---|---|---|---|
| DM-01 | Total bugs | Count of bugs created in range | Standard |
| DM-02 | Open bugs | Count of bugs created in range where status_category is not Done | Standard |
| DM-03 | Resolved bugs | Count of bugs created in range where status_category is Done | Standard |
| DM-04 | Bugs by priority | DM-01 grouped by priority | Standard |
| DM-05 | Bugs by status | DM-01 grouped by status | Standard |
| DM-06 | Bugs by project and team | DM-01 grouped by project and by team | Standard |
| DM-07 | Bug creation trend | Count of bugs by week of `created` | Standard |
| DM-08 | Bug resolution trend | Count of bugs by week of `resolved`, for bugs resolved in range | Standard |
| DM-09 | Average resolution time | Mean of (`resolved` minus `created`) in calendar days, for bugs resolved in range | Provisional |
| DM-10 | Overdue bugs | Count of bugs where status_category is not Done and `due_date` is before the reference date | Provisional |

Notes:

- DM-02 and DM-03 open the question of whether "open" means the current status or the status at the end of the selected range. The POC uses the current status, which is simpler and matches a model refreshed from Jira every day. Historical snapshots would need status history (Jira changelog), which is out of scope for the POC.
- DM-09 uses calendar days. The original may have used business days or excluded some resolutions (for example Duplicate). The settings module has a switch for both.
- DM-10 ignores bugs with no due date. Due dates are created plus a target by priority (see data model). Resolved bugs that missed their due date are reported separately as "Resolved late" (DM-11, provisional) if needed.

## B. Test execution and NRT

All KPIs in this section count test executions. A row is one planned run of one test case in one cycle.

Definitions used below:

- Planned: all executions in scope, whatever their status.
- Executed: status in `EXECUTED_STATUSES`. The default is Pass and Fail.
- Blocked: status Blocked. By default it counts as not executed, which is the usual Zephyr reading. This is a setting, so it can be switched if the original counted Blocked as executed.

| ID | KPI | Formula | Status |
|---|---|---|---|
| TE-01 | Total test executions | Count of planned executions in scope | Standard |
| TE-02 | Results breakdown | Count by status: Pass, Fail, Blocked, In Progress, Not Executed | Standard |
| TE-03 | Test execution rate | Executed / Planned | Provisional |
| TE-04 | Pass rate | Pass / Executed | Standard |
| TE-05 | Fail rate | Fail / Executed | Standard |
| TE-06 | Blocked tests | Count of Blocked | Standard |
| TE-07 | NRT execution rate | Executed / Planned, restricted to cycles with `cycle_type = NRT` | Provisional |
| TE-08 | Execution trend | TE-02 by week of `executed_on` | Standard |
| TE-09 | Results by project and team | TE-02, TE-03 and TE-04 grouped by project and by team | Standard |

Notes on TE-07 (SLI-02 and SLI-04): the original dashboard refers to SLI-02 and SLI-04. Their exact definitions and targets were not available. The POC exposes one NRT execution rate and a configurable target (placeholder: 95%). Once the SLI definitions are known, they can be added as two separate KPIs in `kpis.py` without changing the dashboards' structure.

## C. QA quality and coverage

| ID | KPI | Formula | Status |
|---|---|---|---|
| QQ-01 | Test coverage | Stories in scope with at least one Approved test case covering them / Stories in scope | Provisional |
| QQ-02 | Bug reporting quality | Valid and complete bugs / Bugs reported in range | Provisional |
| QQ-03 | Defect escape rate | Bugs with `environment = PROD` / All bugs, both created in range | Provisional |
| QQ-04 | Automation coverage | Test cases with automation_status Automated / Active test cases (status not Deprecated) | Provisional |
| QQ-05 | Automation stability | 1 minus (automated Fail runs with reason Test script issue or Environment / executed automated runs), for runs in range | Provisional |
| QQ-06 | Production incidents | Count of issues with `issue_type = Incident` created in range | Standard |
| QQ-07 | Reporting timeliness | Weekly reports submitted on or before their due date / Reports due in range | Proxy |
| QQ-08 | QA coordinator retention | Coordinators assigned at the start of the range who are still assigned at the end / Coordinators assigned at the start | Proxy |

Notes:

- QQ-01 is requirement coverage (stories with tests), not code coverage. Code coverage data was not part of the original sources as far as the brief describes.
- QQ-02 counts a bug as valid if its resolution is not Duplicate, Cannot Reproduce or Not a Bug. It counts a bug as complete if it has reproduction steps and an attachment. Both lists are settings. The original dashboard may have used a scoring grid instead of a pass or fail check.
- QQ-03 treats every PROD bug as escaped. A stricter version would count only bugs found after the related release went live. That needs release dates per bug, which the POC does not model.
- QQ-04 includes Not Automatable test cases in the denominator. Excluding them gives a higher figure. This is a setting.
- QQ-05 treats failures caused by product defects as correct test behaviour, so they do not lower stability. Only failures caused by the test or its environment count against it.
- QQ-07 and QQ-08 rely on supporting datasets that are themselves assumptions. Retention uses headcount at the start and end of the range. Turnover rate (leavers / average headcount) is the alternative.

## Composite views

The overview dashboard has two comparison tables ("QA performance by team" and "Project performance comparison"). They do not define new KPIs. Each row shows DM-01, DM-02, DM-09, DM-10, TE-03, TE-04 and QQ-03 for one team or project.

## Targets and thresholds

Colour thresholds on the dashboards come from the settings module. All values below are placeholders until the original targets are known.

| KPI | Green | Amber | Red |
|---|---|---|---|
| TE-03 Test execution rate | 95% or more | 85% to 95% | Below 85% |
| TE-07 NRT execution rate | 95% or more | 90% to 95% | Below 90% |
| TE-04 Pass rate | 90% or more | 80% to 90% | Below 80% |
| QQ-03 Defect escape rate | 5% or less | 5% to 10% | Above 10% |
| QQ-05 Automation stability | 95% or more | 90% to 95% | Below 90% |
| QQ-07 Reporting timeliness | 95% or more | 85% to 95% | Below 85% |

## Open questions for the business

1. Which date did the Power BI model use for issue KPIs: created, resolved or both?
2. What are the exact definitions and targets of SLI-02 and SLI-04?
3. Does the test execution rate count Blocked as executed?
4. How was bug reporting quality measured: a checklist, a score or rejected bugs?
5. Is defect escape rate based on environment, on found-after-release or on a dedicated Jira field?
6. Which source held weekly report submissions and coordinator assignments?
7. Were overdue bugs based on a Jira due date or on SLA targets by priority?
8. The dashboard brief asks for "Critical / Blocker bugs", but the priority scale is Highest to Lowest. Which priorities (or which other field) define them? Until confirmed, the POC shows this KPI as "Not defined" (setting `CRITICAL_PRIORITIES`).
9. For not-executed tests, which cycle date does the date filter use? The POC uses `planned_end` (setting `NOT_EXECUTED_DATE_FIELD`).
