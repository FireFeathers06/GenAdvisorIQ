"""
One-time migration: normalize MongoDB collection names to lowercase + underscores.

Collections renamed:
  Assets    → assets
  goal      → goals
  callLogs  → call_logs

Run against a non-production database first. Verify with:
  db.getCollectionNames()

Usage:
  python scripts/migrate_collection_names.py

Set MONGODB_URL and MONGODB_DATABASE in your environment or .env before running.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


RENAMES = [
    ("Assets", "assets"),
    ("goal", "goals"),
    ("callLogs", "call_logs"),
]


async def main() -> None:
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.mongodb_database]

    existing = await db.list_collection_names()
    print(f"Collections before migration: {existing}\n")

    for old_name, new_name in RENAMES:
        if old_name not in existing:
            print(f"  SKIP  {old_name!r} — not found")
            continue
        if new_name in existing:
            print(f"  SKIP  {old_name!r} → {new_name!r} — target already exists")
            continue

        await db[old_name].rename(new_name)
        print(f"  OK    {old_name!r} → {new_name!r}")

    after = await db.list_collection_names()
    print(f"\nCollections after migration: {after}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
