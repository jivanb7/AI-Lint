"""Configuration loading for AI-Lint.

Supports pyproject.toml [tool.ailint], .ailint.yaml, and CLI overrides.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[no-redef]


_DEFAULT_EXCLUDE = [".venv", "venv", "node_modules", "__pycache__", ".git", ".tox", "dist", "build"]

_AILINT_YAML_TEMPLATE = """\
# AI-Lint configuration
# See https://github.com/jivanb/AI-Lint for documentation

# select: []           # List of rule IDs to enable (empty = all rules)
# ignore: []           # List of rule IDs to disable
# exclude:             # Paths/globs to skip
#   - .venv
#   - node_modules
#   - __pycache__
# severity: INFO       # Minimum severity: INFO, WARNING, ERROR, CRITICAL
# max_tokens_threshold: 1000  # Threshold for AIL012 (no-streaming rule)
# format: terminal     # Output format: terminal, json, sarif
"""


@dataclass
class AilintConfig:
    """Resolved AI-Lint configuration."""

    select: list[str] = field(default_factory=list)
    ignore: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=lambda: list(_DEFAULT_EXCLUDE))
    severity: str = "INFO"
    max_tokens_threshold: int = 1000
    format: str = "terminal"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AilintConfig:
        """Create config from a dictionary, ignoring unknown keys."""
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


def load_config(
    config_path: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> AilintConfig:
    """Load configuration with priority: CLI > explicit config > pyproject.toml > .ailint.yaml > defaults."""
    file_config: dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.suffix in (".yaml", ".yml"):
            file_config = _load_yaml(path)
        elif path.name == "pyproject.toml":
            file_config = _load_pyproject(path)
        else:
            file_config = _load_yaml(path)
    else:
        # Auto-discover config files by walking up from cwd
        file_config = _discover_config()

    # Apply CLI overrides on top
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None:
                file_config[key] = value

    return AilintConfig.from_dict(file_config)


def _is_project_root(directory: Path) -> bool:
    """Return True if this directory is a project root boundary.

    A directory is considered a root if it contains a .git directory or a
    pyproject.toml file.  Discovery stops after inspecting such a directory so
    that config files from unrelated parent projects are never picked up.
    """
    return (directory / ".git").exists() or (directory / "pyproject.toml").exists()


def _discover_config() -> dict[str, Any]:
    """Walk up from cwd looking for pyproject.toml or .ailint.yaml.

    Discovery stops at the first git root (.git directory) or at a
    pyproject.toml boundary, whichever comes first.  This prevents
    accidentally reading config files from unrelated parent projects.
    """
    current = Path.cwd()
    for directory in [current, *current.parents]:
        pyproject = directory / "pyproject.toml"
        if pyproject.exists():
            config = _load_pyproject(pyproject)
            if config:
                return config
            # pyproject.toml exists but has no [tool.ailint] — still a root boundary.
            return {}

        ailint_yaml = directory / ".ailint.yaml"
        if ailint_yaml.exists():
            return _load_yaml(ailint_yaml)

        ailint_yml = directory / ".ailint.yml"
        if ailint_yml.exists():
            return _load_yaml(ailint_yml)

        # Stop at git root even when no config file was found there.
        if (directory / ".git").exists():
            return {}

    return {}


def _load_pyproject(path: Path) -> dict[str, Any]:
    """Load [tool.ailint] section from pyproject.toml."""
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("ailint", {})
    except Exception:
        return {}


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_yaml_template() -> str:
    """Return the default .ailint.yaml template content."""
    return _AILINT_YAML_TEMPLATE
