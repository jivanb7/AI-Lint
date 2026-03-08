"""Tests for the CLI — check, list-rules, init commands."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from ailint.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# ailint check
# ---------------------------------------------------------------------------


def test_check_clean_file_exits_zero(runner, tmp_path):
    """ailint check on a clean file should exit with code 0."""
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1\ny = x + 2\n")
    result = runner.invoke(cli, ["check", str(clean)])
    assert result.exit_code == 0


def test_check_file_with_findings_exits_one(runner, tmp_path):
    """ailint check on a file with findings should exit with code 1."""
    bad = tmp_path / "bad.py"
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    result = runner.invoke(cli, ["check", str(bad)])
    assert result.exit_code == 1


def test_check_nonexistent_path_is_handled(runner):
    """ailint check on nonexistent path should exit without crashing."""
    result = runner.invoke(cli, ["check", "/nonexistent/path"])
    # Should exit 0 (no findings) because no files were found
    assert result.exit_code == 0


def test_check_with_select_filter(runner, tmp_path):
    """--select should limit which rules are run."""
    bad = tmp_path / "bad.py"
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    # Select only AIL003 (hardcoded model) — the file has no hardcoded model
    result = runner.invoke(cli, ["check", str(bad), "--select", "AIL003"])
    assert result.exit_code == 0


def test_check_with_ignore_filter(runner, tmp_path):
    """--ignore should suppress specific rules."""
    bad = tmp_path / "bad.py"
    # AIL002 fires because max_tokens missing
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    result = runner.invoke(
        cli,
        ["check", str(bad), "--select", "AIL002", "--ignore", "AIL002"],
    )
    assert result.exit_code == 0


def test_check_json_format_output(runner, tmp_path):
    """--format json should output valid JSON."""
    bad = tmp_path / "bad.py"
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    result = runner.invoke(cli, ["check", str(bad), "--format", "json", "--select", "AIL002"])
    assert result.exit_code == 1
    # Parse JSON from output
    output_text = result.output.strip()
    data = json.loads(output_text)
    assert "findings" in data
    assert "version" in data
    assert data["findings_count"] >= 1


def test_check_sarif_format_output(runner, tmp_path):
    """--format sarif should output valid SARIF JSON."""
    bad = tmp_path / "bad.py"
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    result = runner.invoke(cli, ["check", str(bad), "--format", "sarif", "--select", "AIL002"])
    assert result.exit_code == 1
    output_text = result.output.strip()
    data = json.loads(output_text)
    assert "version" in data
    assert data["version"] == "2.1.0"
    assert "runs" in data


def test_check_severity_filter(runner, tmp_path):
    """--severity CRITICAL should suppress INFO and WARNING findings."""
    bad = tmp_path / "bad.py"
    bad.write_text("result = client.chat.completions.create(messages=[])\n")
    # AIL002 is WARNING, AIL011 is INFO — both should be hidden at CRITICAL severity
    result = runner.invoke(cli, ["check", str(bad), "--severity", "CRITICAL"])
    assert result.exit_code == 0


def test_check_defaults_to_current_directory(runner, tmp_path):
    """Calling `ailint check` with no paths should default to current directory."""
    clean = tmp_path / "clean.py"
    clean.write_text("x = 1\n")
    # Use isolated filesystem so cwd is tmp_path
    with runner.isolated_filesystem(temp_dir=tmp_path):
        (Path.cwd() / "clean.py").write_text("x = 1\n")
        result = runner.invoke(cli, ["check"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# ailint list-rules
# ---------------------------------------------------------------------------


def test_list_rules_table_format(runner):
    """list-rules default (table) should include all 12 rule IDs."""
    result = runner.invoke(cli, ["list-rules"])
    assert result.exit_code == 0
    for i in range(1, 13):
        assert f"AIL{i:03d}" in result.output


def test_list_rules_json_format(runner):
    """list-rules --format json should output valid JSON with 12 rules."""
    result = runner.invoke(cli, ["list-rules", "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 12
    rule_ids = {r["rule_id"] for r in data}
    for i in range(1, 13):
        assert f"AIL{i:03d}" in rule_ids


def test_list_rules_json_has_required_fields(runner):
    """Each rule in JSON output should have required fields."""
    result = runner.invoke(cli, ["list-rules", "--format", "json"])
    data = json.loads(result.output)
    for rule in data:
        assert "rule_id" in rule
        assert "name" in rule
        assert "severity" in rule
        assert "description" in rule


# ---------------------------------------------------------------------------
# ailint init
# ---------------------------------------------------------------------------


def test_init_creates_ailint_yaml(runner, tmp_path):
    """ailint init should create .ailint.yaml in the current directory."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert Path(".ailint.yaml").exists()


def test_init_does_not_overwrite_existing_file(runner, tmp_path):
    """ailint init should not overwrite an existing .ailint.yaml."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path(".ailint.yaml").write_text("# existing config\n")
        result = runner.invoke(cli, ["init"])
        assert result.exit_code != 0 or "already exists" in result.output
        # Content should be unchanged
        assert Path(".ailint.yaml").read_text() == "# existing config\n"


def test_init_file_contains_key_options(runner, tmp_path):
    """Created .ailint.yaml should contain commented-out config options."""
    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(cli, ["init"])
        content = Path(".ailint.yaml").read_text()
        assert "severity" in content
        assert "ignore" in content


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_version_flag(runner):
    """--version should print the version string."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output
