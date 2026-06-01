from app.core.config import settings, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE


def test_settings_has_defaults():
    assert settings.claude_max_tokens == 2000
    assert settings.claude_temperature == 0.7
    assert settings.mongodb_database != ""


def test_backward_compat_exports():
    assert CLAUDE_MODEL == settings.claude_model
    assert CLAUDE_MAX_TOKENS == settings.claude_max_tokens
    assert CLAUDE_TEMPERATURE == settings.claude_temperature
