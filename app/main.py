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
    get_rider_season_points, get_rider_last_stage_points,
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
    """Returns the logged-in User row, or None if not authenticated.
    Looks up by id (Phase E.4) rather than team_name, so a coach
    renaming their team mid-session doesn't break their own login -
    see get_current_user() in app/auth.py for the full reasoning."""
    user_id = get_current_user(request)
    if not user_id:
        return None
    return db.query(User).filter(User.id == user_id).first()


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


def get_last_synced_stage(db):
    """Returns the most recently synced Stage (highest stage_number with
    results_synced=True), or None if no stage has synced yet. This is
    deliberately the opposite end from get_current_stage() (which finds
    the next UNsynced stage) - Home's redesigned "Live Updates" section
    wants to show what just happened (Stage Star, jersey winners), not
    what's coming up next."""
    return (
        db.query(Stage)
        .filter(Stage.results_synced.is_(True))
        .order_by(Stage.stage_number.desc())
        .first()
    )


def get_roster_leaderboard(db):
    """Returns coaches ranked by season point total, for Home's "Roster
    Leaderboard" table (Phase E.5/redesign - this is the query the
    README's Phase D notes flagged as needed: a per-User sum of
    DailyRoster.points, not just the logged-in coach's own total).
    Each entry is {user, daily, total} where daily is this coach's
    points on the most recently synced stage (0 if they have no
    DailyRoster row for it - e.g. no captain picked) and total is their
    full season sum. Sorted by total descending."""
    last_stage = get_last_synced_stage(db)

    entries = []
    for user in db.query(User).order_by(User.team_name).all():
        total = get_season_total(db, user.id)
        daily = 0.0
        if last_stage:
            row = (
                db.query(DailyRoster)
                .filter(DailyRoster.user_id == user.id, DailyRoster.stage_id == last_stage.id)
                .first()
            )
            if row and row.points is not None:
                daily = row.points
        entries.append({"user": user, "daily": daily, "total": total})

    entries.sort(key=lambda e: e["total"], reverse=True)
    return entries


def get_stage_star(db, stage):
    """Returns {"rider": Rider, "points": float} for whichever rider
    scored the most RiderStageResult points on the given stage (Phase
    E.1 data), or None if the stage has no RiderStageResult rows (not
    synced yet). Powers Home's "Stage Star" card."""
    if not stage:
        return None
    from app.models import RiderStageResult  # local import to avoid disturbing main.py's top-level import list

    row = (
        db.query(RiderStageResult)
        .filter(RiderStageResult.stage_id == stage.id)
        .order_by(RiderStageResult.points.desc())
        .first()
    )
    if not row:
        return None
    rider = db.query(Rider).filter(Rider.id == row.rider_id).first()
    if not rider:
        return None
    return {"rider": rider, "points": row.points}


def get_stage_jersey_winners(db, stage):
    """Returns {"yellow": Rider|None, "green": ..., "polka_dot": ...,
    "white": ...} for whoever held each classification after the given
    stage, by reading StageResult's holds_* flags. Powers Home's "Daily
    Jersey Winners" card. Any jersey not yet established (e.g. no KOM
    leader on stage 1) is None rather than guessed."""
    from app.models import StageResult  # local import, see get_stage_star() above

    winners = {"yellow": None, "green": None, "polka_dot": None, "white": None}
    if not stage:
        return winners

    results = db.query(StageResult).filter(StageResult.stage_id == stage.id).all()
    riders_by_id = {r.id: r for r in db.query(Rider).all()}

    for result in results:
        rider = riders_by_id.get(result.rider_id)
        if not rider:
            continue
        if result.holds_yellow:
            winners["yellow"] = rider
        if result.holds_green:
            winners["green"] = rider
        if result.holds_polka_dot:
            winners["polka_dot"] = rider
        if result.holds_white:
            winners["white"] = rider

    return winners


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

    last_synced_stage = get_last_synced_stage(db)
    leaderboard = get_roster_leaderboard(db)
    stage_star = get_stage_star(db, last_synced_stage)
    jersey_winners = get_stage_jersey_winners(db, last_synced_stage)

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "coach": user.team_name,
            "active_nav": "home",
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(roster),
            "roster_size": ROSTER_SIZE,
            "stage": stage,
            "needs_replacement": needs_replacement,
            "season_total": season_total,
            "last_synced_stage": last_synced_stage,
            "leaderboard": leaderboard,
            "stage_star": stage_star,
            "jersey_winners": jersey_winners,
        },
    )


RIDERS_PER_PAGE = 25


