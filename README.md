### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the
2026 Tour de France. Hosted on Daniel's Oracle Cloud VM.

## Overview — how this app works

Each coach logs in with their own email/password (no open registration —
accounts are created once via `create_coaches.py`) and drafts a 9-rider
roster within a €100 salary cap. Each stage, they pick one rider as captain
for a 2x score multiplier. Transfers and captain picks lock once a stage
starts and reopen once results are synced. If a rostered rider
DNFs or DNSs, the coach can drop them immediately and replace them once
transfers reopen. Coaches can rename their own team at any time (My Team
page) — this doesn't affect login (accounts are keyed by `User.id`
internally, not by team name).

**Scoring engine** (`app/scoring.py`): every stage produces real points.
Finish position earns points (1st through 20th+, see table below), holding
a classification jersey (yellow/green/polka-dot/white) after the stage adds
a bonus on top, and whichever rider a coach named captain has their stage
total doubled. Each rider's own point total per stage is also stored
separately (`RiderStageResult`) — this is what powers the Home page's
Stage Star, My Team's per-rider Last Race/Total Points, and the Riders
page's sortable Last/Total columns.

**Stage results sync** (`sync_results.py`): runs once a day via cron, ~2
hours after that day's stage typically finishes. It scrapes
procyclingstats.com for the day's finish order and jersey holders, stores
them, scores every coach, and marks the stage `results_synced` — which is
what unlocks transfers and captain picks for the next stage.

**Real rider startlist import** (`import_startlist.py`): replaces
placeholder riders with the real Tour startlist from procyclingstats,
priced by world ranking tier. Safe to re-run periodically as team rosters
get finalized — see "Rider data" below for current status.

**Season points + scoring history on Home and My Team** — both pages show a
running "Season points" total, and My Team lists a per-stage points
breakdown once stages start syncing.

**Roster Leaderboard on Home** — ranks all 3 coaches by season point total
(daily + total), not just the logged-in coach's own numbers.

**Scoring rules (tune freely in `app/scoring.py` — nothing else hardcodes
these numbers):**

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

## Tech Stack

* **Framework:** FastAPI
* **Database:** SQLite with SQLAlchemy ORM
* **Templates:** Jinja2 + Tailwind CSS (via CDN), "Vitesse de France" dark
  design system (Barlow Condensed + Inter + JetBrains Mono) applied across
  Home, My Team, and Riders
* **Auth:** bcrypt password hashing via passlib, session cookies via Starlette
  `SessionMiddleware` (signed using `itsdangerous`), keyed by `User.id`
* **External data:** `procyclingstats` (scrapes procyclingstats.com) for
  the rider startlist and daily stage results — requires the `brotli`
  package (in `requirements.txt`) and, depending on the VM, `cloudscraper`
  to get past Cloudflare on some requests

