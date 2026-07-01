"""Seed the local dev database with two demo users and some sample documents."""

from . import auth
from .db import SessionLocal, init_db
from .models import Document, User

DEMO_USERS = [
    {"email": "alice@example.com", "password": "alice-password"},
    {"email": "bob@example.com", "password": "bob-password"},
]

SAMPLE_TITLES = [
    "Q1 planning notes",
    "Onboarding script",
    "Release announcement draft",
    "Customer interview summary",
    "Weekly standup notes",
]


def run() -> None:
    init_db()
    session = SessionLocal()
    try:
        if session.query(User).count() > 0:
            print("Database already seeded, skipping.")
            return

        users = []
        for entry in DEMO_USERS:
            user = User(email=entry["email"], hashed_password=auth.hash_password(entry["password"]))
            session.add(user)
            users.append(user)
        session.commit()
        for user in users:
            session.refresh(user)

        alice = users[0]
        for i, title in enumerate(SAMPLE_TITLES):
            session.add(
                Document(
                    owner_id=alice.id,
                    title=title,
                    text=f"This is sample document #{i + 1} for {title}.",
                )
            )
        session.commit()

        print("Seeded users:")
        for entry in DEMO_USERS:
            print(f"  {entry['email']} / {entry['password']}")
    finally:
        session.close()


if __name__ == "__main__":
    run()
