import os
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./letour.db")

Base = declarative_base()

# League rules (Phase 1 of the PRD): EUR 100 budget, 9 riders per roster.
SALARY_CAP = 100.0
ROSTER_SIZE = 9

team_roster = Table(
    'team_roster',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('rider_id', Integer, ForeignKey('riders.id'))
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    team_name = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_commissioner = Column(Boolean, default=False)
    roster = relationship("Rider", secondary=team_roster)


class Rider(Base):
    __tablename__ = "riders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    team = Column(String)
    price = Column(Float)
    rider_type = Column(String)


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Seed a starter rider pool only if the table is empty, so re-deploys don't wipe drafts.
# This is placeholder data for Phase 1 - replace via a real rider import later.
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
