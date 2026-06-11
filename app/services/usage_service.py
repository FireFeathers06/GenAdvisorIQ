# app/services/usage_service.py — per-advisor AI usage: budget checks + analytics rollups
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from bson import ObjectId

from app.core.database import mongodb

# Endpoints that consume Claude tokens and count against the daily budget
AI_ENDPOINTS = ["/api/v1/chat/complete", "/api/v1/copilot/ask"]


async def tokens_used_today(advisor_id: str) -> int:
    """Sum of AI tokens consumed by this advisor since midnight UTC."""
    db = mongodb.get_db()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pipeline = [
        {"$match": {
            "advisor_id": ObjectId(advisor_id),
            "endpoint": {"$in": AI_ENDPOINTS},
            "timestamp": {"$gte": today},
        }},
        {"$group": {"_id": None, "tokens": {"$sum": {"$ifNull": ["$tokens_used", 0]}}}},
    ]
    result = await db["api_usage"].aggregate(pipeline).to_list(length=1)
    return int(result[0]["tokens"]) if result else 0


def _group_stage() -> Dict[str, Any]:
    return {
        "requests": {"$sum": 1},
        "tokens": {"$sum": {"$ifNull": ["$tokens_used", 0]}},
        "cost_usd": {"$sum": {"$ifNull": ["$cost_usd", 0.0]}},
    }


async def advisor_usage_rollup(advisor_id: str, days: int = 14) -> Dict[str, Any]:
    """Per-advisor AI usage: totals, today, per-endpoint, and a daily series."""
    db = mongodb.get_db()
    coll = db["api_usage"]
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    since = (now - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    base = {"advisor_id": ObjectId(advisor_id), "endpoint": {"$in": AI_ENDPOINTS}}

    async def _one(match):
        rows = await coll.aggregate([
            {"$match": match},
            {"$group": {"_id": None, **_group_stage()}},
        ]).to_list(length=1)
        row = rows[0] if rows else {"requests": 0, "tokens": 0, "cost_usd": 0.0}
        return {
            "requests": row["requests"],
            "tokens": int(row["tokens"]),
            "cost_usd": round(row["cost_usd"], 4),
        }

    total = await _one(base)
    today_stats = await _one({**base, "timestamp": {"$gte": today}})

    per_endpoint = []
    async for row in coll.aggregate([
        {"$match": base},
        {"$group": {"_id": "$endpoint", **_group_stage()}},
        {"$sort": {"tokens": -1}},
    ]):
        per_endpoint.append({
            "endpoint": row["_id"],
            "requests": row["requests"],
            "tokens": int(row["tokens"]),
            "cost_usd": round(row["cost_usd"], 4),
        })

    # Timestamps are ISO strings, so the first 10 chars are the UTC date
    daily_map: Dict[str, Dict[str, Any]] = {}
    async for row in coll.aggregate([
        {"$match": {**base, "timestamp": {"$gte": since}}},
        {"$group": {"_id": {"$substrBytes": ["$timestamp", 0, 10]}, **_group_stage()}},
    ]):
        daily_map[row["_id"]] = row

    daily = []
    for i in range(days):
        date = (now - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        row = daily_map.get(date, {"requests": 0, "tokens": 0, "cost_usd": 0.0})
        daily.append({
            "date": date,
            "requests": row["requests"],
            "tokens": int(row["tokens"]),
            "cost_usd": round(row["cost_usd"], 4),
        })

    return {"total": total, "today": today_stats,
            "endpoints": per_endpoint, "daily": daily}
