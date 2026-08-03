"""Deterministic daily orchestrator: persist today's snapshot, compute the trailing
baseline + deltas, flag anomalies, render the digest. Cred-free and node-free —
the cron job calls this, then hands the digest's narrative slot to the node inference
function and routes ntfy on `has_anomaly`.
"""
from dataclasses import dataclass

from sensing.anomaly import evaluate
from sensing.digest import render_digest


@dataclass
class Report:
    digest: str
    flags: list
    has_anomaly: bool


def build_report(
    store,
    property: str,
    date: str,
    today_metrics: dict,
    metric_sources: dict,
    sources: list,
    generated: str,
    narrative: str | None = None,
    config: dict | None = None,
) -> Report:
    # Persist today's snapshot FIRST (trailing reads date < today, so this can't
    # pollute today's own baseline) — this is how the store accrues history.
    for metric, value in today_metrics.items():
        store.upsert(date=date, source=metric_sources[metric], metric=metric, value=float(value))

    trailing: dict = {}
    deltas: dict = {}
    for metric, value in today_metrics.items():
        vals = store.trailing(source=metric_sources[metric], metric=metric, before_date=date, days=7)
        trailing[metric] = vals
        if vals:
            deltas[metric] = round(value - sum(vals) / len(vals), 2)

    flags = evaluate(today_metrics, trailing, config)
    digest = render_digest(
        property=property, date=date, metrics=today_metrics, flags=flags,
        sources=sources, generated=generated, narrative=narrative, deltas=deltas,
    )
    return Report(digest=digest, flags=flags, has_anomaly=bool(flags))
