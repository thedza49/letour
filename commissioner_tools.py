"""
Commissioner utility: view/edit stage lockout times, and mark riders
inactive (DNF/DNS) or active again.

Usage:
  python3 commissioner_tools.py stages              # list all stages
  python3 commissioner_tools.py set-lockout 5 "2026-07-08 13:00"   # stage 5 lockout at 13:00 UTC
  python3 commissioner_tools.py riders               # list all riders with active status
  python3 commissioner_tools.py deactivate 12         # mark rider id 12 inactive (DNF/DNS)
  python3 commissioner_tools.py activate 12           # mark rider id 12 active again
"""
import sys
from datetime import datetime
from app.models import SessionLocal, Stage, Rider


def list_stages(db):
    stages = db.query(Stage).order_by(Stage.stage_number).all()
    if not stages:
        print("No stages found. Run seed_stages.py first.")
        return
    for s in stages:
        locked = "LOCKED" if s.is_locked() else "open"
        synced = "synced" if s.results_synced else "pending"
        print(f"Stage {s.stage_number:>2} | {s.date.strftime('%Y-%m-%d')} | lockout {s.lockout_at} UTC | {locked} | results {synced}")


def set_lockout(db, stage_number, lockout_str):
    stage = db.query(Stage).filter(Stage.stage_number == int(stage_number)).first()
    if not stage:
        print(f"No stage {stage_number} found.")
        return
    stage.lockout_at = datetime.strptime(lockout_str, "%Y-%m-%d %H:%M")
    db.commit()
    print(f"Stage {stage_number} lockout set to {stage.lockout_at} UTC.")


def list_riders(db):
    riders = db.query(Rider).order_by(Rider.price.desc()).all()
    for r in riders:
        status = "ACTIVE" if r.is_active else "OUT (DNF/DNS)"
        print(f"#{r.id:<4} {r.name:<28} {r.team:<15} €{r.price:<6} {status}")


def set_active(db, rider_id, active):
    rider = db.query(Rider).filter(Rider.id == int(rider_id)).first()
    if not rider:
        print(f"No rider with id {rider_id} found.")
        return
    rider.is_active = active
    db.commit()
    state = "active" if active else "inactive (DNF/DNS)"
    print(f"Rider #{rider_id} ({rider.name}) marked {state}.")
    if not active:
        print("Coaches with this rider on their roster will see a 'needs replacement' prompt on My Team.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    db = SessionLocal()
    cmd = sys.argv[1]

    if cmd == "stages":
        list_stages(db)
    elif cmd == "set-lockout" and len(sys.argv) == 4:
        set_lockout(db, sys.argv[2], sys.argv[3])
    elif cmd == "riders":
        list_riders(db)
    elif cmd == "deactivate" and len(sys.argv) == 3:
        set_active(db, sys.argv[2], False)
    elif cmd == "activate" and len(sys.argv) == 3:
        set_active(db, sys.argv[2], True)
    else:
        print(__doc__)

    db.close()


if __name__ == "__main__":
    main()
