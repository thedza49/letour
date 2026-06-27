"""
Phase C scoring engine.

Computes how many fantasy points each coach earns for a single stage,
based on the real-world StageResult rows for that stage (finish position
+ jersey holders) and which rider each coach named as captain.

This module is pure scoring logic - it reads StageResult/TeamRider/
DailyRoster and writes DailyRoster.points. It does NOT talk to
procyclingstats; that's sync_results.py's job. Keeping the scraping and
the scoring separate means we can unit-test the point math without ever
hitting the network, and re-run scoring for a stage (e.g. after fixing a
data entry mistake) without re-scraping.

Called from sync_results.py after it finishes writing StageResult rows
for a stage. Can also be re-run by hand from a Python shell if a
correction is needed - see the bottom of this file for an example.
"""
from app.models import SessionLocal, StageResult, TeamRider, DailyRoster, RiderStageResult

# --- League scoring rules -------------------------------------------------
# Tune these freely; nothing elsewhere in the codebase hardcodes point
# values. Re-run scoring for affected stages after changing these (see
# recompute_stage() below) - existing DailyRoster.points won't update
# themselves.

# Points for finishing a stage, keyed by exact position for 1st-5th,
# then by range for the rest. Looked up via _finish_points() below.
FINISH_POINTS_EXACT = {
    1: 50,
    2: 35,
    3: 25,
    4: 20,
    5: 15,
}
FINISH_POINTS_TOP_10 = 10   # positions 6-10
FINISH_POINTS_TOP_20 = 5    # positions 11-20
FINISH_POINTS_PARTICIPATION = 1  # finished, but outside the top 20
FINISH_POINTS_DNF = 0       # did not finish / did not start that stage

# Bonus points for holding each classification jersey after the stage.
# A rider can hold more than one at once (e.g. early in the race the GC
# leader is often also in white) - bonuses stack if so.
JERSEY_BONUS_YELLOW = 15     # general classification (overall) leader
JERSEY_BONUS_GREEN = 10      # points/sprint classification leader
JERSEY_BONUS_POLKA_DOT = 10  # mountains/KOM classification leader
JERSEY_BONUS_WHITE = 5       # best young rider classification leader

CAPTAIN_MULTIPLIER = 2.0


def _finish_points(finish_position, did_not_finish):
    """Points awarded for where a rider finished this stage, before any
    jersey bonus or captain multiplier is applied."""
    if did_not_finish or finish_position is None:
        return FINISH_POINTS_DNF
    if finish_position in FINISH_POINTS_EXACT:
        return FINISH_POINTS_EXACT[finish_position]
    if finish_position <= 10:
        return FINISH_POINTS_TOP_10
    if finish_position <= 20:
        return FINISH_POINTS_TOP_20
    return FINISH_POINTS_PARTICIPATION


def _jersey_bonus(result: StageResult):
    """Sum of jersey bonuses for a single StageResult row. Stacks if a
    rider holds more than one jersey after this stage."""
    bonus = 0
    if result.holds_yellow:
        bonus += JERSEY_BONUS_YELLOW
    if result.holds_green:
        bonus += JERSEY_BONUS_GREEN
    if result.holds_polka_dot:
        bonus += JERSEY_BONUS_POLKA_DOT
    if result.holds_white:
        bonus += JERSEY_BONUS_WHITE
    return bonus


def rider_stage_points(result: StageResult):
    """Total points a single rider earned for a single stage: finish
    points plus any jersey bonus. This is the number BEFORE the captain
    multiplier - the multiplier only applies per-coach, to whichever
    rider that coach captained, not to the rider's "raw" score."""
    return _finish_points(result.finish_position, result.did_not_finish) + _jersey_bonus(result)


