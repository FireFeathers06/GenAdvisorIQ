# app/services/query_service.py
from app.services.llm_service import call_llm
from app.services.database_service import DatabaseService
from typing import Dict, Any
import json

def build_financial_context(context: Dict[str, Any]) -> str:
    """Build detailed financial context from MongoDB data"""
    if "error" in context:
        return f"Error loading customer data: {context['error']}"
    
    customer = context.get("customer", {})
    financial_summary = context.get("financial_summary", {})
    assets = context.get("assets", [])
    liabilities = context.get("liabilities", [])
    insurance = context.get("insurance", [])
    goals = context.get("goals", [])
    dependents = context.get("dependents", [])
    
    def n(val, default=0):
        """Coerce None → default so :, formatting never fails."""
        return val if val is not None else default

    context_prompt = f"""
CUSTOMER PROFILE:
- Name: {customer.get('first_name', '')} {customer.get('last_name', '')}
- Age: {customer.get('dob', 'N/A')}
- Occupation: {customer.get('occupation', 'N/A')}
- Marital Status: {customer.get('marital_status', 'N/A')}
- Dependents: {len(dependents)}

FINANCIAL SUMMARY:
- Monthly Income: ${n(financial_summary.get('monthly_income')):,}
- Monthly Expenses: ${n(financial_summary.get('monthly_expenses')):,}
- Monthly Savings: ${n(financial_summary.get('monthly_savings')):,}
- Total Assets: ${n(financial_summary.get('total_assets')):,}
- Total Liabilities: ${n(financial_summary.get('total_liabilities')):,}
- Net Worth: ${n(financial_summary.get('net_worth')):,}
- Risk Profile: {customer.get('rpq_profile', 'N/A')}

ASSETS ({len(assets)} total):
"""
    for asset in assets[:5]:
        context_prompt += f"\n- {asset.get('header', 'N/A')}: ${n(asset.get('amount')):,} ({asset.get('type', 'N/A')})"

    if len(assets) > 5:
        context_prompt += f"\n- ... and {len(assets) - 5} more assets"

    context_prompt += f"\n\nLIABILITIES ({len(liabilities)} total):\n"
    for liability in liabilities[:5]:
        context_prompt += (
            f"\n- {liability.get('header', 'N/A')}: "
            f"${n(liability.get('outstanding_balance')):,} "
            f"(Rate: {liability.get('interest_rate', 'N/A')}%)"
        )

    if len(liabilities) > 5:
        context_prompt += f"\n- ... and {len(liabilities) - 5} more liabilities"

    context_prompt += f"\n\nINSURANCE POLICIES ({len(insurance)} total):\n"
    for policy in insurance[:3]:
        context_prompt += f"\n- {policy.get('product_name', 'N/A')}: Sum Assured ${n(policy.get('sum_assured')):,}"

    context_prompt += f"\n\nFINANCIAL GOALS ({len(goals)} total):\n"
    for goal in goals[:5]:
        context_prompt += (
            f"\n- {goal.get('name', 'N/A')}: "
            f"${n(goal.get('goal_amount')):,} by {goal.get('goal_year', 'N/A')} "
            f"(Current: ${n(goal.get('current_amount')):,})"
        )

    if len(goals) > 5:
        context_prompt += f"\n- ... and {len(goals) - 5} more goals"
    
    return context_prompt


