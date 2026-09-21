import os

def ensure_logs():
    os.makedirs("logs", exist_ok=True)
