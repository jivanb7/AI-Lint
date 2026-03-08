"""AIL010 — Sync in Async: synchronous blocking calls inside async functions."""

from __future__ import annotations

import ast
from collections import deque

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_call_string, get_source_line, is_llm_call


@registry.register
class SyncInAsyncRule(BaseRule):
    rule_id = "AIL010"
    name = "SyncCallInAsyncContext"
    description = "Synchronous blocking call inside an async function"
    severity = Severity.ERROR

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue

            # Walk only the direct body of this async function, not nested async defs.
            # ast.walk(node) would recurse into nested AsyncFunctionDef bodies, causing
            # each call inside a nested async def to be flagged once per enclosing async
            # scope — producing duplicate findings on the same line.
            for child in self._walk_no_nested_async(node):
                if not isinstance(child, ast.Call):
                    continue

                # Check for sync LLM calls (not awaited)
                if is_llm_call(child) and not self._is_awaited(child):
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            severity=self.severity,
                            message="Synchronous LLM call inside async function blocks the event loop",
                            location=Location(
                                file=file_path,
                                line=child.lineno,
                                col=child.col_offset,
                            ),
                            fix_suggestion=(
                                "Use the async client or await the call. "
                                "For sync libs, use asyncio.to_thread()"
                            ),
                            source_line=get_source_line(source_lines, child.lineno),
                        )
                    )

                # Check for time.sleep() in async context
                call_str = get_call_string(child)
                if call_str == "time.sleep":
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            severity=self.severity,
                            message="time.sleep() blocks the event loop — use asyncio.sleep() instead",
                            location=Location(
                                file=file_path,
                                line=child.lineno,
                                col=child.col_offset,
                            ),
                            fix_suggestion="Replace time.sleep(n) with await asyncio.sleep(n)",
                            source_line=get_source_line(source_lines, child.lineno),
                        )
                    )

        return findings

    def _walk_no_nested_async(
        self, node: ast.AST
    ):
        """Walk an AST subtree but do not descend into nested async function defs.

        This prevents double-counting: when the outer async walk visits a nested
        AsyncFunctionDef's body, calls inside it would be flagged again when the
        nested def's own outer-loop iteration runs.
        """
        queue = deque(ast.iter_child_nodes(node))
        while queue:
            child = queue.popleft()
            yield child
            # Do not recurse into nested async function definitions; they will be
            # handled by their own iteration in the outer for-loop.
            if not isinstance(child, ast.AsyncFunctionDef):
                queue.extend(ast.iter_child_nodes(child))

    def _is_awaited(self, node: ast.Call) -> bool:
        """Check if the Call node's parent is an Await expression."""
        parent = getattr(node, "parent", None)
        return isinstance(parent, ast.Await)
