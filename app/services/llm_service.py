from anthropic import AsyncAnthropic
from app.core.config import CLAUDE_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

client = AsyncAnthropic(api_key=CLAUDE_API_KEY)

# Claude pricing per million tokens (USD) — update when Anthropic revises pricing
CLAUDE_PRICING: Dict[str, Dict[str, float]] = {
    # Claude 4.x family (2025–2026)
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
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

# Cache reads cost 10% of the base input rate; cache writes cost 125%.
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_MULTIPLIER = 1.25


def calculate_cost(model: str, input_tokens: int, output_tokens: int,
                   cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> Dict[str, float]:
    pricing = CLAUDE_PRICING.get(model)
    estimated = pricing is None
    if estimated:
        # Cost figures will be wrong until a rate is added — surface it in
        # logs and in the metric itself rather than failing silently.
        logger.warning("unknown_model_pricing", model=model,
                       fallback_rates=_DEFAULT_PRICING)
        pricing = _DEFAULT_PRICING
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    cache_cost = (
        (cache_read_tokens / 1_000_000) * pricing["input"] * CACHE_READ_MULTIPLIER
        + (cache_write_tokens / 1_000_000) * pricing["input"] * CACHE_WRITE_MULTIPLIER
    )
    result = {
        "input_cost": round(input_cost, 6),
        "output_cost": round(output_cost, 6),
        "total_cost": round(input_cost + output_cost + cache_cost, 6),
        "input_rate_per_million": pricing["input"],
        "output_rate_per_million": pricing["output"],
    }
    if cache_read_tokens or cache_write_tokens:
        result["cache_cost"] = round(cache_cost, 6)
    if estimated:
        result["estimated"] = True
    return result


async def call_llm(prompt: str, output_schema: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Single-turn Claude call. When output_schema is given, the response is
    constrained to that JSON schema via structured outputs — no fence-stripping
    or parse-failure fallbacks needed downstream."""
    try:
        kwargs: Dict[str, Any] = {}
        if output_schema is not None:
            kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": output_schema},
            }
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            system="You are a financial advisor.",
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
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
