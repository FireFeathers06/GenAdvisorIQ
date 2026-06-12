# app/services/copilot_service.py — server-side grounding for the advisor copilot.
#
# Hybrid retrieval design (Phase 3):
#   * an always-on book snapshot (one line per client) goes into the cached
#     system prompt so broad questions need no tool round-trips
#   * drill-down tools fetch full client data on demand; every tool query is
#     filtered by the authenticated advisor's AgentId, so a prompt can never
#     reach another advisor's book
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import asyncio
import json

from bson import ObjectId
from bson.errors import InvalidId

from app.core.database import mongodb
from app.models.database import Agent, Customer
from app.api.v1.advisor import (
    _batch_fetch_assets,
    _batch_fetch_liabilities,
    _batch_fetch_insurance,
    _batch_fetch_goals,
    _batch_fetch_call_logs,
    _build_client_record,
)
from app.services.database_service import DatabaseService
import structlog

logger = structlog.get_logger()

MAX_CALL_HISTORY = 20


def _fmt_usd(n: float) -> str:
    if abs(n) >= 1e6:
        return f"${n / 1e6:.2f}M"
    if abs(n) >= 1e3:
        return f"${round(n / 1e3)}k"
    return f"${round(n)}"


# ---------------------------------------------------------------------------
# Book snapshot → cached system prompt
# ---------------------------------------------------------------------------

async def _fetch_client_records(advisor: Agent) -> List[dict]:
    db = mongodb.get_db()
    customers: List[Customer] = []
    async for doc in db["customers"].find({"AgentId": ObjectId(str(advisor.id))}):
        try:
            customers.append(Customer(**doc))
        except Exception as e:
            logger.warning("copilot_skip_bad_customer", error=str(e))
    if not customers:
        return []

    object_ids = [c.id for c in customers if c.id]
    assets_map, liab_map, insurance_map, goals_map, calls_map = await asyncio.gather(
        _batch_fetch_assets(db, object_ids),
        _batch_fetch_liabilities(db, object_ids),
        _batch_fetch_insurance(db, object_ids),
        _batch_fetch_goals(db, object_ids),
        _batch_fetch_call_logs(db, object_ids),
    )

    records = []
    for c in customers:
        cid = str(c.id)
        try:
            records.append(_build_client_record(
                c,
                assets_map.get(cid, []),
                liab_map.get(cid, []),
                goals_map.get(cid, []),
                insurance_map.get(cid, []),
                calls_map.get(cid, []),
            ))
        except Exception as e:
            logger.warning("copilot_skip_bad_client", customer_id=cid, error=str(e))
    records.sort(key=lambda r: r["priority"], reverse=True)
    return records


async def _fetch_product_shelf() -> str:
    """The firm's product catalog (bankProducts) as compact prompt lines."""
    db = mongodb.get_db()
    lines = []
    async for doc in db["bankProducts"].find():
        ptype = str(doc.get("Product Type", "")).strip()
        pname = str(doc.get("Product Name", "")).strip()
        pcat = str(doc.get("Product Category", "") or doc.get("Product Scope", "")).strip()
        if pname:
            lines.append(f"- {pname} ({ptype}{', ' + pcat if pcat else ''})")
    return "\n".join(lines)


def _snapshot_line(r: dict) -> str:
    contact = "never contacted" if r["lastContact"] >= 999 else f"last contact {r['lastContact']}d ago"
    risk = ", AT RISK" if r["flag"] else ""
    return (
        f"- {r['name']} [id {r['id']}] — {r['segment']}, AUM {_fmt_usd(r['aum'])}, "
        f"health {r['score']}/100, {contact}, sentiment {r['sentiment']}, "
        f"{r['goal_count']} goal{'s' if r['goal_count'] != 1 else ''}, "
        f"next action: {r['action']}{risk}"
    )


