from app.services.llm_service import calculate_cost, CLAUDE_PRICING


def test_current_model_rates():
    assert CLAUDE_PRICING["claude-sonnet-4-6"] == {"input": 3.0, "output": 15.0}
    assert CLAUDE_PRICING["claude-opus-4-8"] == {"input": 5.0, "output": 25.0}
    assert CLAUDE_PRICING["claude-haiku-4-5"] == {"input": 1.0, "output": 5.0}


def test_calculate_cost_known_model():
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["input_cost"] == 3.0
    assert cost["output_cost"] == 15.0
    assert cost["total_cost"] == 18.0
    assert "estimated" not in cost


def test_calculate_cost_unknown_model_flagged():
    cost = calculate_cost("nonexistent-model", input_tokens=1_000_000, output_tokens=0)
    assert cost["input_cost"] == 3.0  # falls back to sonnet pricing
    assert cost["estimated"] is True


def test_calculate_cost_zero_tokens():
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=0, output_tokens=0)
    assert cost["total_cost"] == 0.0


def test_calculate_cost_with_cache_tokens():
    # cache reads bill at 10% of the input rate, writes at 125%
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=0, output_tokens=0,
                          cache_read_tokens=1_000_000, cache_write_tokens=1_000_000)
    assert cost["cache_cost"] == round(3.0 * 0.10 + 3.0 * 1.25, 6)
    assert cost["total_cost"] == cost["cache_cost"]
