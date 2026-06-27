"""
Follow-up diagnostic: calls the ACTUAL procyclingstats library the same
way import_startlist.py does, but wraps it to print exactly where it
fails and dumps the raw HTML it received to a file for inspection.

Does not touch the database.

Usage:
    python3 diagnose_startlist2.py
"""
from procyclingstats import RaceStartlist

PCS_STARTLIST_URL = "race/tour-de-france/2026/startlist"

print("Constructing RaceStartlist (this fetches the page)...")
try:
    startlist = RaceStartlist(PCS_STARTLIST_URL)
    print("Constructed OK.")
except Exception as e:
    print(f"FAILED during construction: {type(e).__name__}: {e}")
    raise SystemExit(1)

# Dump the raw HTML the library actually parsed, so we can compare it
# byte-for-byte against what a plain requests.get() got.
raw_html = startlist.html.html
with open("pcs_library_fetched.html", "w", encoding="utf-8") as f:
    f.write(raw_html)
print(f"Dumped {len(raw_html)} characters of HTML to pcs_library_fetched.html")

print()
print("Checking markers directly on the library's own HTMLParser object:")
table_basic = startlist.html.css_first("table.basic")
startlist_v4 = startlist.html.css_first(".startlist_v4")
print(f"  css_first('table.basic'):    {table_basic}")
print(f"  css_first('.startlist_v4'):  {startlist_v4}")

if startlist_v4:
    riders_cont = startlist_v4.css(".ridersCont")
    print(f"  .startlist_v4.css('.ridersCont') found: {len(riders_cont)} blocks")
else:
    print("  .startlist_v4 is None on the library's parsed HTML - this is the bug.")

print()
print("Now actually calling startlist.startlist() (this is what import_startlist.py calls)...")
try:
    rows = startlist.startlist("rider_name", "rider_url", "team_name")
    print(f"SUCCESS: parsed {len(rows)} rider rows.")
    if rows:
        print("First row:", rows[0])
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
