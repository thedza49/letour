"""
Run this once to create the 3 coach accounts for the league.
Usage: python3 create_coaches.py

This is intentionally simple since the league has a fixed, known set of
3 coaches with no open registration. Re-running this script is safe -
it skips any team_name that already exists.
"""
import getpass
from passlib.context import CryptContext
from app.models import SessionLocal, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

COACHES = ["Team Dza", "Team Blaster", "Team MP"]


def main():
    db = SessionLocal()
    try:
        for team_name in COACHES:
            existing = db.query(User).filter(User.team_name == team_name).first()
            if existing:
                print(f"Skipping '{team_name}' - account already exists.")
                continue

            print(f"\nSetting up: {team_name}")
            email = input("  Email: ").strip().lower()
            password = getpass.getpass("  Password: ")
            confirm = getpass.getpass("  Confirm password: ")

            if password != confirm:
                print("  Passwords did not match - skipping this coach. Re-run the script to try again.")
                continue

            user = User(
                email=email,
                team_name=team_name,
                password_hash=pwd_context.hash(password),
            )
            db.add(user)
            db.commit()
            print(f"  Created account for {team_name} ({email}).")
    finally:
        db.close()

    print("\nDone. Coaches can now log in at /login.")


if __name__ == "__main__":
    main()
