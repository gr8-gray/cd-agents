"""Deterministic anomaly flags — computed BEFORE the model, so behavior is testable
and never depends on the node inference being up.

Every rule requires a trailing baseline; with no history (first week) nothing fires.
The two "zero" rules (zero-revenue, tracking-broken) supersede their softer drop rule
so a dead day flags once with the sharper signal instead of double-flagging.
"""
from dataclasses import dataclass


DEFAULTS = {
    "revenue_drop_pct": 0.35,    # revenue-drop: net < 7d-avg * (1 - pct)
    "traffic_drop_ratio": 0.5,   # traffic-drop: visits < 7d-avg * ratio
    "failed_spike_mult": 3.0,    # failed-payment-spike: failed > 7d-avg * mult
}


@dataclass
class Flag:
    key: str
    metric: str
    today: float
    baseline: float
    message: str


def _avg(values):
    return sum(values) / len(values) if values else None


def evaluate(today: dict, trailing: dict, config: dict | None = None) -> list[Flag]:
    cfg = {**DEFAULTS, **(config or {})}
    flags: list[Flag] = []

    # ── revenue ────────────────────────────────────────────────────────────
    rev = today.get("net_revenue")
    rev_avg = _avg(trailing.get("net_revenue", []))
    if rev is not None and rev_avg:
        if rev == 0:
            flags.append(Flag(
                "zero-revenue", "net_revenue", rev, rev_avg,
                f"zero revenue today; the 7-day average is {rev_avg:.2f}",
            ))
        elif rev < rev_avg * (1 - cfg["revenue_drop_pct"]):
            pct = round((1 - rev / rev_avg) * 100)
            flags.append(Flag(
                "revenue-drop", "net_revenue", rev, rev_avg,
                f"net revenue {rev:.2f} is {pct}% below the 7-day average {rev_avg:.2f}",
            ))

    # ── traffic ────────────────────────────────────────────────────────────
    visits = today.get("visits")
    visits_avg = _avg(trailing.get("visits", []))
    if visits is not None and visits_avg:
        if visits == 0:
            flags.append(Flag(
                "tracking-broken", "visits", visits, visits_avg,
                f"zero visits today; the 7-day average is {visits_avg:.0f} — analytics may be broken",
            ))
        elif visits < visits_avg * cfg["traffic_drop_ratio"]:
            pct = round((1 - visits / visits_avg) * 100)
            flags.append(Flag(
                "traffic-drop", "visits", visits, visits_avg,
                f"visits {visits:.0f} are {pct}% below the 7-day average {visits_avg:.0f}",
            ))

    # ── refunds ────────────────────────────────────────────────────────────
    refund = today.get("refund_amount")
    refund_hist = trailing.get("refund_amount", [])
    if refund is not None and refund_hist:
        refund_max = max(refund_hist)
        if refund > refund_max:
            flags.append(Flag(
                "refund-spike", "refund_amount", refund, refund_max,
                f"refunds {refund:.2f} exceed the 7-day high of {refund_max:.2f}",
            ))

    # ── failed payments ────────────────────────────────────────────────────
    failed = today.get("failed_payments")
    failed_avg = _avg(trailing.get("failed_payments", []))
    if failed is not None and failed_avg:
        if failed > failed_avg * cfg["failed_spike_mult"]:
            flags.append(Flag(
                "failed-payment-spike", "failed_payments", failed, failed_avg,
                f"{failed:.0f} failed payments vs a 7-day average of {failed_avg:.1f}",
            ))

    return flags
