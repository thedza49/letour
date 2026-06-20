"""
One-time migration: Phase A -> Phase B schema.

The old schema had a simple many-to-many `team_roster` table (no history).
Phase B replaces it with `team_riders`, which tracks added_date/dropped_date
so we get real transfer history going forward.

This script copies every rider currently on a coach's roster into the new
table as an "added today, never dropped" row, so nobody's existing draft
is lost when this deploys.

Usage: python3 migrate_to_phase_b.py
Safe to re-run - it skips any (user, rider) pair that's already migrated.
"""
from datetime import datetime
from sqlalchemy import text
from app.models import SessionLocal, TeamRider, engine


def main():
    db = SessionLocal()

    # Check whether the old team_roster table even exists (fresh installs
    # that started on Phase B schema won't have it).
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='team_roster'"
        ))
        old_table_exists = result.fetchone() is not None

    if not old_table_exists:
        print("No old team_roster table found - nothing to migrate.")
        db.close()
        return

    with engine.connect() as conn:
        old_rows = conn.execute(text("SELECT user_id, rider_id FROM team_roster")).fetchall()

    if not old_rows:
        print("team_roster table exists but is empty - nothing to migrate.")
        db.close()
        return

    migrated = 0
    skipped = 0
    for user_id, rider_id in old_rows:
        existing = (
            db.query(TeamRider)
            .filter(
                TeamRider.user_id == user_id,
                TeamRider.rider_id == rider_id,
                TeamRider.dropped_date.is_(None),
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        db.add(TeamRider(
            user_id=user_id,
            rider_id=rider_id,
            added_date=datetime.utcnow(),
            dropped_date=None,
        ))
        migrated += 1

    db.commit()
    db.close()
    print(f"Migration complete: {migrated} roster entries migrated, {skipped} already present.")
    print("The old team_roster table was left in place (untouched) in case you need to double-check anything.")


if __name__ == "__main__":
    main()
