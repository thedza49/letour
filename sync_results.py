"""
Phase C results sync.

Run once a day during the Tour, roughly 2 hours after that day's stage
typically finishes (set up as a daily cron job - see README for the
crontab line). On each run it:

  1. Finds the current stage - the earliest seeded stage that hasn't
     already been marked results_synced.
  2. Scrapes that stage's results page on procyclingstats.com: finish
     order, DNF/DNS riders, and who holds each of the four
     classification jerseys (yellow/green/polka-dot/white) after the
     stage.
  3. Writes one StageResult row per rider matched against our Rider
     table (matched by pcs_url - riders not in our table, e.g. ones
     dropped from the startlist import, are skipped and logged).
  4. Calls app.scoring.score_stage() to compute every coach's points
     for that stage.
  5. Marks the stage results_synced = True, which unlocks transfers
     and captain picks for the NEXT stage (see Stage/get_current_stage
     in app/main.py).

Safe to re-run: if you re-run this for a stage that's already synced,
it does nothing (use --force to override - see below). If a run fails
partway through (network blip, PCS page not posted yet), nothing is
committed; just re-run it later, same command.

Usage:
    python3 sync_results.py                  # sync whatever stage is next
    python3 sync_results.py --stage 5         # force-sync a specific stage
    python3 sync_results.py --stage 5 --force # re-sync even if already synced

Requires the `procyclingstats` package (pip install procyclingstats).
"""
import argparse
import sys

from procyclingstats import Stage as PCSStage

from app.models import SessionLocal, Stage, Rider, StageResult
from app.scoring import score_stage

# procyclingstats race identifier slug for the 2026 Tour de France.
# Each stage's results page is at race/tour-de-france/2026/stage-N.
PCS_RACE_SLUG = "tour-de-france/2026"


def get_stage_to_sync(db, forced_stage_number=None):
    """Returns the Stage row to sync. By default, the earliest stage
    that hasn't been synced yet (mirrors get_current_stage() in
    app/main.py, so this script always targets the same stage the app
    is currently waiting on). --stage overrides that."""
    if forced_stage_number is not None:
        stage = db.query(Stage).filter(Stage.stage_number == forced_stage_number).first()
        if not stage:
            print(f"No stage {forced_stage_number} found in the database. Run seed_stages.py first.")
            sys.exit(1)
        return stage

    stage = (
        db.query(Stage)
        .filter(Stage.results_synced.is_(False))
        .order_by(Stage.stage_number)
        .first()
    )
    if not stage:
        print("Every seeded stage is already marked results_synced - nothing to sync.")
        sys.exit(0)
    return stage


def fetch_pcs_stage_data(stage_number):
    """Scrapes procyclingstats for one stage's results and jersey
    holders. Returns (results_rows, jerseys) where:

      results_rows is a list of dicts, one per rider, with keys:
        rider_url, rider_name, rank (int or None if DNF/DNS),
        did_not_finish (bool)

      jerseys is a dict mapping each of "yellow"/"green"/"polka_dot"/
      "white" to the rider_url of whoever holds it after this stage,
      or None if procyclingstats didn't have that classification for
      this race/stage (e.g. very early stages sometimes have no polka
      dot leader yet).

    Raises whatever exception procyclingstats / requests raises on a
    network or parsing failure - main() catches this and exits without
    writing anything, so a failed scrape never leaves partial data in
    the database.
    """
    stage_url = f"race/{PCS_RACE_SLUG}/stage-{stage_number}"
    pcs_stage = PCSStage(stage_url)

    raw_results = pcs_stage.results(
        "rider_url", "rider_name", "rank", "status"
    )

    results_rows = []
    for row in raw_results:
        # procyclingstats' status() returns "DF" for riders who finished
        # normally, and "DNF"/"DNS"/"OTL"/"DSQ" otherwise; rank() is None
        # for any non-finisher. We check both so a quirk in either field
        # alone can't misclassify a rider - if either says "didn't
        # finish", we treat it that way. The league's scoring rules don't
        # distinguish DNF/DNS/OTL/DSQ; they all score 0 finish points.
        status = (row.get("status") or "").strip().upper()
        rank = row.get("rank")
        finished = (status == "DF") and isinstance(rank, int)
        results_rows.append({
            "rider_url": row.get("rider_url"),
            "rider_name": row.get("rider_name"),
            "rank": rank if finished else None,
            "did_not_finish": not finished,
        })

    # Jersey holders: procyclingstats exposes these as separate small
    # classification tables on the same stage page (gc/points/kom/youth).
    # Each returns an empty list - rather than raising - when that
    # classification doesn't exist yet for this race/stage (e.g. no KOM
    # leader established on stage 1), so no try/except is needed here.
    jerseys = {"yellow": None, "green": None, "polka_dot": None, "white": None}

    gc = pcs_stage.gc("rider_url")
    if gc:
        jerseys["yellow"] = gc[0].get("rider_url")

    points = pcs_stage.points("rider_url")
    if points:
        jerseys["green"] = points[0].get("rider_url")

    kom = pcs_stage.kom("rider_url")
    if kom:
        jerseys["polka_dot"] = kom[0].get("rider_url")

    youth = pcs_stage.youth("rider_url")
    if youth:
        jerseys["white"] = youth[0].get("rider_url")

    return results_rows, jerseys