## Setup & Usage (fresh install)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If `import_startlist.py` or `sync_results.py` fail with a Cloudflare-related
error, also run:
```bash
pip install cloudscraper
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

Seed the 21 stages and their route names:
```bash
python3 seed_stages.py
python3 seed_stage_routes.py
```

Import the real rider startlist:
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

**Note:** this project normally runs as a systemd service
(`letour.service`), not a raw `nohup` process — see the next section. Don't
run a manual `uvicorn` command on the same port as the live service; it'll
just fail with "address already in use," or worse, squat on the port and
prevent the real service from starting after a restart.

## Deploying an update to the Oracle VM

```bash
cd ~/letour
git pull
```

If a change touches `app/models.py` and adds a new table or column, a
one-time migration script will be included alongside it — run that before
restarting. (Past migrations get deleted from the repo once they've run
successfully; they're not meant to be reusable.)

Restart the service so the new code takes effect:
```bash
sudo systemctl restart letour.service
sudo systemctl status letour.service
```

`status` should show `Active: active (running)`. If it instead shows
`activating (auto-restart)` repeatedly, check the logs:
```bash
sudo journalctl -u letour.service -n 50 --no-pager
```

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

## Rider data

123 riders in the database: 122 real riders imported from procyclingstats'
2026 Tour startlist (priced by world ranking tier), plus 1 placeholder —
**Wout van Aert**, who withdrew from the Tour and has no real PCS startlist
entry. He stays as-is until handled via the normal drop/replace flow if a
coach has him rostered.

**Rider pricing is an approximation, not an official number from
anywhere.** procyclingstats doesn't publish a fantasy price, so
`import_startlist.py` tiers prices by each rider's position in PCS's
individual world ranking (favorites cost more, similar in spirit to
real fantasy cycling games). The exact tiers live in `PRICE_TIERS` at
the top of that script — easy to retune before the real draft, or to
override by hand afterward with `commissioner_tools.py`.

**Re-run `import_startlist.py` periodically** until all teams have
finalized and submitted their full rosters (PCS updates the startlist as
teams confirm). It matches existing riders by `pcs_url`, so re-running is
safe — it only adds genuinely new riders and updates pricing for existing
ones, never creates duplicates.

## Roster lockout

Each stage has a `lockout_at` time (UTC). Once that time passes, transfers
and captain picks freeze for every coach until that stage's results sync
(`sync_results.py`) reopens them for the next stage. The app announces this
clearly — Home shows a banner, My Team shows a "LOCKED" pill in place of
the Captain/Drop buttons, and Riders disables drafting with a lock icon —
so coaches always know why an action isn't available, rather than a button
just silently doing nothing.

**The one exception:** dropping a rider who's gone inactive (DNF/DNS) is
always allowed, even while locked — otherwise a coach could be stuck
unable to fix their roster mid-stage. Replacing that dropped rider still
waits until the lockout lifts.

**Current default lockout time is a placeholder — 11:00 UTC on every
stage's race day:**

| Time zone | Lockout time |
|---|---|
| UTC | 11:00 |
| PDT (Pacific, Daniel's time zone) | 4:00 AM |
| JST (Tokyo) | 8:00 PM (same day) |

This is not the real ASO start time for any specific stage — just a
placeholder so the app has *some* working lockout before real times are
set. Adjust per-stage via:
```bash
python3 commissioner_tools.py set-lockout <stage_number> "2026-07-08 13:00"
```
(time is UTC). Worth doing before opening the league to other coaches, so
lockout actually lines up with each stage's real start.

Stage route names (e.g. "Nice to Col de la Couillole") are seeded from the
official ASO route table via `seed_stage_routes.py` — all 21 stages have
their real start/finish towns.

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
* [x] **Phase E.1 — Per-rider stage scoring:** every rider's own point
  total is now stored per stage (`RiderStageResult`), independent of
  whether they were drafted or captained. Powers Home's Stage Star, My
  Team's per-rider Last Race/Total Points, and Riders' sortable
  Last/Total columns.
* [x] **Phase E.2 — Riders page browsing/filtering:** search by name,
  team filter (real dropdown of all teams), sortable Last/Total/Price
  columns, pagination (25 per page). Specialty filter stays visible but
  disabled — procyclingstats doesn't classify riders by specialty, so
  `Rider.rider_type` has no real data to filter against yet.
* [x] **Phase E.3 — Riders page remaining budget display:** shown
  alongside the existing budget-used line.
* [x] **Phase E.4 — My Team editable team name:** rename form on My Team,
  reflected immediately on Home and in the nav header. Session identity
  is keyed by `User.id`, not team name, so renaming never breaks login.
* [x] **Phase E.5 — Stage name/route data:** `Stage.route_name` populated
  for all 21 stages from the official ASO route table
  (`seed_stage_routes.py`).
* [x] **Frontend redesign ("Vitesse de France"):** Home, My Team, and
  Riders all rebuilt against the Stitch design system. Home shows the
  current/last stage, Roster Leaderboard (3 real coaches), Stage Star,
  and Daily Jersey Winners. My Team shows budget/roster/remaining in one
  card, roster cards with per-rider points and jersey badges, and team
  rename. Riders shows the full real rider pool with working
  search/filter/sort/pagination.
* [ ] **Phase D (ideas, not started):** automated DNF/DNS detection
  from synced stage results (currently still a manual
  `commissioner_tools.py deactivate` call), accurate per-stage lockout
  times pulled from the official ASO schedule instead of the 11:00 UTC
  placeholder.
* [ ] **Specialty filter on Riders:** blocked until there's a real way
  to classify riders by type — procyclingstats doesn't expose this, so
  it'd need either manual entry per rider or a different data source.

**Dropped from consideration:** a numeric "live time gap" on Home's
stage visualization (would need real-time timing data we don't have —
results only sync once daily after the stage ends, not live), and a
generic numeric "rank" badge in the header (no use case for a
3-person league).

---
