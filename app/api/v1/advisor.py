# app/api/v1/advisor.py — advisor book-of-business endpoint
from fastapi import APIRouter, Request
from app.models.api import success_response, error_response
from app.core.database import mongodb
from app.models.database import Customer, Agent, Asset, Liability, Insurance, Goal, CallLog
from bson import ObjectId
from datetime import datetime
import asyncio
import re
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/advisor", tags=["Advisor"])


# ---------------------------------------------------------------------------
# Date parsing helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _age_from_dob(dob_str: str | None) -> int:
    dt = _parse_date(dob_str)
    if not dt:
        return 0
    today = datetime.today()
    return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))


def _days_since(date_str: str | None) -> int | None:
    dt = _parse_date(date_str)
    if not dt:
        return None
    return (datetime.today() - dt).days


# ---------------------------------------------------------------------------
# Health score computation
# ---------------------------------------------------------------------------

_LIQUID_RE = re.compile(r"savings|cash|liquid|fd|bank", re.IGNORECASE)


def _compute_health_score(customer: Customer, assets: list, liabilities: list,
                           goals: list, insurance: list) -> tuple[int, list]:
    income = customer.earning or 0
    expenses = customer.expenses or 0
    total_assets = sum(a.amount for a in assets)
    total_liab = sum(l.outstanding_balance for l in liabilities)

    # Savings rate component (0-30) — only scored when expenses are known
    has_expenses = customer.expenses is not None and customer.expenses > 0
    savings_rate = (income - expenses) / income if (income > 0 and has_expenses) else 0
    savings_pts = min(30, savings_rate / 0.30 * 30) if has_expenses else 0

    # Debt ratio component (0-25)
    if total_assets > 0:
        debt_ratio_pts = (1 - min(1.0, total_liab / total_assets)) * 25
    else:
        debt_ratio_pts = 0 if total_liab > 0 else 25

    # Goal progress component (0-20)
    if goals:
        prog = [min(1.0, g.current_amount / g.goal_amount) for g in goals if g.goal_amount > 0]
        goal_pts = (sum(prog) / len(prog) * 20) if prog else 0
    else:
        goal_pts = 0

    # Insurance component (0-15) — "Active" or "Inforce" counts
    _ACTIVE_STATUSES = {"active", "inforce", "in force", "in-force"}
    has_active_insurance = any(i.status.strip().lower() in _ACTIVE_STATUSES for i in insurance)
    insurance_pts = 15 if has_active_insurance else 0

    # Emergency fund component (0-10)
    liquid = sum(a.amount for a in assets if _LIQUID_RE.search(a.type or "") or _LIQUID_RE.search(a.header or ""))
    monthly_expenses = expenses if expenses > 0 else 1
    liquid_months = liquid / monthly_expenses
    emergency_pts = min(10, liquid_months / 6 * 10)

    total = savings_pts + debt_ratio_pts + goal_pts + insurance_pts + emergency_pts
    score = round(total)

    # Build hsFactors (0-100 per factor)
    savings_factor_v = round(min(100, savings_rate / 0.30 * 100)) if has_expenses else None
    hs_factors = [
        {"k": "Savings rate",    "v": savings_factor_v},
        {"k": "Debt ratio",      "v": round((1 - min(1.0, total_liab / total_assets)) * 100) if total_assets > 0 else 100},
        {"k": "Goal progress",   "v": round(sum(min(1, g.current_amount / g.goal_amount) for g in goals if g.goal_amount > 0) / max(len(goals), 1) * 100) if goals else 0},
        {"k": "Insurance",       "v": 100 if has_active_insurance else 0},
        {"k": "Emergency fund",  "v": round(min(100, liquid_months / 6 * 100))},
    ]

    return score, hs_factors


# ---------------------------------------------------------------------------
# Batch-fetch helpers (one query per collection across all customers)
# ---------------------------------------------------------------------------

async def _batch_fetch_assets(db, customer_ids: list[ObjectId]) -> dict[str, list]:
    result: dict[str, list] = {str(cid): [] for cid in customer_ids}
    async for doc in db["Assets"].find({"CustomerId": {"$in": customer_ids}}):
        try:
            a = Asset(**doc)
            result[str(a.customer_id)].append(a)
        except Exception:
            pass
    return result


async def _batch_fetch_liabilities(db, customer_ids: list[ObjectId]) -> dict[str, list]:
    result: dict[str, list] = {str(cid): [] for cid in customer_ids}
    async for doc in db["liabilities"].find({"CustomerId": {"$in": customer_ids}}):
        try:
            l = Liability(**doc)
            result[str(l.customer_id)].append(l)
        except Exception:
            pass
    return result


