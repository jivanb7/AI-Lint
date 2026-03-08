"""Tests for AIL002 — UnboundedTokenUsage."""

from __future__ import annotations

from ailint.rules.ail002_unbounded_tokens import UnboundedTokensRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_llm_call_missing_max_tokens():
    """LLM call with no max_tokens keyword should trigger."""
    source = """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
        )
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL002"


def test_llm_invoke_missing_max_tokens():
    """llm.invoke() with no max_tokens should trigger."""
    source = """
        result = llm.invoke("What is 2+2?")
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL002"


def test_generate_content_missing_max_tokens():
    """model.generate_content() with no max_tokens should trigger."""
    source = """
        response = model.generate_content("Tell me a story")
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL002"


def test_messages_create_missing_max_tokens():
    """client.messages.create() with no max_tokens should trigger."""
    source = """
        msg = client.messages.create(model="claude-3-opus-20240229", messages=[])
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL002"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_llm_call_with_max_tokens():
    """LLM call with max_tokens set should not trigger."""
    source = """
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1024,
        )
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 0


def test_llm_call_with_max_completion_tokens():
    """LLM call with max_completion_tokens set should not trigger."""
    source = """
        response = client.chat.completions.create(
            messages=[],
            max_completion_tokens=512,
        )
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 0


def test_non_llm_call_ignored():
    """Regular function calls should not trigger AIL002."""
    source = """
        result = some_function(data=42)
        math.sqrt(4)
    """
    findings = parse_and_check(source, UnboundedTokensRule)
    assert len(findings) == 0
