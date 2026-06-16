from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import create_engine

Base = declarative_base()

team_roster = Table(
    'team_roster',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('rider_id', Integer, ForeignKey('riders.id'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, unique=True)
    roster = relationship("Rider", secondary=team_roster)

class Rider(Base):
    __tablename__ = "riders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    team = Column(String)
    price = Column(Float)

engine = create_engine("sqlite:///./letour.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Auto-seed some data so the list isn't empty
db = SessionLocal()
if not db.query(Rider).first():
    db.add_all([
        Rider(name="Tadej Pogacar", team="UAE", price=55.0),
        Rider(name="Jonas Vingegaard", team="Visma", price=52.0),
        Rider(name="Remco Evenepoel", team="Soudal", price=48.0)
    ])
    db.commit()
db.close()
