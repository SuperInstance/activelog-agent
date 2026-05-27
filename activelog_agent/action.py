"""Action types for log alert responses."""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class ActionType(enum.Enum):
    """What to do when an alert rule fires."""

    NOTIFY = "notify"
    ESCALATE = "escalate"
    THROTTLE = "throttle"
    SNAPSHOT = "snapshot"


@dataclass
class Action:
    """An action executed in response to a triggered alert rule.

    Attributes:
        id: Unique action identifier.
        action_type: The kind of action performed.
        rule_id: The alert rule that triggered this action.
        message: Human-readable description of what happened.
        metadata: Arbitrary extra data attached to the action.
        created_at: When the action was created (UTC).
    """

    action_type: ActionType
    rule_id: str
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # -- convenience constructors ----------------------------------------

    @classmethod
    def notify(
        cls,
        rule_id: str,
        message: str,
        channel: str = "default",
        **meta: Any,
    ) -> Action:
        """Create a NOTIFY action."""
        return cls(
            action_type=ActionType.NOTIFY,
            rule_id=rule_id,
            message=message,
            metadata={"channel": channel, **meta},
        )

    @classmethod
    def escalate(
        cls,
        rule_id: str,
        message: str,
        level: int = 1,
        **meta: Any,
    ) -> Action:
        """Create an ESCALATE action."""
        return cls(
            action_type=ActionType.ESCALATE,
            rule_id=rule_id,
            message=message,
            metadata={"level": level, **meta},
        )

    @classmethod
    def throttle(
        cls,
        rule_id: str,
        message: str,
        cooldown_seconds: int = 60,
        **meta: Any,
    ) -> Action:
        """Create a THROTTLE action (suppress further alerts for a window)."""
        return cls(
            action_type=ActionType.THROTTLE,
            rule_id=rule_id,
            message=message,
            metadata={"cooldown_seconds": cooldown_seconds, **meta},
        )

    @classmethod
    def snapshot(
        cls,
        rule_id: str,
        message: str,
        context_lines: int = 10,
        **meta: Any,
    ) -> Action:
        """Create a SNAPSHOT action (capture surrounding log lines)."""
        return cls(
            action_type=ActionType.SNAPSHOT,
            rule_id=rule_id,
            message=message,
            metadata={"context_lines": context_lines, **meta},
        )

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "rule_id": self.rule_id,
            "message": self.message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        data = dict(data)
        data["action_type"] = ActionType(data["action_type"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)
