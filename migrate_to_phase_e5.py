"""
One-time migration: adds route_name to the stages table (Phase E.5).

Phase E.5 adds a `route_name` column to Stage (e.g. "Nice to Col de la
Couillole") - the redesigned Home page wants to show this text, but
seed_stages.py only ever set stage_number and date.

Same chicken-and-egg problem as migrate_to_phase_c.py's pcs_url column:
every script that does `from app.models import ...` immediately queries
the riders table (to decide whether to seed placeholders), and that
import path also touches the stages table indirectly once anything
queries Stage. On an existing database, the new Stage model expects a
route_name column that doesn't exist yet - so a normal import would
crash before any migration code got a chance to run. This script
deliberately avoids `from app.models import ...` and talks to SQLite
directly instead, exactly like migrate_to_phase_c.py does.

Safe to re-run: checks whether the column already exists first.

Usage: python3 migrate_to_phase_e5.py
Run BEFORE import_stage_routes.py and before restarting the app.
"""
import os
import sqlite3

from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), "app", ".env")
load_dotenv(_ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letour.db")


def _sqlite_path_from_url(database_url):
    if not database_url.startswith("sqlite:///"):
        raise ValueError(
            f"This migration only supports sqlite:/// URLs. Got: {database_url}. "
            "If you're running a different database, run the equivalent "
            "'ALTER TABLE stages ADD COLUMN route_name VARCHAR' by hand instead."
        )
    return database_url.replace("sqlite:///", "", 1)


def main():
    db_path = _sqlite_path_from_url(DATABASE_URL)
    if not os.path.exists(db_path):
        print(f"No database file found at {db_path} - this looks like a fresh install.")
        print("Nothing to migrate; app/models.py will create the full schema (including route_name) automatically on first import.")
        return

    conn = sqlite3.connect(db_path)
    try:
        existing_columns = [row[1] for row in conn.execute("PRAGMA table_info(stages)").fetchall()]

        if "route_name" in existing_columns:
            print("stages.route_name already exists - nothing to migrate.")
            return

        conn.execute("ALTER TABLE stages ADD COLUMN route_name VARCHAR")
        conn.commit()
        print("Added stages.route_name column.")
    finally:
        conn.close()

    print("Migration complete. It's now safe to run other scripts (the app itself, etc.) again.")
    print("Next: run `python3 import_stage_routes.py` to populate stage names from procyclingstats.")


if __name__ == "__main__":
    main()
