import json
from datetime import datetime

def log_scan(snapshot):
    with open("logs/scans.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": datetime.utcnow().isoformat(), "snapshot": snapshot}) + "\n")

def log_decision(decision):
    with open("logs/decisions.jsonl", "a") as f:
        f.write(json.dumps(decision) + "\n")
