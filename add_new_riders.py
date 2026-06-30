"""
Manual patch: adds riders newly visible on the live PCS 2026 Tour
startlist page that import_startlist.py couldn't pull automatically
(Cloudflare blocking the Oracle VM as of 2026-06-29).

Pulled by hand from:
https://www.procyclingstats.com/race/tour-de-france/2026/startlist

All 7 new riders are unranked in PCS's top-100 individual ranking page,
so they get PRICE_UNRANKED (€3.0) - the same fallback import_startlist.py
itself would assign. Safe to re-run: matches by pcs_url, skips anyone
already present.

Usage (on the Oracle VM, inside the venv):
    python3 add_new_riders.py
"""
from app.models import SessionLocal, Rider

PRICE_UNRANKED = 3.0

NEW_RIDERS = [
    # (name, team, pcs_url)
    ("BAUHAUS Phil", "Bahrain - Victorious (WT)", "rider/phil-bauhaus"),
    ("CARUSO Damiano", "Bahrain - Victorious (WT)", "rider/damiano-caruso"),
    ("GRADEK Kamil", "Bahrain - Victorious (WT)", "rider/kamil-gradek"),
    ("STANNARD Robert", "Bahrain - Victorious (WT)", "rider/robert-stannard"),
    ("VAN MECHELEN Vlad", "Bahrain - Victorious (WT)", "rider/vlad-van-mechelen"),
    ("GRÉGOIRE Romain", "Groupama - FDJ United (WT)", "rider/romain-gregoire"),
    ("ARTZ Huub", "Lotto Intermarché (WT)", "rider/huub-artz"),
]


def main():
    db = SessionLocal()
    try:
        existing_urls = {
            r.pcs_url for r in db.query(Rider).filter(Rider.pcs_url.isnot(None)).all()
        }
        added = 0
        skipped = 0
        for name, team, pcs_url in NEW_RIDERS:
            if pcs_url in existing_urls:
                print(f"  Skipping {name} - already in db.")
                skipped += 1
                continue
            db.add(Rider(
                name=name,
                team=team,
                price=PRICE_UNRANKED,
                rider_type=None,
                uci_rank=None,
                is_active=True,
                pcs_url=pcs_url,
            ))
            added += 1
            print(f"  Added {name} ({team}) - €{PRICE_UNRANKED}")
        db.commit()
        print(f"\nDone. Added {added} new riders, skipped {skipped} already present.")
        print("Run `python3 commissioner_tools.py riders` to confirm.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