# JSON schema enforced via structured outputs (output_config) — the response
# is guaranteed to match this shape, replacing the old fence-strip-and-pray
# parsing of a JSON template embedded in the prompt.
ADVICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["analysis", "recommendations", "financial_projections",
                 "risk_assessment", "next_steps", "follow_up_questions"],
    "properties": {
        "analysis": {"type": "string", "description": "Brief summary of the customer's financial situation (max 300 chars)"},
        "recommendations": {
            "type": "array",
            "description": "3-4 recommendations maximum",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["priority", "category", "title", "description",
                             "action_items", "expected_impact", "timeframe"],
                "properties": {
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "category": {"type": "string", "enum": ["savings", "investments", "debt", "insurance", "goals", "retirement"]},
                    "title": {"type": "string", "description": "Brief title (max 50 chars)"},
                    "description": {"type": "string", "description": "Detailed explanation (max 200 chars)"},
                    "action_items": {"type": "array", "items": {"type": "string"}},
                    "expected_impact": {"type": "string", "description": "Expected financial impact (max 150 chars)"},
                    "timeframe": {"type": "string", "enum": ["immediate", "short_term", "long_term"]},
                },
            },
        },
        "financial_projections": {
            "type": "object",
            "additionalProperties": False,
            "required": ["current_net_worth", "projected_net_worth_1year",
                         "projected_net_worth_5years", "monthly_savings_potential",
                         "debt_payoff_timeline", "retirement_readiness"],
            "properties": {
                "current_net_worth": {"type": "number"},
                "projected_net_worth_1year": {"type": "number"},
                "projected_net_worth_5years": {"type": "number"},
                "monthly_savings_potential": {"type": "number"},
                "debt_payoff_timeline": {"type": "string", "description": "Estimated months"},
                "retirement_readiness": {"type": "string", "description": "Percentage or status"},
            },
        },
        "risk_assessment": {
            "type": "object",
            "additionalProperties": False,
            "required": ["current_risk_level", "recommended_risk_level",
                         "risk_concerns", "risk_mitigation"],
            "properties": {
                "current_risk_level": {"type": "string", "enum": ["conservative", "moderate", "aggressive"]},
                "recommended_risk_level": {"type": "string", "enum": ["conservative", "moderate", "aggressive"]},
                "risk_concerns": {"type": "array", "items": {"type": "string"}, "description": "Max 3 items"},
                "risk_mitigation": {"type": "array", "items": {"type": "string"}, "description": "Max 3 items"},
            },
        },
        "next_steps": {"type": "array", "items": {"type": "string"}, "description": "Max 3 immediate actions"},
        "follow_up_questions": {"type": "array", "items": {"type": "string"}, "description": "Max 3 questions"},
    },
}


def build_prompt(customer_context: str, question: str) -> str:
    """Build enhanced prompt with customer context and question. The response
    shape is enforced separately by ADVICE_SCHEMA (structured outputs)."""
    return f"""You are an expert financial advisor. Use the following customer profile and context to provide personalized, actionable financial advice.

{customer_context}

CUSTOMER QUESTION:
{question}

Keep descriptions and explanations CONCISE (under 200 characters each). Limit to 3-4 recommendations maximum. Be specific with numbers and provide actionable advice based on their profile."""


async def process_query(query):
    """Process customer query with MongoDB context and Claude AI"""
    try:
        # Fetch customer context from MongoDB
        customer_context = await DatabaseService.get_customer_context(query.customer_id)
        
        # Build prompt with customer context
        context_str = build_financial_context(customer_context)
        prompt = build_prompt(context_str, query.question)
        
        # Call Claude AI — structured outputs guarantee the response matches
        # ADVICE_SCHEMA, so no fence-stripping or parse fallback is needed.
        llm_result = await call_llm(prompt, output_schema=ADVICE_SCHEMA)
        structured_response = json.loads(llm_result["response"])
        
        return {
            "structured_advice": structured_response,
            "status": "generated",
            "customer_id": query.customer_id,
            "metrics": llm_result["metrics"],
            "context_summary": {
                "total_assets": customer_context.get("financial_summary", {}).get("total_assets", 0),
                "total_liabilities": customer_context.get("financial_summary", {}).get("total_liabilities", 0),
                "net_worth": customer_context.get("financial_summary", {}).get("net_worth", 0),
            }
        }
    except Exception as e:
        return {
            "answer": f"Error processing query: {str(e)}",
            "status": "error",
            "customer_id": query.customer_id,
            "metrics": {
                "model": "N/A",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": {
                    "input_cost": 0.0,
                    "output_cost": 0.0,
                    "total_cost": 0.0,
                }
            }
        }