async def _batch_fetch_insurance(db, customer_ids: list[ObjectId]) -> dict[str, list]:
    result: dict[str, list] = {str(cid): [] for cid in customer_ids}
    async for doc in db["insurance"].find({"CustomerId": {"$in": customer_ids}}):
        try:
            i = Insurance(**doc)
            result[str(i.customer_id)].append(i)
        except Exception:
            pass
    return result


async def _batch_fetch_goals(db, customer_ids: list[ObjectId]) -> dict[str, list]:
    result: dict[str, list] = {str(cid): [] for cid in customer_ids}
    async for doc in db["goal"].find({"CustomerId": {"$in": customer_ids}}):
        try:
            g = Goal(**doc)
            result[str(g.customer_id)].append(g)
        except Exception:
            pass
    return result


async def _batch_fetch_call_logs(db, customer_ids: list[ObjectId]) -> dict[str, list]:
    result: dict[str, list] = {str(cid): [] for cid in customer_ids}
    # Sort descending so newest first; limit handled per-customer below
    async for doc in db["callLogs"].find(
        {"CustomerId": {"$in": customer_ids}},
    ).sort("Call Date", -1):
        try:
            log = CallLog(**doc)
            cid_str = str(log.customer_id)
            if len(result[cid_str]) < 5:
                result[cid_str].append(log)
        except Exception:
            pass
    return result


# ---------------------------------------------------------------------------
# Per-client enrichment
# ---------------------------------------------------------------------------

_SENTIMENT_MAP = {
    "very positive": "champion",
    "positive":      "warm",
    "postive":       "warm",   # common DB typo
    "neutral":       "warm",
    "negative":      "cooling",
    "nagative":      "cooling", # common DB typo
    "very negative": "cooling",
}

_SEGMENT_THRESHOLDS = [
    (1_000_000, "High net worth"),
    (500_000,   "Mass affluent"),
    (0,         "Emerging"),
]


def _segment(aum: int) -> str:
    for threshold, label in _SEGMENT_THRESHOLDS:
        if aum >= threshold:
            return label
    return "Emerging"


def _opp_from_goals(goals: list) -> dict:
    if not goals:
        return {"label": "No active goals", "value": 0, "type": "Review"}
    goal_count = len(goals)
    return {"label": f"Review {goal_count} goal{'s' if goal_count != 1 else ''}", "value": 0, "type": "Review"}


