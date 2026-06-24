"""
Phase C rider startlist import.

One-time script (re-runnable) that replaces the 12 placeholder riders in
the Rider table with the real ~180-rider 2026 Tour de France startlist,
scraped from procyclingstats.com once ASO/PCS publishes it (usually a
few days before the race - it won't exist yet in early/mid June).

Since procyclingstats' startlist page doesn't include a price or
ranking, this script makes a second call to PCS's individual world
ranking page and joins the two by each rider's pcs_url, then assigns a
price using the PRICE_TIERS table below: better-ranked riders cost more,
similar in spirit to how real fantasy cycling games price favorites
higher. Riders who aren't found in the ranking pages (younger/lesser-
known riders, common on a ~180-rider startlist) get the lowest tier
price rather than failing the import.

This pricing model is a placeholder you can tune freely - either by
editing PRICE_TIERS and re-running this script (safe: see below), or by
hand afterward with commissioner_tools.py once real drafting starts and
you have a feel for who coaches actually want.

Re-running this script:
  - Updates existing riders (matched by pcs_url) in place - price tier,
    team, and active status refresh; it won't duplicate them.
  - Adds any new riders found in the new startlist.
  - Does NOT remove riders no longer in the startlist (e.g. a late
    scratch) - mark those inactive by hand via commissioner_tools.py so
    any coach who already drafted them gets the normal DNF/DNS
    replacement flow instead of silently losing a roster slot.
  - Never touches placeholder riders that already have rosters built on
    them in a way that would orphan a coach's draft - TeamRider rows
    reference Rider by id, and ids are never reused, so existing rosters
    stay intact even if you re-run this multiple times.

Usage:
    python3 import_startlist.py
"""
import sys

from procyclingstats import RaceStartlist, Ranking

from app.models import SessionLocal, Rider

PCS_STARTLIST_URL = "race/tour-de-france/2026/startlist"

# World individual ranking page used to tier-price riders. "me" = the
# current/latest ranking snapshot on procyclingstats. NOTE: the
# procyclingstats package has no built-in pagination support for this
# page, and procyclingstats.com's own pagination is a query string on
# the live site (not something this wrapper exposes) - rather than
# guess at an unverified URL scheme, this script fetches just the one
# page PCS serves by default (typically the top ~100 riders). Riders
# ranked below that cutoff, or simply not found on this page, fall back
# to PRICE_UNRANKED. That's a reasonable outcome for most of a ~180-
# rider Tour startlist anyway, since plenty of domestiques and lesser-
# known riders aren't in the top 100 of the world ranking regardless.
PCS_RANKING_URL = "rankings/me/individual"

# Price tiers by world ranking position. A rider ranked within
# RANK_CEILING of a tier gets that tier's price; anyone ranked worse
# than the last tier's ceiling, or not found in the ranking at all,
# gets PRICE_UNRANKED. Edit freely - nothing else in the codebase
# hardcodes prices.
PRICE_TIERS = [
    (10, 28.0),    # ranked 1-10
    (25, 22.0),    # ranked 11-25
    (50, 16.0),    # ranked 26-50
    (100, 10.0),   # ranked 51-100
    (200, 6.0),    # ranked 101-200
]
PRICE_UNRANKED = 3.0  # not found in top-500 world ranking


def price_for_rank(rank):
    if rank is None:
        return PRICE_UNRANKED
    for ceiling, price in PRICE_TIERS:
        if rank <= ceiling:
            return price
    return PRICE_UNRANKED


def fetch_startlist():
    """Returns the raw startlist rows from procyclingstats. Raises on
    network failure or if PCS hasn't published the 2026 startlist yet -
    main() reports this clearly rather than writing partial data."""
    startlist = RaceStartlist(PCS_STARTLIST_URL)
    return startlist.startlist("rider_name", "rider_url", "team_name")


