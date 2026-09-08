"""Seed the mock user database with demo accounts + API keys.

Run from the backend directory:
    ./.venv/bin/python scripts/seed_users.py

Prints the demo credentials and keys so you can log into the portal.
"""
from __future__ import annotations

import datetime as dt
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.base import Base, SessionLocal, engine  # noqa: E402
from app.db.models import ApiKey, User  # noqa: E402
from app.services.security import generate_api_key, hash_password  # noqa: E402

DEMO_USERS = [
    # email, password, plan, monthly_limit, fixed_demo_key
    ("demo@statvault.io", "demo1234", "free", 1000, "sv_live_demo_free_key_0001"),
    ("pro@statvault.io", "pro12345", "pro", 50000, "sv_live_demo_pro_key_0002"),
    ("trial@statvault.io", "trial123", "free", 5, "sv_live_demo_trial_key_003"),
]


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        print("Seeding demo users...\n")
        for email, password, plan, limit, demo_key in DEMO_USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    plan=plan,
                    monthly_limit=limit,
                )
                db.add(user)
                db.flush()
            else:
                user.hashed_password = hash_password(password)
                user.plan = plan
                user.monthly_limit = limit

            api_key = db.scalar(select(ApiKey).where(ApiKey.user_id == user.id))
            if api_key is None:
                api_key = ApiKey(
                    key=demo_key or generate_api_key(),
                    label="default",
                    user_id=user.id,
                    period_start=dt.date.today().replace(day=1),
                )
                db.add(api_key)
            db.commit()

            print(f"  {email}")
            print(f"    password : {password}")
            print(f"    plan     : {plan}  (limit {limit}/mo)")
            print(f"    api_key  : {api_key.key}\n")
        print("Done. Log into the portal with any pair above.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
