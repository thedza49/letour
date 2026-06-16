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

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    team_name = Column(String, unique=True)
    password_hash = Column(String)
    
    # This tells the database to pull all riders associated with this user
    roster = relationship("Rider", secondary=team_roster, backref="teams")

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
