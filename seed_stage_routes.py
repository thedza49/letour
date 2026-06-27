"""
Phase E.5 stage route seed.

One-time script (re-runnable) that populates Stage.route_name for all
21 stages, e.g. "Barcelone to Barcelone" or "Gap to Alpe d'Huez" - the
text the redesigned Home page wants to show next to each stage (see
DESIGN.md / README Phase E.5).

ROUTE_NAMES below is transcribed directly from the official ASO route
table (letour.fr/en/overall-route), not scraped - the 2026 route was
finalized and published well before this script was written, so this
is just static data entry rather than something that needs scraping
logic or network access. If ASO amends a stage later, update the
matching tuple below and re-run.

Re-running this script overwrites route_name for every stage - safe,
since this is reference data with one correct value at any given time.

Usage:
    python3 seed_stage_routes.py
"""
from app.models import SessionLocal, Stage

# (stage_number, "Start to Finish") - in race order, matching the
# official ASO route. Town names kept as published (French spelling,
# e.g. "Barcelone" not "Barcelona").
ROUTE_NAMES = [
    (1, "Barcelone to Barcelone"),
    (2, "Tarragone to Barcelone"),
    (3, "Granollers to Les Angles"),
    (4, "Carcassonne to Foix"),
    (5, "Lannemezan to Pau"),
    (6, "Pau to Gavarnie-Gèdre"),
    (7, "Hagetmau to Bordeaux"),
    (8, "Périgueux to Bergerac"),
    (9, "Malemort to Ussel"),
    (10, "Aurillac to Le Lioran"),
    (11, "Vichy to Nevers"),
    (12, "Circuit Nevers Magny-Cours to Chalon-sur-Saône"),
    (13, "Dole to Belfort"),
    (14, "Mulhouse to Le Markstein Fellering"),
    (15, "Champagnole to Plateau de Solaison"),
    (16, "Évian-les-Bains to Thonon-les-Bains"),
    (17, "Chambery to Voiron"),
    (18, "Voiron to Orcières-Merlette"),
    (19, "Gap to Alpe d'Huez"),
    (20, "Le Bourg d'Oisans to Alpe d'Huez"),
    (21, "Thoiry to Paris Champs-Élysées"),
]


def main():
    db = SessionLocal()
    try:
        updated = 0
        missing = []

        for stage_number, route_name in ROUTE_NAMES:
            stage = db.query(Stage).filter(Stage.stage_number == stage_number).first()
            if not stage:
                missing.append(stage_number)
                continue
            stage.route_name = route_name
            updated += 1

        db.commit()
        print(f"Updated route_name for {updated} of {len(ROUTE_NAMES)} stages.")
        if missing:
            print(f"Stage(s) {missing} not found in the database - run seed_stages.py first, then re-run this script.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
