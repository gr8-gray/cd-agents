"""Daily metric snapshot store (sqlite) — the trailing-baseline the anomaly layer reads."""
import sqlite3


class MetricStore:
    def __init__(self, db_path: str = ":memory:"):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS metrics (
                date   TEXT NOT NULL,
                source TEXT NOT NULL,
                metric TEXT NOT NULL,
                value  REAL NOT NULL,
                PRIMARY KEY (date, source, metric)
            )
            """
        )
        self._conn.commit()

    def upsert(self, date: str, source: str, metric: str, value: float) -> None:
        self._conn.execute(
            """
            INSERT INTO metrics (date, source, metric, value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (date, source, metric) DO UPDATE SET value = excluded.value
            """,
            (date, source, metric, value),
        )
        self._conn.commit()

    def get(self, date: str, source: str, metric: str):
        row = self._conn.execute(
            "SELECT value FROM metrics WHERE date = ? AND source = ? AND metric = ?",
            (date, source, metric),
        ).fetchone()
        return row[0] if row else None

    def trailing(self, source: str, metric: str, before_date: str, days: int = 7) -> list:
        """Values of the up-to-`days` most recent snapshots with date < before_date, oldest first.

        ISO date strings sort chronologically, so lexical comparison is correct here.
        """
        rows = self._conn.execute(
            """
            SELECT value FROM metrics
            WHERE source = ? AND metric = ? AND date < ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (source, metric, before_date, days),
        ).fetchall()
        return [r[0] for r in reversed(rows)]
