from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="LeTour Fantasy")

@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
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
                <div class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700 cursor-pointer">
                    <div class="text-5xl mb-4">📋</div>
                    <h3 class="text-2xl font-semibold">My Team</h3>
                    <p class="text-gray-400 mt-2">Build & Manage</p>
                </div>
                <div class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700 cursor-pointer">
                    <div class="text-5xl mb-4">🏅</div>
                    <h3 class="text-2xl font-semibold">Leaderboard</h3>
                    <p class="text-gray-400 mt-2">Live Standings</p>
                </div>
                <div class="bg-gray-800 p-8 rounded-2xl hover:bg-gray-700 cursor-pointer">
                    <div class="text-5xl mb-4">🚴</div>
                    <h3 class="text-2xl font-semibold">All Riders</h3>
                    <p class="text-gray-400 mt-2">Browse & Draft</p>
                </div>
            </div>
            
            <div class="mt-16 text-center">
                <p class="text-gray-500">Server is running successfully ✅</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/status")
async def status():
    return {"status": "ok", "message": "LeTour Fantasy is running!"}
