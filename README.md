### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the
2026 Tour de France. Hosted on Daniel's Oracle Cloud VM.

## Status as of June 23, 2026 — Phase C complete (code), pending real data

**New in Phase C:**
- **Scoring engine** (`app/scoring.py`): every stage now produces real
  points. Finish position earns points (1st through 20th+, see table
  below), holding a classification jersey (yellow/green/polka-dot/white)
  after the stage adds a bonus on top, and whichever rider a coach
  named captain has their stage total doubled.
- **Stage results sync** (`sync_results.py`): a script meant to run
  once a day, ~2 hours after that day's stage typically finishes. It
  scrapes procyclingstats.com for the day's finish order and jersey
  holders, stores them, scores every coach, and marks the stage
  `results_synced` — which is what unlocks transfers and captain picks
  for the next stage.
- **Real rider startlist import** (`import_startlist.py`): one-time
  script that replaces the 12 placeholder riders with the real ~180-
  rider Tour startlist from procyclingstats, priced by world ranking
  tier (see "Known placeholder/approximate data" below — pricing is a
  reasonable starting model, not an official number from anywhere).

**Scoring rules (tune freely in `app/scoring.py` — nothing else
hardcodes these numbers):**

| Finish position | Points |
|---|---|
| 1st | 50 |
| 2nd | 35 |
| 3rd | 25 |
| 4th | 20 |
| 5th | 15 |
| 6th–10th | 10 |
| 11th–20th | 5 |
| Finished, outside top 20 | 1 |
| DNF/DNS | 0 |

| Jersey held after the stage | Bonus |
|---|---|
| Yellow (GC leader) | +15 |
| Green (points leader) | +10 |
| Polka-dot (KOM leader) | +10 |
| White (best young rider) | +5 |

A coach's captain pick has their total stage score (finish + jersey
bonus) doubled. Bonuses stack if a rider holds more than one jersey.

## Action needed before this goes live

1. **Pull this onto the Oracle VM** (see "Deploying this update" below).
2. **Run the schema migration FIRST, before anything else** —
   `python3 migrate_to_phase_c.py`. This one is order-sensitive: it adds
   a `pcs_url` column to the existing `riders` table using a raw SQLite
   connection, deliberately avoiding `app.models` — because importing
   `app.models` against an un-migrated database crashes immediately
   (the new Rider model expects a column that doesn't exist yet). Run
   this before starting the app, before `commissioner_tools.py`, before
   anything else that touches the database.
3. **Run `python3 import_startlist.py` once procyclingstats publishes
   the 2026 startlist** (typically a few days before race day — it
   will likely return nothing if you run it too early in June). Safe
   to re-run as the startlist firms up; it upserts by rider, it doesn't
   duplicate.
4. **Set up the daily sync as a cron job** once the race starts:
   ```
   # crontab -e — runs ~2 hours after a typical Tour stage finish (stage
   # finishes are usually mid-afternoon CEST; adjust to taste)
   0 16 * * * cd /home/ubuntu/letour && /home/ubuntu/letour/venv/bin/python3 sync_results.py >> /home/ubuntu/letour/sync.log 2>&1
   ```
   Safe to run more than once a day if you want extra margin — it's a
   no-op once a stage is already marked synced, unless you pass
   `--force`.
5. **Adjust lockout times if you haven't already** — same as Phase B,
   via `commissioner_tools.py set-lockout`.

## Overview

Each coach logs in with their own email/password (no open registration —
accounts are created once via `create_coaches.py`) and drafts a 9-rider
roster within a €100 salary cap. Each stage, they pick one rider as captain
for a 2x score multiplier. Transfers and captain picks lock once a stage
starts and reopen once results are synced. If a rostered rider
DNFs or DNSs, the coach can drop them immediately and replace them once
transfers reopen.

## Tech Stack

* **Framework:** FastAPI
* **Database:** SQLite with SQLAlchemy ORM
* **Templates:** Jinja2 + Tailwind CSS (via CDN)
* **Auth:** bcrypt password hashing via passlib, session cookies via Starlette
  `SessionMiddleware` (signed using `itsdangerous`)
* **External data:** `procyclingstats` (scrapes procyclingstats.com) for
  the rider startlist and daily stage results

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

Import the real rider startlist once procyclingstats has published it
(safe to re-run; falls back gracefully with placeholder riders if you
run this before the startlist is up):
```bash
python3 import_startlist.py
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
python3 migrate_to_phase_c.py      # MUST run before anything else touches the DB - see "Action needed" above
python3 import_startlist.py        # once the 2026 startlist is published on procyclingstats
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

To re-score a single stage by hand (e.g. after fixing a data mistake in
`StageResult`), from a Python shell on the Oracle VM:
```bash
python3 -c "from app.scoring import recompute_stage; recompute_stage(5)"
```

## Known Placeholder/Approximate Data

Until `import_startlist.py` is run against a published 2026 startlist,
`app/models.py` still seeds the original 12 placeholder riders (real
names, made-up prices) on a fresh install, purely so drafting is
testable. `_archived_scripts/` contains two earlier, unfinished
attempts at automated rider import — parked there for reference, not
currently used (`import_startlist.py` replaces them).

**Rider pricing is an approximation, not an official number from
anywhere.** procyclingstats doesn't publish a fantasy price, so
`import_startlist.py` tiers prices by each rider's position in PCS's
individual world ranking (favorites cost more, similar in spirit to
real fantasy cycling games). The exact tiers live in `PRICE_TIERS` at
the top of that script — easy to retune before the real draft, or to
override by hand afterward with `commissioner_tools.py`.

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
* [x] **Phase C:** Scoring engine (finish points + jersey bonuses +
  captain multiplier), automated daily stage results sync from
  procyclingstats, real rider startlist import with ranking-based
  pricing
* [ ] **Phase D (ideas, not started):** automated DNF/DNS detection
  from synced stage results (currently still a manual
  `commissioner_tools.py deactivate` call), accurate per-stage lockout
  times pulled from the official ASO schedule instead of the 11:00 UTC
  placeholder, a standings/leaderboard page across all 3 coaches

---
