"""Headless render of every dashboard page (Streamlit AppTest)."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest


def _page_script(view_name: str, db_path: str, empty: bool) -> None:
    import importlib
    from datetime import date
    from pathlib import Path

    from qa_dashboard.data.db import load_dataset
    from qa_dashboard.models import Filters

    ds = load_dataset(Path(db_path))
    if empty:
        f = Filters(date(2026, 1, 1), date(2026, 1, 1), teams=("TEAM-C",), priorities=("Lowest",), statuses=("Blocked",))
    else:
        f = Filters(date(2025, 11, 1), date(2026, 10, 31))
    importlib.import_module(f"ui.views.{view_name}").render(ds, f)


@pytest.mark.parametrize("empty", [False, True], ids=["full", "empty"])
@pytest.mark.parametrize("view", ["overview", "defects", "execution", "quality", "reference"])
def test_page_renders_without_error(view, empty, synthetic_db):
    at = AppTest.from_function(_page_script, args=(view, str(synthetic_db), empty), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
