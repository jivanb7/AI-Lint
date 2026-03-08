"""AIL007 — No Input Validation: user input passed to LLM without checks."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import (
    get_enclosing_function,
    get_source_line,
    get_tainted_params,
    is_llm_call,
)

# Names of functions/methods that indicate validation.
_VALIDATION_NAMES: set[str] = {
    "len", "strip", "lower", "upper", "match", "search",
    "fullmatch", "validate", "check", "truncate",
}


@registry.register
class NoInputValidationRule(BaseRule):
    rule_id = "AIL007"
    name = "NoInputValidation"
    description = "User input is passed to LLM without length or content validation"
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
                continue

            tainted = get_tainted_params(func)
            if not tainted:
                continue

            # Check which tainted params are used in the LLM call arguments
            used_in_call: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and child.id in tainted:
                    used_in_call.add(child.id)

            if not used_in_call:
                continue

            # Check if validation exists before the LLM call
            unvalidated = {
                name for name in used_in_call
                if not self._is_validated(name, func, node.lineno)
            }

            if unvalidated:
                names = ", ".join(sorted(unvalidated))
                findings.append(
                    Finding(
                        rule_id=self.rule_id,
                        rule_name=self.name,
                        severity=self.severity,
                        message=(
                            f"Input parameter ({names}) passed to LLM "
                            f"without validation"
                        ),
                        location=Location(
                            file=file_path,
                            line=node.lineno,
                            col=node.col_offset,
                        ),
                        fix_suggestion=(
                            "Validate user input before LLM call: check length "
                            "with len(), truncate if needed, and validate content"
                        ),
                        source_line=get_source_line(source_lines, node.lineno),
                    )
                )

        return findings

    def _is_validated(
        self,
        name: str,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        call_line: int,
    ) -> bool:
        """Check if *name* has validation applied before *call_line*."""
        for node in ast.walk(func):
            if not hasattr(node, "lineno") or node.lineno >= call_line:
                continue

            # Check for if-statements testing the variable
            if isinstance(node, ast.If):
                if self._condition_tests_var(node.test, name):
                    return True

            # Check for slicing: name[:n] or name[:MAX]
            if isinstance(node, ast.Subscript):
                if isinstance(node.value, ast.Name) and node.value.id == name:
                    return True

            # Check for validation calls: len(name), name.strip(), re.match(..., name)
            if isinstance(node, ast.Call):
                if self._is_validation_call(node, name):
                    return True

        return False

    def _condition_tests_var(self, test: ast.expr, name: str) -> bool:
        """Check if a condition expression references the variable."""
        for child in ast.walk(test):
            if isinstance(child, ast.Call):
                func_name = self._get_func_name(child)
                if func_name in _VALIDATION_NAMES:
                    for arg in child.args:
                        if isinstance(arg, ast.Name) and arg.id == name:
                            return True
            if isinstance(child, ast.Name) and child.id == name:
                # Direct comparison: if name > ... or if name == ...
                return True
        return False

    def _is_validation_call(self, call: ast.Call, name: str) -> bool:
        func_name = self._get_func_name(call)
        if func_name in _VALIDATION_NAMES:
            for arg in call.args:
                if isinstance(arg, ast.Name) and arg.id == name:
                    return True
        # Method call: name.strip()
        if isinstance(call.func, ast.Attribute):
            if (
                isinstance(call.func.value, ast.Name)
                and call.func.value.id == name
                and call.func.attr in _VALIDATION_NAMES
            ):
                return True
        return False

    def _get_func_name(self, call: ast.Call) -> str:
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return ""
