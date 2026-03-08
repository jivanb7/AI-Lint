"""AIL001 — Prompt Injection: user input flowing unsanitized into LLM prompts."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import (
    SANITIZE_CALLS,
    get_enclosing_function,
    get_source_line,
    get_tainted_params,
    is_llm_call,
)


@registry.register
class PromptInjectionRule(BaseRule):
    rule_id = "AIL001"
    name = "PromptInjection"
    description = "User-controlled input flows unsanitized into an LLM prompt"
    severity = Severity.CRITICAL

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not is_llm_call(node):
                continue

            func = get_enclosing_function(node)
            if func is None:
                continue

            tainted = get_tainted_params(func)
            if not tainted:
                continue

            # Check all arguments (positional + keyword values) of the LLM call
            arg_nodes: list[ast.expr] = list(node.args) + [
                kw.value for kw in node.keywords
            ]

            for arg_node in arg_nodes:
                used_tainted = self._find_tainted_names(arg_node, tainted)
                if not used_tainted:
                    continue

                # Check if any sanitization happened before this call
                unsanitized = {
                    name
                    for name in used_tainted
                    if not self._is_sanitized(name, func, node)
                }
                if unsanitized:
                    names = ", ".join(sorted(unsanitized))
                    findings.append(
                        Finding(
                            rule_id=self.rule_id,
                            rule_name=self.name,
                            severity=self.severity,
                            message=(
                                f"User input ({names}) flows into LLM call "
                                f"without sanitization"
                            ),
                            location=Location(
                                file=file_path,
                                line=node.lineno,
                                col=node.col_offset,
                            ),
                            fix_suggestion=(
                                "Sanitize user input before passing to LLM: "
                                "validate length, strip special characters, or "
                                "use a dedicated sanitization library."
                            ),
                            source_line=get_source_line(source_lines, node.lineno),
                        )
                    )
                    break  # One finding per call is enough

        return findings

    def _find_tainted_names(
        self, node: ast.expr, tainted: set[str]
    ) -> set[str]:
        """Find tainted variable names referenced in an expression tree."""
        found: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id in tainted:
                found.add(child.id)
        return found

    def _is_sanitized(
        self,
        name: str,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        call_node: ast.Call,
    ) -> bool:
        """Check if *name* is sanitized before *call_node* in the function body."""
        call_line = call_node.lineno

        for node in ast.walk(func):
            # Look for reassignment: name = something.sanitize_call(...)
            if isinstance(node, ast.Assign) and node.lineno < call_line:
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        if self._value_is_sanitized(node.value, name):
                            return True

            # Look for standalone sanitize calls on the variable before the LLM call
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and node.lineno < call_line
            ):
                if self._call_is_sanitize(node.value, name):
                    return True

        return False

    def _value_is_sanitized(self, value: ast.expr, name: str) -> bool:
        """Check if a value expression involves a sanitization call on *name*."""
        for child in ast.walk(value):
            if isinstance(child, ast.Call) and self._call_is_sanitize(child, name):
                return True
        return False

    def _call_is_sanitize(self, call: ast.Call, name: str) -> bool:
        """Check if *call* is a sanitization function applied to *name*."""
        # Method call: name.strip(), name.replace(...)
        if isinstance(call.func, ast.Attribute):
            if call.func.attr in SANITIZE_CALLS:
                if isinstance(call.func.value, ast.Name) and call.func.value.id == name:
                    return True
            # Function call: html.escape(name), bleach.clean(name)
            if call.func.attr in SANITIZE_CALLS:
                for arg in call.args:
                    if isinstance(arg, ast.Name) and arg.id == name:
                        return True

        # Plain function call: sanitize(name)
        if isinstance(call.func, ast.Name) and call.func.id in SANITIZE_CALLS:
            for arg in call.args:
                if isinstance(arg, ast.Name) and arg.id == name:
                    return True

        return False
