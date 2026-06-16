### LeTour Fantasy 2026

A custom web application for managing fantasy cycling teams for the 2026 Tour de France.

## Overview

LeTour Fantasy allows users to draft cyclists, manage a team roster, and stay within a defined salary cap. The application features a budget-based drafting system and an automated synchronization engine to pull real-time startlist data directly from ProCyclingStats.

## Key Features

* **Coach Authentication:** Selectable team profiles for a personalized experience.
* **Smart Drafting:** Real-time budget tracking with a 150.0 salary cap.
* **Automated Data Sync:** Integrated scraping engine to import the latest 2026 Tour de France startlist.
* **Responsive UI:** Built with Tailwind CSS for a clean, mobile-friendly interface.

## Tech Stack

* **Framework:** FastAPI
* **Database:** SQLite with SQLAlchemy ORM
* **Data Integration:** `undetected-chromedriver` and `BeautifulSoup` for automated web scraping.
* **Frontend:** HTML5 with Tailwind CSS (via CDN).

## Setup & Usage

### 1. Installation

Ensure you are in the project root and your virtual environment is active:

```bash
source venv/bin/activate
pip install -r requirements.txt

```

### 2. Running the Application

Start the development server with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

### 3. Synchronizing Data

To update your local database with the latest 2026 rider information, run the synchronization script:

```bash
python3 sync_riders.py

```

## Project Roadmap

* [x] **Phase 1:** Core Architecture (Auth, DB, Models)
* [x] **Phase 2:** Drafting Logic & Salary Cap
* [x] **Phase 3:** UI Navigation & Dashboard
* [ ] **Phase 4:** Rider Metadata (Climber/Sprinter categorization)
* [ ] **Phase 5:** Full Data Pipeline Integration

---
