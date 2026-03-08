"""Tests for AIL003 — HardcodedModelName."""

from __future__ import annotations

from ailint.rules.ail003_hardcoded_model import HardcodedModelRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_gpt4_in_model_kwarg():
    """gpt-4o as model= kwarg should trigger."""
    source = """
        response = client.chat.completions.create(model="gpt-4o", messages=[])
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL003"
    assert "gpt-4o" in findings[0].message


def test_claude_in_model_kwarg():
    """claude-3-opus as model= kwarg should trigger."""
    source = """
        msg = client.messages.create(model="claude-3-opus-20240229", messages=[])
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 1
    assert "claude-3-opus-20240229" in findings[0].message


def test_gemini_in_model_kwarg():
    """gemini-pro as model= kwarg should trigger."""
    source = """
        response = model.generate_content(model="gemini-pro", contents=[])
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL003"


def test_model_assigned_to_model_variable():
    """Model name assigned to variable named 'model' should trigger."""
    source = """
        model = "gpt-4-turbo"
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL003"


def test_model_name_assigned_to_model_name_variable():
    """Model name assigned to variable named 'model_name' should trigger."""
    source = """
        model_name = "claude-2"
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL003"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_env_var_model_assignment():
    """Model loaded from environment variable should not trigger."""
    source = """
        import os
        model = os.getenv("MODEL_NAME", "gpt-4o")
    """
    findings = parse_and_check(source, HardcodedModelRule)
    # os.getenv default arg is a Constant but its parent is an ast.Call, not ast.keyword or ast.Assign to model*
    # The string "gpt-4o" here is the default for getenv, not a direct assignment to model var
    assert len(findings) == 0


def test_model_string_in_comment_like_context():
    """String that doesn't match model pattern should not trigger."""
    source = """
        greeting = "hello world"
        name = "gpt"
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 0


def test_model_string_as_non_model_kwarg():
    """Model-looking string as non-model keyword arg should not trigger."""
    source = """
        result = some_func(provider="gpt-4o")
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 0


def test_variable_named_different_from_model():
    """Model string assigned to non-model variable should not trigger."""
    source = """
        preferred_engine = "gpt-4o"
    """
    findings = parse_and_check(source, HardcodedModelRule)
    assert len(findings) == 0
