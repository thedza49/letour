### LeTour Fantasy 2026

A fantasy cycling app for a private league of 3 coaches drafting riders for the 2026 Tour de France.

## Overview

Each coach logs in with their own email/password (no open registration — accounts
are created once via `create_coaches.py`) and drafts a 9-rider roster within a
€100 salary cap. Everyone manages their own team from their own device.

## Key Features

* **Per-coach accounts:** Email + password login, sessions kept separate per coach.
* **Drafting rules enforced server-side:** €100 salary cap and 9-rider roster limit,
  checked on every draft so you can't go over either by refreshing or resubmitting.
* **Clean dashboard:** Home, Browse Riders, and My Team pages built from real Jinja
  templates (no more giant inline HTML strings).

## Tech Stack

* **Framework:** FastAPI
* **Database:** SQLite with SQLAlchemy ORM
* **Templates:** Jinja2 + Tailwind CSS (via CDN)
* **Auth:** bcrypt password hashing via passlib

## Setup & Usage

### 1. Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure secrets

`app/.env` already has a generated `SECRET_KEY`. Don't commit this file or share
it — it's already in `.gitignore`. If you ever need a new one:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Create the 3 coach accounts (one-time)

```bash
python3 create_coaches.py
```

This walks you through setting an email + password for Team Dza, Team Blaster,
and Team MP. Safe to re-run — it skips any team that already has an account.

### 4. Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Visit `http://localhost:8000/login` (or your Oracle VM's address) and log in.

## Current Rider Pool

`app/models.py` seeds a starter pool of 12 placeholder riders on first run so you
can test drafting immediately. Replace this with the real 2026 startlist when
you're ready — see `_archived_scripts/README.md` for notes on the two earlier,
unfinished attempts at automated rider import from ProCyclingStats.

## Project Roadmap

* [x] **Phase A:** Real per-coach auth, fixed budget/roster rules, Jinja templates,
  fixed crash bugs, secrets out of source code
* [ ] **Phase B:** Captain selection (2x score multiplier), transfer windows,
  add/drop history
* [ ] **Phase C:** Automated stage results sync + scoring engine, DNF/DNS handling

---