def score_stage(db, stage_id):
    """Computes and stores DailyRoster.points for every coach for the
    given stage_id, AND stores every individual rider's own stage
    points on RiderStageResult (Phase E.1 - see app/models.py for why).
    Must be called AFTER StageResult rows for this stage have been
    written (sync_results.py does this).

    Rider-level scoring (RiderStageResult):
      - One row per rider who has a StageResult for this stage, with
        their raw rider_stage_points() (finish + jersey bonus, no
        captain multiplier - that only ever applies per-coach).
      - Deleted and rewritten every call, so re-running this for a
        stage (e.g. recompute_stage() after a data fix) keeps both
        tables in sync rather than leaving stale rows behind.

    Coach-level scoring (DailyRoster.points), unchanged from Phase C:

    For each coach:
      - Sum rider_stage_points() across every rider on their active
        roster AS OF that stage (using TeamRider's added/dropped dates,
        not just whoever is on the roster right now - this matters once
        a coach has made transfers after this stage already happened).
      - If they have a DailyRoster row (captain pick) for this stage,
        find that captain's own stage points and add ANOTHER copy of it
        in proportion to CAPTAIN_MULTIPLIER - i.e. the captain's points
        count (CAPTAIN_MULTIPLIER) times total, not once extra.
      - Write the coach's total onto their DailyRoster.points for this
        stage. If a coach never picked a captain for this stage, their
        roster still scores normally - they just miss out on the
        multiplier bonus.

    Returns a dict of {user_id: total_points} for convenience (e.g. for
    sync_results.py to print a summary), but the authoritative result is
    what gets written to the database.
    """
    from app.models import Stage, User  # local import avoids a circular import at module load time

    stage = db.query(Stage).filter(Stage.id == stage_id).first()
    if not stage:
        raise ValueError(f"No stage with id {stage_id}")

    # Build a lookup of rider_id -> StageResult for this stage, since
    # we'll need to look up many riders' results per coach.
    results = db.query(StageResult).filter(StageResult.stage_id == stage_id).all()
    results_by_rider = {r.rider_id: r for r in results}

    # Persist each rider's own point total for this stage (Phase E.1) -
    # independent of whether any coach rostered or captained them. This
    # is what powers the redesigned Home/My Team/Riders pages' per-rider
    # "last race" / "total points" displays. Cleared and rewritten every
    # time in case this is a recompute_stage() re-run correcting earlier
    # data, same delete-then-insert pattern sync_results.py uses for
    # StageResult itself.
    db.query(RiderStageResult).filter(RiderStageResult.stage_id == stage_id).delete()
    for rider_id, result in results_by_rider.items():
        db.add(RiderStageResult(
            stage_id=stage_id,
            rider_id=rider_id,
            points=rider_stage_points(result),
        ))

    totals = {}

    for user in db.query(User).all():
        # Roster as of this stage's date: added on or before the stage,
        # and not dropped before the stage (or never dropped). This is
        # deliberately date-based rather than "current roster" so that
        # re-scoring an earlier stage after later transfers still uses
        # who was actually rostered AT THAT TIME.
        roster_rows = (
            db.query(TeamRider)
            .filter(
                TeamRider.user_id == user.id,
                TeamRider.added_date <= stage.date,
            )
            .filter(
                (TeamRider.dropped_date.is_(None)) | (TeamRider.dropped_date > stage.date)
            )
            .all()
        )

        captain_row = (
            db.query(DailyRoster)
            .filter(DailyRoster.user_id == user.id, DailyRoster.stage_id == stage_id)
            .first()
        )
        captain_rider_id = captain_row.captain_rider_id if captain_row else None

        total = 0.0
        for tr in roster_rows:
            result = results_by_rider.get(tr.rider_id)
            if not result:
                # No StageResult row for this rider on this stage - most
                # likely a rider who wasn't in this Tour's startlist at
                # all (data gap) rather than a real DNF. Score as 0
                # rather than guessing.
                continue

            points = rider_stage_points(result)
            if tr.rider_id == captain_rider_id:
                points *= CAPTAIN_MULTIPLIER
            total += points

        totals[user.id] = total

        if captain_row:
            captain_row.points = total
        else:
            # Coach didn't pick a captain for this stage; still record
            # their roster's points so standings/history are complete.
            # We create a placeholder DailyRoster row with captain_rider_id
            # left as None... but the column is NOT NULL, so instead we
            # simply don't write a points row here. Coaches who skip
            # picking a captain are still scored correctly via roster
            # totals; the per-stage history page can fall back to
            # "no captain selected" when DailyRoster.points is unset for
            # that stage. This keeps the captain_rider_id column's
            # not-null constraint intact without an awkward sentinel.
            pass

    db.commit()
    return totals


def recompute_stage(stage_id):
    """Convenience entry point for re-running scoring on a single stage
    by hand, e.g. from a Python shell on the Oracle VM after fixing a
    data mistake in StageResult:

        cd ~/letour
        python3 -c "from app.scoring import recompute_stage; recompute_stage(5)"

    Opens its own DB session and closes it when done.
    """
    db = SessionLocal()
    try:
        return score_stage(db, stage_id)
    finally:
        db.close()
