"""
Seeds the 21 stages of the 2026 Tour de France (July 4-26, Barcelona to Paris)
with placeholder lockout times. Real ASO start times vary by stage (mountain
stages often start early afternoon, flat stages can start later) - this
seeds a simple default of 11:00 UTC on race day for every stage, which you
can adjust per-stage later with edit_stage.py once official start times
are confirmed closer to race day.

Rest days (no stage): July 13 and July 20, 2026.

Usage: python3 seed_stages.py
Safe to re-run - skips any stage_number that already exists.
"""
from datetime import datetime, timedelta, date
from app.models import SessionLocal, Stage

REST_DAYS = {date(2026, 7, 13), date(2026, 7, 20)}
START_DATE = date(2026, 7, 4)
DEFAULT_LOCKOUT_HOUR_UTC = 11  # placeholder - adjust per stage later


def main():
    db = SessionLocal()

    stage_num = 1
    d = START_DATE
    created = 0
    skipped = 0

    while stage_num <= 21:
        if d in REST_DAYS:
            d += timedelta(days=1)
            continue

        existing = db.query(Stage).filter(Stage.stage_number == stage_num).first()
        if existing:
            skipped += 1
        else:
            stage_date = datetime(d.year, d.month, d.day)
            lockout = stage_date.replace(hour=DEFAULT_LOCKOUT_HOUR_UTC)
            db.add(Stage(
                stage_number=stage_num,
                date=stage_date,
                lockout_at=lockout,
                results_synced=False,
            ))
            created += 1

        stage_num += 1
        d += timedelta(days=1)

    db.commit()
    db.close()
    print(f"Done: {created} stages created, {skipped} already existed.")
    print("Lockout times default to 11:00 UTC on race day - adjust with edit_stage.py as needed.")


if __name__ == "__main__":
    main()
