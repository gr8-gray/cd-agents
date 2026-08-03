from sensing.store import MetricStore


def test_upsert_then_get_returns_the_stored_value():
    store = MetricStore(":memory:")
    store.upsert(date="2026-08-03", source="stripe", metric="net_revenue", value=173.13)

    assert store.get(date="2026-08-03", source="stripe", metric="net_revenue") == 173.13


def test_upsert_same_key_twice_keeps_latest_value():
    store = MetricStore(":memory:")
    store.upsert(date="2026-08-03", source="stripe", metric="net_revenue", value=100.0)
    store.upsert(date="2026-08-03", source="stripe", metric="net_revenue", value=250.0)

    assert store.get(date="2026-08-03", source="stripe", metric="net_revenue") == 250.0


def test_get_returns_none_when_absent():
    store = MetricStore(":memory:")
    assert store.get(date="2026-08-03", source="stripe", metric="net_revenue") is None


def test_trailing_returns_the_n_most_recent_values_before_a_date_oldest_first():
    store = MetricStore(":memory:")
    # 8 daily snapshots, Aug 1..8
    for day, val in enumerate([10, 20, 30, 40, 50, 60, 70, 80], start=1):
        store.upsert(date=f"2026-08-0{day}", source="cf", metric="visits", value=float(val))

    # trailing 7 days strictly before Aug 8 -> Aug 1..7, oldest first
    trailing = store.trailing(source="cf", metric="visits", before_date="2026-08-08", days=7)

    assert trailing == [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0]


def test_trailing_excludes_the_before_date_and_other_sources_metrics():
    store = MetricStore(":memory:")
    store.upsert(date="2026-08-01", source="cf", metric="visits", value=1.0)
    store.upsert(date="2026-08-02", source="cf", metric="visits", value=2.0)
    store.upsert(date="2026-08-02", source="stripe", metric="net_revenue", value=999.0)
    store.upsert(date="2026-08-03", source="cf", metric="visits", value=3.0)  # the before_date

    trailing = store.trailing(source="cf", metric="visits", before_date="2026-08-03", days=7)

    assert trailing == [1.0, 2.0]
