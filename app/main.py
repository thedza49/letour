from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.models import Rider, User, SessionLocal

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

def get_current_coach(request: Request):
    return request.session.get("coach")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    coach = get_current_coach(request)
    if coach:
        return f"""
        <script src="https://cdn.tailwindcss.com"></script>
        <body class="bg-gray-900 text-white p-10 text-center">
            <h1 class="text-4xl">Logged in as {coach}</h1>
            <div class="mt-6"><a href="/riders" class="bg-blue-600 p-4 rounded">Draft Riders</a> <a href="/my-team" class="bg-green-600 p-4 rounded">My Team</a></div>
        </body>"""
    return """
    <script src="https://cdn.tailwindcss.com"></script>
    <body class="bg-gray-900 text-white p-10 text-center">
        <form action="/login" method="post">
            <select name="coach" class="text-black"><option>Team Dza</option><option>Team Blaster</option><option>Team MP</option></select>
            <button type="submit" class="bg-yellow-400 p-2 text-black">Login</button>
        </form>
    </body>"""

@app.post("/login")
async def login(request: Request, coach: str = Form(...)):
    request.session["coach"] = coach
    return RedirectResponse("/", status_code=303)

@app.get("/riders", response_class=HTMLResponse)
async def riders_page(request: Request):
    coach = get_current_coach(request)
    db = SessionLocal()
    riders = db.query(Rider).all()
    user = db.query(User).filter(User.team_name == coach).first()
    remaining = 150.0 - sum(r.price for r in (user.roster if user else []))
    db.close()
    
    rows = "".join(f"<tr><td class='p-2'>{r.name}</td><td class='p-2'>{r.rider_type}</td><td class='p-2'>{r.price}</td><td class='p-2'><form action='/draft/{r.id}' method='post'><button class='text-yellow-400'>Draft</button></form></td></tr>" for r in riders)
    return f"""<script src="https://cdn.tailwindcss.com"></script><body class="bg-gray-900 text-white p-10">
    <div class='mb-5'>Budget Left: {remaining:.1f}/150</div><table class='w-full'>{rows}</table><a href='/'>Back</a></body>"""

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
    db.close()
    rows = "".join(f"<li>{r.name} ({r.rider_type}) - {r.price}</li>" for r in roster)
    return f"""<script src="https://cdn.tailwindcss.com"></script><body class="bg-gray-900 text-white p-10">
    <h1>Your Team</h1><ul>{rows}</ul><form action='/clear-team' method='post'><button class='text-red-500'>Clear Team</button></form><a href='/riders'>Back</a></body>"""

@app.post("/clear-team")
async def clear_team(request: Request):
    coach = get_current_coach(request)
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    if user: user.roster = []
    db.commit()
    db.close()
    return RedirectResponse("/my-team", status_code=303)
