from sensing.store import MetricStore
from sensing.pipeline import build_report


def _seed_week(store, metric, value, source):
    for day in range(1, 8):  # Aug 1..7
        store.upsert(date=f"2026-08-0{day}", source=source, metric=metric, value=float(value))


def test_build_report_flags_drops_against_the_stored_trailing_baseline():
    store = MetricStore(":memory:")
    _seed_week(store, "net_revenue", 200.0, source="stripe")
    _seed_week(store, "visits", 400.0, source="cf")

    report = build_report(
        store,
        property="IV",
        date="2026-08-08",
        today_metrics={"net_revenue": 100.0, "visits": 100.0},
        metric_sources={"net_revenue": "stripe", "visits": "cf"},
        sources=["stripe", "cf"],
        generated="2026-08-09T06:00:00Z",
    )

    keys = [f.key for f in report.flags]
    assert "revenue-drop" in keys
    assert "traffic-drop" in keys
    assert report.has_anomaly is True
    assert "revenue-drop" in report.digest


def test_build_report_persists_todays_snapshot_for_future_baselines():
    store = MetricStore(":memory:")
    _seed_week(store, "net_revenue", 200.0, source="stripe")

    build_report(
        store,
        property="IV",
        date="2026-08-08",
        today_metrics={"net_revenue": 100.0},
        metric_sources={"net_revenue": "stripe"},
        sources=["stripe"],
        generated="2026-08-09T06:00:00Z",
    )

    assert store.get(date="2026-08-08", source="stripe", metric="net_revenue") == 100.0


def test_build_report_has_no_anomaly_on_a_healthy_day():
    store = MetricStore(":memory:")
    _seed_week(store, "net_revenue", 200.0, source="stripe")

    report = build_report(
        store,
        property="IV",
        date="2026-08-08",
        today_metrics={"net_revenue": 195.0},
        metric_sources={"net_revenue": "stripe"},
        sources=["stripe"],
        generated="2026-08-09T06:00:00Z",
    )

    assert report.flags == []
    assert report.has_anomaly is False
    assert "No anomalies" in report.digest
