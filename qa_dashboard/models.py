"""Plain data containers shared by the data, KPI and UI layers."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class Dataset:
    """All entities of docs/data-model.md as DataFrames (dates as datetime64)."""

    teams: pd.DataFrame
    projects: pd.DataFrame
    users: pd.DataFrame
    coordinator_assignments: pd.DataFrame
    issues: pd.DataFrame
    test_cases: pd.DataFrame
    test_cycles: pd.DataFrame
    test_executions: pd.DataFrame
    qa_reports: pd.DataFrame
    reference_date: date


@dataclass(frozen=True)
class Filters:
    """Global dashboard filters. An empty tuple means "no restriction"."""

    start: date
    end: date
    teams: tuple[str, ...] = field(default_factory=tuple)
    projects: tuple[str, ...] = field(default_factory=tuple)
    priorities: tuple[str, ...] = field(default_factory=tuple)
    statuses: tuple[str, ...] = field(default_factory=tuple)

    def with_(self, **changes) -> "Filters":
        return replace(self, **changes)
