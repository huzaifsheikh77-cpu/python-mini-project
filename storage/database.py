"""Database connection helpers for the Employee Payroll Management System.

The application reads its database configuration from environment variables
only. A local ``.env`` file is loaded when present (development convenience);
on Vercel the variables come from the project's Environment settings.

Supabase connection strings are normalised to the SQLAlchemy + psycopg (v3)
driver. Serverless deployments should use Supabase's transaction pooler
(port 6543) together with ``NullPool`` so that no connection is held between
invocations.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# override=False: real environment variables always win over .env
load_dotenv(PROJECT_ROOT / ".env", override=False)


class StorageError(RuntimeError):
    """Raised when the configured storage backend cannot complete an operation."""


def get_database_url():
    """Return the configured PostgreSQL URL, or an empty string."""

    return os.environ.get("DATABASE_URL", "").strip()


def normalise_url(url):
    """Convert a Supabase/Heroku style URL into a SQLAlchemy psycopg URL."""

    url = url.strip()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def is_sqlite_url(url):
    return normalise_url(url).startswith("sqlite")


def create_db_engine(url=None, **options) -> Engine:
    """Create a SQLAlchemy engine for PostgreSQL (Supabase) or SQLite."""

    raw_url = url if url else get_database_url()

    if not raw_url:
        raise StorageError(
            "DATABASE_URL is not set. Copy .env.example to .env and add your "
            "Supabase connection string, or set PAYROLL_STORAGE=csv to use "
            "the local CSV backend."
        )

    normalised = normalise_url(raw_url)

    engine_options = {
        "pool_pre_ping": True,
        "future": True,
    }

    if normalised.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
    else:
        # Serverless friendly: one short-lived connection per request.
        engine_options["poolclass"] = NullPool

    engine_options.update(options)

    engine = create_engine(normalised, **engine_options)

    if normalised.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine
