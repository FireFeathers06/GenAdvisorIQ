from app.services.llm_service import calculate_cost, CLAUDE_PRICING


def test_current_model_in_pricing():
    assert "claude-sonnet-4-6" in CLAUDE_PRICING


def test_calculate_cost_known_model():
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost["input_cost"] == 3.0
    assert cost["output_cost"] == 15.0
    assert cost["total_cost"] == 18.0


def test_calculate_cost_unknown_model_falls_back():
    cost = calculate_cost("nonexistent-model", input_tokens=1_000_000, output_tokens=0)
    assert cost["input_cost"] == 3.0  # falls back to sonnet pricing


def test_calculate_cost_zero_tokens():
    cost = calculate_cost("claude-sonnet-4-6", input_tokens=0, output_tokens=0)
    assert cost["total_cost"] == 0.0
