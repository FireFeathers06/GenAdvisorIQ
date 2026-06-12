# app/services/signal_service.py — rule-based client signals.
#
# Scans a client's real MongoDB data for advisor-actionable moments (upcoming
# birthday, out-of-pocket spend with no matching cover, premiums due, goal
# shortfalls, protection gaps, expensive debt) and turns each into a copilot
# suggestion: a short chip label plus a tailored prompt that steers the
# copilot toward relevant products on the shelf.
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import re

from bson import ObjectId

from app.core.database import mongodb
import structlog

logger = structlog.get_logger()

MAX_SUGGESTIONS = 4
BIRTHDAY_WINDOW_DAYS = 45
PREMIUM_DUE_WINDOW_DAYS = 60
GOAL_HORIZON_YEARS = 2
GOAL_FUNDED_THRESHOLD = 0.60
HIGH_APR_THRESHOLD = 10
RETIREMENT_SIGNAL_AGE = 50

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y")

_MEDICAL_RE = re.compile(r"medic|hospital|doctor|surger|dental|clinic|test|pharma|treatment|health", re.IGNORECASE)
_LIFE_EVENT_RE = re.compile(r"wedding|education|tuition|school|college|vacation|travel|renovat|funeral", re.IGNORECASE)
_ACTIVE_STATUSES = {"active", "inforce", "in force", "in-force"}


