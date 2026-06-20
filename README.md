### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the
2026 Tour de France. Hosted on Daniel's Oracle Cloud VM.

## Status as of June 19, 2026 — Phase B complete

**New in Phase B (tested end-to-end before delivery):**
- **Daily Captain:** pick one rider per stage for a 2x score multiplier
  (multiplier itself isn't applied to points yet — that's Phase C's scoring
  engine — but the captain pick is stored per stage and ready for it).
- **Stage model with lockout:** all 21 real 2026 Tour stages are seeded with
  correct dates (July 4–26, accounting for both rest days). Once a stage's
  lockout time passes, drafting, dropping, and changing captain all freeze
  until that stage's results are marked synced.
- **Real transfer history:** rosters are now tracked in a `team_riders` table
  with `added_date`/`dropped_date`, replacing the old simple roster list.
  This means we can answer "who had which rider, and when" — needed for
  Phase C scoring and useful for settling any "wait, when did I drop him"
  arguments.
- **DNF/DNS handling:** commissioner can mark a rider inactive
  (`commissioner_tools.py deactivate <rider_id>`). Any coach with that rider
  on their roster sees a red "Action needed" warning on Home and My Team,
  and can drop that rider even if the stage is otherwise locked — they're
  never stuck unable to fix a dead roster slot. They still can't draft a
  replacement until the stage unlocks, by design, since that's also the
  normal transfer rule.

**Bug caught and fixed during testing (not something you'd have hit, but
worth knowing about):** the "Action needed" replacement warning was being
calculated but never actually passed into the My Team page's template —
it only worked on Home. Fixed before this was handed over; verified working
on both pages now.

## Action needed before this goes live

1. **Pull this onto the Oracle VM** (see "Deploying this update" below).
2. **Run the schema migration** — `python3 migrate_to_phase_b.py` — this
   carries your 3 coaches' existing rosters from the old schema into the
   new transfer-history table. **Do this before anyone drafts again**, or
   their current picks won't show up. Safe to re-run if you're ever unsure
   whether it already ran.
3. **Run `python3 seed_stages.py`** to load all 21 stage dates.
4. **Adjust lockout times if needed.** Right now every stage defaults to an
   11:00 UTC lockout on race day, which is a placeholder, not the real ASO
   start time. Use `python3 commissioner_tools.py stages` to view them and
   `python3 commissioner_tools.py set-lockout <stage_number> "YYYY-MM-DD HH:MM"`
   to adjust.

## Overview

Each coach logs in with their own email/password (no open registration —
accounts are created once via `create_coaches.py`) and drafts a 9-rider
roster within a €100 salary cap. Each stage, they pick one rider as captain
for a 2x score multiplier. Transfers and captain picks lock once a stage
starts and reopen once results are synced (Phase C). If a rostered rider
DNFs or DNSs, the coach can drop them immediately and replace them once
transfers reopen.

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

Seed the 21 stages:
```bash
python3 seed_stages.py
```

Run the app:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

To keep it running after closing the SSH session:
```bash
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

## Deploying this update to an existing install (the Oracle VM)

```bash
cd ~/letour
git fetch origin
git reset --hard origin/main
pip install -r requirements.txt
python3 migrate_to_phase_b.py      # carries existing rosters into the new schema
python3 seed_stages.py             # loads all 21 stage dates
```
Then restart the running server so the new code takes effect:
```bash
pkill -f uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
```

**Important:** `git reset --hard` only touches files Git already tracks.
Untracked clutter (old experiments, stray `.pyc` files, leftover folders from
earlier attempts at this project) won't be removed by this and can pile up
over time. Periodically worth checking `git status` for an `Untracked files`
list that's grown unexpectedly.

## Commissioner tools

```bash
python3 commissioner_tools.py stages                          # list all stages + lockout state
python3 commissioner_tools.py set-lockout 5 "2026-07-08 13:00" # adjust stage 5's lockout (UTC)
python3 commissioner_tools.py riders                           # list all riders + active status
python3 commissioner_tools.py deactivate <rider_id>             # mark a rider DNF/DNS
python3 commissioner_tools.py activate <rider_id>               # undo that (e.g. data entry mistake)
```

## Known Placeholder Data

`app/models.py` seeds a starter pool of 12 placeholder riders (real names,
made-up prices) on first run, purely so drafting is testable. This is not
the real 2026 startlist. `_archived_scripts/` contains two earlier, unfinished
attempts at automated rider import from ProCyclingStats — parked there for
reference, not currently used.

Stage lockout times default to 11:00 UTC on race day everywhere — a
placeholder, not the real ASO start time for each stage. Adjust via
`commissioner_tools.py set-lockout` once official times are confirmed.

## Project Roadmap

* [x] **Phase A:** Real per-coach auth, fixed budget/roster rules, Jinja
  templates, fixed crash bugs, secrets out of source code, dependency and
  dotenv-loading fixes
* [x] **Phase B:** Captain selection (2x multiplier stored), stage/lockout
  model with real 2026 dates, transfer add/drop history, DNF/DNS
  replace-rider workflow
* [ ] **Phase C:** Automated stage results sync + scoring engine (this is
  where the captain's 2x multiplier actually gets applied to points),
  automated DNF/DNS detection, real rider startlist import, accurate
  per-stage lockout times from the official ASO schedule

---
