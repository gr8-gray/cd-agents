from sensing.anomaly import evaluate


def test_revenue_drop_fires_when_today_is_well_below_the_trailing_average():
    today = {"net_revenue": 100.0}
    trailing = {"net_revenue": [200.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0]}  # avg 200

    flags = evaluate(today, trailing)

    keys = [f.key for f in flags]
    assert "revenue-drop" in keys  # 100 < 200 * (1 - 0.35) = 130


def test_revenue_drop_does_not_fire_when_today_is_within_threshold():
    today = {"net_revenue": 180.0}
    trailing = {"net_revenue": [200.0, 200.0, 200.0, 200.0, 200.0, 200.0, 200.0]}  # avg 200

    flags = evaluate(today, trailing)

    assert "revenue-drop" not in [f.key for f in flags]  # 180 >= 130


def test_no_flags_when_there_is_no_trailing_baseline():
    # First week of operation: nothing to compare against -> stay quiet, never false-flag.
    today = {"net_revenue": 5.0, "visits": 1.0, "failed_payments": 99.0}
    trailing = {"net_revenue": [], "visits": [], "failed_payments": []}

    assert evaluate(today, trailing) == []


def test_zero_revenue_fires_and_supersedes_revenue_drop():
    today = {"net_revenue": 0.0}
    trailing = {"net_revenue": [200.0] * 7}

    keys = [f.key for f in evaluate(today, trailing)]

    assert "zero-revenue" in keys
    assert "revenue-drop" not in keys  # zero-revenue is the sharper signal; don't double-flag


def test_traffic_drop_fires_when_visits_fall_below_half_the_average():
    today = {"visits": 100.0}
    trailing = {"visits": [400.0] * 7}  # avg 400, half = 200

    assert "traffic-drop" in [f.key for f in evaluate(today, trailing)]


def test_tracking_broken_fires_and_supersedes_traffic_drop_when_visits_are_zero():
    today = {"visits": 0.0}
    trailing = {"visits": [400.0] * 7}

    keys = [f.key for f in evaluate(today, trailing)]

    assert "tracking-broken" in keys
    assert "traffic-drop" not in keys


def test_refund_spike_fires_when_today_exceeds_the_trailing_max():
    today = {"refund_amount": 50.0}
    trailing = {"refund_amount": [0.0, 10.0, 30.0, 0.0, 0.0, 20.0, 0.0]}  # max 30

    assert "refund-spike" in [f.key for f in evaluate(today, trailing)]


def test_failed_payment_spike_fires_above_three_times_average():
    today = {"failed_payments": 10.0}
    trailing = {"failed_payments": [2.0] * 7}  # avg 2, 3x = 6

    assert "failed-payment-spike" in [f.key for f in evaluate(today, trailing)]
