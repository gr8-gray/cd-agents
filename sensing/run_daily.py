"""L2 daily sensing run (the node, cron ~06:00 CT).

Pull IV metrics for yesterday -> build_report (persist snapshot + trailing baseline +
anomaly flags + digest, narrated by the node model) -> write the digest into the vault
-> ntfy only on an anomaly. Prints a STOP-9 evidence line for the cron log.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

from sensing.store import MetricStore
from sensing.pipeline import build_report
from sensing.adapters_iv import iv_daily_metrics
from sensing.narrate import narrate
from sensing.notify import notify_anomaly

HOME = Path.home()
DB = HOME / ".jarvis" / "sensing.sqlite"
SENSING_DIR = HOME / "vault" / "master" / "sensing"


def main() -> int:
    now = datetime.now(timezone.utc)
    generated = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    date_str, metrics, msrc, sources = iv_daily_metrics(now)
    if not metrics:
        print(f"sensing: {generated} no metrics pulled (creds missing?) — nothing written")
        return 0

    store = MetricStore(str(DB))
    report = build_report(
        store, property="IV", date=date_str, today_metrics=metrics,
        metric_sources=msrc, sources=sources, generated=generated, narrator=narrate,
    )

    SENSING_DIR.mkdir(parents=True, exist_ok=True)
    out = SENSING_DIR / f"iv-{date_str}.md"
    out.write_text(report.digest, encoding="utf-8")

    sent = report.has_anomaly and notify_anomaly("IV", date_str, report.flags)
    print(
        f"sensing: IV {date_str} metrics={metrics} "
        f"flags={[f.key for f in report.flags]} digest={out} "
        f"ntfy={'sent' if sent else 'none'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
