"""Tests for AIL005 — ExposedAPIKey."""

from __future__ import annotations

from ailint.rules.ail005_exposed_api_key import ExposedAPIKeyRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_openai_sk_key_literal():
    """String matching OpenAI sk- pattern should trigger."""
    source = """
        api_key = "sk-abcdefghijklmnopqrstuvwxyz123456"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"


def test_anthropic_sk_ant_key():
    """String matching Anthropic sk-ant- pattern should trigger."""
    source = """
        key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"


def test_long_string_assigned_to_secret_variable():
    """Long alphanumeric string assigned to 'secret' variable should trigger."""
    source = """
        secret = "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"


def test_api_key_kwarg_with_value():
    """Hardcoded value passed as api_key= keyword argument should trigger."""
    source = """
        client = openai.OpenAI(api_key="supersecretpassword123")
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"


def test_bearer_token_string():
    """String starting with 'Bearer ' followed by long token should trigger."""
    source = """
        header = "Bearer abcdefghijklmnopqrstuvwxyz1234567890"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_env_var_api_key():
    """API key loaded from environment variable should not trigger."""
    source = """
        import os
        api_key = os.getenv("OPENAI_API_KEY")
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) == 0


def test_short_string_assigned_to_key_var():
    """Short string in key-named variable should not trigger (too short to be a key)."""
    source = """
        token = "abc"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) == 0


def test_plain_string_in_non_secret_context():
    """Plain string in unrelated context should not trigger."""
    source = """
        greeting = "Hello, world!"
        description = "This is a description of the service."
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) == 0


def test_long_string_in_non_secret_variable():
    """Long alphanumeric string in non-secret variable should not trigger."""
    source = """
        user_id = "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) == 0


def test_ann_assign_api_key_triggers():
    """Annotated assignment (api_key: str = ...) should trigger AIL005."""
    source = """
        api_key: str = "abcdefghijklmnopqrstuvwxyz1234567890ABCD"
    """
    findings = parse_and_check(source, ExposedAPIKeyRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL005"
