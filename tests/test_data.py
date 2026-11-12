"""Synthetic generator and SQLite layer."""

from __future__ import annotations

import pandas as pd

from qa_dashboard.data.db import load_dataset
from qa_dashboard.data.generator import generate_dataset
from qa_dashboard.data.validation import validate


def test_synthetic_data_respects_all_consistency_rules(synthetic):
    assert validate(synthetic) == []


def test_generation_is_reproducible(synthetic):
    again = generate_dataset()
    pd.testing.assert_frame_equal(synthetic.issues, again.issues)
    pd.testing.assert_frame_equal(synthetic.test_executions, again.test_executions)


def test_volumes_match_data_model(synthetic):
    assert len(synthetic.teams) == 5 and len(synthetic.projects) == 10 and len(synthetic.users) == 22
    assert synthetic.issues["issue_type"].value_counts().to_dict() == {"Bug": 850, "Story": 200, "Task": 80, "Incident": 70}
    assert 500 <= len(synthetic.test_cases) <= 700
    assert 2000 <= len(synthetic.test_executions) <= 3200
    assert 240 <= len(synthetic.qa_reports) <= 270
    assert (synthetic.projects.groupby("team_id").size() == 2).all()


def test_validation_detects_broken_rules(synthetic):
    issues = synthetic.issues.copy()
    issues.loc[issues.index[0], "project_key"] = "NOPE"
    broken = synthetic.__class__(**{**synthetic.__dict__, "issues": issues})
    assert any(e.startswith("Rule 1") for e in validate(broken))


def test_sqlite_round_trip(synthetic, synthetic_db):
    loaded = load_dataset(synthetic_db)
    assert validate(loaded) == []
    for name in ("issues", "test_cases", "test_executions", "qa_reports"):
        assert len(getattr(loaded, name)) == len(getattr(synthetic, name))
    assert loaded.test_executions["defect_keys"].map(len).sum() == synthetic.test_executions["defect_keys"].map(len).sum()
    assert pd.api.types.is_datetime64_any_dtype(loaded.issues["created"])
