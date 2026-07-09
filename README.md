# activelog-agent

**Autonomous log monitoring and alerting** — pattern matching, threshold alerts, escalation, and state persistence. Pure Python, zero dependencies.

## What This Gives You

- **Pattern matching** — substring, regex, and exact match rules
- **Threshold alerts** — fire after N matches in a configurable time window
- **Throttling** — automatic cooldown to prevent alert storms
- **Escalation** — auto-escalate high-severity rules
- **Snapshots** — capture surrounding context on match
- **State persistence** — save/load sessions to JSON

## Installation

```bash
pip install activelog-agent
```

## Quick Start

```python
from activelog_agent import Agent, AlertRule, MatchType

agent = Agent()
rule = AlertRule(
    name="errors",
    pattern=r"ERROR|FATAL",
    match_type=MatchType.REGEX,
    threshold=3,
    window_seconds=60,
)
session = agent.create_session("prod-monitor", rules=[rule])
agent.start_session(session.id)

actions = agent.process_lines([
    "2026-05-26 INFO server started",
    "2026-05-26 ERROR connection refused",
    "2026-05-26 ERROR timeout",
    "2026-05-26 FATAL disk full",
], session.id)

for a in actions:
    print(f"[{a.action_type.value}] {a.message}")
```

## API Reference

| Module | Purpose |
|--------|---------|
| `agent.py` | Top-level `Agent` orchestrating sessions |
| `watcher.py` | `LogWatcher` tailing log files |
| `rule.py` | `AlertRule` with matching + thresholds |
| `action.py` | `Action` types: notify, escalate, throttle, snapshot |
| `session.py` | `MonitoringSession` with lifecycle + persistence |

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## How It Fits

- ✅ **Real today** — a standalone, zero-dependency log-monitoring toolkit. Every feature listed above (pattern matching, thresholds, throttling, escalation, snapshots, state persistence) is implemented and covered by the test suite.
- 🔮 **Later phase** — integration with a broader `activelog` pipeline (e.g. a separate `activelog-backend` store, downstream analytics) and running as a PLATO fleet agent are aspirational directions, not anything present in this package today.

## License

MIT
