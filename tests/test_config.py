"""Tests for config loading — AilintConfig, load_config, pyproject.toml, .ailint.yaml."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from ailint.config import AilintConfig, load_config, get_yaml_template


# ---------------------------------------------------------------------------
# AilintConfig defaults
# ---------------------------------------------------------------------------


def test_default_config_has_all_fields():
    """Default AilintConfig should populate all fields with sensible defaults."""
    config = AilintConfig()
    assert config.select == []
    assert config.ignore == []
    assert config.severity == "INFO"
    assert config.max_tokens_threshold == 1000
    assert config.format == "terminal"
    assert isinstance(config.exclude, list)
    assert len(config.exclude) > 0


def test_default_config_excludes_venv():
    """.venv should be in the default exclude list."""
    config = AilintConfig()
    assert ".venv" in config.exclude


def test_from_dict_ignores_unknown_keys():
    """from_dict should silently ignore keys not in the dataclass."""
    data = {"severity": "WARNING", "unknown_key": "some_value"}
    config = AilintConfig.from_dict(data)
    assert config.severity == "WARNING"
    assert not hasattr(config, "unknown_key")


def test_from_dict_sets_known_fields():
    """from_dict should correctly set known fields."""
    data = {
        "select": ["AIL001", "AIL002"],
        "ignore": ["AIL011"],
        "severity": "ERROR",
        "max_tokens_threshold": 500,
        "format": "json",
    }
    config = AilintConfig.from_dict(data)
    assert config.select == ["AIL001", "AIL002"]
    assert config.ignore == ["AIL011"]
    assert config.severity == "ERROR"
    assert config.max_tokens_threshold == 500
    assert config.format == "json"


# ---------------------------------------------------------------------------
# load_config — YAML file
# ---------------------------------------------------------------------------


def test_load_config_from_yaml_file(tmp_path: Path):
    """load_config should read settings from a .ailint.yaml file."""
    config_file = tmp_path / ".ailint.yaml"
    config_file.write_text(textwrap.dedent("""\
        severity: WARNING
        ignore:
          - AIL011
        max_tokens_threshold: 500
    """))
    config = load_config(config_path=str(config_file))
    assert config.severity == "WARNING"
    assert "AIL011" in config.ignore
    assert config.max_tokens_threshold == 500


def test_load_config_empty_yaml_uses_defaults(tmp_path: Path):
    """Empty YAML file should result in all-defaults config."""
    config_file = tmp_path / ".ailint.yaml"
    config_file.write_text("")
    config = load_config(config_path=str(config_file))
    assert config.severity == "INFO"
    assert config.format == "terminal"


# ---------------------------------------------------------------------------
# load_config — pyproject.toml
# ---------------------------------------------------------------------------


def test_load_config_from_pyproject_toml(tmp_path: Path):
    """load_config should read [tool.ailint] from pyproject.toml."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(textwrap.dedent("""\
        [tool.ailint]
        severity = "ERROR"
        select = ["AIL001", "AIL005"]
    """))
    config = load_config(config_path=str(pyproject))
    assert config.severity == "ERROR"
    assert "AIL001" in config.select
    assert "AIL005" in config.select


def test_load_config_pyproject_without_ailint_section(tmp_path: Path):
    """pyproject.toml without [tool.ailint] should use defaults."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(textwrap.dedent("""\
        [tool.pytest.ini_options]
        testpaths = ["tests"]
    """))
    config = load_config(config_path=str(pyproject))
    assert config.severity == "INFO"


# ---------------------------------------------------------------------------
# load_config — CLI overrides
# ---------------------------------------------------------------------------


def test_cli_overrides_take_precedence_over_file(tmp_path: Path):
    """CLI overrides should win over file config."""
    config_file = tmp_path / ".ailint.yaml"
    config_file.write_text("severity: WARNING\n")
    config = load_config(
        config_path=str(config_file),
        cli_overrides={"severity": "CRITICAL"},
    )
    assert config.severity == "CRITICAL"


def test_cli_override_none_values_are_ignored(tmp_path: Path):
    """CLI overrides with None values should not override file config."""
    config_file = tmp_path / ".ailint.yaml"
    config_file.write_text("severity: ERROR\n")
    config = load_config(
        config_path=str(config_file),
        cli_overrides={"severity": None},
    )
    assert config.severity == "ERROR"


def test_cli_override_select_and_ignore(tmp_path: Path):
    """CLI select and ignore should be respected."""
    config_file = tmp_path / ".ailint.yaml"
    config_file.write_text("")
    config = load_config(
        config_path=str(config_file),
        cli_overrides={"select": ["AIL001"], "ignore": ["AIL002"]},
    )
    assert config.select == ["AIL001"]
    assert config.ignore == ["AIL002"]


# ---------------------------------------------------------------------------
# yaml template
# ---------------------------------------------------------------------------


def test_get_yaml_template_returns_string():
    """get_yaml_template should return a non-empty string."""
    template = get_yaml_template()
    assert isinstance(template, str)
    assert len(template) > 0


def test_get_yaml_template_contains_common_keys():
    """Template should mention key config options."""
    template = get_yaml_template()
    assert "severity" in template
    assert "ignore" in template
    assert "exclude" in template
