import os
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load app/.env explicitly so this works regardless of which directory
# this module is imported from (e.g. create_coaches.py at the project root).
_ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letour.db")

Base = declarative_base()

# League rules (Phase 1 of the PRD): EUR 100 budget, 9 riders per roster.
SALARY_CAP = 100.0
ROSTER_SIZE = 9


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    team_name = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_commissioner = Column(Boolean, default=False)

    team_riders = relationship("TeamRider", back_populates="user")


class Rider(Base):
    __tablename__ = "riders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    team = Column(String)
    price = Column(Float)
    rider_type = Column(String)
    uci_rank = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)  # flips to False on DNF/DNS
    # procyclingstats' stable per-rider URL slug, e.g. "rider/tadej-pogacar".
    # This is how import_startlist.py and sync_results.py match a PCS row
    # back to our Rider record - names alone are too fragile (accents,
    # nicknames, "POGAČAR Tadej" vs "Tadej Pogacar" formatting differences).
    pcs_url = Column(String, unique=True, nullable=True, index=True)


class Stage(Base):
    """One stage of the Tour. lockout_at is when transfers/captain picks
    freeze for that stage. results_synced marks whether scoring has been
    applied (Phase C will set this)."""
    __tablename__ = "stages"
    id = Column(Integer, primary_key=True, index=True)
    stage_number = Column(Integer, unique=True, nullable=False)
    date = Column(DateTime, nullable=False)
    lockout_at = Column(DateTime, nullable=False)
    results_synced = Column(Boolean, default=False)

    def is_locked(self, now=None):
        now = now or datetime.utcnow()
        return now >= self.lockout_at


class TeamRider(Base):
    """Replaces the old simple team_roster many-to-many table.
    Tracks when a rider was added/dropped from a coach's roster so we
    keep real transfer history instead of just a current snapshot."""
    __tablename__ = "team_riders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("riders.id"), nullable=False)
    added_date = Column(DateTime, default=datetime.utcnow)
    dropped_date = Column(DateTime, nullable=True)  # NULL = currently on roster

    user = relationship("User", back_populates="team_riders")
    rider = relationship("Rider")


class DailyRoster(Base):
    """Tracks which rider is captain (2x multiplier) for each coach,
    per stage. One row per (user, stage). points is filled in by the
    Phase C scoring engine (app/scoring.py) once a stage syncs."""
    __tablename__ = "daily_rosters"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)
    captain_rider_id = Column(Integer, ForeignKey("riders.id"), nullable=False)
    points = Column(Float, nullable=True)

    __table_args__ = (UniqueConstraint("user_id", "stage_id", name="uq_user_stage_captain"),)

    user = relationship("User")
    stage = relationship("Stage")
    captain_rider = relationship("Rider")


class RiderStageResult(Base):
    """One row per (rider, stage): that rider's OWN point total for the
    stage (finish points + jersey bonus, from
    scoring.rider_stage_points()) - regardless of whether any coach had
    them rostered or captained that stage. This exists separately from
    StageResult (the raw finish/jersey data) and from DailyRoster.points
    (a coach's team total, captain multiplier included) because none of
    those answer "how many points did this one rider score in this one
    stage" on their own, which is what the frontend redesign needs in
    three places (Phase E.1 - see README roadmap):
      - Home's "Stage Star" card (a featured rider's points)
      - My Team's roster cards (each rostered rider's own Last Race /
        Total Points, not the team's captain-driven total)
      - Riders page sortable LAST / TOTAL columns across the full pool

    Written by app/scoring.py's score_stage(), once per StageResult row,
    in the same pass that computes coach totals - so this table and
    DailyRoster.points are always in sync with each other and with
    StageResult.

    A rider with no row for a given stage means they had no StageResult
    for that stage (not in that day's race, e.g. not yet imported into
    the startlist) - distinct from scoring 0 points, same convention
    DailyRoster/get_scoring_history already uses elsewhere in this app.
    """
    __tablename__ = "rider_stage_results"
    id = Column(Integer, primary_key=True, index=True)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("riders.id"), nullable=False)
    points = Column(Float, nullable=False)

    __table_args__ = (UniqueConstraint("stage_id", "rider_id", name="uq_stage_rider_points"),)

    stage = relationship("Stage")
    rider = relationship("Rider")


