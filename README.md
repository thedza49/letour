### README.md

# LeTour Fantasy 2026

A custom-built Fantasy Cycling platform for the 2026 season. Built with FastAPI, SQLite, and Tailwind CSS.

## Project Status

We have established the core architecture, including secure user authentication and database modeling.

**Current Blocker:** The `bcrypt` password hashing library is experiencing environment conflicts during the registration process on the Oracle cloud server.

## Roadmap

| Phase | Task | Status |
| --- | --- | --- |
| **1. Auth** | User Registration & Login | ⚠️ Blocked (Bcrypt Conflict) |
| **2. Core** | Database Setup & Rider Seeding | ✅ Complete |
| **3. Draft** | Logic: Budgeting & Roster Limits | ⏳ Pending |
| **4. UI** | Responsive Dashboard & Drafting | ⏳ Pending |
| **5. Scaling** | CSV Data Import for full Pelotón | 📅 Next |

## How to Deploy

1. **Pull Repo:** `git pull origin main`
2. **Setup Env:** `source venv/bin/activate`
3. **Dependencies:** `pip install -r requirements.txt`
4. **Run Server:** `uvicorn app.main:app --reload`

---

### Understanding the Architecture

Before we fix the registration, it is helpful to visualize how these components interact.

### The "Ghost" of the Registration Issue

The `ValueError: password cannot be longer than 72 bytes` and the `AttributeError` for `bcrypt` are happening because your server’s Python environment is pulling in incompatible versions of security packages.

**My proposal to fix this without further "ghost" errors:**
Instead of relying on the system-wide `bcrypt` (which keeps breaking), we should force the environment to use a standalone wrapper.
