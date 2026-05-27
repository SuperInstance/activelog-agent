"""Alert rules with pattern matching and thresholds."""

from __future__ import annotations

import enum
import re
import uuid
from dataclasses import dataclass, field
from typing import Any


class MatchType(enum.Enum):
    """How a rule pattern is interpreted."""

    SUBSTRING = "substring"
    REGEX = "regex"
    EXACT = "exact"


@dataclass
class AlertRule:
    """A rule that matches log lines and fires actions.

    Attributes:
        id: Unique rule identifier.
        name: Human-readable rule name.
        pattern: The string/regex to match against log lines.
        match_type: How *pattern* is interpreted.
        threshold: Number of matches within *window_seconds* required to fire.
        window_seconds: Sliding time window for threshold counting (seconds).
        case_sensitive: Whether matching is case-sensitive.
        enabled: Whether the rule is active.
        tags: Free-form tags for filtering / grouping.
        _match_count: Internal counter of recent matches.
    """

    name: str
    pattern: str
    match_type: MatchType = MatchType.SUBSTRING
    threshold: int = 1
    window_seconds: float = 60.0
    case_sensitive: bool = True
    enabled: bool = True
    tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    _match_timestamps: list[float] = field(default_factory=list, repr=False)

    # -- matching ---------------------------------------------------------

    def matches(self, line: str) -> bool:
        """Return True if *line* triggers this rule's pattern."""
        if not self.enabled:
            return False

        subject = line if self.case_sensitive else line.lower()
        pattern = self.pattern if self.case_sensitive else self.pattern.lower()

        if self.match_type == MatchType.SUBSTRING:
            return pattern in subject
        elif self.match_type == MatchType.EXACT:
            return pattern == subject
        elif self.match_type == MatchType.REGEX:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            return re.search(pattern, subject, flags) is not None
        return False

    def evaluate(self, line: str, now: float) -> bool:
        """Check *line*, update counters, return True if threshold is met."""
        if not self.matches(line):
            return False

        self._match_timestamps.append(now)
        self._prune(now)

        return len(self._match_timestamps) >= self.threshold

    def _prune(self, now: float) -> None:
        """Drop timestamps outside the sliding window."""
        cutoff = now - self.window_seconds
        self._match_timestamps = [
            ts for ts in self._match_timestamps if ts > cutoff
        ]

    def reset(self) -> None:
        """Clear match counters."""
        self._match_timestamps.clear()

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pattern": self.pattern,
            "match_type": self.match_type.value,
            "threshold": self.threshold,
            "window_seconds": self.window_seconds,
            "case_sensitive": self.case_sensitive,
            "enabled": self.enabled,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertRule:
        data = dict(data)
        data["match_type"] = MatchType(data["match_type"])
        data.pop("_match_timestamps", None)
        return cls(**data)
