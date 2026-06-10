"""
Set or reset an advisor's password in the agents collection.

The hash format is werkzeug-compatible scrypt, the same format already used
by existing agent documents, so both old and new credentials verify through
app.core.security.verify_password.

Usage (from repo root):
  python scripts/set_advisor_password.py <username-or-email> <new-password>

Set MONGODB_URL and MONGODB_DATABASE in your environment or .env before running.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.security import hash_password


async def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    ident, password = sys.argv[1].strip().lower(), sys.argv[2]
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        sys.exit(1)

    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]

    result = await db["agents"].update_one(
        {"$or": [{"username": ident}, {"email": ident}]},
        {"$set": {"password": hash_password(password)}},
    )
    if result.matched_count == 0:
        print(f"No agent found with username or email '{ident}'.")
        sys.exit(1)

    print(f"Password updated for '{ident}'.")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
