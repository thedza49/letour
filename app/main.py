import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from app.models import Rider, User, SessionLocal, SALARY_CAP, ROSTER_SIZE
from app.auth import router as auth_router, get_current_user

load_dotenv()

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


@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    total_spent = sum(r.price for r in user.roster)
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "coach": user.team_name,
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(user.roster),
            "roster_size": ROSTER_SIZE,
        },
    )


@app.get("/riders")
async def riders_page(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    riders = db.query(Rider).order_by(Rider.price.desc()).all()
    total_spent = sum(r.price for r in user.roster)
    drafted_ids = {r.id for r in user.roster}

    return templates.TemplateResponse(
        request,
        "riders.html",
        {
            "coach": user.team_name,
            "riders": riders,
            "drafted_ids": drafted_ids,
            "total_spent": total_spent,
            "salary_cap": SALARY_CAP,
            "roster_count": len(user.roster),
            "roster_size": ROSTER_SIZE,
        },
    )


@app.post("/draft/{rider_id}")
async def draft_rider(rider_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if not rider:
        return RedirectResponse("/riders", status_code=303)

    already_drafted = any(r.id == rider.id for r in user.roster)
    over_budget = sum(r.price for r in user.roster) + rider.price > SALARY_CAP
    roster_full = len(user.roster) >= ROSTER_SIZE

    if not already_drafted and not over_budget and not roster_full:
        user.roster.append(rider)
        db.add(user)
        db.commit()

    return RedirectResponse("/riders", status_code=303)


@app.get("/my-team")
async def my_team(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    roster = user.roster
    total_cost = sum(r.price for r in roster)

    return templates.TemplateResponse(
        request,
        "my_team.html",
        {
            "coach": user.team_name,
            "roster": roster,
            "total_cost": total_cost,
            "salary_cap": SALARY_CAP,
            "roster_size": ROSTER_SIZE,
        },
    )


@app.post("/clear-team")
async def clear_team(request: Request, db: Session = Depends(get_db)):
    user = require_coach(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)

    user.roster = []
    db.commit()
    return RedirectResponse("/my-team", status_code=303)
