"""Storage backend selection.

``PAYROLL_STORAGE`` chooses the backend explicitly:

    PAYROLL_STORAGE=csv        local CSV files in data/
    PAYROLL_STORAGE=database   Supabase PostgreSQL (requires DATABASE_URL)

When the variable is absent, PostgreSQL is used as soon as ``DATABASE_URL``
is set, otherwise the project falls back to CSV so it still runs offline.
"""

import os

from storage.csv_manager import CSVManager
from storage.database import StorageError, get_database_url


_STORE = None

DATABASE_CHOICES = {"database", "db", "postgres", "postgresql"}


def build_store():
    """Create the store described by the current environment."""

    choice = os.environ.get("PAYROLL_STORAGE", "").strip().lower()

    if choice == "csv":
        return CSVManager()

    if choice in DATABASE_CHOICES:
        from storage.database_store import DatabaseStore

        return DatabaseStore()

    if get_database_url():
        from storage.database_store import DatabaseStore

        return DatabaseStore()

    return CSVManager()


def get_store():
    global _STORE

    if _STORE is None:
        _STORE = build_store()

    return _STORE


def set_store(store):
    """Override the active store (used by the database tests)."""

    global _STORE
    _STORE = store


def reset_store():
    global _STORE
    _STORE = None


def init_storage():
    return get_store().initialize_files()


def storage_backend_name():
    return getattr(get_store(), "name", "csv")


__all__ = [
    "StorageError",
    "build_store",
    "get_store",
    "set_store",
    "reset_store",
    "init_storage",
    "storage_backend_name",
]
