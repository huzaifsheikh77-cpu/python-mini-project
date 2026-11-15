import os

import pytest

from storage.backend import reset_store


@pytest.fixture(autouse=True)
def isolated_storage_backend(monkeypatch):
    """Keep every test away from any real database.

    When no dedicated test database is configured, the suite is pinned to the
    CSV backend and any DATABASE_URL from the developer's environment (or from
    .env) is ignored, so a stray run can never write to Supabase.
    """

    if not os.environ.get("PAYROLL_TEST_DATABASE_URL"):
        monkeypatch.setenv("PAYROLL_STORAGE", "csv")
        monkeypatch.delenv("DATABASE_URL", raising=False)

    reset_store()

    yield

    reset_store()
