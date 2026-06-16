from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.models import Rider, User, SessionLocal

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

def get_current_coach(request: Request):
    return request.session.get("coach")

# This creates a shared navigation menu for all pages
def nav_bar():
    return """
    <nav class="bg-gray-800 p-4 mb-6 flex space-x-6 text-yellow-400 font-bold border-b border-gray-700">
        <a href="/">Home</a>
        <a href="/my-team">My Team</a>
        <a href="/riders">Browse Players</a>
    </nav>
    """

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    coach = get_current_coach(request)
    if not coach:
        return """<script src="https://cdn.tailwindcss.com"></script>
        <body class="bg-gray-900 text-white p-10"><form action="/login" method="post">
        <select name="coach" class="text-black"><option>Team Dza</option><option>Team Blaster</option><option>Team MP</option></select>
        <button type="submit" class="bg-yellow-400 p-2 text-black">Login</button></form></body>"""
    return f"""<script src="https://cdn.tailwindcss.com"></script><body class="bg-gray-900 text-white">
    {nav_bar()}<h1 class="p-10 text-4xl">Welcome, {coach}</h1></body>"""

@app.post("/login")
async def login(request: Request, coach: str = Form(...)):
    request.session["coach"] = coach
    return RedirectResponse("/", status_code=303)

@app.get("/riders", response_class=HTMLResponse)
async def riders_page(request: Request):
    db = SessionLocal()
    riders = db.query(Rider).all()
    coach = get_current_coach(request)
    user = db.query(User).filter(User.team_name == coach).first()
    total_spent = sum(r.price for r in (user.roster if user else []))
    db.close()
    rows = "".join(f"<tr><td class='p-2'>{r.name}</td><td class='p-2'>{r.rider_type}</td><td class='p-2'>{r.price}</td><td class='p-2'><form action='/draft/{r.id}' method='post'><button class='text-yellow-400'>Draft</button></form></td></tr>" for r in riders)
    return f"""<script src="https://cdn.tailwindcss.com"></script><body class="bg-gray-900 text-white">
    {nav_bar()}<div class='px-10'>Budget Used: {total_spent}/150</div>
    <table class='w-full mt-4'>{rows}</table></body>"""

@app.post("/draft/{rider_id}")
async def draft_rider(rider_id: int, request: Request):
    coach = get_current_coach(request)
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first() or User(team_name=coach)
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    if sum(r.price for r in user.roster) + rider.price <= 150.0:
        user.roster.append(rider)
        db.add(user)
        db.commit()
    db.close()
    return RedirectResponse("/my-team", status_code=303)

@app.get("/my-team", response_class=HTMLResponse)
async def my_team(request: Request):
    coach = get_current_coach(request)
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    roster = user.roster if user else []
    total_cost = sum(r.price for r in roster)
    db.close()
    rows = "".join(f"<li class='p-2'>{r.name} ({r.rider_type}) - {r.price}</li>" for r in roster)
    return f"""<script src="https://cdn.tailwindcss.com"></script><body class="bg-gray-900 text-white">
    {nav_bar()}<div class='px-10'><h1 class='text-2xl'>Your Roster</h1>
    <p>Total Team Cost: {total_cost}/150</p>
    <ul>{rows}</ul>
    <form action='/clear-team' method='post'><button class='text-red-500 mt-4'>Clear Team</button></form>
    </div></body>"""

@app.post("/clear-team")
async def clear_team(request: Request):
    coach = get_current_coach(request)
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    if user: user.roster = []
    db.commit()
    db.close()
    return RedirectResponse("/my-team", status_code=303)
