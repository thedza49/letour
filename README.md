### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the
2026 Tour de France. Hosted on Daniel's Oracle Cloud VM.

## Status as of June 23, 2026 — Phase C live and verified on production

Phase C is deployed on the Oracle VM and has been end-to-end tested
against the real production database (not just locally) — login,
drafting, and a full fake-stage scoring run were all confirmed working
on the live site.

**What's confirmed working on the live VM:**
- Schema migration (`migrate_to_phase_c.py`) ran clean against the
  existing Phase B database.
- App restarted successfully and serves `/login` (200 OK).
- A live scoring test was run against Team Dza's real roster (Tadej
  Pogacar, Remco Evenepoel, Jasper Philipsen) using fake `StageResult`
  rows for stage 1: Pogacar finished 1st and held yellow, Evenepoel
  finished 5th, Philipsen DNF'd, and Pogacar was captained. The
  scoring engine correctly computed 145.0 points
  (`(50 + 15) × 2` captain multiplier `+ 15 + 0`), and that number
  correctly showed up on the My Team page's season points and scoring
  history sections.
- Coach login was reset — all three coach accounts
  (`dvpetta@gmail.com` / Team Dza, `robert@rpetta.com` / Team Blaster,
  `petta.marc@gmail.com` / Team MP) currently share the same simple
  password for convenience. Fine for a private 3-person league, but
  worth knowing if that ever needs to be tightened up.

**⚠️ Open item before the real Tour starts — stage 1 needs resetting.**
The live test above left stage 1 marked `results_synced = True` with
fake `StageResult` rows still in the database. `sync_results.py` will
skip any stage already marked synced, so if this isn't cleaned up
before July 4, the real stage 1 results will never get pulled. Reset
it with:
```bash
cd ~/letour && source venv/bin/activate
python3 -c "
from app.models import SessionLocal, Stage, DailyRoster, StageResult
db = SessionLocal()
stage1 = db.query(Stage).filter(Stage.stage_number == 1).first()
db.query(StageResult).filter(StageResult.stage_id == stage1.id).delete()
db.query(DailyRoster).filter(DailyRoster.stage_id == stage1.id).delete()
stage1.results_synced = False
db.commit()
print('Stage 1 reset - ready for real results.')
db.close()
"
```

**What Phase C added:**
- **Scoring engine** (`app/scoring.py`): every stage produces real
  points. Finish position earns points (1st through 20th+, see table
  below), holding a classification jersey (yellow/green/polka-dot/white)
  after the stage adds a bonus on top, and whichever rider a coach
  named captain has their stage total doubled.
- **Stage results sync** (`sync_results.py`): a script meant to run
  once a day, ~2 hours after that day's stage typically finishes. It
  scrapes procyclingstats.com for the day's finish order and jersey
  holders, stores them, scores every coach, and marks the stage
  `results_synced` — which is what unlocks transfers and captain picks
  for the next stage. Not yet running on a cron schedule (see "Action
  needed" below).
- **Real rider startlist import** (`import_startlist.py`): one-time
  script meant to replace the 12 placeholder riders with the real
  ~180-rider Tour startlist from procyclingstats, priced by world
  ranking tier. **Tried on June 23 — procyclingstats hasn't published
  the 2026 startlist yet** (the script failed cleanly with "Failed to
  fetch the startlist," which is expected this far before race day).
  All 3 coaches' rosters are still drafted from the 12 placeholder
  riders for now. Re-run this every few days as race day approaches.
- **Season points + scoring history on Home and My Team** — both pages
  now show a running "Season points" total, and My Team lists a
  per-stage points breakdown once stages start syncing.

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

## Action needed before this goes live for real

1. ~~Pull this onto the Oracle VM.~~ ✅ Done June 23.
2. ~~Run the schema migration.~~ ✅ Done June 23 —
   `migrate_to_phase_c.py` ran clean.
3. **Reset stage 1's fake test data** — see the warning above. This is
   the one must-do item before July 4.
4. **Re-run `python3 import_startlist.py`** every few days until
   procyclingstats publishes the 2026 startlist. As of June 23 it
   hasn't yet.
5. **Set up the daily sync as a cron job** before the race starts:
   ```
   # crontab -e — runs ~2 hours after a typical Tour stage finish (stage
   # finishes are usually mid-afternoon CEST; adjust to taste)
   0 16 * * * cd /home/ubuntu/letour && /home/ubuntu/letour/venv/bin/python3 sync_results.py >> /home/ubuntu/letour/sync.log 2>&1
   ```
   Not yet confirmed installed — double check with `crontab -l` on
   the VM.
6. **Adjust lockout times if you haven't already** — same as Phase B,
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
Note: as of June 23, all three coaches share the same simple password
("tour") rather than the unique passwords `create_coaches.py` prompts
for individually — it was reset directly in the database for
convenience during testing. Fine for a private 3-person league; reset
any account's password by hand if you ever want it unique again:
```bash
python3 -c "
from passlib.context import CryptContext
from app.models import SessionLocal, User
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
db = SessionLocal()
user = db.query(User).filter(User.email == 'coach@example.com').first()
user.password_hash = pwd_context.hash('new-password-here')
db.commit()
db.close()
"
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
