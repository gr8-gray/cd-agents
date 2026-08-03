"""ntfy anomaly push — reuses the node's blessed notifier (~/jarvis/bin/notify),
the same path site-monitor and weekly-report use, so server/topic/auth stay in one place.
"""
import subprocess
from pathlib import Path

HOME = Path.home()
NOTIFY = HOME / "jarvis" / "bin" / "notify"
REPORT_URL = "https://node.internal/report"  # ntfy tap (matches site-monitor)


def notify_anomaly(property: str, date: str, flags, priority: str = "high") -> bool:
    if not NOTIFY.exists() or not flags:
        return False
    title = f"{property} sensing anomaly — {date}"
    body = "; ".join(f.message for f in flags)
    try:
        subprocess.run([str(NOTIFY), title, body, priority, REPORT_URL], timeout=15)
        return True
    except Exception:
        return False