async def build_system_blocks(advisor: Agent, scope: Optional[str] = None) -> tuple[List[dict], Dict[str, str]]:
    """System prompt blocks ([cached book snapshot, optional uncached client-focus
    note]) plus a {client_id: name} map for UI status labels."""
    records = await _fetch_client_records(advisor)
    product_shelf = await _fetch_product_shelf()
    advisor_name = f"{advisor.first_name} {advisor.last_name}".strip() or "the advisor"
    company = advisor.company or "GenAdvisorIQ"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_aum = sum(r["aum"] for r in records)
    at_risk = sum(1 for r in records if r["flag"])

    lines = "\n".join(_snapshot_line(r) for r in records) or "(no clients in book)"

    system_text = f"""You are Copilot, the AI assistant inside GenAdvisorIQ for {advisor_name}, a wealth advisor at {company}. You help the advisor grow and retain their book of business. Today's date is {today}.

BOOK SNAPSHOT ({len(records)} clients, {_fmt_usd(total_aum)} total AUM, {at_risk} at risk):
{lines}

PRODUCT SHELF (the only products you may recommend):
{product_shelf or "(no catalog available)"}

TOOLS: The snapshot is a summary. When a question needs specifics — assets, liabilities, income, insurance coverage, goal amounts, transactions, demographics, or what was discussed on past calls — call get_client_details or get_call_history with the client id shown in brackets. Never guess or invent numbers the snapshot doesn't contain.

RULES:
- Be concise and action-oriented (2-4 sentences unless asked to draft something). Talk like a sharp practice-management coach.
- Reference SPECIFIC client names and dollar figures from the snapshot or tool results.
- When a conversation opens a product opportunity, recommend the most relevant product(s) from the PRODUCT SHELF by name with a one-line reason grounded in the client's data. Never recommend a product that isn't on the shelf, and never pitch when it doesn't genuinely fit.
- If asked to draft an email or call script, write it ready-to-send.
- If a tool returns "not found", that client is not in this advisor's book — say so plainly.
- Never invent compliance-sensitive claims or guarantee returns.
- Format responses with markdown where it helps (bold, short bullet lists)."""

    blocks: List[dict] = [{
        "type": "text",
        "text": system_text,
        "cache_control": {"type": "ephemeral"},
    }]

    # Client focus is per-conversation, so it lives outside the cached block.
    if scope and scope.startswith("client:"):
        cid = scope.split(":", 1)[1]
        rec = next((r for r in records if r["id"] == cid), None)
        if rec:
            from app.services.signal_service import compute_client_signals, signals_summary_text
            try:
                signals = await compute_client_signals(cid)
            except Exception as e:
                logger.warning("copilot_signals_error", customer_id=cid, error=str(e))
                signals = []
            blocks.append({
                "type": "text",
                "text": (
                    f"The advisor is currently viewing {rec['name']} [id {rec['id']}]. "
                    f"Questions about 'this client' refer to them."
                    + signals_summary_text(signals)
                ),
            })
    return blocks, {r["id"]: r["name"] for r in records}


# ---------------------------------------------------------------------------
# Drill-down tools
# ---------------------------------------------------------------------------

COPILOT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_client_details",
        "description": (
            "Full financial profile for one client in the advisor's book: demographics, "
            "income and expenses, every asset, liability, insurance policy, goal, "
            "dependents, and recent out-of-pocket transactions. Use when a question "
            "needs specifics beyond the book snapshot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "The client id shown in brackets in the book snapshot",
                },
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "get_call_history",
        "description": (
            "Recent call log for one client: date, purpose, customer sentiment, feedback, "
            "and advisor notes. Use for questions about past conversations, relationship "
            "history, or what was promised on a call."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "The client id shown in brackets in the book snapshot",
                },
                "limit": {
                    "type": "integer",
                    "description": f"Number of most recent calls to return (default 10, max {MAX_CALL_HISTORY})",
                },
            },
            "required": ["client_id"],
        },
    },
]

_NOT_FOUND = json.dumps({"error": "not found", "detail": "No such client in this advisor's book."})


async def _owned_customer(advisor_id: str, client_id: str) -> Optional[dict]:
    """The ownership gate every tool goes through — AgentId is non-negotiable."""
    try:
        oid = ObjectId(client_id)
    except (InvalidId, TypeError):
        return None
    return await mongodb.get_db()["customers"].find_one(
        {"_id": oid, "AgentId": ObjectId(advisor_id)}
    )


