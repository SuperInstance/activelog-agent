"""Comprehensive test suite for activelog-agent."""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from activelog_agent.action import Action, ActionType
from activelog_agent.agent import Agent
from activelog_agent.rule import AlertRule, MatchType
from activelog_agent.session import MonitoringSession, SessionState
from activelog_agent.watcher import LogEntry, LogWatcher


# ---------------------------------------------------------------------------
# Action tests
# ---------------------------------------------------------------------------


class TestAction:
    def test_notify_factory(self):
        a = Action.notify("r1", "hello", channel="slack")
        assert a.action_type == ActionType.NOTIFY
        assert a.rule_id == "r1"
        assert a.metadata["channel"] == "slack"
        assert a.id  # auto-generated

    def test_escalate_factory(self):
        a = Action.escalate("r2", "urgent", level=3)
        assert a.action_type == ActionType.ESCALATE
        assert a.metadata["level"] == 3

    def test_throttle_factory(self):
        a = Action.throttle("r3", "cooling", cooldown_seconds=120)
        assert a.action_type == ActionType.THROTTLE
        assert a.metadata["cooldown_seconds"] == 120

    def test_snapshot_factory(self):
        a = Action.snapshot("r4", "captured", context_lines=20)
        assert a.action_type == ActionType.SNAPSHOT
        assert a.metadata["context_lines"] == 20

    def test_serialisation_roundtrip(self):
        a = Action.notify("r1", "test msg", extra="val")
        d = a.to_dict()
        assert d["action_type"] == "notify"
        restored = Action.from_dict(d)
        assert restored.action_type == ActionType.NOTIFY
        assert restored.rule_id == "r1"
        assert restored.message == "test msg"
        assert restored.id == a.id


# ---------------------------------------------------------------------------
# AlertRule tests
# ---------------------------------------------------------------------------


class TestAlertRule:
    def test_substring_match(self):
        rule = AlertRule(name="error", pattern="ERROR")
        assert rule.matches("this is an ERROR message")
        assert not rule.matches("all good")

    def test_case_insensitive(self):
        rule = AlertRule(name="warn", pattern="warning", case_sensitive=False)
        assert rule.matches("WARNING: disk full")
        assert rule.matches("Warning: low memory")

    def test_exact_match(self):
        rule = AlertRule(name="exact", pattern="OK", match_type=MatchType.EXACT)
        assert rule.matches("OK")
        assert not rule.matches("OK ")
        assert not rule.matches("everything OK")

    def test_regex_match(self):
        rule = AlertRule(name="http5xx", pattern=r"HTTP [5]\d{2}", match_type=MatchType.REGEX)
        assert rule.matches("server returned HTTP 503")
        assert not rule.matches("server returned HTTP 200")

    def test_disabled_rule_never_matches(self):
        rule = AlertRule(name="off", pattern="anything", enabled=False)
        assert not rule.matches("anything")

    def test_threshold(self):
        rule = AlertRule(name="burst", pattern="ERR", threshold=3, window_seconds=10)
        now = time.time()
        assert not rule.evaluate("ERR line 1", now)
        assert not rule.evaluate("ERR line 2", now)
        assert rule.evaluate("ERR line 3", now)  # threshold met

    def test_threshold_window_expiry(self):
        rule = AlertRule(name="burst", pattern="ERR", threshold=2, window_seconds=0.1)
        now = time.time()
        assert not rule.evaluate("ERR", now)
        time.sleep(0.15)
        # Old match expired, still need 2
        assert not rule.evaluate("ERR", time.time())

    def test_reset(self):
        rule = AlertRule(name="r", pattern="X", threshold=5)
        now = time.time()
        for _ in range(4):
            rule.evaluate("X", now)
        rule.reset()
        assert rule.evaluate("X", now) is False  # back to 1 match

    def test_serialisation_roundtrip(self):
        rule = AlertRule(
            name="test",
            pattern=r"\d+ errors",
            match_type=MatchType.REGEX,
            threshold=3,
            window_seconds=30,
            tags=["prod"],
        )
        d = rule.to_dict()
        restored = AlertRule.from_dict(d)
        assert restored.name == "test"
        assert restored.match_type == MatchType.REGEX
        assert restored.threshold == 3
        assert restored.tags == ["prod"]


# ---------------------------------------------------------------------------
# LogWatcher tests
# ---------------------------------------------------------------------------


class TestLogWatcher:
    def test_scan_lines(self):
        w = LogWatcher()
        entries = w.scan_lines(["line 1", "line 2"], source="test")
        assert len(entries) == 2
        assert entries[0].line == "line 1"
        assert entries[0].source == "test"
        assert entries[0].line_number == 1

    def test_add_remove_source(self):
        w = LogWatcher()
        w.add_source("app", "/tmp/app.log")
        assert "app" in w.sources
        w.remove_source("app")
        assert "app" not in w.sources

    def test_read_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            f.write("hello\nworld\n")
            f.flush()
            path = f.name
        try:
            w = LogWatcher(sources={"test": path})
            entries = w.read_existing()
            assert len(entries) == 2
            assert entries[0].line == "hello"
            assert entries[1].line_number == 2
        finally:
            os.unlink(path)

    def test_read_missing_file(self):
        w = LogWatcher(sources={"ghost": "/tmp/nonexistent_12345.log"})
        assert w.read_existing("ghost") == []


# ---------------------------------------------------------------------------
# MonitoringSession tests
# ---------------------------------------------------------------------------


