from procyclingstats import RaceStartlist
from app.models import SessionLocal, Rider

def sync_riders():
    # 1. Choose the race (e.g., Tour de France 2025)
    # You can get this URL from ProCyclingStats
    url = "race/tour-de-france/2025/startlist" 
    
    print(f"Fetching data from {url}...")
    startlist = RaceStartlist(url)
    data = startlist.startlist() # This is the list of riders
    
    db = SessionLocal()
    
    # Optional: Clear old riders first
    db.query(Rider).delete()
    
    # 2. Add them to your database
    for entry in data:
        new_rider = Rider(
            name=entry['rider_name'],
            team=entry['team_name'],
            price=25.0, # Default price until we add logic to determine it
            rider_type="Unknown"
        )
        db.add(new_rider)
    
    db.commit()
    db.close()
    print("Sync complete!")

if __name__ == "__main__":
    sync_riders()
