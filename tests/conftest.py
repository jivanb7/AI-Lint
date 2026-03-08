"""Shared fixtures and helpers for AI-Lint tests."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Type

import pytest

from ailint.models import Finding
from ailint.rules.base import BaseRule
from ailint.visitor import annotate_parents


def parse_and_check(source_code: str, rule_cls: Type[BaseRule]) -> list[Finding]:
    """Parse source code and run a rule against it.

    1. Parses the source string into an AST.
    2. Annotates every node with its parent reference.
    3. Instantiates the rule and calls check().
    4. Returns the list of findings.

    Args:
        source_code: Python source code as a string.
        rule_cls: The rule class to instantiate and run.

    Returns:
        List of Finding objects produced by the rule.
    """
    source = textwrap.dedent(source_code)
    tree = ast.parse(source, filename="<test>")
    annotate_parents(tree)
    source_lines = source.splitlines()
    rule = rule_cls()
    return rule.check(tree, source_lines, "<test>")


@pytest.fixture
def check_rule():
    """Fixture that returns the parse_and_check helper."""
    return parse_and_check


@pytest.fixture
def tmp_py_file(tmp_path: Path):
    """Fixture that returns a factory for creating temporary Python files."""

    def _make(content: str, name: str = "test_file.py") -> Path:
        f = tmp_path / name
        f.write_text(textwrap.dedent(content))
        return f

    return _make
