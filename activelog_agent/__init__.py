"""activelog-agent — Autonomous log monitoring and alerting."""

from activelog_agent.agent import Agent
from activelog_agent.watcher import LogWatcher
from activelog_agent.rule import AlertRule, MatchType
from activelog_agent.action import Action, ActionType
from activelog_agent.session import MonitoringSession, SessionState

__all__ = [
    "Agent",
    "LogWatcher",
    "AlertRule",
    "MatchType",
    "Action",
    "ActionType",
    "MonitoringSession",
    "SessionState",
]
__version__ = "0.3.0"