def write_stage_results(db, stage, results_rows, jerseys):
    """Writes one StageResult row per matched rider. Returns
    (matched_count, unmatched_names) so main() can report on riders
    that came back from PCS but don't exist in our Rider table (e.g.
    a late startlist addition we haven't re-imported yet)."""
    # Clear out any existing StageResult rows for this stage first, in
    # case this is a --force re-sync correcting earlier bad data.
    db.query(StageResult).filter(StageResult.stage_id == stage.id).delete()

    riders_by_pcs_url = {
        r.pcs_url: r for r in db.query(Rider).filter(Rider.pcs_url.isnot(None)).all()
    }

    matched_count = 0
    unmatched_names = []

    for row in results_rows:
        rider = riders_by_pcs_url.get(row["rider_url"])
        if not rider:
            unmatched_names.append(row["rider_name"])
            continue

        db.add(StageResult(
            stage_id=stage.id,
            rider_id=rider.id,
            finish_position=row["rank"],
            did_not_finish=row["did_not_finish"],
            holds_yellow=(row["rider_url"] == jerseys["yellow"]),
            holds_green=(row["rider_url"] == jerseys["green"]),
            holds_polka_dot=(row["rider_url"] == jerseys["polka_dot"]),
            holds_white=(row["rider_url"] == jerseys["white"]),
        ))
        matched_count += 1

    db.commit()
    return matched_count, unmatched_names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, default=None, help="Force-sync this stage number instead of the next pending one.")
    parser.add_argument("--force", action="store_true", help="Re-sync even if this stage is already marked results_synced.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stage = get_stage_to_sync(db, args.stage)

        if stage.results_synced and not args.force:
            print(f"Stage {stage.stage_number} is already synced. Use --force to re-sync it.")
            return

        print(f"Syncing stage {stage.stage_number} ({stage.date.strftime('%Y-%m-%d')})...")
        try:
            results_rows, jerseys = fetch_pcs_stage_data(stage.stage_number)
        except Exception as exc:
            print(f"Failed to fetch stage {stage.stage_number} from procyclingstats: {exc}")
            print("Nothing was written. This is normal if the stage hasn't finished or PCS hasn't posted results yet - just re-run this later.")
            sys.exit(1)

        if not results_rows:
            print(f"procyclingstats returned no results for stage {stage.stage_number} - it likely hasn't finished yet. Nothing written.")
            sys.exit(1)

        matched_count, unmatched_names = write_stage_results(db, stage, results_rows, jerseys)
        print(f"Wrote {matched_count} StageResult rows.")
        if unmatched_names:
            print(f"WARNING: {len(unmatched_names)} riders from PCS results weren't found in our Rider table (skipped):")
            for name in unmatched_names[:10]:
                print(f"  - {name}")
            if len(unmatched_names) > 10:
                print(f"  ...and {len(unmatched_names) - 10} more.")
            print("These riders won't score points for any coach until import_startlist.py is re-run to add them.")

        totals = score_stage(db, stage.id)
        print(f"Scored {len(totals)} coaches for stage {stage.stage_number}.")

        stage.results_synced = True
        db.commit()
        print(f"Stage {stage.stage_number} marked results_synced. Transfers/captain picks for the next stage are now unlocked.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
