"""Regenerate the synthetic SQLite database: python scripts/build_db.py"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qa_dashboard.config import DB_PATH  # noqa: E402
from qa_dashboard.data.repository import build_database  # noqa: E402


def main() -> None:
    ds = build_database(DB_PATH)
    print(f"Database written to {DB_PATH}")
    for name in ("teams", "projects", "users", "coordinator_assignments", "issues",
                 "test_cases", "test_cycles", "test_executions", "qa_reports"):
        print(f"  {name:<24} {len(getattr(ds, name)):>6} rows")
    print("  issue types:", ds.issues["issue_type"].value_counts().to_dict())


if __name__ == "__main__":
    main()
