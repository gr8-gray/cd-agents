"""Live IV pulls for the daily sensing run — reuses site-monitor's proven Stripe +
Cloudflare calls, but windowed to YESTERDAY (full UTC day). Today is partial and would
false-flag traffic-drop/zero every morning, so the daily snapshot is always yesterday.

Creds on cire (never in repo — STOP 21):
  ~/.jarvis/secrets/stripe-iv.key     restricted read-only rk_live_
  ~/.jarvis/secrets/cf-analytics.token  CF token (Account Analytics:Read + Zone:Read)
"""
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

HOME = Path.home()
STRIPE_KEY_FILE = HOME / ".jarvis" / "secrets" / "stripe-iv.key"
CF_TOKEN_FILE = HOME / ".jarvis" / "secrets" / "cf-analytics.token"
IV_ZONE = "theimmortalvibes.com"
TIMEOUT = 20


def _stripe_day(key: str, day_start: int, day_end: int):
    """Net succeeded revenue (cents) + paid-order count for [day_start, day_end)."""
    total = count = 0
    more, after = True, None
    while more:
        params = {"created[gte]": day_start, "created[lt]": day_end, "limit": 100}
        if after:
            params["starting_after"] = after
        resp = requests.get("https://api.stripe.com/v1/charges", auth=(key, ""),
                            params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for c in data["data"]:
            if c.get("paid") and c.get("status") == "succeeded":
                total += c["amount"] - c.get("amount_refunded", 0)
                count += 0 if c.get("refunded") else 1
        more = data.get("has_more")
        after = data["data"][-1]["id"] if (more and data["data"]) else None
    return total, count


def _cf_day(token: str, zone_name: str, day: str):
    """{visits, pageviews} for a single UTC date, or None if the zone/day is absent."""
    H = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    zr = requests.get("https://api.cloudflare.com/client/v4/zones?per_page=50",
                      headers=H, timeout=TIMEOUT)
    zones = {z["name"]: z["id"] for z in zr.json().get("result", []) if z.get("status") == "active"}
    tag = zones.get(zone_name)
    if not tag:
        return None
    q = ('{viewer{zones(filter:{zoneTag:"%s"}){httpRequests1dGroups(limit:1,'
         'filter:{date:"%s"}){dimensions{date} sum{pageViews} uniq{uniques}}}}}') % (tag, day)
    gr = requests.post("https://api.cloudflare.com/client/v4/graphql",
                       headers=H, json={"query": q}, timeout=TIMEOUT)
    groups = gr.json()["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]
    if not groups:
        return {"visits": 0, "pageviews": 0}
    g = groups[0]
    return {"visits": g["uniq"]["uniques"], "pageviews": g["sum"]["pageViews"]}


def iv_daily_metrics(now: datetime | None = None):
    """(date_str, today_metrics, metric_sources, sources) for YESTERDAY (UTC).

    Degrades gracefully: a missing cred simply drops that source's metrics.
    """
    now = now or datetime.now(timezone.utc)
    midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yday = midnight_today - timedelta(days=1)
    date_str = yday.strftime("%Y-%m-%d")

    metrics: dict = {}
    msrc: dict = {}
    sources: list = []

    if STRIPE_KEY_FILE.exists():
        try:
            key = STRIPE_KEY_FILE.read_text().strip()
            cents, orders = _stripe_day(key, int(yday.timestamp()), int(midnight_today.timestamp()))
            metrics["net_revenue"] = round(cents / 100, 2)
            metrics["payments"] = orders
            msrc["net_revenue"] = msrc["payments"] = "stripe"
            sources.append("stripe")
        except Exception as e:
            print(f"adapters_iv: stripe pull failed, skipping — {str(e)[:140]}")

    token = os.environ.get("CF_API_TOKEN") or (
        CF_TOKEN_FILE.read_text().strip() if CF_TOKEN_FILE.exists() else None
    )
    if token:
        try:
            cf = _cf_day(token, IV_ZONE, date_str)
            if cf is not None:
                metrics["visits"] = cf["visits"]
                metrics["pageviews"] = cf["pageviews"]
                msrc["visits"] = msrc["pageviews"] = "cf"
                sources.append("cf")
        except Exception as e:
            print(f"adapters_iv: cloudflare pull failed, skipping — {str(e)[:140]}")

    return date_str, metrics, msrc, sources
