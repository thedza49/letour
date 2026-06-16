from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine

Base = declarative_base()

# The Invisible Bridge: Links Users to their drafted Riders
team_roster = Table(
    'team_roster',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('rider_id', Integer, ForeignKey('riders.id'))
)

# In app/models.py
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, unique=True) # Used as the login ID
    # No password_hash needed anymore!

class Rider(Base):
    __tablename__ = "riders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    team = Column(String)
    price = Column(Float)
    uci_rank = Column(Integer)

engine = create_engine("sqlite:///./letour.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Add this to the end of app/models.py ---
def seed_data():
    db = SessionLocal()
    if not db.query(Rider).first():
        sample_riders = [
            Rider(name="Tadej Pogacar", team="UAE", price=55.0, uci_rank=1),
            Rider(name="Jonas Vingegaard", team="Visma", price=52.0, uci_rank=2),
            Rider(name="Remco Evenepoel", team="Soudal", price=48.0, uci_rank=3)
        ]
        db.add_all(sample_riders)
        db.commit()
    db.close()

# Call this once
seed_data()
