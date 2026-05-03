"""
PLATO ActiveLog Agent — Fitness Guardian for activelog.ai

Wearable fitness data → PLATO → agent health insights.
Vessels accumulate personal health knowledge over time.

Usage:
    from activelog_agent import ActiveLogAgent
    agent = ActiveLogAgent(user_id="casey")
    agent.log_hrv(72, hrv_ms=45)
    agent.log_sleep(hours=7.5, quality=0.85)
    print(agent.ask("how's my recovery?"))
"""

import time
import requests
from typing import Optional
from dataclasses import dataclass

DEFAULT_PLATO_URL = "http://localhost:8847"
ROOM = "activelog-ai"


class ActiveLogAgent:
    """
    Fitness Guardian agent.
    
    Wearable data (HRV, sleep, activity) → PLATO tiles.
    Agent reads PLATO → presents health trends and insights.
    """
    
    def __init__(self, user_id: str = "default", plato_url: str = DEFAULT_PLATO_URL):
        self.user_id = user_id
        self.plato_url = plato_url.rstrip("/")
        self.room = ROOM
    
    def _write(self, metric_type: str, value: float, metadata: dict) -> bool:
        tile = {
            "question": f"health:{self.user_id}:{metric_type}",
            "answer": str(value),
            "confidence": 0.9,
            "metadata": {
                "user_id": self.user_id,
                "metric_type": metric_type,
                "timestamp": time.time(),
                **metadata
            }
        }
        try:
            resp = requests.post(f"{self.plato_url}/room/{self.room}", json=tile, timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def log_hrv(self, heart_rate: int, hrv_ms: float, source: str = "watch") -> bool:
        """Log heart rate variability."""
        return self._write("hrv", hrv_ms, {"heart_rate": heart_rate, "source": source})
    
    def log_sleep(self, hours: float, quality: float, source: str = "watch") -> bool:
        """Log sleep data."""
        return self._write("sleep", hours, {"quality": quality, "source": source})
    
    def log_activity(self, steps: int, active_minutes: int, source: str = "watch") -> bool:
        """Log activity data."""
        return self._write("activity", steps, {"active_minutes": active_minutes, "source": source})
    
    def log_recovery(self, score: float) -> bool:
        """Log recovery score (0-100)."""
        return self._write("recovery", score, {})
    
    def ask(self, question: str) -> str:
        """Ask about health trends."""
        try:
            resp = requests.get(f"{self.plato_url}/room/{self.room}?limit=20", timeout=5)
            if resp.status_code == 200:
                tiles = resp.json().get("tiles", [])
                if tiles:
                    latest = tiles[-1]
                    return f"Latest {latest.get('question','').split(':')[1]}: {latest.get('answer','')}"
        except:
            pass
        return "Health system unavailable."
