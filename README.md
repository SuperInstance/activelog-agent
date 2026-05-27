# activelog-agent

Autonomous log monitoring and alerting agent for Python.

## Quick Start

```python
from activelog_agent import Agent, AlertRule, MatchType

# Create an agent with a monitoring session
agent = Agent()
rule = AlertRule(name="errors", pattern=r"ERROR|FATAL", match_type=MatchType.REGEX, threshold=3, window_seconds=60)
session = agent.create_session("prod-monitor", rules=[rule])
agent.start_session(session.id)

# Feed log lines
actions = agent.process_lines([
    "2026-05-26 INFO server started",
    "2026-05-26 ERROR connection refused",
    "2026-05-26 ERROR timeout",
    "2026-05-26 FATAL disk full",
], session.id)

for a in actions:
    print(f"[{a.action_type.value}] {a.message}")

# Persist session state
session.save("monitoring-state.json")
```

## Architecture

| Module | Purpose |
|---|---|
| `agent.py` | Top-level `Agent` orchestrating sessions |
| `watcher.py` | `LogWatcher` tailing log files and scanning lines |
| `rule.py` | `AlertRule` with substring, regex, and exact matching + thresholds |
| `action.py` | `Action` types: notify, escalate, throttle, snapshot |
| `session.py` | `MonitoringSession` with lifecycle, persistence, and throttle state |

## Features

- **Pattern matching** — substring, regex, exact match
- **Threshold alerts** — fire only after N matches in a time window
- **Throttling** — automatic cooldown to prevent alert storms
- **Escalation** — auto-escalate high-threshold rules
- **Snapshots** — capture context around matching lines
- **State persistence** — save/load sessions to JSON
- **Zero dependencies** — stdlib only, pytest for testing

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Related

- [activelog.ai](https://activelog.ai)
