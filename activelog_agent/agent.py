"""Agent class — orchestrates log monitoring sessions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from activelog_agent.action import Action, ActionType
from activelog_agent.rule import AlertRule
from activelog_agent.session import MonitoringSession, SessionState
from activelog_agent.watcher import LogEntry, LogWatcher


@dataclass
class Agent:
    """Top-level agent managing monitoring sessions.

    Create an agent, add sessions with rules, then feed log entries through
    :meth:`process` or :meth:`process_lines`.

    Attributes:
        sessions: Active monitoring sessions keyed by session id.
        watcher: The underlying :class:`LogWatcher`.
    """

    sessions: dict[str, MonitoringSession] = field(default_factory=dict)
    watcher: LogWatcher = field(default_factory=LogWatcher)

    # -- session management -----------------------------------------------

    def create_session(
        self,
        name: str = "default",
        rules: list[AlertRule] | None = None,
    ) -> MonitoringSession:
        """Create and register a new monitoring session."""
        session = MonitoringSession(name=name)
        for rule in rules or []:
            session.add_rule(rule)
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> MonitoringSession | None:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False

    def start_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.start()
            return True
        return False

    def stop_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session.stop()
            return True
        return False

    # -- core processing --------------------------------------------------

    def process_entry(self, entry: LogEntry, session_id: str) -> list[Action]:
        """Run *entry* through all rules in the given session.

        Returns the list of actions produced (may be empty).
        """
        session = self.sessions.get(session_id)
        if session is None or session.state != SessionState.RUNNING:
            return []

        session.lines_processed += 1
        now = time.time()
        actions: list[Action] = []

        for rule in session.rules:
            if not rule.enabled:
                continue
            if session.is_throttled(rule.id, now):
                continue
            if rule.evaluate(entry.line, now):
                fired = self._fire_actions(rule, entry, session, now)
                actions.extend(fired)

        return actions

    def process_lines(
        self,
        lines: list[str],
        session_id: str,
        source: str = "memory",
    ) -> list[Action]:
        """Convenience: process a batch of raw text lines."""
        entries = self.watcher.scan_lines(lines, source)
        all_actions: list[Action] = []
        for entry in entries:
            all_actions.extend(self.process_entry(entry, session_id))
        return all_actions

    # -- action generation ------------------------------------------------

    def _fire_actions(
        self,
        rule: AlertRule,
        entry: LogEntry,
        session: MonitoringSession,
        now: float,
    ) -> list[Action]:
        """Build actions when *rule* fires on *entry*."""
        actions: list[Action] = []

        # Default: always notify
        notify = Action.notify(
            rule_id=rule.id,
            message=f"[{rule.name}] matched in {entry.source}:{entry.line_number}: {entry.line[:120]}",
            source=entry.source,
            line_number=entry.line_number,
        )
        actions.append(notify)
        session.record_action(notify)

        # Snapshot: capture context
        if "snapshot" in rule.tags:
            snap = Action.snapshot(
                rule_id=rule.id,
                message=f"Snapshot for rule {rule.name}",
                context_lines=10,
                line=entry.line,
            )
            actions.append(snap)
            session.record_action(snap)

        # Escalate: if threshold is high
        if rule.threshold >= 5:
            esc = Action.escalate(
                rule_id=rule.id,
                message=f"Escalating rule {rule.name} (threshold={rule.threshold})",
                level=2,
            )
            actions.append(esc)
            session.record_action(esc)

        # Throttle: always apply cooldown for the rule
        throttle = Action.throttle(
            rule_id=rule.id,
            message=f"Throttling rule {rule.name} for 60s",
            cooldown_seconds=60,
        )
        session.set_throttle(rule.id, 60, now)
        actions.append(throttle)
        session.record_action(throttle)

        return actions

    # -- summary ----------------------------------------------------------

    def status(self) -> dict[str, Any]:
        return {
            "sessions": len(self.sessions),
            "total_rules": sum(len(s.rules) for s in self.sessions.values()),
            "total_actions": sum(len(s.actions) for s in self.sessions.values()),
            "total_lines": sum(s.lines_processed for s in self.sessions.values()),
        }
