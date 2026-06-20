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
    per stage. One row per (user, stage). points is filled in later
    by the Phase C scoring engine."""
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
