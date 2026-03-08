"""Shared AST utilities used across all rules.

Provides LLM call detection heuristics, parent tracking, and helper
functions for navigating annotated AST trees.
"""

from __future__ import annotations

import ast
import re

# ---------------------------------------------------------------------------
# LLM call detection
# ---------------------------------------------------------------------------

# Dotted callee patterns that identify LLM API calls.
_LLM_CALL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\.chat\.completions\.create$"),
    re.compile(r"\.messages\.create$"),
    re.compile(r"openai\.ChatCompletion\.create$"),
    re.compile(r"\.complete$"),
    re.compile(r"llm\.(invoke|predict|generate)$"),
    re.compile(r"chain\.(run|invoke)$"),
    re.compile(r"\.generate_content$"),
    re.compile(r"anthropic\.messages\.create$"),
    re.compile(r"cohere\.chat$"),
    re.compile(r"groq\.chat\.completions\.create$"),
]

# Object names whose method calls are likely LLM-related.
_LLM_OBJECT_NAMES: set[str] = {
    "llm", "model", "client", "chat", "completion",
    "openai_client", "anthropic_client", "claude", "gpt",
}

_LLM_OBJECT_SUFFIXES: tuple[str, ...] = ("_llm", "_client")

# Suspicious parameter names that may carry user-controlled input.
TAINTED_PARAM_NAMES: set[str] = {
    "user_input", "query", "message", "text", "prompt",
    "request", "content", "question", "input_text", "user_message",
    "user_query", "user_text", "user_prompt",
}

# Sanitization calls that neutralize tainted input.
SANITIZE_CALLS: set[str] = {
    "replace", "strip", "escape", "html.escape", "bleach.clean",
    "sanitize", "clean", "validate",
}


def get_call_string(node: ast.Call) -> str:
    """Reconstruct the dotted call string from a Call node's func attribute.

    Examples:
        ``client.chat.completions.create`` -> ``"client.chat.completions.create"``
        ``llm.invoke`` -> ``"llm.invoke"``
    """
    return _dotted_name(node.func)


def _dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        # e.g. SomeFactory().method  — just get the method chain
        return _dotted_name(node.func)
    return ""


def is_llm_call(node: ast.Call) -> bool:
    """Return True if *node* looks like an LLM API call."""
    call_str = get_call_string(node)
    if not call_str:
        return False

    for pattern in _LLM_CALL_PATTERNS:
        if pattern.search(call_str):
            return True

    # Check object-name heuristic: the immediate receiver of the method call.
    if isinstance(node.func, ast.Attribute):
        obj_name = _get_receiver_name(node.func.value)
        if obj_name:
            if obj_name in _LLM_OBJECT_NAMES:
                return True
            if obj_name.endswith(_LLM_OBJECT_SUFFIXES):
                return True

    return False


def _get_receiver_name(node: ast.expr) -> str:
    """Get the leftmost Name in a chain. E.g. ``client.chat`` -> ``"client"``."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _get_receiver_name(node.value)
    return ""


# ---------------------------------------------------------------------------
# Parent tracking
# ---------------------------------------------------------------------------

def annotate_parents(tree: ast.AST) -> None:
    """Add a ``parent`` attribute to every node in *tree*."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]
    # The root module has no parent.
    tree.parent = None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tree navigation helpers
# ---------------------------------------------------------------------------

def is_inside_try(node: ast.AST) -> bool:
    """Return True if *node* sits inside the body of a Try statement."""
    current = getattr(node, "parent", None)
    while current is not None:
        if isinstance(current, ast.Try):
            return True
        current = getattr(current, "parent", None)
    return False


def get_enclosing_function(
    node: ast.AST,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Walk up from *node* to find the nearest enclosing function definition."""
    current = getattr(node, "parent", None)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current
        current = getattr(current, "parent", None)
    return None


def has_keyword(call: ast.Call, name: str) -> bool:
    """Return True if *call* has a keyword argument named *name*."""
    return any(kw.arg == name for kw in call.keywords)


def get_keyword_value(call: ast.Call, name: str) -> ast.expr | None:
    """Return the value node of keyword *name*, or None."""
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def get_tainted_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return parameter names that match suspicious user-input naming patterns."""
    tainted: set[str] = set()
    for arg in func.args.args + func.args.kwonlyargs:
        if arg.arg in TAINTED_PARAM_NAMES:
            tainted.add(arg.arg)
    return tainted


def get_source_line(source_lines: list[str], lineno: int) -> str | None:
    """Safely retrieve a source line (1-indexed) or return None."""
    if 1 <= lineno <= len(source_lines):
        return source_lines[lineno - 1].rstrip("\n")
    return None
