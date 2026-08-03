from sensing.anomaly import Flag
from sensing.digest import render_digest


def _metrics():
    return {
        "net_revenue": 173.13,
        "payments": 4,
        "visits": 540,
    }


def test_digest_has_frontmatter_with_property_and_date():
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=[], sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
    )
    assert md.startswith("---")
    assert "property: IV" in md
    assert "date: 2026-08-03" in md


def test_digest_renders_every_metric_value():
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=[], sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
    )
    assert "173.13" in md
    assert "540" in md
    assert "net_revenue" in md


def test_digest_lists_each_flag_message_when_anomalies_present():
    flags = [Flag("revenue-drop", "net_revenue", 100.0, 200.0, "net revenue 100.00 is 50% below the 7-day average 200.00")]
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=flags, sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
    )
    assert "net revenue 100.00 is 50% below" in md
    assert "revenue-drop" in md


def test_digest_says_no_anomalies_when_flags_empty():
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=[], sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
    )
    assert "No anomalies" in md


def test_digest_includes_narrative_when_provided():
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=[], sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
        narrative="Revenue held steady and traffic was normal.",
    )
    assert "Revenue held steady and traffic was normal." in md


def test_digest_evidence_footer_lists_sources_and_generated_time():
    md = render_digest(
        property="IV", date="2026-08-03", metrics=_metrics(),
        flags=[], sources=["stripe", "cf"], generated="2026-08-04T06:00:00Z",
    )
    assert "stripe" in md and "cf" in md
    assert "2026-08-04T06:00:00Z" in md