async def _get_client_details(advisor_id: str, tool_input: dict) -> str:
    client_id = str(tool_input.get("client_id", ""))
    if not await _owned_customer(advisor_id, client_id):
        return _NOT_FOUND

    ctx = await DatabaseService.get_customer_context(client_id)
    if "error" in ctx:
        return _NOT_FOUND

    customer = ctx.get("customer") or {}
    details = {
        "name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip(),
        "demographics": {
            "dob": customer.get("dob"),
            "gender": customer.get("gender"),
            "marital_status": customer.get("marital_status"),
            "occupation": customer.get("occupation"),
            "risk_profile": customer.get("rpq_profile"),
            "risk_profile_description": customer.get("rpq_description"),
            "retirement_age": customer.get("retirement_age"),
            "best_call_time": customer.get("best_call_time"),
        },
        "financial_summary": ctx.get("financial_summary"),
        "assets": [
            {"name": a.get("header"), "type": a.get("type"),
             "amount": a.get("amount"), "firm": a.get("firm")}
            for a in ctx.get("assets", [])
        ],
        "liabilities": [
            {"name": l.get("header"), "type": l.get("type"),
             "outstanding_balance": l.get("outstanding_balance"),
             "interest_rate_pct": l.get("interest_rate"),
             "emi": l.get("emi"), "firm": l.get("firm")}
            for l in ctx.get("liabilities", [])
        ],
        "insurance": [
            {"product": p.get("product_name"), "type": p.get("policy_type"),
             "sum_assured": p.get("sum_assured"), "premium": p.get("premium"),
             "status": p.get("status"), "end_date": p.get("end_date"),
             "beneficiary": p.get("beneficiary")}
            for p in ctx.get("insurance", [])
        ],
        "goals": [
            {"name": g.get("name"), "type": g.get("goal_type"),
             "target_amount": g.get("goal_amount"),
             "current_amount": g.get("current_amount"),
             "target_year": g.get("goal_year")}
            for g in ctx.get("goals", [])
        ],
        "dependents": [
            {"name": f"{d.get('first_name', '')} {d.get('last_name', '')}".strip(),
             "relation": d.get("relation"), "dob": d.get("dob")}
            for d in ctx.get("dependents", [])
        ],
        "recent_transactions": [
            {"date": t.get("transaction_date"), "amount": t.get("amount"),
             "description": t.get("description"), "recurring": t.get("recurring_status")}
            for t in ctx.get("recent_transactions", [])
        ],
        "advisor_summary": customer.get("summary"),
    }
    return json.dumps(details, default=str)


async def _get_call_history(advisor_id: str, tool_input: dict) -> str:
    client_id = str(tool_input.get("client_id", ""))
    if not await _owned_customer(advisor_id, client_id):
        return _NOT_FOUND

    try:
        limit = min(int(tool_input.get("limit") or 10), MAX_CALL_HISTORY)
    except (TypeError, ValueError):
        limit = 10

    db = mongodb.get_db()
    calls = []
    async for doc in db["callLogs"].find(
        {"CustomerId": ObjectId(client_id)}
    ).sort("Call Date", -1).limit(limit):
        calls.append({
            "date": doc.get("Call Date"),
            "time": doc.get("Call Time"),
            "purpose": doc.get("Call Purpose"),
            "status": doc.get("Status (Opened/Closed)"),
            "sentiment": (doc.get("Customer Sentiment ") or doc.get("Customer Sentiment") or "").strip(),
            "feedback": doc.get("Customer Feedback"),
            "notes": doc.get("Notes"),
        })
    return json.dumps({"calls": calls, "count": len(calls)}, default=str)


_TOOL_RUNNERS = {
    "get_client_details": _get_client_details,
    "get_call_history": _get_call_history,
}


async def run_copilot_tool(name: str, tool_input: dict, advisor_id: str) -> str:
    runner = _TOOL_RUNNERS.get(name)
    if not runner:
        return json.dumps({"error": f"unknown tool '{name}'"})
    try:
        return await runner(advisor_id, tool_input or {})
    except Exception as e:
        logger.error("copilot_tool_error", tool=name, error=str(e))
        return json.dumps({"error": "tool execution failed"})


def tool_status_label(name: str, tool_input: dict, client_names: Dict[str, str] | None = None) -> str:
    """Human-readable status line shown in the UI while a tool runs."""
    cid = str((tool_input or {}).get("client_id", ""))
    who = (client_names or {}).get(cid, "client")
    if name == "get_client_details":
        return f"Looking up {who}'s financial details…"
    if name == "get_call_history":
        return f"Reviewing {who}'s call history…"
    return "Fetching data…"