class StageResult(Base):
    """One row per rider, per stage: their finish position and whether
    they held one of the four classification jerseys after that stage
    finished. Populated by sync_results.py once a day, ~2 hours after
    the stage typically ends. This is the raw data app/scoring.py reads
    to compute each coach's points for that stage.

    finish_position is NULL when did_not_finish is True (a rider who
    started but dropped out mid-stage, or didn't start at all - both
    score 0 finish points per the league scoring rules)."""
    __tablename__ = "stage_results"
    id = Column(Integer, primary_key=True, index=True)
    stage_id = Column(Integer, ForeignKey("stages.id"), nullable=False)
    rider_id = Column(Integer, ForeignKey("riders.id"), nullable=False)
    finish_position = Column(Integer, nullable=True)
    did_not_finish = Column(Boolean, default=False)

    # Jersey holders after this stage. At most one rider per stage should
    # have each of these set True - sync_results.py enforces that, but it
    # isn't a DB constraint since SQLite makes that fiddly across rows.
    holds_yellow = Column(Boolean, default=False)     # GC leader
    holds_green = Column(Boolean, default=False)      # points/sprint leader
    holds_polka_dot = Column(Boolean, default=False)  # KOM/mountains leader
    holds_white = Column(Boolean, default=False)      # best young rider

    __table_args__ = (UniqueConstraint("stage_id", "rider_id", name="uq_stage_rider_result"),)

    stage = relationship("Stage")
    rider = relationship("Rider")


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_active_roster(db, user_id):
    """Returns the list of Rider objects currently on a user's roster
    (added but not dropped)."""
    rows = (
        db.query(TeamRider)
        .filter(TeamRider.user_id == user_id, TeamRider.dropped_date.is_(None))
        .all()
    )
    return [row.rider for row in rows]


def get_rider_season_points(db, rider_id):
    """Sum of a single rider's own RiderStageResult.points across every
    stage they've scored in so far. Used by the Riders page's TOTAL
    column (Phase E.2) and My Team's roster cards (Phase E.1/E.2) -
    this is the rider's own total, NOT scaled by any coach's captain
    multiplier."""
    rows = db.query(RiderStageResult).filter(RiderStageResult.rider_id == rider_id).all()
    return sum(row.points for row in rows)


def get_rider_last_stage_points(db, rider_id):
    """Returns {"stage": Stage, "points": float} for the most recent
    stage this rider has a RiderStageResult row for, or None if they
    haven't scored yet (no synced stage has included them). Used by
    the Riders page's LAST column and My Team's "Last Race" card text
    (Phase E.1/E.2)."""
    row = (
        db.query(RiderStageResult)
        .join(Stage, RiderStageResult.stage_id == Stage.id)
        .filter(RiderStageResult.rider_id == rider_id)
        .order_by(Stage.stage_number.desc())
        .first()
    )
    if not row:
        return None
    return {"stage": row.stage, "points": row.points}


# Seed a starter rider pool only if the table is empty, so re-deploys don't wipe drafts.
# This is placeholder data - replace via a real rider import later.
db = SessionLocal()
if not db.query(Rider).first():
    db.add_all([
        Rider(name="Tadej Pogacar", team="UAE", price=28.0, rider_type="Climber"),
        Rider(name="Jonas Vingegaard", team="Visma", price=26.0, rider_type="Climber"),
        Rider(name="Remco Evenepoel", team="Soudal", price=24.0, rider_type="GC Contender"),
        Rider(name="Jasper Philipsen", team="Alpecin", price=18.0, rider_type="Sprinter"),
        Rider(name="Mathieu van der Poel", team="Alpecin", price=16.0, rider_type="Classics"),
        Rider(name="Wout van Aert", team="Visma", price=15.0, rider_type="Classics"),
        Rider(name="Primoz Roglic", team="Red Bull", price=14.0, rider_type="Climber"),
        Rider(name="Richard Carapaz", team="EF", price=10.0, rider_type="Climber"),
        Rider(name="Mads Pedersen", team="Lidl-Trek", price=9.0, rider_type="Sprinter"),
        Rider(name="Biniam Girmay", team="Intermarche", price=8.0, rider_type="Sprinter"),
        Rider(name="Arnaud De Lie", team="Lotto", price=6.0, rider_type="Sprinter"),
        Rider(name="Domestique A", team="Various", price=2.0, rider_type="Domestique"),
    ])
    db.commit()
db.close()
