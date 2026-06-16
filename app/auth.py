from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.models import User, SessionLocal

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/register", response_class=HTMLResponse)
async def register_page():
    html = """
    <html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-900 text-white">
    <div class="max-w-md mx-auto mt-20 p-8 bg-gray-800 rounded-2xl">
        <h2 class="text-3xl font-bold text-yellow-400 mb-6 text-center">Register</h2>
        <form method="post" action="/register">
            <input type="email" name="email" placeholder="Email" class="w-full p-3 mb-4 bg-gray-700 rounded" required><br>
            <input type="text" name="team_name" placeholder="Team Name" class="w-full p-3 mb-4 bg-gray-700 rounded" required><br>
            <input type="password" name="password" placeholder="Password" class="w-full p-3 mb-6 bg-gray-700 rounded" required><br>
            <button type="submit" class="w-full bg-yellow-400 text-black py-3 rounded font-bold">Create Account</button>
        </form>
        <p class="text-center mt-4"><a href="/login" class="text-yellow-400">Already have an account? Login</a></p>
        <p class="text-center mt-4"><a href="/" class="text-gray-400">← Home</a></p>
    </div>
    </body></html>
    """
    return HTMLResponse(content=html)

@router.post("/register")
async def register(
    email: str = Form(...), 
    team_name: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse("/register", status_code=303)

    hashed = pwd_context.hash(password)
    user = User(email=email, team_name=team_name, password_hash=hashed)
    db.add(user)
    db.commit()
    return RedirectResponse("/login", status_code=303)

@router.get("/login", response_class=HTMLResponse)
async def login_page():
    html = """
    <html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-900 text-white">
    <div class="max-w-md mx-auto mt-20 p-8 bg-gray-800 rounded-2xl">
        <h2 class="text-3xl font-bold text-yellow-400 mb-6 text-center">Login</h2>
        <form method="post" action="/login">
            <input type="email" name="email" placeholder="Email" class="w-full p-3 mb-4 bg-gray-700 rounded" required><br>
            <input type="password" name="password" placeholder="Password" class="w-full p-3 mb-6 bg-gray-700 rounded" required><br>
            <button type="submit" class="w-full bg-yellow-400 text-black py-3 rounded font-bold">Login</button>
        </form>
        <p class="text-center mt-4"><a href="/register" class="text-yellow-400">Need an account? Register</a></p>
        <p class="text-center mt-4"><a href="/" class="text-gray-400">← Home</a></p>
    </div>
    </body></html>
    """
    return HTMLResponse(content=html)

@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        return RedirectResponse("/login", status_code=303)

    request.session["user_id"] = user.id
    request.session["team_name"] = user.team_name
    return RedirectResponse("/my-team", status_code=303)

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
