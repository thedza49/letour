"""
Diagnostic script for the import_startlist.py failure.

Does NOT touch your database - it only fetches the real PCS startlist
page and checks for the EXACT HTML markers the procyclingstats library's
RaceStartlist.startlist() method depends on (verified by reading that
library's actual source code in race_startlist_scraper.py):

  1. First it looks for `table.basic` - a startlist rendered as a plain
     table (used for some races/situations).
  2. If that's not found, it falls back to `.startlist_v4` containing
     one or more `.ridersCont` blocks (one per team) - this is the
     normal grand-tour layout, confirmed against this library's own
     2022 Tour de France test fixture, which has exactly this
     structure.
  3. If NEITHER is found, the library's code crashes with exactly the
     error you saw: 'NoneType' object has no attribute 'css' - because
     it doesn't check if `.startlist_v4` was found before immediately
     calling `.css(".ridersCont")` on it.

This script checks for all three markers directly, so we can see
exactly which one (if any) is missing on the real 2026 page.

Usage:
    python3 diagnose_startlist.py
"""
import requests

URL = "https://www.procyclingstats.com/race/tour-de-france/2026/startlist"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Fetching {URL} ...")
resp = requests.get(URL, headers=HEADERS, timeout=20)
print(f"HTTP status: {resp.status_code}")
print(f"Page length: {len(resp.text)} characters")
print()

html = resp.text

if "Page not found" in html:
    print("Page contains 'Page not found' - PCS doesn't have this URL.")
if "technical difficulties" in html:
    print("Page contains a 'technical difficulties' message from PCS.")

import re
title_match = re.search(r"<title>(.*?)</title>", html)
print(f"Page <title>: {title_match.group(1) if title_match else '(not found)'}")
print()

print("=== Checking the EXACT markers the library's code depends on ===")
has_table_basic = bool(re.search(r'<table[^>]*class="[^"]*\bbasic\b', html))
has_startlist_v4 = 'startlist_v4' in html
riders_cont_count = html.count('ridersCont')

print(f"  table.basic present:      {has_table_basic}")
print(f"  .startlist_v4 present:    {has_startlist_v4}")
print(f"  .ridersCont occurrences:  {riders_cont_count}")
print()

if has_table_basic:
    print("-> table.basic FOUND - the library should use this path successfully.")
elif has_startlist_v4 and riders_cont_count > 0:
    print("-> .startlist_v4 + .ridersCont FOUND - the library should work via the fallback path.")
elif has_startlist_v4 and riders_cont_count == 0:
    print("-> .startlist_v4 found but NO .ridersCont inside it - PCS changed the inner structure.")
else:
    print("-> NEITHER marker found - PCS has renamed/restructured the startlist container.")
    print("   This confirms the page layout has changed since this library was last updated.")

print()
print("=== Other clues: any class name containing 'startlist' or 'rider' ===")
other_classes = set(re.findall(r'class="([^"]*(?:startlist|rider|team)[^"]*)"', html, re.IGNORECASE))
for c in sorted(other_classes)[:30]:
    print(f"  {c}")

print()
print("First 2000 characters of <body>:")
body_start = html.find("<body")
print(html[body_start:body_start + 2000] if body_start != -1 else "(<body> tag not found)")
