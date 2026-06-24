"""
One-time migration: Phase B -> Phase C schema.

Phase C adds:
  - a new `stage_results` table (StageResult model)
  - a new `pcs_url` column on the existing `riders` table

IMPORTANT - run this BEFORE anything else after pulling Phase C code,
including before starting the app or running any other script. Here's
why: every script in this project (commissioner_tools.py, create_coaches.py,
the app itself, even this migration if it imported app.models the normal
way) loads `from app.models import ...`, and that import immediately runs
a query against the `riders` table to decide whether to seed placeholder
data. The new Rider model expects a `pcs_url` column. On an existing
Phase B database, that column doesn't exist yet - so the very act of
importing app.models would crash with "no such column: riders.pcs_url"
before any other code gets a chance to run, including a migration
script that tried to fix it the normal way.

To get around that chicken-and-egg problem, this script deliberately
does NOT import app.models. It connects to the database directly via
Python's built-in sqlite3 module, using the same DATABASE_URL your
app/.env already points at, and runs a raw ALTER TABLE. Only after
that succeeds is it safe for anything else (including this script's
own optional post-check) to import app.models.

This script is safe to re-run: it checks whether the column already
exists before trying to add it.

Usage: python3 migrate_to_phase_c.py
"""
import os
import sqlite3

from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), "app", ".env")
load_dotenv(_ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letour.db")


def _sqlite_path_from_url(database_url):
    """Turns a SQLAlchemy sqlite URL like sqlite:///./letour.db into a
    plain filesystem path sqlite3.connect() can use directly. This
    migration only supports SQLite (the only database this project
    uses) - if you've switched to Postgres or similar, you'll need to
    run the equivalent ALTER TABLE by hand instead."""
    if not database_url.startswith("sqlite:///"):
        raise ValueError(
            f"This migration only supports sqlite:/// URLs. Got: {database_url}. "
            "If you're running a different database, run the equivalent "
            "'ALTER TABLE riders ADD COLUMN pcs_url VARCHAR' (plus a unique "
            "index on that column) by hand instead."
        )
    return database_url.replace("sqlite:///", "", 1)


def main():
    db_path = _sqlite_path_from_url(DATABASE_URL)
    if not os.path.exists(db_path):
        print(f"No database file found at {db_path} - this looks like a fresh install.")
        print("Nothing to migrate; app/models.py will create the full Phase C schema (including pcs_url) automatically on first import.")
        return

    conn = sqlite3.connect(db_path)
    try:
        existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(riders)").fetchall()]

        if "pcs_url" in existing_columns:
            print("riders.pcs_url already exists - nothing to migrate.")
            return

        # SQLite doesn't allow a UNIQUE constraint inline on ALTER TABLE
        # ADD COLUMN, so this adds the plain column first, then a
        # separate unique index - functionally identical to what the
        # SQLAlchemy model declares (unique=True, nullable=True). SQLite's
        # unique indexes don't treat NULLs as duplicates of each other,
        # so every existing rider can keep pcs_url=NULL without conflict.
        conn.execute("ALTER TABLE riders ADD COLUMN pcs_url VARCHAR")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_riders_pcs_url ON riders (pcs_url)")
        conn.commit()
        print("Added riders.pcs_url column and unique index.")
    finally:
        conn.close()

    print("Phase C schema migration complete. It's now safe to run other scripts (commissioner_tools.py, the app itself, etc.) again.")
    print("Next: run `python3 import_startlist.py` once the 2026 startlist is published on procyclingstats.")


if __name__ == "__main__":
    main()



if __name__ == "__main__":
    main()
