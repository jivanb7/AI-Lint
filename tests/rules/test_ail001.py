"""Tests for AIL001 — PromptInjection."""

from __future__ import annotations

import pytest

from ailint.rules.ail001_prompt_injection import PromptInjectionRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_fstring_tainted_param_in_llm_call():
    """f-string with tainted param passed to LLM call should trigger."""
    source = """
        def ask(user_input):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Answer: {user_input}"}]
            )
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL001"


def test_direct_tainted_param_as_kwarg():
    """Tainted param passed directly as keyword arg should trigger."""
    source = """
        def handle(prompt):
            result = llm.invoke(prompt=prompt)
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL001"


def test_message_param_to_llm_call():
    """Parameter named 'message' flowing into LLM call should trigger."""
    source = """
        def process(message):
            out = client.complete(message)
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL001"


def test_query_param_in_chain_invoke():
    """Parameter named 'query' used in chain.invoke should trigger."""
    source = """
        def run_chain(query):
            answer = chain.invoke({"input": query})
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL001"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_sanitized_with_strip_before_call():
    """Tainted param stripped before LLM call should not trigger."""
    source = """
        def ask(user_input):
            user_input = user_input.strip()
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": user_input}]
            )
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) == 0


def test_sanitized_with_html_escape():
    """Tainted param escaped via html.escape before LLM call should not trigger."""
    source = """
        def ask(user_input):
            user_input = html.escape(user_input)
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": user_input}]
            )
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) == 0


def test_no_tainted_params():
    """Function with no tainted params should not trigger."""
    source = """
        def greet(name):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Hello {name}"}]
            )
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) == 0


def test_tainted_param_not_used_in_llm_call():
    """Tainted param present but not passed to LLM call should not trigger."""
    source = """
        def process(user_input):
            log(user_input)
            response = client.chat.completions.create(
                messages=[{"role": "system", "content": "You are helpful"}]
            )
    """
    findings = parse_and_check(source, PromptInjectionRule)
    assert len(findings) == 0


def test_module_level_call_without_function_skipped():
    """LLM call at module level (no enclosing function) should not trigger AIL001."""
    source = """
        response = client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, PromptInjectionRule)
    # AIL001 only triggers when there's an enclosing function with tainted params
    assert len(findings) == 0
