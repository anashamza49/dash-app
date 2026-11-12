"""Technical configuration of the POC (paths, reference period, seed).

Values come from docs/data-model.md, section "Reference period".
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "qa_dashboard.sqlite"

HISTORY_START = date(2025, 11, 1)
REFERENCE_DATE = date(2026, 10, 31)
RANDOM_SEED = 42
