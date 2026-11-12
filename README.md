# QA KPI Dashboard — Streamlit POC

Proof of concept to replace the Power BI QA KPI dashboard with a lightweight Python dashboard
(Streamlit + Pandas + Plotly + SQLite). It runs locally on Windows with synthetic Jira/Zephyr-like data.
No real client data, person or credential is used.

## Quick start (Windows, PowerShell)

Requires Python 3.12.

```powershell
cd "path\to\dash-app"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The dashboard opens at <http://localhost:8501>. On first start the app generates the synthetic
database `data\qa_dashboard.sqlite` (about 10 seconds).

If you activate the virtual environment (`.\.venv\Scripts\Activate.ps1`), the short form works too:

```powershell
streamlit run app.py
```

Other commands:

```powershell
# Regenerate the synthetic database (fixed seed 42, reproducible)
.\.venv\Scripts\python.exe scripts\build_db.py

# Run the automated tests (KPI formulas, filters, data rules, page rendering)
.\.venv\Scripts\python.exe -m pytest
```

## What the dashboard shows

| Page | Content |
|---|---|
| Overview | Bug and test KPI cards, bug creation vs resolution, test results, team and project comparison tables |
| Defect Management | DM-01 to DM-10: status, priority, project and team distribution, trends, resolution time, overdue bugs |
| Test Execution | TE-01 to TE-09: execution and pass rates, results breakdown, weekly trend, NRT rate per cycle vs target |
| Quality & Coverage | QQ-01 to QQ-08: coverage, reporting quality, escape rate, production defects, automation, trends, retention |
| KPI reference | KPI catalogue with status, POC decisions, open business questions, active settings |

Interactions:

- Global sidebar filters: period, QA team, project, priority, bug status. Filters change the KPI
  calculations themselves, following the "Filter behaviour" table of the KPI document.
- Click bars (bug status, priority, project, team, test status, NRT cycle) to drill down into the records table.
- Every records table has an **Export CSV** button with the filtered rows.
- Each KPI card shows its ID and status badge (Standard / Provisional / Proxy / Unresolved). Hover a card
  for its definition notes. Coloured left borders use the placeholder RAG thresholds.

## Project structure

```text
app.py                      Streamlit entry point: navigation, data loading, global filters
qa_dashboard/               Business layer, no Streamlit import
  config.py                 Paths, reference period, random seed
  models.py                 Dataset and Filters containers
  filters.py                Scoping rules (date, project, team, priority, status)
  kpi_settings.py           Every KPI parameter (status lists, switches, thresholds)
  kpis.py                   One function per KPI ID of docs/kpi-definitions.md
  data/
    db.py                   SQLite schema (SQLAlchemy Core), save and load
    generator.py            Reproducible synthetic data (docs/data-model.md)
    validation.py           Consistency rules 1-12 of the data model
    repository.py           build_database() / get_dataset()
ui/                         Presentation layer
  theme.py                  Colours, chart style, CSS
  components.py             KPI cards, charts with drill-down, tables with CSV export
  filters.py                Sidebar filters
  views/                    One module per page
scripts/build_db.py         CLI to regenerate the database
tests/                      pytest suite
docs/                       Data model and KPI definitions (source of truth)
```

Architecture: synthetic data (later Jira/Zephyr connectors) → SQLite → pandas DataFrames → KPI layer → Streamlit.
KPIs are computed on the fly from the filtered records rather than stored pre-aggregated, so every
filter combination is exact and no KPI value is hardcoded. With a few thousand rows this takes milliseconds.

## Changing a business rule

Edit `qa_dashboard/kpi_settings.py` (parameters) or `qa_dashboard/kpis.py` (formulas), and update
`docs/kpi-definitions.md`. Never put business logic in `ui/`. Examples:

| Question | Setting |
|---|---|
| Count Blocked as executed? | `EXECUTED_STATUSES = ("Pass", "Fail", "Blocked")` |
| Define Critical / Blocker bugs | `CRITICAL_PRIORITIES = ("Highest",)` |
| Resolution time in business days | `RESOLUTION_TIME_BUSINESS_DAYS = True` |
| Exclude Duplicates from resolution time | `RESOLUTION_TIME_EXCLUDED_RESOLUTIONS = ("Duplicate",)` |
| Exclude Not Automatable from automation coverage | `AUTOMATION_EXCLUDE_NOT_AUTOMATABLE = True` |
| RAG thresholds and NRT target | `THRESHOLDS`, `NRT_EXECUTION_TARGET` |

## Known limitations and open points

- Most formulas are **Provisional** or **Proxy**: no official DAX measure was available. See the open
  questions at the end of `docs/kpi-definitions.md` (also shown on the KPI reference page).
- "Critical / Blocker bugs" has no documented definition and is displayed as *Not defined*.
- SLI-02 / SLI-04 are not defined; one provisional NRT execution rate (TE-07) stands in for them.
- Open/resolved use the current status (no Jira changelog history).
- QQ-01 and QQ-04 are current snapshots; the automation coverage trend applies today's Deprecated status.
- Data is synthetic, with a fixed reference date of 31 Oct 2026.
