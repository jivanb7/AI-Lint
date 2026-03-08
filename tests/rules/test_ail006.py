"""Tests for AIL006 — MissingErrorHandling."""

from __future__ import annotations

from ailint.rules.ail006_missing_error_handling import MissingErrorHandlingRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_llm_call_outside_try_block():
    """LLM call without try/except should trigger."""
    source = """
        def ask():
            response = client.chat.completions.create(messages=[])
            return response
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL006"


def test_module_level_llm_call_without_try():
    """Module-level LLM call with no try/except should trigger."""
    source = """
        result = llm.invoke("hello")
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL006"


def test_llm_call_after_try_but_not_inside():
    """LLM call after a try block but not inside it should trigger."""
    source = """
        def ask():
            try:
                setup()
            except Exception:
                pass
            return client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL006"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_llm_call_inside_try_block():
    """LLM call inside try/except should not trigger."""
    source = """
        def ask():
            try:
                response = client.chat.completions.create(messages=[])
                return response
            except Exception as e:
                raise
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 0


def test_llm_call_nested_in_try():
    """LLM call nested inside try block should not trigger."""
    source = """
        def ask():
            try:
                for item in items:
                    result = llm.invoke(item)
            except Exception:
                pass
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 0


def test_non_llm_call_outside_try():
    """Non-LLM call outside try should not trigger."""
    source = """
        def process():
            result = math.sqrt(4)
            return result
    """
    findings = parse_and_check(source, MissingErrorHandlingRule)
    assert len(findings) == 0
