"""Tests for AIL010 — SyncCallInAsyncContext."""

from __future__ import annotations

from ailint.rules.ail010_sync_in_async import SyncInAsyncRule
from tests.conftest import parse_and_check


# ---------------------------------------------------------------------------
# Positive cases — should trigger
# ---------------------------------------------------------------------------


def test_sync_llm_call_in_async_function():
    """Sync LLM call (not awaited) inside async def should trigger."""
    source = """
        async def ask():
            response = client.chat.completions.create(messages=[])
            return response
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL010"
    assert "async" in findings[0].message.lower() or "event loop" in findings[0].message.lower()


def test_time_sleep_in_async_function():
    """time.sleep() inside async def should trigger."""
    source = """
        import time

        async def wait_and_call():
            time.sleep(2)
            response = await client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert any("time.sleep" in f.message for f in findings)
    assert all(f.rule_id == "AIL010" for f in findings)


def test_sync_invoke_in_async():
    """Sync llm.invoke() (not awaited) inside async function should trigger."""
    source = """
        async def run():
            result = llm.invoke("question")
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) >= 1
    assert findings[0].rule_id == "AIL010"


# ---------------------------------------------------------------------------
# Negative cases — should NOT trigger
# ---------------------------------------------------------------------------


def test_awaited_llm_call_in_async():
    """Awaited LLM call inside async def should not trigger."""
    source = """
        async def ask():
            response = await client.chat.completions.create(messages=[])
            return response
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) == 0


def test_sync_llm_call_in_sync_function():
    """Sync LLM call in a regular (non-async) function should not trigger."""
    source = """
        def ask():
            response = client.chat.completions.create(messages=[])
            return response
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) == 0


def test_asyncio_sleep_in_async_is_fine():
    """asyncio.sleep() inside async def should not trigger."""
    source = """
        import asyncio

        async def wait():
            await asyncio.sleep(1)
            response = await client.chat.completions.create(messages=[])
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) == 0


def test_empty_async_function_no_trigger():
    """Async function with no LLM or sleep calls should not trigger."""
    source = """
        async def empty():
            return 42
    """
    findings = parse_and_check(source, SyncInAsyncRule)
    assert len(findings) == 0