def fetch_world_rankings():
    """Returns {rider_url: rank} from the PCS individual world ranking
    page. Only fetches the single page PCS serves at this URL (see the
    note above PCS_RANKING_URL about why this script doesn't try to
    paginate further). A failure fetching the ranking is non-fatal for
    the import as a whole - every rider just falls back to
    PRICE_UNRANKED - since the startlist itself is the must-have data
    and ranking is "nice to have" for pricing."""
    try:
        ranking = Ranking(PCS_RANKING_URL)
        rows = ranking.individual_ranking("rider_url", "rank")
    except Exception as exc:
        print(f"  Warning: couldn't fetch world rankings ({exc}). All riders will default to the lowest price tier - you can re-price by hand afterward.")
        return {}

    return {row["rider_url"]: row.get("rank") for row in rows if row.get("rider_url")}


def import_riders(db, startlist_rows, ranks_by_url):
    """Upserts each startlist rider into the Rider table, matched by
    pcs_url. Returns (added_count, updated_count)."""
    existing_by_url = {r.pcs_url: r for r in db.query(Rider).filter(Rider.pcs_url.isnot(None)).all()}

    added = 0
    updated = 0

    for row in startlist_rows:
        pcs_url = row.get("rider_url")
        if not pcs_url:
            continue  # malformed row from PCS; skip rather than guess

        rank = ranks_by_url.get(pcs_url)
        price = price_for_rank(rank)
        name = (row.get("rider_name") or "").strip() or "Unknown rider"
        team = (row.get("team_name") or "").strip() or "Unknown team"

        rider = existing_by_url.get(pcs_url)
        if rider:
            rider.name = name
            rider.team = team
            rider.price = price
            rider.uci_rank = rank
            rider.is_active = True
            updated += 1
        else:
            db.add(Rider(
                name=name,
                team=team,
                price=price,
                rider_type=None,  # PCS doesn't classify rider type; set by hand if you want it
                uci_rank=rank,
                is_active=True,
                pcs_url=pcs_url,
            ))
            added += 1

    db.commit()
    return added, updated


def remove_placeholder_riders_if_unused(db):
    """The original 12 placeholder riders (seeded in app/models.py,
    pcs_url is NULL for all of them) are only safe to delete if no coach
    has ever drafted one - check TeamRider before deleting so we never
    silently break a roster. Returns the count removed."""
    from app.models import TeamRider

    placeholders = db.query(Rider).filter(Rider.pcs_url.is_(None)).all()
    removed = 0
    for rider in placeholders:
        ever_drafted = db.query(TeamRider).filter(TeamRider.rider_id == rider.id).first()
        if ever_drafted:
            print(f"  Keeping placeholder rider '{rider.name}' (id {rider.id}) - at least one coach has drafted them at some point.")
            continue
        db.delete(rider)
        removed += 1
    db.commit()
    return removed


def main():
    db = SessionLocal()
    try:
        print("Fetching 2026 Tour de France startlist from procyclingstats...")
        try:
            startlist_rows = fetch_startlist()
        except Exception as exc:
            print(f"Failed to fetch the startlist: {exc}")
            print("This is expected if PCS hasn't published the 2026 startlist yet (it usually appears a few days before the race). Nothing was written - just re-run this closer to race day.")
            sys.exit(1)

        if not startlist_rows:
            print("procyclingstats returned an empty startlist - it likely isn't published yet. Nothing written.")
            sys.exit(1)

        print(f"Found {len(startlist_rows)} riders in the startlist.")

        print("Fetching world rankings for price tiering...")
        ranks_by_url = fetch_world_rankings()
        print(f"Matched rankings for {len(ranks_by_url)} riders.")

        added, updated = import_riders(db, startlist_rows, ranks_by_url)
        print(f"Added {added} new riders, updated {updated} existing riders.")

        removed = remove_placeholder_riders_if_unused(db)
        if removed:
            print(f"Removed {removed} unused placeholder riders.")

        print("Done. Run `python3 commissioner_tools.py riders` to review the full list.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
