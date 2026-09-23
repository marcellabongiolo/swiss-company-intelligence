from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class AnalysisStore:
    """SQLite-backed persistence for analysis runs and company score snapshots."""

    def __init__(self, path: str | Path = "data/analysis_history.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS analysis_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    company_count INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS company_scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    company TEXT NOT NULL,
                    canton TEXT NOT NULL,
                    sector TEXT NOT NULL,
                    attention_score REAL NOT NULL,
                    priority_band TEXT NOT NULL,
                    reasons TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_company_scores_company
                    ON company_scores(company);
                CREATE INDEX IF NOT EXISTS idx_company_scores_run
                    ON company_scores(run_id);
                """
            )

    def save_analysis(self, report: pd.DataFrame, source: str = "dashboard") -> int:
        """Persist one analyzed report and return the run id."""
        required = {
            "company",
            "canton",
            "sector",
            "attention_score",
            "priority_band",
            "reasons",
        }
        missing = sorted(required - set(report.columns))
        if missing:
            raise ValueError(f"Report missing required columns: {', '.join(missing)}")

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO analysis_runs (source, company_count)
                VALUES (?, ?)
                """,
                (source, len(report)),
            )
            run_id = int(cursor.lastrowid)

            rows = [
                (
                    run_id,
                    str(row.company),
                    str(row.canton),
                    str(row.sector),
                    float(row.attention_score),
                    str(row.priority_band),
                    str(row.reasons),
                )
                for row in report.itertuples(index=False)
            ]
            connection.executemany(
                """
                INSERT INTO company_scores (
                    run_id,
                    company,
                    canton,
                    sector,
                    attention_score,
                    priority_band,
                    reasons
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return run_id

    def list_runs(self, limit: int = 20) -> pd.DataFrame:
        """Return recent analysis runs, newest first."""
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT id, created_at, source, company_count
                FROM analysis_runs
                ORDER BY id DESC
                LIMIT ?
                """,
                connection,
                params=(limit,),
            )

    def company_history(self, company: str) -> pd.DataFrame:
        """Return the historical score snapshots for one company."""
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT
                    r.id AS run_id,
                    r.created_at,
                    r.source,
                    s.company,
                    s.canton,
                    s.sector,
                    s.attention_score,
                    s.priority_band,
                    s.reasons
                FROM company_scores AS s
                JOIN analysis_runs AS r ON r.id = s.run_id
                WHERE s.company = ?
                ORDER BY r.id ASC
                """,
                connection,
                params=(company,),
            )
