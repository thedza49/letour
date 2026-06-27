"""
One-time cleanup: merges old placeholder riders into their real
imported counterparts.

Why this is needed: import_startlist.py matches existing riders by
pcs_url. Placeholder riders (the original 12 test riders) all have
pcs_url=NULL, so they can never match a real PCS row - even when it's
obviously the same person (e.g. placeholder "Tadej Pogacar" vs. real
"POGAČAR Tadej"). The import script knows this and deliberately keeps
any placeholder that's been drafted by a coach, rather than guessing
at a name match and risking a wrong merge - see the "Keeping
placeholder rider..." messages it printed.

That leaves you with two rows for the same real person: the old
placeholder (still referenced by that coach's TeamRider draft pick,
and possibly old fake StageResult/RiderStageResult/captain rows from
the Stage 1 test data) and the new real rider (with the correct
pcs_url, team, and price tier going forward).

This script merges each such pair by hand - it does NOT try to
pattern-match names automatically, because an automatic name-based
merge is exactly the kind of guess that could silently merge two
different people who happen to share a name. You tell it which
placeholder id merges into which real id via MERGE_PAIRS below, it
double-checks both ids exist and aren't the same row, then:

  1. Re-points every TeamRider.rider_id, RiderStageResult.rider_id,
     StageResult.rider_id, and DailyRoster.captain_rider_id reference
     from the placeholder's id onto the real rider's id.
  2. If that re-pointing would create a duplicate row that violates a
     unique constraint (e.g. both placeholder and real already have a
     StageResult or RiderStageResult for the same stage - possible
     leftover from Stage 1 test data), keeps the REAL rider's row and
     discards the placeholder's, rather than crashing.
  3. Deletes the now-unreferenced placeholder rider row.

Safe to re-run: skips any pair where the placeholder id no longer
exists (already merged).

Usage:
    python3 merge_placeholder_riders.py
"""
from app.models import (
    SessionLocal, Rider, TeamRider, RiderStageResult, StageResult, DailyRoster,
)

# (placeholder_id, real_id) - confirmed by hand from the duplicate-name
# check run after the first real import_startlist.py run. Update this
# list if you find more collisions after a later re-import.
MERGE_PAIRS = [
    (1, 95),   # Tadej Pogacar -> POGAČAR Tadej
    (2, 94),   # Jonas Vingegaard -> VINGEGAARD Jonas
    (3, 61),   # Remco Evenepoel -> EVENEPOEL Remco
    (4, 13),   # Jasper Philipsen -> PHILIPSEN Jasper
    (5, 15),   # Mathieu van der Poel -> VAN DER POEL Mathieu
    (8, 28),   # Richard Carapaz -> CARAPAZ Richard
]


def merge_one(db, placeholder_id, real_id):
    placeholder = db.query(Rider).filter(Rider.id == placeholder_id).first()
    real = db.query(Rider).filter(Rider.id == real_id).first()

    if not placeholder:
        print(f"  id={placeholder_id}: placeholder already gone - skipping (already merged?).")
        return
    if not real:
        print(f"  id={placeholder_id} -> id={real_id}: real rider id {real_id} not found - skipping, check MERGE_PAIRS.")
        return
    if placeholder_id == real_id:
        print(f"  id={placeholder_id}: same id on both sides - skipping.")
        return

    print(f"  Merging '{placeholder.name}' (id={placeholder_id}) -> '{real.name}' (id={real_id})...")

    # TeamRider: a coach's draft pick. Always safe to re-point - a coach
    # can't have drafted the same rider twice under two different ids
    # at once in practice, but guard anyway.
    moved = (
        db.query(TeamRider)
        .filter(TeamRider.rider_id == placeholder_id)
        .update({"rider_id": real_id})
    )
    if moved:
        print(f"    Re-pointed {moved} TeamRider row(s).")

    # DailyRoster.captain_rider_id: same idea, a coach's captain pick.
    moved = (
        db.query(DailyRoster)
        .filter(DailyRoster.captain_rider_id == placeholder_id)
        .update({"captain_rider_id": real_id})
    )
    if moved:
        print(f"    Re-pointed {moved} DailyRoster captain pick(s).")

    # RiderStageResult and StageResult both have a UNIQUE(stage_id,
    # rider_id) constraint, so re-pointing could collide if the real
    # rider already has a row for the same stage (e.g. leftover Stage 1
    # fake test data on both). Check per-stage and keep the real row,
    # discard the placeholder's, rather than crash.
    for model, label in [(RiderStageResult, "RiderStageResult"), (StageResult, "StageResult")]:
        placeholder_rows = db.query(model).filter(model.rider_id == placeholder_id).all()
        moved_count = 0
        dropped_count = 0
        for row in placeholder_rows:
            collision = (
                db.query(model)
                .filter(model.stage_id == row.stage_id, model.rider_id == real_id)
                .first()
            )
            if collision:
                db.delete(row)
                dropped_count += 1
            else:
                row.rider_id = real_id
                moved_count += 1
        if moved_count:
            print(f"    Re-pointed {moved_count} {label} row(s).")
        if dropped_count:
            print(f"    Dropped {dropped_count} {label} row(s) (real rider already had data for that stage).")

    db.delete(placeholder)
    print(f"    Deleted placeholder row id={placeholder_id}.")


def main():
    db = SessionLocal()
    try:
        print(f"Merging {len(MERGE_PAIRS)} placeholder/real rider pair(s)...")
        for placeholder_id, real_id in MERGE_PAIRS:
            merge_one(db, placeholder_id, real_id)
        db.commit()
        print("Done.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
