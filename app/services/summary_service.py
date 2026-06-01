"""
Customer summary refresh service.

Generates (or refreshes) the advisor-facing `summary` field on every customer
document by sending the full financial context to Claude.

Called:
  - Automatically every week via APScheduler — only refreshes customers whose
    summary is 3+ months old or has never been generated.
  - On-demand via POST /api/v1/admin/customers/{id}/refresh-summary
  - Bulk on-demand via POST /api/v1/admin/refresh-summaries[?force=true]
"""

import asyncio
from typing import Optional
import structlog

from app.services.database_service import DatabaseService
from app.services.query_service import build_financial_context
from app.services.llm_service import call_llm, CLAUDE_PRICING
from app.core.config import settings

logger = structlog.get_logger()

_SUMMARY_PROMPT = """\
You are a financial advisor's AI assistant. Based on the complete customer \
profile below, write a concise 3-5 sentence advisor-facing summary using \
markdown **bold** for key figures.

Cover: full name, age, occupation, location, monthly income, total assets, \
total liabilities, net worth, risk profile, number of dependents, key \
financial goals, and best call time.

Write in third-person. Return only the summary paragraph — no headers, \
no JSON, no extra commentary.

CUSTOMER PROFILE:
{context}
"""

_EMPTY_METRICS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "cost_usd": 0.0,
}


async def generate_customer_summary(customer_id: str) -> tuple[Optional[str], dict]:
    """
    Fetch full context for one customer, call Claude, return (summary_text, metrics).
    summary_text is None on any failure.
    """
    context = await DatabaseService.get_customer_context(customer_id)
    if "error" in context:
        logger.warning("summary_skip_no_context", customer_id=customer_id, reason=context["error"])
        return None, _EMPTY_METRICS

    context_text = build_financial_context(context)
    prompt = _SUMMARY_PROMPT.format(context=context_text)

    result = await call_llm(prompt)
    summary = result.get("response", "").strip()

    if not summary or summary.startswith("Error calling Claude API"):
        logger.error("summary_llm_error", customer_id=customer_id, response=summary[:120])
        return None, _EMPTY_METRICS

    m = result.get("metrics", {})
    metrics = {
        "input_tokens": m.get("input_tokens", 0),
        "output_tokens": m.get("output_tokens", 0),
        "total_tokens": m.get("total_tokens", 0),
        "cost_usd": m.get("cost", {}).get("total_cost", 0.0),
    }
    return summary, metrics


async def refresh_customer_summary(customer_id: str) -> tuple[bool, dict]:
    """Generate and persist the summary for one customer. Returns (success, metrics)."""
    summary, metrics = await generate_customer_summary(customer_id)
    if summary is None:
        return False, _EMPTY_METRICS

    saved = await DatabaseService.update_customer_summary(customer_id, summary)
    if saved:
        logger.info("summary_refreshed", customer_id=customer_id, **metrics)
    else:
        logger.warning("summary_not_saved", customer_id=customer_id)
    return saved, metrics


async def refresh_all_summaries(force: bool = False) -> dict:
    """
    Weekly job: regenerate summaries for customers due for a refresh.
    force=True regenerates every customer regardless of last refresh date.

    Returns a full metrics dict including token counts, costs, and per-customer averages.
    """
    if force:
        customer_ids = await DatabaseService.get_all_customer_ids()
        mode = "force_all"
    else:
        customer_ids = await DatabaseService.get_customers_due_for_summary_refresh(months=3)
        mode = "due_only"

    total = len(customer_ids)
    logger.info("summary_batch_started", mode=mode, total=total)

    if total == 0:
        logger.info("summary_batch_nothing_due")
        return _batch_result(mode, total=0, success=0, failed=0,
                             input_tokens=0, output_tokens=0, cost_usd=0.0)

    success = failed = 0
    input_tokens = output_tokens = 0
    cost_usd = 0.0

    for idx, customer_id in enumerate(customer_ids, start=1):
        try:
            ok, m = await refresh_customer_summary(customer_id)
            if ok:
                success += 1
                input_tokens += m["input_tokens"]
                output_tokens += m["output_tokens"]
                cost_usd += m["cost_usd"]
            else:
                failed += 1
        except Exception as e:
            logger.error("summary_batch_error", customer_id=customer_id, error=str(e))
            failed += 1

        if idx < total:
            await asyncio.sleep(0.5)

    result = _batch_result(mode, total=total, success=success, failed=failed,
                           input_tokens=input_tokens, output_tokens=output_tokens,
                           cost_usd=cost_usd)
    logger.info("summary_batch_complete", **{k: v for k, v in result.items()
                                             if k not in ("projection",)})
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _batch_result(mode: str, *, total: int, success: int, failed: int,
                  input_tokens: int, output_tokens: int, cost_usd: float) -> dict:
    avg_tokens = round((input_tokens + output_tokens) / success, 1) if success else 0
    avg_cost   = round(cost_usd / success, 6) if success else 0.0

    return {
        "mode": mode,
        "customers": {"total": total, "success": success, "failed": failed},
        "tokens": {
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens,
        },
        "cost_usd": round(cost_usd, 6),
        "avg_per_customer": {
            "tokens": avg_tokens,
            "cost_usd": avg_cost,
        },
        "model": settings.claude_model,
        "projection": _build_projection(avg_cost),
    }


def _build_projection(avg_cost_per_customer: float) -> list[dict]:
    """Cost table at 10^1 … 10^5 customers, refreshed every 3 months = 4×/year."""
    rows = []
    for exp in range(1, 6):          # 10, 100, 1 000, 10 000, 100 000
        n = 10 ** exp
        per_run   = round(avg_cost_per_customer * n, 4)
        per_month = round(per_run / 3, 4)          # quarterly → monthly average
        per_year  = round(per_run * 4, 4)           # 4 refreshes per year
        rows.append({
            "customers": n,
            "per_batch_run_usd": per_run,
            "per_month_usd": per_month,
            "per_year_usd": per_year,
        })
    return rows
