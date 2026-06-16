from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from app.models import Rider, SessionLocal
from app.auth import router as auth_router

app = FastAPI(title="LeTour Fantasy")

app.add_middleware(SessionMiddleware, secret_key="super-secret-letour-key")
app.include_router(auth_router)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user_id = request.session.get("user_id")
    
    if user_id:
        auth_buttons = """
            <a href="/my-team" class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700 border border-yellow-400">
                <div class="text-5xl mb-4">🏆</div>
                <h3 class="text-2xl font-bold text-yellow-400">My Team</h3>
            </a>
            <a href="/logout" class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700">
                <div class="text-5xl mb-4">🚪</div>
                <h3 class="text-2xl">Logout</h3>
            </a>
        """
    else:
        auth_buttons = """
            <a href="/register" class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700">
                <div class="text-5xl mb-4">👤</div>
                <h3 class="text-2xl">Register</h3>
            </a>
            <a href="/login" class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700">
                <div class="text-5xl mb-4">🔑</div>
                <h3 class="text-2xl">Login</h3>
            </a>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LeTour Fantasy</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-white min-h-screen">
        <div class="max-w-4xl mx-auto p-8">
            <h1 class="text-6xl font-bold text-yellow-400 text-center mb-6">🏆 LeTour Fantasy 2026</h1>
            <p class="text-center text-2xl mb-12">€100 Budget • 9 Riders • Daily Captain</p>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
                {auth_buttons}
                <a href="/riders" class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700">
                    <div class="text-5xl mb-4">🚴</div>
                    <h3 class="text-2xl">Browse Riders</h3>
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/riders", response_class=HTMLResponse)
async def riders_page():
    db = SessionLocal()
    riders = db.query(Rider).all()
    db.close()

    rows = "".join(f"""
        <tr class="border-b border-gray-700 hover:bg-gray-800">
            <td class="p-4">{r.name}</td>
            <td class="p-4 text-gray-400">{r.team}</td>
            <td class="p-4 font-bold text-yellow-400">€{r.price}</td>
            <td class="p-4 text-gray-400">#{r.uci_rank}</td>
        </tr>
    """ for r in riders)

    html = f"""
    <!DOCTYPE html>
    <html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-900 text-white">
    <div class="max-w-6xl mx-auto p-8">
        <h1 class="text-4xl font-bold text-yellow-400 mb-8">All Riders ({len(riders)} total)</h1>
        <table class="w-full"><thead><tr class="bg-gray-800">
            <th class="p-4 text-left">Rider</th><th class="p-4 text-left">Team</th>
            <th class="p-4 text-left">Price</th><th class="p-4 text-left">Rank</th>
        </tr></thead><tbody>{rows}</tbody></table>
        <a href="/" class="mt-8 inline-block text-yellow-400">← Home</a>
    </div></body></html>
    """
    return HTMLResponse(content=html)

@app.get("/my-team", response_class=HTMLResponse)
async def my_team(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)
        
    team_name = request.session.get("team_name", "My Team")
    
    html = f"""
    <html><head><script src="https://cdn.tailwindcss.com"></script></head><body class="bg-gray-900 text-white">
    <div class="max-w-6xl mx-auto p-8">
        <h1 class="text-4xl font-bold text-yellow-400 mb-8">{team_name}</h1>
        <div class="bg-gray-800 p-6 rounded-2xl mb-8 flex justify-between items-center">
            <div>
                <p class="text-xl">Budget Remaining: <span class="text-green-400 font-bold">€100.0</span> / €100.0</p>
                <p class="text-xl">Squad: <span class="text-white font-bold">0</span> / 9 Riders</p>
            </div>
            <a href="/riders" class="bg-yellow-400 text-black px-6 py-3 rounded-xl font-bold hover:bg-yellow-500">Draft Riders</a>
        </div>
        <div class="border-2 border-dashed border-gray-700 p-12 text-center rounded-2xl">
            <div class="text-6xl mb-4">🚳</div>
            <p class="text-gray-400 text-xl">Your squad is empty. Start drafting riders to build your team!</p>
        </div>
        <a href="/" class="mt-8 inline-block text-gray-400 hover:text-white">← Back to Home</a>
    </div></body></html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
