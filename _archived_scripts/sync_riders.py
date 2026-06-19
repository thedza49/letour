import cloudscraper
from procyclingstats import RaceStartlist
from app.models import SessionLocal, Rider

def sync_riders():
    # The URL for the 2026 Tour de France
    url = "race/tour-de-france/2026/startlist" 
    
    # Initialize the "Cloak" (Cloudscraper)
    scraper = cloudscraper.create_scraper()
    
    # Get the HTML page as if we were a normal browser
    print(f"Fetching data for 2026 from {url}...")
    html_content = scraper.get(f"https://www.procyclingstats.com/{url}").text
    
    # Feed that HTML into the RaceStartlist tool
    startlist = RaceStartlist(url, html=html_content)
    data = startlist.startlist() 
    
    db = SessionLocal()
    
    # Clear old riders
    db.query(Rider).delete()
    
    # Add new riders
    for entry in data:
        new_rider = Rider(
            name=entry['rider_name'],
            team=entry['team_name'] if 'team_name' in entry else "Unknown",
            price=25.0, 
            rider_type="Unknown"
        )
        db.add(new_rider)
    
    db.commit()
    db.close()
    print("Sync complete! 2026 riders loaded.")

if __name__ == "__main__":
    sync_riders()
