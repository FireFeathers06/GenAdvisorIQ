from anthropic import AsyncAnthropic
from app.core.config import CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE
from typing import Dict, Any

client = AsyncAnthropic(api_key=CLAUDE_API_KEY)

# Claude pricing per million tokens (USD) — update when Anthropic revises pricing
CLAUDE_PRICING: Dict[str, Dict[str, float]] = {
    # Claude 4.x family (2025–2026)
    "claude-opus-4-8": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.0},
    # Claude 3.5 family
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
    # Claude 3 legacy (kept for historical cost queries)
    "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-sonnet-20240620": {"input": 3.0, "output": 15.0},
}

_DEFAULT_PRICING = CLAUDE_PRICING["claude-sonnet-4-6"]


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
    pricing = CLAUDE_PRICING.get(model, _DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost, 6),
        "input_rate_per_million": pricing["input"],
        "output_rate_per_million": pricing["output"],
    }


async def call_llm(prompt: str) -> Dict[str, Any]:
    try:
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            system="You are a financial advisor.",
            messages=[{"role": "user", "content": prompt}],
        )

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return {
            "response": response.content[0].text,
            "metrics": {
                "model": CLAUDE_MODEL,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost": calculate_cost(CLAUDE_MODEL, input_tokens, output_tokens),
            },
        }

    except Exception as e:
        pricing = CLAUDE_PRICING.get(CLAUDE_MODEL, _DEFAULT_PRICING)
        return {
            "response": f"Error calling Claude API: {str(e)}",
            "metrics": {
                "model": CLAUDE_MODEL,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": {
                    "input_cost": 0.0,
                    "output_cost": 0.0,
                    "total_cost": 0.0,
                    "input_rate_per_million": pricing["input"],
                    "output_rate_per_million": pricing["output"],
                },
            },
        }
