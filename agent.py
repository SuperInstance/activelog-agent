#!/usr/bin/env python3
"""activelog-agent — Activity logging and task tracking"""
import json, time
from typing import List, Dict

class ActiveLogAgent:
    def __init__(self, plato_url="http://147.224.38.131:8847"):
        self.plato_url = plato_url
        self.tasks: List[Dict] = []
    
    def log_task(self, task: str, category: str, completed: bool, duration_min: int=0, notes: str=""):
        entry = {"task": task, "category": category, "completed": completed, "duration": duration_min, "notes": notes, "time": time.time()}
        self.tasks.append(entry)
        status = "completed" if completed else "in-progress"
        self._submit(f"Task: {task}", f"{status} ({duration_min}min). {notes}")
        return entry
    
    def get_productivity(self) -> Dict:
        if not self.tasks: return {"error": "No tasks"}
        completed = [t for t in self.tasks if t["completed"]]
        cats = {}
        for t in self.tasks: cats[t["category"]] = cats.get(t["category"], 0) + 1
        return {"total_tasks": len(self.tasks), "completed": len(completed), "completion_rate": round(len(completed)/len(self.tasks), 2), "by_category": cats, "total_hours": round(sum(t["duration"] for t in self.tasks)/60, 1)}
    
    def _submit(self, q: str, a: str):
        try:
            import urllib.request
            urllib.request.urlopen(urllib.request.Request(f"{self.plato_url}/submit", data=json.dumps({"question": q, "answer": a, "agent": "activelog-agent", "room": "activelog"}).encode(), headers={"Content-Type": "application/json"}), timeout=5)
        except: pass

def demo():
    a = ActiveLogAgent()
    a.log_task("Review PRs", "code", True, 45, "3 PRs merged")
    a.log_task("Write agent template", "code", True, 90, "BaseFleetAgent class")
    a.log_task("Build dashboard", "design", False, 30, "Need to finish CSS")
    print(a.get_productivity())

if __name__ == "__main__": demo()
