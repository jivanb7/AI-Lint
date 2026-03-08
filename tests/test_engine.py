"""Tests for the AnalysisEngine."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

import ailint.rules  # noqa: F401 — trigger registration
from ailint.config import AilintConfig
from ailint.engine import AnalysisEngine
from ailint.models import Severity
from ailint.registry import RuleRegistry, registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(config: AilintConfig | None = None) -> AnalysisEngine:
    """Create an engine with default config and global registry."""
    if config is None:
        config = AilintConfig()
    return AnalysisEngine(config, registry)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def test_collect_single_python_file(tmp_path: Path):
    """Engine should collect a single .py file passed directly."""
    py_file = tmp_path / "example.py"
    py_file.write_text("x = 1\n")
    engine = make_engine()
    files = engine._collect_files([str(py_file)])
    assert len(files) == 1
    assert files[0].name == "example.py"


def test_collect_files_from_directory(tmp_path: Path):
    """Engine should recursively collect .py files from a directory."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.py").write_text("z = 3\n")
    engine = make_engine()
    files = engine._collect_files([str(tmp_path)])
    assert len(files) == 3


def test_collect_ignores_non_py_files(tmp_path: Path):
    """Engine should ignore non-.py files."""
    (tmp_path / "script.py").write_text("x = 1\n")
    (tmp_path / "readme.md").write_text("# README\n")
    (tmp_path / "data.json").write_text("{}\n")
    engine = make_engine()
    files = engine._collect_files([str(tmp_path)])
    assert len(files) == 1
    assert files[0].name == "script.py"


def test_collect_deduplicates_paths(tmp_path: Path):
    """Engine should not include the same file twice."""
    py_file = tmp_path / "example.py"
    py_file.write_text("x = 1\n")
    engine = make_engine()
    # Pass the same file path twice
    files = engine._collect_files([str(py_file), str(py_file)])
    assert len(files) == 1


def test_collect_respects_exclude_patterns(tmp_path: Path):
    """Engine should skip files matching exclude patterns."""
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib.py").write_text("x = 1\n")
    (tmp_path / "main.py").write_text("y = 2\n")
    config = AilintConfig(exclude=[".venv"])
    engine = make_engine(config)
    files = engine._collect_files([str(tmp_path)])
    names = [f.name for f in files]
    assert "main.py" in names
    assert "lib.py" not in names


def test_collect_handles_nonexistent_path():
    """Engine should not crash on nonexistent paths."""
    engine = make_engine()
    files = engine._collect_files(["/nonexistent/path/that/does/not/exist"])
    assert files == []


# ---------------------------------------------------------------------------
# AST parsing
# ---------------------------------------------------------------------------


def test_analyze_file_skips_syntax_errors(tmp_path: Path):
    """Engine should return no findings for files with syntax errors."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("def broken(:\n    pass\n")
    engine = make_engine()
    rules = registry.get_active_rules()
    findings = engine.analyze_file(str(bad_file), rules)
    assert findings == []


def test_analyze_file_handles_unreadable_file(tmp_path: Path):
    """Engine should return no findings for unreadable files."""
    engine = make_engine()
    rules = registry.get_active_rules()
    findings = engine.analyze_file("/nonexistent/file.py", rules)
    assert findings == []


def test_analyze_file_returns_findings_for_bad_code(tmp_path: Path):
    """Engine should return findings for code that triggers rules."""
    bad_file = tmp_path / "bad.py"
    bad_file.write_text("result = client.chat.completions.create(messages=[])\n")
    config = AilintConfig(select=["AIL002"])
    engine = make_engine(config)
    rules = registry.get_active_rules(select=["AIL002"])
    findings = engine.analyze_file(str(bad_file), rules)
    assert len(findings) >= 1
    assert all(f.rule_id == "AIL002" for f in findings)


# ---------------------------------------------------------------------------
# Inline ignore comments
# ---------------------------------------------------------------------------


def test_inline_ignore_bare_suppresses_all(tmp_path: Path):
    """# ailint: ignore on a line should suppress all findings on that line."""
    py_file = tmp_path / "test.py"
    py_file.write_text(
        "result = client.chat.completions.create(messages=[])  # ailint: ignore\n"
    )
    engine = make_engine()
    rules = registry.get_active_rules()
    findings = engine.analyze_file(str(py_file), rules)
    assert len(findings) == 0


def test_inline_ignore_specific_rule(tmp_path: Path):
    """# ailint: ignore[AIL002] should suppress only AIL002 findings."""
    py_file = tmp_path / "test.py"
    py_file.write_text(
        "result = client.chat.completions.create(messages=[])  # ailint: ignore[AIL002]\n"
    )
    config = AilintConfig(select=["AIL002", "AIL011"])
    engine = make_engine(config)
    rules = registry.get_active_rules(select=["AIL002", "AIL011"])
    findings = engine.analyze_file(str(py_file), rules)
    # AIL002 should be suppressed; AIL011 should remain
    rule_ids = {f.rule_id for f in findings}
    assert "AIL002" not in rule_ids


def test_inline_ignore_different_rule_not_suppressed(tmp_path: Path):
    """# ailint: ignore[AIL003] should not suppress AIL002 findings."""
    py_file = tmp_path / "test.py"
    py_file.write_text(
        "result = client.chat.completions.create(messages=[])  # ailint: ignore[AIL003]\n"
    )
    config = AilintConfig(select=["AIL002"])
    engine = make_engine(config)
    rules = registry.get_active_rules(select=["AIL002"])
    findings = engine.analyze_file(str(py_file), rules)
    assert len(findings) >= 1
    assert any(f.rule_id == "AIL002" for f in findings)


# ---------------------------------------------------------------------------
# analyze_paths integration
# ---------------------------------------------------------------------------


def test_analyze_paths_returns_file_count(tmp_path: Path):
    """analyze_paths should return correct files_checked count."""
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    config = AilintConfig(select=[])  # no active rules, just count files
    engine = make_engine(config)
    findings, count = engine.analyze_paths([str(tmp_path)])
    assert count == 2


def test_analyze_paths_clean_file_no_findings(tmp_path: Path):
    """Clean Python file should produce no findings."""
    clean_file = tmp_path / "clean.py"
    clean_file.write_text("x = 1\ny = x + 2\n")
    engine = make_engine()
    findings, _ = engine.analyze_paths([str(clean_file)])
    assert findings == []
