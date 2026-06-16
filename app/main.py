from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.models import Rider, User, SessionLocal

app = FastAPI(title="LeTour Fantasy")
app.add_middleware(SessionMiddleware, secret_key="super-secret-key")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    coach = request.session.get("coach")
    if coach:
        return f"""
        <body class="bg-gray-900 text-white p-10 text-center">
            <h1 class="text-4xl">Logged in as: <span class="text-yellow-400">{coach}</span></h1>
            <div class="mt-10 space-x-4">
                <a href="/riders" class="bg-blue-600 p-4 rounded">Draft Riders</a>
                <a href="/my-team" class="bg-green-600 p-4 rounded">View My Team</a>
                <a href="/logout" class="bg-red-600 p-4 rounded">Logout</a>
            </div>
        </body>
        """
    return """
    <body class="bg-gray-900 text-white p-10 text-center">
        <h1 class="text-4xl mb-10">Select Your Coach</h1>
        <form action="/login" method="post" class="space-x-4">
            <select name="coach" class="text-black p-2">
                <option value="Team Dza">Team Dza</option>
                <option value="Team Blaster">Team Blaster</option>
                <option value="Team MP">Team MP</option>
            </select>
            <button type="submit" class="bg-yellow-400 text-black px-4 py-2 font-bold">Login</button>
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

# ... (Keep your existing /riders, /draft, /drop, and /my-team functions here)