def _parse_date(s) -> Optional[datetime]:
    if not s:
        return None
    s = str(s).strip()
    # ISO timestamps like 2024-01-16T00:00:00Z
    if "T" in s:
        s = s.split("T", 1)[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _first_name(customer: dict) -> str:
    return (customer.get("FirstName") or "the client").strip()


def _signal(kind: str, priority: int, label: str, ask: str) -> Dict[str, Any]:
    return {"kind": kind, "priority": priority, "label": label, "ask": ask}


async def compute_client_signals(customer_id: str) -> List[Dict[str, Any]]:
    """All detected signals for one client, highest priority first.

    Callers are responsible for the ownership check — this only reads data.
    """
    db = mongodb.get_db()
    oid = ObjectId(customer_id)
    customer = await db["customers"].find_one({"_id": oid})
    if not customer:
        return []

    insurance = [d async for d in db["insurance"].find({"CustomerId": oid})]
    goals = [d async for d in db["goal"].find({"CustomerId": oid})]
    liabilities = [d async for d in db["liabilities"].find({"CustomerId": oid})]
    transactions = [d async for d in db["transactions"].find({"CustomerId": oid})]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    name = _first_name(customer)
    signals: List[Dict[str, Any]] = []

    active_policies = [p for p in insurance
                       if str(p.get("Status", "")).strip().lower() in _ACTIVE_STATUSES]
    has_health_cover = any("health" in str(p.get("Product Type", "") or p.get("Policy Type", "")).lower()
                           or "medical" in str(p.get("Product Name", "")).lower()
                           for p in active_policies)

    # --- Premium due / overdue on an active policy -------------------------
    for p in active_policies:
        due = _parse_date(p.get("Due Date"))
        if not due:
            continue
        days = (due - now).days
        product = str(p.get("Product Name") or p.get("Policy Type") or "policy").strip()
        if days < 0:
            signals.append(_signal(
                "premium_overdue", 100,
                f"Premium overdue on {product}",
                f"{name}'s premium on their {product} policy was due {due.date()} and appears unpaid. "
                f"Draft a tactful reminder call script, explain the lapse risk, and suggest whether a "
                f"renewal or an upgraded product from the shelf fits better at this point.",
            ))
        elif days <= PREMIUM_DUE_WINDOW_DAYS:
            signals.append(_signal(
                "premium_due", 90,
                f"Premium due in {days}d ({product})",
                f"{name}'s premium on their {product} policy is due on {due.date()} ({days} days away). "
                f"Draft a friendly renewal reminder and check if a coverage review makes sense.",
            ))

    # --- Out-of-pocket spend not covered by insurance -----------------------
    for t in transactions:
        desc = str(t.get("Description", ""))
        amount = t.get("Amount") or 0
        tdate = _parse_date(t.get("TransactionDate"))
        when = tdate.date().isoformat() if tdate else "recently"
        if _MEDICAL_RE.search(desc) and not has_health_cover:
            signals.append(_signal(
                "uncovered_medical", 95,
                f"${amount:,.0f} medical spend, no health cover",
                f"{name} paid ${amount:,.0f} out of pocket on {when} for \"{desc.strip()}\" and has no "
                f"active health/medical insurance. Outline how to raise this gap empathetically and "
                f"recommend the most suitable health product(s) from the shelf with a one-line why.",
            ))
        elif _LIFE_EVENT_RE.search(desc) and amount >= 500:
            signals.append(_signal(
                "life_event_spend", 60,
                f"Life event: {desc.strip().rstrip('.')[:28]}",
                f"{name} spent ${amount:,.0f} on \"{desc.strip()}\" on {when} — a life-event expense paid "
                f"out of pocket. Suggest how to turn this into a planning conversation and which savings "
                f"or goal-based products from the shelf would fund moments like this in future.",
            ))

    # --- Birthday coming up --------------------------------------------------
    dob = _parse_date(customer.get("DOB"))
    if dob:
        next_bday = dob.replace(year=now.year)
        if next_bday < now:
            next_bday = dob.replace(year=now.year + 1)
        days = (next_bday - now).days
        if 0 <= days <= BIRTHDAY_WINDOW_DAYS:
            turning = next_bday.year - dob.year
            signals.append(_signal(
                "birthday", 80,
                f"Birthday in {days}d — plan a touchpoint",
                f"{name}'s birthday is on {next_bday.strftime('%B %d')} ({days} days away, turning {turning}). "
                f"Draft a warm, personal birthday note (not salesy) and suggest one natural follow-up — e.g. "
                f"an annual review or an age-relevant product from the shelf if one genuinely fits at {turning}.",
            ))

    # --- Goal shortfall near its target year --------------------------------
    for g in goals:
        target = g.get("Goal Amount") or 0
        current = g.get("Current Amount yearmarked for the goal") or 0
        year = g.get("Goal Year")
        gname = str(g.get("Name") or "").strip() or "Unnamed goal"
        if not target or not year:
            continue
        funded = current / target
        if funded < GOAL_FUNDED_THRESHOLD and 0 <= int(year) - now.year <= GOAL_HORIZON_YEARS:
            signals.append(_signal(
                "goal_shortfall", 70,
                f"{gname}: {round(funded * 100)}% funded for {year}",
                f"{name}'s \"{gname}\" targets ${target:,.0f} by {year} but only ${current:,.0f} "
                f"({round(funded * 100)}%) is earmarked. Calculate the required monthly top-up and recommend "
                f"which saving/wealth product from the shelf fits this timeline.",
            ))

    # --- No active protection at all ----------------------------------------
    if not active_policies:
        signals.append(_signal(
            "protection_gap", 65,
            "No active insurance on file",
            f"{name} has no active insurance policies on file. Review their income, dependents and risk "
            f"profile, then recommend a starter protection package from the shelf (health + income "
            f"protection first) with a short rationale for each pick.",
        ))

    # --- Expensive debt -------------------------------------------------------
    for l in liabilities:
        apr = l.get("InterestRate") or 0
        if apr >= HIGH_APR_THRESHOLD:
            lname = str(l.get("Header") or l.get("Type") or "a loan").strip()
            bal = l.get("OutstandingBalance") or 0
            signals.append(_signal(
                "high_apr_debt", 55,
                f"{lname} at {apr}% APR",
                f"{name} carries ${bal:,.0f} on \"{lname}\" at {apr}% APR. Sketch a payoff/consolidation "
                f"approach and whether redirecting the savings into a shelf product makes sense afterwards.",
            ))

    # --- Approaching retirement with no retirement product -------------------
    if dob:
        age = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
        has_retirement = any("retire" in str(p.get("Product Type", "")).lower() for p in active_policies) \
            or any("retire" in str(g.get("Name", "")).lower() for g in goals)
        if age >= RETIREMENT_SIGNAL_AGE and not has_retirement:
            signals.append(_signal(
                "retirement_gap", 50,
                f"Age {age}, no retirement plan on file",
                f"{name} is {age} with no retirement product or goal on file. Open a retirement-readiness "
                f"conversation and recommend the retirement products from the shelf that fit their horizon.",
            ))

    signals.sort(key=lambda s: s["priority"], reverse=True)
    return signals


async def client_suggestions(customer_id: str) -> List[Dict[str, str]]:
    """Top suggestion chips for the copilot UI."""
    signals = await compute_client_signals(customer_id)
    return [{"label": s["label"], "ask": s["ask"]} for s in signals[:MAX_SUGGESTIONS]]


def signals_summary_text(signals: List[Dict[str, Any]]) -> str:
    """Compact signal list for the copilot's client-focus system block."""
    if not signals:
        return ""
    lines = "\n".join(f"- {s['label']}" for s in signals[:6])
    return f"\nKnown signals for this client (verified from their data):\n{lines}"
