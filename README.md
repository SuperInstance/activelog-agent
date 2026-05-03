# PLATO ActiveLog Agent

Movement & Wellness Logger for activelog.ai. Wearable data → PLATO → health insights.

## Quick Start

```python
from activelog_agent import ActiveLogAgent

agent = ActiveLogAgent(user_id="casey")
agent.log_hrv(72, hrv_ms=45)
agent.log_sleep(hours=7.5, quality=0.85)
agent.log_activity(steps=8500, active_minutes=45)
print(agent.ask("how's my recovery?"))
```

## Architecture

- Wearable data (HRV, sleep, activity) → PLATO tiles
- Agent reads PLATO → presents wellness checkups
- "Don the health shell" → load personal health context
