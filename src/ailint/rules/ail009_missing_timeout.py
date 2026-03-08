"""AIL009 — Missing Timeout: HTTP/LLM calls without timeout parameter."""

from __future__ import annotations

import ast

from ailint.models import Finding, Location, Severity
from ailint.registry import registry
from ailint.rules.base import BaseRule
from ailint.visitor import get_call_string, get_source_line, has_keyword, is_llm_call

# HTTP library call patterns that should have timeouts.
_HTTP_CALL_PATTERNS: set[str] = {
    "requests.get", "requests.post", "requests.put", "requests.delete",
    "requests.patch", "requests.head", "requests.options", "requests.request",
    "httpx.get", "httpx.post", "httpx.put", "httpx.delete",
    "httpx.patch", "httpx.head", "httpx.options", "httpx.request",
    "httpx.Client", "httpx.AsyncClient",
    "aiohttp.ClientSession",
    "urllib.request.urlopen",
}


@registry.register
class MissingTimeoutRule(BaseRule):
    rule_id = "AIL009"
    name = "MissingTimeout"
    description = "HTTP or LLM call is missing a timeout parameter"
    severity = Severity.WARNING

    def check(
        self, tree: ast.AST, source_lines: list[str], file_path: str
    ) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            call_str = get_call_string(node)
            is_http = call_str in _HTTP_CALL_PATTERNS
            is_llm = is_llm_call(node)

            if not is_http and not is_llm:
                continue

            if has_keyword(node, "timeout"):
                continue

            call_type = "HTTP" if is_http else "LLM"
            findings.append(
                Finding(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"{call_type} call is missing timeout parameter",
                    location=Location(
                        file=file_path,
                        line=node.lineno,
                        col=node.col_offset,
                    ),
                    fix_suggestion="Add timeout=30 (seconds) to prevent hanging requests",
                    source_line=get_source_line(source_lines, node.lineno),
                )
            )

        return findings
