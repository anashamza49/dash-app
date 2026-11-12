"""Data access entry points used by the dashboard and the CLI."""

from __future__ import annotations

from pathlib import Path

from ..config import DB_PATH
from ..models import Dataset
from .db import database_exists, load_dataset, save_dataset
from .generator import generate_dataset
from .validation import validate


class DataValidationError(RuntimeError):
    pass


def build_database(db_path: Path = DB_PATH) -> Dataset:
    """Generate the synthetic dataset, validate it and write it to SQLite."""
    ds = generate_dataset()
    errors = validate(ds)
    if errors:
        raise DataValidationError("Synthetic data breaks consistency rules:\n- " + "\n- ".join(errors))
    save_dataset(ds, db_path)
    return ds


def get_dataset(db_path: Path = DB_PATH) -> Dataset:
    """Load the dataset from SQLite, building the database on first use."""
    if not database_exists(db_path):
        build_database(db_path)
    return load_dataset(db_path)
