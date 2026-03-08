"""AIL005 — Exposed API Key: hardcoded secrets in source code."""

from __future__ import annotations

import ast
import re

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_source_line

# Patterns for known API key formats.
# Note: many real API keys contain hyphens in the body (e.g. sk-ant-api03-XXX,
# sk-proj-XXX), so character classes include hyphens and underscores.
_KEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^sk-[A-Za-z0-9_\-]{20,}"),         # OpenAI (sk-XXX or sk-proj-XXX)
    re.compile(r"^sk-ant-[A-Za-z0-9_\-]{20,}"),      # Anthropic (sk-ant-api03-XXX)
    re.compile(r"^Bearer\s+[A-Za-z0-9._\-]{20,}"),   # Bearer tokens
    re.compile(r"^xai-[A-Za-z0-9_\-]{20,}"),         # xAI
    re.compile(r"^gsk_[A-Za-z0-9_\-]{20,}"),         # Groq
    re.compile(r"^key-[A-Za-z0-9_\-]{20,}"),         # Generic
]

# Variable names that suggest API key storage.
_SECRET_VAR_NAMES: set[str] = {
    "api_key", "apikey", "api_secret", "secret_key", "token",
    "secret", "bearer", "auth_token", "access_token", "openai_key",
    "anthropic_key", "api_token",
}

# Long random-looking strings assigned to key-like variable names.
_LONG_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{32,}$")


@registry.register
class ExposedAPIKeyRule(BaseRule):
    rule_id = "AIL005"
    name = "ExposedAPIKey"
    description = "API key or secret appears to be hardcoded in source code"
    severity = Severity.CRITICAL

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Check for known key patterns anywhere
                if self._matches_key_pattern(node.value):
                    findings.append(
                        self._make_finding(
                            node, file_path, source_lines,
                            "String matches known API key pattern",
                        )
                    )
                    continue

                # Check for long random strings assigned to key-like variables
                parent = getattr(node, "parent", None)
                if self._is_secret_assignment(node.value, parent):
                    findings.append(
                        self._make_finding(
                            node, file_path, source_lines,
                            "Possible hardcoded secret assigned to key-like variable",
                        )
                    )
                    continue

                # Check for api_key="..." keyword argument in calls
                if isinstance(parent, ast.keyword) and parent.arg in _SECRET_VAR_NAMES:
                    if len(node.value) >= 8:  # Avoid flagging short strings
                        findings.append(
                            self._make_finding(
                                node, file_path, source_lines,
                                f'Hardcoded value passed as "{parent.arg}" argument',
                            )
                        )

        return findings

    def _matches_key_pattern(self, value: str) -> bool:
        return any(p.match(value) for p in _KEY_PATTERNS)

    def _is_secret_assignment(self, value: str, parent: ast.AST | None) -> bool:
        if not _LONG_KEY_PATTERN.match(value):
            return False
        # ast.Assign: e.g.  api_key = "sk-..."
        if isinstance(parent, ast.Assign):
            for target in parent.targets:
                if isinstance(target, ast.Name) and target.id.lower() in _SECRET_VAR_NAMES:
                    return True
        # ast.AnnAssign: e.g.  api_key: str = "sk-..."
        if isinstance(parent, ast.AnnAssign):
            target = parent.target
            if isinstance(target, ast.Name) and target.id.lower() in _SECRET_VAR_NAMES:
                return True
        return False

    def _make_finding(
        self,
        node: ast.Constant,
        file_path: str,
        source_lines: list[str],
        message: str,
    ) -> Finding:
        return Finding(
            rule_id=self.rule_id,
            rule_name=self.name,
            severity=self.severity,
            message=message,
            location=Location(
                file=file_path,
                line=node.lineno,
                col=node.col_offset,
            ),
            fix_suggestion='Use environment variables: os.getenv("API_KEY") or a secrets manager',
            source_line=get_source_line(source_lines, node.lineno),
        )
