# activelog-agent

A standalone log-monitoring and alerting toolkit for Python. Define rules that match log lines by substring, regex, or exact text, then process log streams through them to produce notification, escalation, throttle, and snapshot actions. Pure Python, zero runtime dependencies.

## Features

- **Pattern matching** — substring, regex, and exact-match rules
- **Threshold alerts** — fire after N matches within a configurable time window
- **Throttling** — every rule that fires enters a 60-second cooldown
- **Escalation** — rules with a threshold of 5 or higher also generate an escalate action
- **Snapshots** — rules tagged `"snapshot"` capture the matched line as context
- **State persistence** — save and load sessions to JSON via `MonitoringSession.save()` / `.load()`

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

## How It Works

Each log line is checked against every enabled, non-throttled rule in the session. When a rule's pattern matches:

1. A **notify** action is always generated.
2. If the rule is tagged `"snapshot"`, a **snapshot** action captures the matched line.
3. If the rule's threshold is ≥ 5, an **escalate** action is generated.
4. The rule enters a 60-second **throttle** cooldown, during which further matches are skipped.

Thresholds are evaluated against a sliding time window: a rule only fires when the number of matches within `window_seconds` reaches `threshold`. The default threshold is 1 (fire on every match).

## API Reference

| Module | Purpose |
|--------|---------|
| `agent.py` | `Agent` — creates sessions and processes log lines |
| `watcher.py` | `LogWatcher` — scans lines into `LogEntry` objects |
| `rule.py` | `AlertRule` — pattern matching and threshold logic |
| `action.py` | `Action` — action types: notify, escalate, throttle, snapshot |
| `session.py` | `MonitoringSession` — lifecycle, throttle state, and JSON persistence |

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## Scope

- ✅ **Real today** — a standalone, zero-dependency log-monitoring toolkit. Every feature listed above (pattern matching, thresholds, throttling, escalation, snapshots, state persistence) is implemented and covered by the test suite.
- 🔮 **Later phase** — integration with a broader `activelog` pipeline (e.g. a separate `activelog-backend` store, downstream analytics) and running as a PLATO fleet agent are aspirational directions, not anything present in this package today.

**Naming note (read before assuming a connection):** this package monitors
*software log files* (server output, application logs). It shares the
"ActiveLog" name with — but does **not** implement, depend on, or relate to —
the ActiveLog timestamped *event-log format* designed in
[SuperInstance/cocapn-foundation](https://github.com/SuperInstance/cocapn-foundation)
(`activelog-spec`: the append-only, `(dev, seq)`-keyed voice/event envelope
behind the Cocapn/DeckBoss line of work). Same word, two unrelated systems.

## License

MIT