class TestMonitoringSession:
    def test_lifecycle(self):
        s = MonitoringSession(name="test")
        assert s.state == SessionState.CREATED
        s.start()
        assert s.state == SessionState.RUNNING
        s.pause()
        assert s.state == SessionState.PAUSED
        s.resume()
        assert s.state == SessionState.RUNNING
        s.stop()
        assert s.state == SessionState.STOPPED
        assert s.stopped_at is not None

    def test_add_remove_rule(self):
        s = MonitoringSession()
        rule = AlertRule(name="r1", pattern="ERR")
        s.add_rule(rule)
        assert len(s.rules) == 1
        assert s.get_rule(rule.id) is rule
        s.remove_rule(rule.id)
        assert len(s.rules) == 0

    def test_record_action(self):
        s = MonitoringSession()
        a = Action.escalate("r1", "big problem", level=2)
        s.record_action(a)
        assert len(s.actions) == 1
        assert s.alerts_fired == 1  # escalate increments

    def test_throttle_cooldown(self):
        s = MonitoringSession()
        now = time.time()
        assert not s.is_throttled("r1", now)
        s.set_throttle("r1", 10, now)
        assert s.is_throttled("r1", now)
        assert not s.is_throttled("r1", now + 11)

    def test_save_and_load(self, tmp_path):
        s = MonitoringSession(name="persist-test")
        s.add_rule(AlertRule(name="err", pattern="ERROR"))
        s.start()
        s.lines_processed = 42
        s.save(tmp_path / "session.json")

        loaded = MonitoringSession.load(tmp_path / "session.json")
        assert loaded.name == "persist-test"
        assert loaded.state == SessionState.RUNNING
        assert len(loaded.rules) == 1
        assert loaded.rules[0].name == "err"
        assert loaded.lines_processed == 42

    def test_summary(self):
        s = MonitoringSession(name="sum")
        summary = s.summary()
        assert summary["name"] == "sum"
        assert summary["state"] == "created"


# ---------------------------------------------------------------------------
# Agent integration tests
# ---------------------------------------------------------------------------


class TestAgent:
    def _make_running_session(self, agent: Agent, rules: list[AlertRule] | None = None) -> str:
        session = agent.create_session("test", rules=rules)
        agent.start_session(session.id)
        return session.id

    def test_create_and_start_session(self):
        agent = Agent()
        sid = self._make_running_session(agent)
        session = agent.get_session(sid)
        assert session is not None
        assert session.state == SessionState.RUNNING

    def test_process_lines_basic(self):
        agent = Agent()
        rule = AlertRule(name="error", pattern="ERROR", threshold=1)
        sid = self._make_running_session(agent, rules=[rule])

        actions = agent.process_lines(["all good", "ERROR: crash"], sid)
        assert len(actions) >= 1
        notify_actions = [a for a in actions if a.action_type == ActionType.NOTIFY]
        assert len(notify_actions) == 1
        assert "crash" in notify_actions[0].message

    def test_no_actions_for_non_matching(self):
        agent = Agent()
        rule = AlertRule(name="err", pattern="FATAL", threshold=1)
        sid = self._make_running_session(agent, rules=[rule])

        actions = agent.process_lines(["all is well", "nothing to see"], sid)
        assert actions == []

    def test_throttle_suppresses_repeated_fires(self):
        agent = Agent()
        rule = AlertRule(name="err", pattern="ERR", threshold=1)
        sid = self._make_running_session(agent, rules=[rule])

        actions1 = agent.process_lines(["ERR line"], sid)
        assert len(actions1) >= 1

        # Within throttle window — should be suppressed
        actions2 = agent.process_lines(["ERR line again"], sid)
        assert actions2 == []

    def test_stopped_session_ignores(self):
        agent = Agent()
        rule = AlertRule(name="err", pattern="ERR", threshold=1)
        session = agent.create_session("stopped", rules=[rule])
        agent.start_session(session.id)
        agent.stop_session(session.id)

        actions = agent.process_lines(["ERR"], session.id)
        assert actions == []

    def test_snapshot_action_on_tagged_rule(self):
        agent = Agent()
        rule = AlertRule(name="snap", pattern="PANIC", threshold=1, tags=["snapshot"])
        sid = self._make_running_session(agent, rules=[rule])

        actions = agent.process_lines(["PANIC!"], sid)
        snapshot_actions = [a for a in actions if a.action_type == ActionType.SNAPSHOT]
        assert len(snapshot_actions) == 1

    def test_escalate_on_high_threshold(self):
        agent = Agent()
        rule = AlertRule(name="high", pattern="BAD", threshold=5, window_seconds=60)
        sid = self._make_running_session(agent, rules=[rule])

        # First 4 lines don't trigger; 5th does
        actions = agent.process_lines(["BAD"] * 5, sid)
        escalate_actions = [a for a in actions if a.action_type == ActionType.ESCALATE]
        assert len(escalate_actions) == 1

    def test_status(self):
        agent = Agent()
        self._make_running_session(agent, rules=[
            AlertRule(name="r1", pattern="A"),
            AlertRule(name="r2", pattern="B"),
        ])
        status = agent.status()
        assert status["sessions"] == 1
        assert status["total_rules"] == 2

    def test_remove_session(self):
        agent = Agent()
        session = agent.create_session("temp")
        assert agent.remove_session(session.id)
        assert agent.get_session(session.id) is None
        assert not agent.remove_session("nonexistent")

    def test_session_persistence_integration(self, tmp_path):
        agent = Agent()
        rule = AlertRule(name="err", pattern="ERROR", threshold=1)
        session = agent.create_session("persist", rules=[rule])
        agent.start_session(session.id)
        agent.process_lines(["ERROR: something broke"], session.id)

        path = tmp_path / "session.json"
        session.save(path)

        loaded = MonitoringSession.load(path)
        assert loaded.state == SessionState.RUNNING
        assert len(loaded.rules) == 1
        assert loaded.lines_processed == 1
