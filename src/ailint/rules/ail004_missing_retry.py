"""AIL004 — Missing Retry Logic: LLM calls without retry/backoff handling."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_enclosing_function, get_source_line, is_llm_call

_RETRY_DECORATORS: set[str] = {
    "retry", "backoff", "on_exception", "stamina",
    "tenacity", "retrying",
}


@registry.register
class MissingRetryRule(BaseRule):
    rule_id = "AIL004"
    name = "MissingRetryLogic"
    description = "LLM call has no retry/backoff logic for transient failures"
    severity = Severity.WARNING

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            func = get_enclosing_function(node)
            if func is None:
                # Module-level call — flag it
                findings.append(self._make_finding(node, file_path, source_lines))
                continue

            if self._has_retry_decorator(func):
                continue

            if self._has_retry_loop(func):
                continue

            findings.append(self._make_finding(node, file_path, source_lines))

        return findings

    def _has_retry_decorator(
        self, func: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        for decorator in func.decorator_list:
            name = self._decorator_name(decorator)
            if any(part in _RETRY_DECORATORS for part in name.lower().split(".")):
                return True
        return False

    def _decorator_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._decorator_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._decorator_name(node.func)
        return ""

    def _has_retry_loop(self, func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        """Check for while/for loop with try/except and sleep — manual retry pattern."""
        for node in ast.walk(func):
            if isinstance(node, (ast.While, ast.For)):
                has_try = False
                has_sleep = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Try):
                        has_try = True
                    if isinstance(child, ast.Call):
                        call_name = self._call_name(child)
                        if "sleep" in call_name.lower():
                            has_sleep = True
                if has_try and has_sleep:
                    return True
        return False

    def _call_name(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ""

    def _make_finding(
        self, node: ast.Call, file_path: str, source_lines: list[str]
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            rule_name=self.name,
            severity=self.severity,
            message="LLM call has no retry logic — transient failures will crash",
            location=Location(
                file=file_path,
                line=node.lineno,
                col=node.col_offset,
            ),
            fix_suggestion="Add @tenacity.retry or @backoff.on_exception decorator to handle transient errors",
            source_line=get_source_line(source_lines, node.lineno),
        )
