from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.models import Rider, User, SessionLocal

app = FastAPI(title="LeTour Fantasy")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

# Helper to get the logged-in coach
def get_current_coach(request: Request):
    return request.session.get("coach")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    coach = get_current_coach(request)
    if coach:
        return f"""
        <script src="https://cdn.tailwindcss.com"></script>
        <body class="bg-gray-900 text-white min-h-screen flex flex-col items-center justify-center">
            <h1 class="text-6xl font-bold text-yellow-400 mb-6">Welcome, {coach}</h1>
            <div class="space-x-4">
                <a href="/riders" class="bg-blue-600 px-8 py-4 rounded-xl font-bold hover:bg-blue-500">Browse & Draft Riders</a>
                <a href="/my-team" class="bg-green-600 px-8 py-4 rounded-xl font-bold hover:bg-green-500">View My Team</a>
                <a href="/logout" class="bg-red-600 px-8 py-4 rounded-xl font-bold hover:bg-red-500">Logout</a>
            </div>
        </body>
        """
    return """
    <script src="https://cdn.tailwindcss.com"></script>
    <body class="bg-gray-900 text-white min-h-screen flex flex-col items-center justify-center">
        <h1 class="text-5xl font-bold mb-10">Select Your Coach</h1>
        <form action="/login" method="post" class="bg-gray-800 p-10 rounded-2xl">
            <select name="coach" class="text-black p-3 rounded mb-4 w-full">
                <option value="Team Dza">Team Dza</option>
                <option value="Team Blaster">Team Blaster</option>
                <option value="Team MP">Team MP</option>
            </select>
            <button type="submit" class="w-full bg-yellow-400 text-black p-3 rounded font-bold">Login</button>
        </form>
    </body>
    """

@app.post("/login")
async def login(request: Request, coach: str = Form(...)):
    request.session["coach"] = coach
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

@app.get("/riders", response_class=HTMLResponse)
async def riders_page(request: Request):
    coach = get_current_coach(request)
    if not coach: return RedirectResponse("/", status_code=303)
    db = SessionLocal()
    riders = db.query(Rider).all()
    db.close()
    
    rows = "".join(f"""
        <tr class="border-b border-gray-700">
            <td class="p-4">{r.name}</td>
            <td class="p-4">{r.price}</td>
            <td class="p-4"><form action="/draft/{r.id}" method="post"><button class="text-yellow-400">Draft</button></form></td>
        </tr>
    """ for r in riders)
    
    return f"""<script src="https://cdn.tailwindcss.com"></script>
    <body class="bg-gray-900 text-white p-10"><table class="w-full text-left">{rows}</table><a href="/" class="text-gray-400">Back</a></body>"""

@app.post("/draft/{rider_id}")
async def draft_rider(rider_id: int, request: Request):
    coach = get_current_coach(request)
    if not coach: return RedirectResponse("/", status_code=303)
    
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    if not user:
        user = User(team_name=coach)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    rider = db.query(Rider).filter(Rider.id == rider_id).first()
    
    # Calculate current roster total
    current_total = sum(r.price for r in user.roster)
    
    # Budget Logic: 150 cap
    if rider and rider not in user.roster and (current_total + rider.price <= 150.0):
        user.roster.append(rider)
        db.commit()
    
    db.close()
    return RedirectResponse("/my-team", status_code=303)


@app.get("/my-team", response_class=HTMLResponse)
async def my_team(request: Request):
    coach = get_current_coach(request)
    if not coach: return RedirectResponse("/", status_code=303)

    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    roster = user.roster if user else []
    total_cost = sum(r.price for r in roster)
    db.close()

    rows = "".join(f"<li class='p-2 border-b border-gray-700'>{r.name} - {r.price}</li>" for r in roster)
    
    return f"""<script src="https://cdn.tailwindcss.com"></script>
    <body class="bg-gray-900 text-white p-10">
        <h1 class='text-3xl font-bold mb-2'>{coach}'s Roster</h1>
        <div class='text-xl mb-5 text-yellow-400'>Budget Used: {total_cost}/150.0</div>
        <ul class='bg-gray-800 rounded p-4'>{rows or '<li>No riders drafted yet.</li>'}</ul>
        <a href='/riders' class='block mt-5 text-blue-400'>← Back to Draft</a>
    </body>"""

@app.post("/clear-team")
async def clear_team(request: Request):
    coach = get_current_coach(request)
    if not coach: return RedirectResponse("/", status_code=303)
    
    db = SessionLocal()
    user = db.query(User).filter(User.team_name == coach).first()
    if user:
        user.roster = [] # Clears the relationship
        db.commit()
    db.close()
    return RedirectResponse("/my-team", status_code=303)


