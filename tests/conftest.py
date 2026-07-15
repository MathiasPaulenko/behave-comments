"""Shared fixtures and test infrastructure for behave-comments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeStep:
    """Mimics a Behave step object for testing."""

    text: str | None = None
    name: str = ""
    line: int = 0


@dataclass
class FakeFeature:
    """Mimics a Behave feature object."""

    filename: str | None = None
    name: str = ""
    tags: list[str] = field(default_factory=list)
    scenarios: list[Any] = field(default_factory=list)


@dataclass
class FakeScenario:
    """Mimics a Behave scenario object."""

    name: str = ""
    tags: list[str] = field(default_factory=list)
    feature: Any = None


@dataclass
class FakeContext:
    """Mimics a Behave context object."""

    _attrs: dict[str, Any] = field(default_factory=dict)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_attrs":
            super().__setattr__(name, value)
        else:
            self._attrs[name] = value

    def __getattr__(self, name: str) -> Any:
        if name == "_attrs":
            raise AttributeError(name)
        if name in self._attrs:
            return self._attrs[name]
        raise AttributeError(name)
