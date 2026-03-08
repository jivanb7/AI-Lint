"""Tests for AIL004 — MissingRetryLogic."""

from __future__ import annotations

from ailint.rules.ail004_missing_retry import MissingRetryRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_llm_call_in_function_no_retry():
    """LLM call in function with no retry decorator or loop should trigger."""
    source = """
        def call_llm():
            return client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL004"


def test_module_level_llm_call_no_retry():
    """Module-level LLM call with no enclosing function should trigger."""
    source = """
        result = llm.invoke("hello")
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL004"


def test_function_with_try_but_no_retry():
    """Function with try/except but no retry pattern should still trigger."""
    source = """
        def call_llm():
            try:
                return client.chat.completions.create(messages=[])
            except Exception as e:
                raise
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 1
    assert findings[0].rule_id == "AIL004"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_function_with_tenacity_retry_decorator():
    """Function decorated with @tenacity.retry should not trigger."""
    source = """
        import tenacity

        @tenacity.retry
        def call_llm():
            return client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 0


def test_function_with_retry_decorator():
    """Function decorated with @retry should not trigger."""
    source = """
        @retry
        def call_llm():
            return client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 0


def test_function_with_backoff_decorator():
    """Function decorated with @backoff.on_exception should not trigger."""
    source = """
        import backoff

        @backoff.on_exception(backoff.expo, Exception)
        def call_llm():
            return client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 0


def test_function_with_manual_retry_loop():
    """Function with while loop containing try/except and sleep should not trigger."""
    source = """
        import time

        def call_llm():
            attempts = 0
            while attempts < 3:
                try:
                    return client.chat.completions.create(messages=[])
                except Exception:
                    time.sleep(1)
                    attempts += 1
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 0


def test_non_llm_function():
    """Function with no LLM calls should not trigger."""
    source = """
        def process_data(items):
            return [x * 2 for x in items]
    """
    findings = parse_and_check(source, MissingRetryRule)
    assert len(findings) == 0
