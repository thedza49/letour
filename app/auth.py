from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models import User, SessionLocal

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request):
    """Returns the logged-in coach's team_name, or None."""
    return request.session.get("team_name")


@router.get("/login")
async def login_page(request: Request):
    if request.session.get("team_name"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"coach": None})


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""

    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"coach": None, "error": "Incorrect email or password."},
            status_code=401,
        )

    request.session["user_id"] = user.id
    request.session["team_name"] = user.team_name
    return RedirectResponse("/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
