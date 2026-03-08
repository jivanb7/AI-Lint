"""Core data models for AI-Lint findings and rule metadata."""

from __future__ import annotations

from enum import IntEnum

from pydantic import BaseModel


class Severity(IntEnum):
    """Finding severity levels, ordered by importance."""

    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3


class Location(BaseModel):
    """Source location of a finding."""

    file: str
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None


class Finding(BaseModel):
    """A single lint finding produced by a rule."""

    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    location: Location
    fix_suggestion: str | None = None
    source_line: str | None = None


class RuleMetadata(BaseModel):
    """Metadata describing a registered rule."""

    rule_id: str
    name: str
    description: str
    severity: Severity
