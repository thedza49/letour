import os
from datetime import datetime
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models import (
    Rider, User, Stage, TeamRider, DailyRoster,
    SessionLocal, SALARY_CAP, ROSTER_SIZE, get_active_roster,
)
from app.auth import router as auth_router, get_current_user

# Load app/.env explicitly so this works regardless of which directory
# uvicorn is launched from.
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_PATH)

app = FastAPI()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Add a SECRET_KEY value to app/.env before starting the app."
    )
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(auth_router)

templates = Jinja2Templates(directory="app/templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_coach(request: Request, db: Session):
    """Returns the logged-in User row, or None if not authenticated."""
    team_name = get_current_user(request)
    if not team_name:
        return None
    return db.query(User).filter(User.team_name == team_name).first()


def get_current_stage(db):
    """Returns the next stage that hasn't had results synced yet, i.e. the
    stage coaches are currently prepping for or racing. Returns None if
    every seeded stage is already synced (season over) or no stages exist."""
    return (
        db.query(Stage)
        .filter(Stage.results_synced.is_(False))
        .order_by(Stage.stage_number)
        .first()
    )


def get_inactive_roster_riders(db, user_id):
    """Riders currently on a coach's roster who have been marked
    inactive (DNF/DNS) - these need to be replaced."""
    roster = get_active_roster(db, user_id)
    return [r for r in roster if not r.is_active]


def get_scoring_history(db, user_id):
    """Returns a list of {stage, points} for every synced stage this
    coach has a DailyRoster row for, ordered by stage number. Stages
    where the coach didn't pick a captain (and so has no DailyRoster
    row at all, per the scoring engine's design - see app/scoring.py)
    are omitted rather than shown as zero, since "no row" and "scored
    zero points" mean different things and conflating them would be
    misleading on the My Team history view."""
    rows = (
        db.query(DailyRoster)
        .join(Stage, DailyRoster.stage_id == Stage.id)
        .filter(DailyRoster.user_id == user_id, Stage.results_synced.is_(True))
        .order_by(Stage.stage_number)
        .all()
    )
    return [{"stage": row.stage, "points": row.points or 0.0} for row in rows]


def get_season_total(db, user_id):
    """Sum of points across every synced stage for this coach. Used on
    Home and My Team to show a running season total."""
    history = get_scoring_history(db, user_id)
    return sum(entry["points"] for entry in history)


@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    roster = get_active_roster(db, user.id)
    total_spent = sum(r.price for r in roster)
    stage = get_current_stage(db)
    needs_replacement = get_inactive_roster_riders(db, user.id)
    season_total = get_season_total(db, user.id)

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "coach": user.team_name,
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(roster),
            "roster_size": ROSTER_SIZE,
            "stage": stage,
            "needs_replacement": needs_replacement,
            "season_total": season_total,
        },
    )


