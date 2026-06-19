from procyclingstats import Rider, Race
import pandas as pd
from datetime import datetime

print("🔄 Fetching 2026 Tour de France riders...")

# This will pull current pro riders (we'll filter for Tour participants later)
# For now, get a list of top riders
riders_data = []

# Example top riders - we'll expand this
top_riders = [
    "tadej-pogacar", "jonas-vingegaard", "remco-evenepoel", "primoz-roglic",
    "mathieu-van-der-poel", "wout-van-aert", "richard-carapaz"
]

for rider_slug in top_riders:
    try:
        rider = Rider(rider_slug)
        riders_data.append({
            "name": rider.name,
            "team": rider.team,
            "price": 20,  # default high price, we'll adjust later
            "uci_rank": 1
        })
        print(f"✅ Added {rider.name}")
    except:
        print(f"⚠️  Could not load {rider_slug}")

print(f"\nImported {len(riders_data)} riders.")
print("We'll expand this to full Tour startlist soon.")
