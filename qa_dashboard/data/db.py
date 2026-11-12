"""SQLite schema (SQLAlchemy Core) and load/save of the Dataset.

Tables and columns follow docs/data-model.md. List fields (labels, defect_keys)
are stored as JSON text.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, MetaData, String, Table, Text, create_engine, event, select,
)
from sqlalchemy.engine import Engine

from ..config import DB_PATH, REFERENCE_DATE
from ..models import Dataset

metadata = MetaData()

teams = Table(
    "teams", metadata,
    Column("team_id", String, primary_key=True),
    Column("team_name", String, nullable=False),
    Column("location", String),
)

projects = Table(
    "projects", metadata,
    Column("project_key", String, primary_key=True),
    Column("project_name", String, nullable=False),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("project_type", String),
    Column("criticality", String),
)

users = Table(
    "users", metadata,
    Column("user_id", String, primary_key=True),
    Column("display_name", String, nullable=False),
    Column("role", String, nullable=False),
    Column("team_id", String, ForeignKey("teams.team_id")),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date),
)

coordinator_assignments = Table(
    "coordinator_assignments", metadata,
    Column("assignment_id", String, primary_key=True),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("user_id", String, ForeignKey("users.user_id"), nullable=False),
    Column("start_date", Date, nullable=False),
    Column("end_date", Date),
)

# linked_execution_id has no declared FK: issues and executions reference each
# other. The generator's validation checks it instead.
issues = Table(
    "issues", metadata,
    Column("issue_key", String, primary_key=True),
    Column("project_key", String, ForeignKey("projects.project_key"), nullable=False),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("issue_type", String, nullable=False),
    Column("summary", String),
    Column("status", String, nullable=False),
    Column("status_category", String, nullable=False),
    Column("priority", String, nullable=False),
    Column("assignee_id", String, ForeignKey("users.user_id")),
    Column("reporter_id", String, ForeignKey("users.user_id"), nullable=False),
    Column("created", DateTime, nullable=False),
    Column("updated", DateTime, nullable=False),
    Column("resolved", DateTime),
    Column("due_date", Date),
    Column("resolution", String),
    Column("labels", Text),
    Column("environment", String),
    Column("fix_version", String),
    Column("linked_execution_id", String),
    Column("linked_issue_key", String, ForeignKey("issues.issue_key")),
    Column("has_repro_steps", Boolean),
    Column("has_attachment", Boolean),
)

test_cases = Table(
    "test_cases", metadata,
    Column("test_case_key", String, primary_key=True),
    Column("project_key", String, ForeignKey("projects.project_key"), nullable=False),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("name", String),
    Column("test_type", String),
    Column("is_nrt", Boolean, nullable=False),
    Column("priority", String),
    Column("status", String, nullable=False),
    Column("automation_status", String, nullable=False),
    Column("automated_since", Date),
    Column("covered_story_key", String, ForeignKey("issues.issue_key")),
    Column("created", Date, nullable=False),
    Column("owner_id", String, ForeignKey("users.user_id"), nullable=False),
)

test_cycles = Table(
    "test_cycles", metadata,
    Column("cycle_id", String, primary_key=True),
    Column("project_key", String, ForeignKey("projects.project_key"), nullable=False),
    Column("name", String),
    Column("cycle_type", String, nullable=False),
    Column("version", String),
    Column("planned_start", Date, nullable=False),
    Column("planned_end", Date, nullable=False),
)

test_executions = Table(
    "test_executions", metadata,
    Column("execution_id", String, primary_key=True),
    Column("cycle_id", String, ForeignKey("test_cycles.cycle_id"), nullable=False),
    Column("test_case_key", String, ForeignKey("test_cases.test_case_key"), nullable=False),
    Column("project_key", String, ForeignKey("projects.project_key"), nullable=False),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("status", String, nullable=False),
    Column("executed_on", DateTime),
    Column("executed_by", String, ForeignKey("users.user_id")),
    Column("execution_mode", String, nullable=False),
    Column("failure_reason", String),
    Column("defect_keys", Text),
)

qa_reports = Table(
    "qa_reports", metadata,
    Column("report_id", String, primary_key=True),
    Column("team_id", String, ForeignKey("teams.team_id"), nullable=False),
    Column("week_start", Date, nullable=False),
    Column("due_date", DateTime, nullable=False),
    Column("submitted_at", DateTime),
    Column("author_id", String, ForeignKey("users.user_id"), nullable=False),
)

# Insertion order respects foreign keys.
TABLE_ORDER = (
    "teams", "projects", "users", "coordinator_assignments", "qa_reports",
    "issues", "test_cases", "test_cycles", "test_executions",
)
LIST_COLUMNS = {"issues": ("labels",), "test_executions": ("defect_keys",)}


def get_engine(db_path: Path = DB_PATH) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    return engine


def _to_python(value):
    """Convert pandas scalars to values SQLAlchemy's SQLite types accept."""
    if value is None or (not isinstance(value, (list, tuple)) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if hasattr(value, "item"):
        return value.item()
    return value


def _records(name: str, df: pd.DataFrame) -> list[dict]:
    table = metadata.tables[name]
    df = df.copy()
    for col in LIST_COLUMNS.get(name, ()):
        df[col] = df[col].map(lambda v: json.dumps(list(v)) if isinstance(v, (list, tuple)) else json.dumps([]))
    date_cols = [c.name for c in table.columns if isinstance(c.type, Date) and not isinstance(c.type, DateTime)]
    records = []
    for row in df[[c.name for c in table.columns]].to_dict(orient="records"):
        rec = {k: _to_python(v) for k, v in row.items()}
        for col in date_cols:
            if isinstance(rec[col], datetime):
                rec[col] = rec[col].date()
        records.append(rec)
    return records


def save_dataset(ds: Dataset, db_path: Path = DB_PATH) -> None:
    """Recreate the schema and write every table."""
    engine = get_engine(db_path)
    metadata.drop_all(engine)
    metadata.create_all(engine)
    with engine.begin() as conn:
        for name in TABLE_ORDER:
            df = getattr(ds, name)
            if name == "issues":
                # Incidents reference bugs: insert them after every other issue.
                df = df.sort_values("issue_type", key=lambda s: s.eq("Incident"), kind="stable")
            records = _records(name, df)
            if records:
                conn.execute(metadata.tables[name].insert(), records)
    engine.dispose()


def load_dataset(db_path: Path = DB_PATH, reference_date: date = REFERENCE_DATE) -> Dataset:
    """Read every table into DataFrames with datetime64 date columns."""
    engine = get_engine(db_path)
    frames: dict[str, pd.DataFrame] = {}
    with engine.connect() as conn:
        for name in TABLE_ORDER:
            table = metadata.tables[name]
            df = pd.read_sql(select(table), conn)
            for col in table.columns:
                if isinstance(col.type, (Date, DateTime)):
                    df[col.name] = pd.to_datetime(df[col.name])
                elif isinstance(col.type, Boolean):
                    df[col.name] = df[col.name].astype("boolean").fillna(False).astype(bool)
            for col in LIST_COLUMNS.get(name, ()):
                df[col] = df[col].map(lambda v: json.loads(v) if isinstance(v, str) else [])
            frames[name] = df
    engine.dispose()
    return Dataset(reference_date=reference_date, **frames)


def database_exists(db_path: Path = DB_PATH) -> bool:
    return db_path.exists() and db_path.stat().st_size > 0