def _build_client_record(
    customer: Customer,
    assets: list,
    liabilities: list,
    goals: list,
    insurance: list,
    call_logs: list,
) -> dict:
    cid = str(customer.id)
    name = f"{customer.first_name} {customer.last_name}"
    initials = (customer.first_name[:1] + customer.last_name[:1]).upper()
    age = _age_from_dob(customer.dob)

    total_assets = sum(a.amount for a in assets)
    total_liab = sum(l.outstanding_balance for l in liabilities)
    net_worth = total_assets - total_liab
    income = customer.earning or 0
    expenses = customer.expenses or 0
    savings = income - expenses

    health_score, hs_factors = _compute_health_score(customer, assets, liabilities, goals, insurance)

    # Last contact
    last_contact_days = None
    last_sentiment_raw = None
    for log in sorted(call_logs, key=lambda x: _parse_date(x.call_date) or datetime.min, reverse=True):
        if last_contact_days is None:
            last_contact_days = _days_since(log.call_date)
        if last_sentiment_raw is None:
            # The field has a trailing space in alias "Customer Sentiment "
            last_sentiment_raw = log.customer_sentiment.strip().lower()
        if last_contact_days is not None and last_sentiment_raw is not None:
            break

    last_contact_days = last_contact_days if last_contact_days is not None else 999
    sentiment = _SENTIMENT_MAP.get(last_sentiment_raw or "", "warm")

    flag = last_contact_days > 60 or health_score < 60

    seg = _segment(total_assets)
    opp = _opp_from_goals(goals)

    # who string
    who_parts = []
    if customer.occupation:
        who_parts.append(customer.occupation)
    if age:
        who_parts.append(f"{age} yrs")
    if customer.rpq_profile:
        who_parts.append(customer.rpq_profile)
    who = " · ".join(who_parts)

    # priority score: higher = more urgent
    priority = 0
    if flag:
        priority += 40
    if last_contact_days > 60:
        priority += min(30, last_contact_days - 60)
    priority += max(0, 60 - health_score)
    priority = min(99, priority)

    action = "Annual review"
    if last_contact_days > 90:
        action = "Urgent: schedule call"
    elif last_contact_days > 60:
        action = "Re-engagement call"
    elif goals:
        action = f"Review {len(goals)} goal{'s' if len(goals) != 1 else ''}"

    return {
        "id": cid,
        "name": name,
        "initials": initials,
        "occupation": customer.occupation,
        "age": age,
        "persona": customer.persona or "",
        "rpq_profile": customer.rpq_profile or "",
        "aum": total_assets,
        "net_worth": net_worth,
        "total_assets": total_assets,
        "total_liabilities": total_liab,
        "monthly_income": income,
        "monthly_expenses": expenses,
        "monthly_savings": savings,
        "health_score": health_score,
        "hs_factors": hs_factors,
        "last_contact_days": last_contact_days,
        "last_sentiment": (last_sentiment_raw or "").title(),
        "goal_count": len(goals),
        "flag": flag,
        "summary": customer.summary or None,
        "priority": priority,
        "segment": seg,
        "who": who,
        "score": health_score,
        "lastContact": last_contact_days,
        "sentiment": sentiment,
        "opp": opp,
        "action": action,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/book", summary="Advisor book of business")
async def get_advisor_book(request: Request):
    request_id: str = getattr(request.state, "request_id", None)
    try:
        db = mongodb.get_db()

        # Fetch all customers
        customers: list[Customer] = []
        async for doc in db["customers"].find({}):
            try:
                customers.append(Customer(**doc))
            except Exception as e:
                logger.warning("skip_bad_customer_doc", error=str(e))

        if not customers:
            return success_response({
                "advisor": {"name": "Advisor", "initials": "A", "title": "Wealth Advisor"},
                "kpis": {"total_aum": 0, "client_count": 0, "at_risk_count": 0, "goal_count": 0},
                "clients": [],
            }, request_id=request_id)

        # Pick the agent from the first customer (all customers share one advisor in this demo)
        agent: Agent | None = None
        if customers:
            agent_id = str(customers[0].agent_id) if customers[0].agent_id else None
            if agent_id:
                agent_doc = await db["agents"].find_one({"_id": ObjectId(agent_id)})
                if agent_doc:
                    try:
                        agent = Agent(**agent_doc)
                    except Exception:
                        pass

        object_ids = [c.id for c in customers if c.id]

        # Batch-fetch all related data in parallel
        assets_map, liab_map, insurance_map, goals_map, calls_map = await asyncio.gather(
            _batch_fetch_assets(db, object_ids),
            _batch_fetch_liabilities(db, object_ids),
            _batch_fetch_insurance(db, object_ids),
            _batch_fetch_goals(db, object_ids),
            _batch_fetch_call_logs(db, object_ids),
        )

        # Build client records
        client_records = []
        for c in customers:
            cid = str(c.id)
            try:
                rec = _build_client_record(
                    c,
                    assets_map.get(cid, []),
                    liab_map.get(cid, []),
                    goals_map.get(cid, []),
                    insurance_map.get(cid, []),
                    calls_map.get(cid, []),
                )
                client_records.append(rec)
            except Exception as e:
                logger.warning("skip_bad_client", customer_id=cid, error=str(e))

        # Sort by priority desc
        client_records.sort(key=lambda x: x["priority"], reverse=True)

        # KPIs
        total_aum = sum(r["aum"] for r in client_records)
        at_risk = sum(1 for r in client_records if r["flag"])
        goal_count = sum(r["goal_count"] for r in client_records)

        # Advisor info
        if agent:
            fn = getattr(agent, "first_name", "") or ""
            ln = getattr(agent, "last_name", "") or ""
            advisor_name = f"{fn} {ln}".strip() or "Advisor"
            initials = (fn[:1] + ln[:1]).upper() or "A"
            company = getattr(agent, "company", None) or "Meridian Capital"
            advisor_title = f"Senior Advisor · {company}"
        else:
            advisor_name = "Advisor"
            initials = "A"
            advisor_title = "Senior Advisor · Meridian Capital"

        return success_response({
            "advisor": {
                "name": advisor_name,
                "initials": initials,
                "title": advisor_title,
            },
            "kpis": {
                "total_aum": total_aum,
                "client_count": len(client_records),
                "at_risk_count": at_risk,
                "goal_count": goal_count,
            },
            "clients": client_records,
        }, request_id=request_id)

    except Exception as e:
        logger.error("advisor_book_error", error=str(e))
        return error_response("SERVER_ERROR", str(e), request_id=request_id)
