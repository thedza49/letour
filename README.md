### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the
2026 Tour de France. Hosted on Daniel's Oracle Cloud VM.

## Status as of June 19, 2026

**Working and deployed on the Oracle VM:**
- 3 coach accounts created and confirmed logging in successfully:
  Team Dza, Team Blaster, Team MP
- Login/logout, Browse Riders, My Team, and drafting all tested working
- €100 salary cap and 9-rider roster limit enforced server-side
- Secrets (`SECRET_KEY`) live only in `app/.env` on the VM, never in Git

**Fixed in this session (not yet re-verified on the VM after the latest pull):**
- Added `itsdangerous` to `requirements.txt` — this was missing and caused
  `ModuleNotFoundError: No module named 'itsdangerous'` on a fresh install,
  since Starlette's `SessionMiddleware` needs it but pip doesn't always pull
  it in automatically.
- Fixed `load_dotenv()` in `app/main.py` and `app/models.py` to point
  explicitly at `app/.env` instead of relying on python-dotenv's automatic
  search. The automatic search only looks in the current/parent directories,
  not subdirectories — so depending on which directory `uvicorn` is launched
  from, it could silently fail to find `app/.env` and crash with
  "SECRET_KEY is not set." Explicitly pointing at the file removes that
  fragility entirely.

**Action needed:** pull this latest version on the Oracle VM
(see "Syncing GitHub and the VM" below) and restart the server to pick up
both fixes.

## Overview

Each coach logs in with their own email/password (no open registration —
accounts are created once via `create_coaches.py`) and drafts a 9-rider
roster within a €100 salary cap. Everyone manages their own team from
their own device.

## Tech Stack

* **Framework:** FastAPI
* **Database:** SQLite with SQLAlchemy ORM
* **Templates:** Jinja2 + Tailwind CSS (via CDN)
* **Auth:** bcrypt password hashing via passlib, session cookies via Starlette
  `SessionMiddleware` (signed using `itsdangerous`)

## Setup & Usage (fresh install)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `app/.env` by hand (never commit this file — it's in `.gitignore`):
```
SECRET_KEY=<generate with: python3 -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=sqlite:///./letour.db
ADMIN_EMAIL=your-email@example.com
```

Create the 3 coach accounts (one-time, safe to re-run):
```bash
python3 create_coaches.py
```

Run the app:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

To keep it running after closing the SSH session:
```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

## Syncing GitHub and the Oracle VM

GitHub (`thedza49/letour`, `main` branch) is the source of truth for code.
The Oracle VM should always be a `git pull` away from matching it exactly,
**except** for `app/.env`, `letour.db`, and `venv/`, which only ever exist
locally on the VM and are never pushed to GitHub (enforced by `.gitignore`).

To bring the VM in sync with the latest GitHub commit:
```bash
cd ~/letour
git fetch origin
git reset --hard origin/main
pip install -r requirements.txt   # picks up any new dependencies
```
Then restart the running server (kill the old `uvicorn`/`nohup` process and
start it again) so the new code actually takes effect.

**Important:** `git reset --hard` only touches files Git already tracks.
Untracked clutter (old experiments, stray `.pyc` files, leftover folders from
earlier attempts at this project) won't be removed by this and can pile up
over time. Periodically worth checking `git status` for an `Untracked files`
list that's grown unexpectedly.

## Known Placeholder Data

`app/models.py` seeds a starter pool of 12 placeholder riders (real names,
made-up prices) on first run, purely so drafting is testable. This is not
the real 2026 startlist. `_archived_scripts/` contains two earlier, unfinished
attempts at automated rider import from ProCyclingStats — parked there for
reference, not currently used.

## Project Roadmap

* [x] **Phase A:** Real per-coach auth, fixed budget/roster rules, Jinja
  templates, fixed crash bugs, secrets out of source code, dependency and
  dotenv-loading fixes
* [ ] **Phase B:** Captain selection (2x score multiplier), transfer windows,
  add/drop history
* [ ] **Phase C:** Automated stage results sync + scoring engine, DNF/DNS
  handling, real rider startlist import

---