@app.get("/riders")
async def riders_page(
    request: Request,
    db: Session = Depends(get_db),
    q: str = "",
    team: str = "",
    sort: str = "price",
    direction: str = "desc",
    page: int = 1,
):
    """Phase E.2: search (q), team filter, sort, and pagination on top
    of the Phase E.1 per-rider points data. All via query params and a
    full page reload (simple form submit, no JS) per the agreed
    approach - keeps this reliable and easy to reason about rather than
    chasing live-filter edge cases.

    Sorting by last/total points can't be pushed into SQL (those are
    computed in Python from RiderStageResult, not a column on Rider),
    so this loads every rider, computes their points, then sorts and
    paginates in Python. Fine at today's ~123-rider scale; would need
    revisiting only if the rider pool grew by an order of magnitude.
    """
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    roster = get_active_roster(db, user.id)
    total_spent = sum(r.price for r in roster)
    drafted_ids = {r.id for r in roster}
    stage = get_current_stage(db)
    locked = stage.is_locked() if stage else False

    all_riders = db.query(Rider).all()

    # Distinct teams for the filter dropdown - computed from all riders
    # (not just the filtered set) so the dropdown's options don't shrink
    # as someone filters.
    all_teams = sorted({r.team for r in all_riders if r.team})

    # --- Filtering ---
    filtered = all_riders
    q_clean = q.strip()
    if q_clean:
        q_lower = q_clean.lower()
        filtered = [r for r in filtered if q_lower in r.name.lower()]
    if team:
        filtered = [r for r in filtered if r.team == team]

    # --- Per-rider points (needed before sorting, since last/total are
    # valid sort keys) ---
    rider_points = {
        r.id: {
            "last": get_rider_last_stage_points(db, r.id),
            "total": get_rider_season_points(db, r.id),
        }
        for r in filtered
    }

    # --- Sorting ---
    sort_keys = {
        "name": lambda r: r.name.lower(),
        "price": lambda r: r.price,
        "last": lambda r: (rider_points[r.id]["last"]["points"] if rider_points[r.id]["last"] else float("-inf")),
        "total": lambda r: rider_points[r.id]["total"],
    }
    sort = sort if sort in sort_keys else "price"
    direction = direction if direction in ("asc", "desc") else "desc"
    filtered.sort(key=sort_keys[sort], reverse=(direction == "desc"))

    # --- Pagination ---
    total_riders = len(filtered)
    total_pages = max(1, (total_riders + RIDERS_PER_PAGE - 1) // RIDERS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start = (page - 1) * RIDERS_PER_PAGE
    page_riders = filtered[start:start + RIDERS_PER_PAGE]

    return templates.TemplateResponse(
        request,
        "riders.html",
        {
            "coach": user.team_name,
            "active_nav": "riders",
            "riders": page_riders,
            "drafted_ids": drafted_ids,
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(roster),
            "roster_size": ROSTER_SIZE,
            "stage": stage,
            "locked": locked,
            "rider_points": rider_points,
            "all_teams": all_teams,
            "q": q_clean,
            "selected_team": team,
            "sort": sort,
            "direction": direction,
            "page": page,
            "total_pages": total_pages,
            "total_riders": total_riders,
        },
    )



@app.post("/draft/{rider_id}")
async def draft_rider(rider_id: int, request: Request, db: Session = Depends(get_db)):
    """Drafts a rider onto the coach's roster. return_to (a hidden form
    field carrying the current page's query string - see riders.html)
    lets this redirect back to wherever the coach was on the Riders
    page (a specific search/filter/sort/page) instead of always
    bouncing to page 1, which was disorienting when drafting from deep
    in a paginated list."""
    form = await request.form()
    return_to = form.get("return_to") or "/riders"

    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    stage = get_current_stage(db)
    if stage and stage.is_locked():
        # Transfers are frozen once the current stage has started.
        return RedirectResponse(return_to, status_code=303)

    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider or not rider.is_active:
        return RedirectResponse(return_to, status_code=303)

    roster = get_active_roster(db, user.id)
    already_drafted = any(r.id == rider.id for r in roster)
    over_budget = sum(r.price for r in roster) + rider.price > SALARY_CAP
    roster_full = len(roster) >= ROSTER_SIZE

    if not already_drafted and not over_budget and not roster_full:
        db.add(TeamRider(user_id=user.id, rider_id=rider.id, added_date=datetime.utcnow()))
        db.commit()

    return RedirectResponse(return_to, status_code=303)



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

    # Per-rider points (Phase E.1) and last-stage jersey (implementation
    # note in README: jersey badge always reflects last stage's holder,
    # not a separately-tracked "season leader") for each roster card.
    from app.models import StageResult  # local import, mirrors get_stage_star()/get_stage_jersey_winners() above
    last_synced_stage = get_last_synced_stage(db)

    rider_extra = {}
    for r in roster:
        jersey = None
        if last_synced_stage:
            result = (
                db.query(StageResult)
                .filter(StageResult.stage_id == last_synced_stage.id, StageResult.rider_id == r.id)
                .first()
            )
            if result:
                if result.holds_yellow:
                    jersey = "yellow"
                elif result.holds_green:
                    jersey = "green"
                elif result.holds_polka_dot:
                    jersey = "polka_dot"
                elif result.holds_white:
                    jersey = "white"
        rider_extra[r.id] = {
            "last": get_rider_last_stage_points(db, r.id),
            "total": get_rider_season_points(db, r.id),
            "jersey": jersey,
        }

    return templates.TemplateResponse(
        request,
        "my_team.html",
        {
            "coach": user.team_name,
            "active_nav": "my-team",
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
            "rider_extra": rider_extra,
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


@app.post("/team-name")
async def update_team_name(request: Request, db: Session = Depends(get_db)):
    """Phase E.4: lets a coach rename their own team. Safe to do at any
    time, including mid-stage - this is just a display label change,
    not a roster/transfer action, so it isn't gated by lockout. (This
    only works cleanly because Phase E.4 also switched session identity
    to user_id instead of team_name - see require_coach()/get_current_user()
    - otherwise renaming would log the coach out of their own session.)"""
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    new_name = (form.get("team_name") or "").strip()

    if new_name and new_name != user.team_name:
        user.team_name = new_name
        db.commit()

    return RedirectResponse("/my-team", status_code=303)