@app.get("/riders")
async def riders_page(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    riders = db.query(Rider).order_by(Rider.price.desc()).all()
    roster = get_active_roster(db, user.id)
    total_spent = sum(r.price for r in roster)
    drafted_ids = {r.id for r in roster}
    stage = get_current_stage(db)
    locked = stage.is_locked() if stage else False

    return templates.TemplateResponse(
        request,
        "riders.html",
        {
            "coach": user.team_name,
            "riders": riders,
            "drafted_ids": drafted_ids,
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(roster),
            "roster_size": ROSTER_SIZE,
            "stage": stage,
            "locked": locked,
        },
    )


@app.post("/draft/{rider_id}")
async def draft_rider(rider_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    stage = get_current_stage(db)
    if stage and stage.is_locked():
        # Transfers are frozen once the current stage has started.
        return RedirectResponse("/riders", status_code=303)

    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider or not rider.is_active:
        return RedirectResponse("/riders", status_code=303)

    roster = get_active_roster(db, user.id)
    already_drafted = any(r.id == rider.id for r in roster)
    over_budget = sum(r.price for r in roster) + rider.price > SALARY_CAP
    roster_full = len(roster) >= ROSTER_SIZE

    if not already_drafted and not over_budget and not roster_full:
        db.add(TeamRider(user_id=user.id, rider_id=rider.id, added_date=datetime.utcnow()))
        db.commit()

    return RedirectResponse("/riders", status_code=303)


@app.post("/drop/{rider_id}")
async def drop_rider(rider_id: int, request: Request, db: Session = Depends(get_db)):
    """Drops a rider from the roster. Used both for voluntary drops (when
    unlocked) and for the forced replace-rider flow (when a rostered rider
    goes inactive, dropping them is always allowed even if the stage is
    locked, so the coach isn't stuck unable to fix their roster)."""
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    entry = (
        db.query(TeamRider)
        .filter(
            TeamRider.user_id == user.id,
            TeamRider.rider_id == rider_id,
            TeamRider.dropped_date.is_(None),
        )
        .first()
    )
    if not entry:
        return RedirectResponse("/my-team", status_code=303)

    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    stage = get_current_stage(db)
    is_forced_replacement = rider and not rider.is_active

    if stage and stage.is_locked() and not is_forced_replacement:
        # Voluntary drops are frozen once the stage starts; forced
        # replacements for an inactive rider are always allowed.
        return RedirectResponse("/my-team", status_code=303)

    entry.dropped_date = datetime.utcnow()
    db.commit()
    return RedirectResponse("/my-team", status_code=303)


@app.get("/my-team")
async def my_team(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    roster = get_active_roster(db, user.id)
    total_cost = sum(r.price for r in roster)
    stage = get_current_stage(db)
    locked = stage.is_locked() if stage else False
    needs_replacement = get_inactive_roster_riders(db, user.id)
    season_total = get_season_total(db, user.id)
    scoring_history = get_scoring_history(db, user.id)

    current_captain_id = None
    if stage:
        captain_row = (
            db.query(DailyRoster)
            .filter(DailyRoster.user_id == user.id, DailyRoster.stage_id == stage.id)
            .first()
        )
        if captain_row:
            current_captain_id = captain_row.captain_rider_id

    return templates.TemplateResponse(
        request,
        "my_team.html",
        {
            "coach": user.team_name,
            "roster": roster,
            "total_cost": total_cost,
            "salary_cap": SALARY_CAP,
            "roster_size": ROSTER_SIZE,
            "stage": stage,
            "locked": locked,
            "current_captain_id": current_captain_id,
            "needs_replacement": needs_replacement,
            "season_total": season_total,
            "scoring_history": scoring_history,
        },
    )


@app.post("/captain/{rider_id}")
async def set_captain(rider_id: int, request: Request, db: Session = Depends(get_db)):
    """Sets the captain (2x multiplier) for the current stage. Locked once
    that stage starts, same as transfers."""
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    stage = get_current_stage(db)
    if not stage or stage.is_locked():
        return RedirectResponse("/my-team", status_code=303)

    roster = get_active_roster(db, user.id)
    if not any(r.id == rider_id for r in roster):
        # Can only captain a rider that's actually on your roster.
        return RedirectResponse("/my-team", status_code=303)

    existing = (
        db.query(DailyRoster)
        .filter(DailyRoster.user_id == user.id, DailyRoster.stage_id == stage.id)
        .first()
    )
    if existing:
        existing.captain_rider_id = rider_id
    else:
        db.add(DailyRoster(user_id=user.id, stage_id=stage.id, captain_rider_id=rider_id))
    db.commit()

    return RedirectResponse("/my-team", status_code=303)


@app.post("/clear-team")
async def clear_team(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    now = datetime.utcnow()
    db.query(TeamRider).filter(
        TeamRider.user_id == user.id, TeamRider.dropped_date.is_(None)
    ).update({"dropped_date": now})
    db.commit()
    return RedirectResponse("/my-team", status_code=303)
