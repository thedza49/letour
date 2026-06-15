# LeTour Fantasy

Tour de France Fantasy League


## summary


✅ Project Summary for Transition
Here’s a clear, complete overview of where we are with LeTour Fantasy — ready to hand off to another chatbot (or developer).
Current Status (as of June 2026)
What has been built and is working:
	•	Project Structure: Clean FastAPI + SQLite setup on your Oracle Cloud Ubuntu server.
	•	Homepage: Nice dark/TdF-themed responsive page with Tailwind CSS (mobile-friendly).
	•	Riders Page (/riders): Displays all loaded riders in a table with name, team, price, and UCI rank.
	•	Database: SQLAlchemy models for User, Rider, and TeamRider (following your PRD).
	•	Rider Data: 11 sample top riders loaded into the database (with tier-based pricing). Easy to expand.
	•	Basic Auth: Register page (/register) with email, team name, and password. Data is hashed and saved.
	•	Deployment Ready: Running on port 8000 via uvicorn. Firewall rules set. GitHub repo synced: https://github.com/thedza49/letour
Tech Stack (matches your PRD)
	•	Backend: FastAPI (Python)
	•	Database: SQLite (letour.db)
	•	Frontend: Jinja-style HTML + Tailwind CSS (lightweight, no React yet)
	•	Data: Manual + procyclingstats-ready
	•	Hosting: Oracle Cloud Ubuntu VPS

Updated `README.md` (Recommended Content)
You can copy this into your repo:
# LeTour Fantasy - Tour de France Fantasy League

Budget-based fantasy game (€100 for 9 riders, open ownership, daily captain 2x multiplier).

## Current Features
- Beautiful mobile-friendly homepage
- Browse all riders with prices and rankings
- User registration (email + team name + password)
- SQLite database with proper models
- Rider import system (expandable via CSV or procyclingstats)

## Setup on Server

```bash
cd ~/letour
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Access at: http://YOUR-IP:8000
Project Structure
letour/
├── app/
│   ├── main.py          # Routes + pages
│   ├── models.py        # Database models
│   └── auth.py          # Registration logic
├── riders.csv
├── letour.db
├── requirements.txt
└── import_riders.py
Next Development Priorities
Phase 1 - Core Game (High Priority)
	1	Login functionality + session management (currently only register works)
	2	My Team page:
	◦	View current squad
	◦	Add/remove riders with €100 budget validation
	◦	9-rider limit enforcement
	◦	Daily Captain selection
	3	Team persistence using TeamRider join table
Phase 2 - Scoring & Automation
	4	Scoring Engine (mimic official Fantasy by Tissot)
	◦	Stage results points
	◦	Jersey bonuses
	◦	Captain 2x multiplier
	5	Daily data sync using procyclingstats + APScheduler (post-stage results)
	6	Leaderboard page
Phase 3 - Admin & Polish
	7	Commissioner Admin Dashboard
	◦	View all teams
	◦	Manual score overrides
	◦	Rider activation (DNF handling)
	8	Transfer system (post-stage lock/unlock)
	9	Better rider import for full 2026 startlist
	10	Deployment improvements (systemd service, Nginx reverse proxy, domain + SSL)
Nice-to-Haves
	•	Password login + protected routes
	•	Team editing with budget calculator
	•	Mobile PWA feel
	•	Docker support (optional)

Would you like me to generate the next specific file(s) before you hand this off? (e.g. complete login + protected “My Team” stub)
Just let the next chatbot know they can continue from here — the foundation is solid and follows your original PRD closely.
Let me know if you want any adjustments to this summary! 🚴‍♂️

## How to run on your server

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000





