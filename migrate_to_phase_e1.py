"""
One-time migration: Phase C -> Phase E.1 schema.

Phase E.1 adds a new `rider_stage_results` table (RiderStageResult model)
- one row per (rider, stage) storing that rider's own point total for
the stage, independent of which coach (if any) rostered or captained
them. See the RiderStageResult docstring in app/models.py for the full
rationale; short version is this is the foundation the frontend
redesign needs for per-rider "last race" / "total points" displays on
Home, My Team, and Riders.

This migration is simpler than migrate_to_phase_c.py's column-add: a
brand new table doesn't have that script's chicken-and-egg problem
(there's no existing column for a normal `from app.models import ...`
to crash on), so this script imports app.models normally.
`Base.metadata.create_all()` - which already runs at the bottom of
models.py on import - creates the new table automatically. This
script's real job is the backfill step below.

Backfill: any stage already marked results_synced has StageResult rows
but, before this migration, no RiderStageResult rows (that table didn't
exist yet). This recomputes them by calling the same
app.scoring.score_stage() used for every live sync, so the backfilled
numbers are guaranteed to use the exact same point math as everything
else - rather than this script duplicating that logic and risking it
drifting out of sync later.

Safe to re-run: score_stage() already deletes-then-rewrites
RiderStageResult rows for a stage, so running this twice just
recomputes the same numbers.

Usage: python3 migrate_to_phase_e1.py
"""
from app.models import SessionLocal, Stage
from app.scoring import score_stage


def main():
    db = SessionLocal()
    try:
        synced_stages = (
            db.query(Stage)
            .filter(Stage.results_synced.is_(True))
            .order_by(Stage.stage_number)
            .all()
        )

        if not synced_stages:
            print("rider_stage_results table created (if it didn't already exist).")
            print("No stages are marked results_synced yet - nothing to backfill.")
            return

        print(f"rider_stage_results table created (if it didn't already exist).")
        print(f"Backfilling RiderStageResult rows for {len(synced_stages)} already-synced stage(s)...")
        for stage in synced_stages:
            totals = score_stage(db, stage.id)
            print(f"  Stage {stage.stage_number}: re-scored {len(totals)} coaches, RiderStageResult rows written.")

        print("Backfill complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
