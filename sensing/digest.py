"""Render the deterministic vault digest.

CONTRACT: every number is rendered HERE, from the pulled metrics — the node
inference function only writes prose for the `narrative` slot, so it can never
introduce or alter a figure. That guardrail lives in this separation.
"""


def _fmt(v) -> str:
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else f"{v:.2f}"
    return str(v)


def render_digest(
    property: str,
    date: str,
    metrics: dict,
    flags: list,
    sources: list,
    generated: str,
    narrative: str | None = None,
    deltas: dict | None = None,
) -> str:
    deltas = deltas or {}
    lines: list[str] = []

    # frontmatter
    lines += [
        "---",
        f"property: {property}",
        f"date: {date}",
        f"generated: {generated}",
        "type: sensing-digest",
        f"anomalies: {len(flags)}",
        "---",
        "",
        f"# {property} — sensing digest {date}",
        "",
    ]

    # metrics table
    lines += ["## Metrics", "", "| metric | value | 7d Δ |", "|---|---|---|"]
    for name, value in metrics.items():
        delta = _fmt(deltas[name]) if name in deltas else "—"
        lines.append(f"| {name} | {_fmt(value)} | {delta} |")
    lines.append("")

    # anomalies
    lines += ["## Anomalies", ""]
    if flags:
        for f in flags:
            lines.append(f"- **{f.key}** — {f.message}")
    else:
        lines.append("No anomalies flagged.")
    lines.append("")

    # narrative (node inference fills this; deterministic placeholder otherwise)
    lines += ["## Narrative", ""]
    lines.append(narrative if narrative else "_No narrative (node inference not run)._")
    lines.append("")

    # evidence footer (STOP 9)
    lines += ["---", f"_Sources: {', '.join(sources)} · generated {generated}_"]

    return "\n".join(lines)
