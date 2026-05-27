"""Monitoring session with state persistence."""

from __future__ import annotations

import enum
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from activelog_agent.action import Action
from activelog_agent.rule import AlertRule


class SessionState(enum.Enum):
    """Lifecycle state of a monitoring session."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MonitoringSession:
    """Tracks the state of a single monitoring run.

    Attributes:
        id: Unique session identifier.
        name: Human-readable session name.
        rules: Alert rules active in this session.
        actions: Actions that have been fired.
        state: Current lifecycle state.
        created_at: When the session was created.
        started_at: When monitoring began.
        stopped_at: When monitoring ended.
        lines_processed: Total lines examined.
        alerts_fired: Total alerts triggered.
    """

    name: str = "default"
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    rules: list[AlertRule] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    state: SessionState = SessionState.CREATED
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    lines_processed: int = 0
    alerts_fired: int = 0
    _throttle_cooldowns: dict[str, float] = field(
        default_factory=dict, repr=False
    )

    # -- lifecycle --------------------------------------------------------

    def start(self) -> None:
        """Transition to RUNNING."""
        if self.state == SessionState.RUNNING:
            return
        self.state = SessionState.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def pause(self) -> None:
        """Transition to PAUSED."""
        if self.state != SessionState.RUNNING:
            return
        self.state = SessionState.PAUSED

    def resume(self) -> None:
        """Resume from PAUSED."""
        if self.state == SessionState.PAUSED:
            self.state = SessionState.RUNNING

    def stop(self) -> None:
        """Transition to STOPPED."""
        self.state = SessionState.STOPPED
        self.stopped_at = datetime.now(timezone.utc)

    def error(self) -> None:
        """Mark session as errored."""
        self.state = SessionState.ERROR
        self.stopped_at = datetime.now(timezone.utc)

    # -- rules -----------------------------------------------------------

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        return len(self.rules) < before

    def get_rule(self, rule_id: str) -> AlertRule | None:
        for r in self.rules:
            if r.id == rule_id:
                return r
        return None

    # -- actions ----------------------------------------------------------

    def record_action(self, action: Action) -> None:
        self.actions.append(action)
        if action.action_type.value == "escalate":
            self.alerts_fired += 1

    def is_throttled(self, rule_id: str, now: float) -> bool:
        """Check if a rule is currently in throttle cooldown."""
        cooldown_end = self._throttle_cooldowns.get(rule_id)
        if cooldown_end is None:
            return False
        if now >= cooldown_end:
            del self._throttle_cooldowns[rule_id]
            return False
        return True

    def set_throttle(self, rule_id: str, cooldown_seconds: float, now: float) -> None:
        """Enter throttle cooldown for a rule."""
        self._throttle_cooldowns[rule_id] = now + cooldown_seconds

    # -- stats ------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "rules": len(self.rules),
            "actions": len(self.actions),
            "lines_processed": self.lines_processed,
            "alerts_fired": self.alerts_fired,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
        }

    # -- persistence ------------------------------------------------------

    def save(self, path: str | Path) -> None:
        """Persist session state to a JSON file."""
        data = {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "rules": [r.to_dict() for r in self.rules],
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "lines_processed": self.lines_processed,
            "alerts_fired": self.alerts_fired,
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> MonitoringSession:
        """Restore session state from a JSON file."""
        data = json.loads(Path(path).read_text())
        session = cls(
            id=data["id"],
            name=data["name"],
            state=SessionState(data["state"]),
            rules=[AlertRule.from_dict(r) for r in data.get("rules", [])],
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"])
                if data.get("started_at")
                else None
            ),
            stopped_at=(
                datetime.fromisoformat(data["stopped_at"])
                if data.get("stopped_at")
                else None
            ),
            lines_processed=data.get("lines_processed", 0),
            alerts_fired=data.get("alerts_fired", 0),
        )
        return session
