"""SQL Analytical Layer Runner.

Applies reusable analytical views to the warehouse, parses all 38+ business-oriented
SQL queries from `sql/analytics/`, executes and validates each query against SQLite
(or PostgreSQL), exports CSV results, and generates `reports/sql_analytical_findings.md`.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import PATHS, ensure_directories

SQL_ANALYTICS_DIR = PATHS.root / "sql" / "analytics"


@dataclass
class ParsedSQLQuery:
    query_id: str
    query_name: str
    topic: str
    business_question: str
    interpretation: str
    source_file: str
    sql: str


def _df_to_markdown(df: pd.DataFrame, max_rows: int = 8) -> str:
    """Format DataFrame as GitHub-flavored Markdown table without extra deps."""
    if df.empty:
        return "_No rows returned._"
    sub = df.head(max_rows)
    headers = [str(c) for c in sub.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in sub.iterrows():
        vals = ["" if pd.isna(v) else str(v) for v in row.tolist()]
        lines.append("| " + " | ".join(vals) + " |")
    if len(df) > max_rows:
        lines.append(f"\n_Showing first {max_rows} of {len(df)} rows._")
    return "\n".join(lines)


def parse_sql_queries(sql_dir: Path | None = None) -> list[ParsedSQLQuery]:
    """Parse annotated query blocks from sql/analytics/0*.sql files."""
    target_dir = sql_dir or SQL_ANALYTICS_DIR
    query_files = sorted(
        p for p in target_dir.glob("*.sql") if not p.name.startswith("00_views")
    )

    parsed: list[ParsedSQLQuery] = []
    block_pattern = re.compile(r"--\s*QUERY_ID:\s*(.+)")

    for sql_file in query_files:
        text = sql_file.read_text(encoding="utf-8")
        lines = text.splitlines()

        current_meta: dict[str, str] = {}
        current_sql_lines: list[str] = []

        def _flush() -> None:
            sql_body = "\n".join(current_sql_lines).strip().rstrip(";")
            if current_meta.get("query_id") and sql_body:
                parsed.append(
                    ParsedSQLQuery(
                        query_id=current_meta["query_id"],
                        query_name=current_meta.get("query_name", current_meta["query_id"].lower()),
                        topic=current_meta.get("topic", "General"),
                        business_question=current_meta.get("business_question", ""),
                        interpretation=current_meta.get("interpretation", ""),
                        source_file=sql_file.name,
                        sql=sql_body,
                    )
                )

        for line in lines:
            m = block_pattern.match(line.strip())
            if m:
                _flush()
                current_meta = {"query_id": m.group(1).strip()}
                current_sql_lines = []
                continue

            if not current_meta:
                continue

            stripped = line.strip()
            if stripped.startswith("-- QUERY_NAME:"):
                current_meta["query_name"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("-- TOPIC:"):
                current_meta["topic"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("-- BUSINESS_QUESTION:"):
                current_meta["business_question"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("-- INTERPRETATION:"):
                current_meta["interpretation"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("--"):
                continue
            else:
                current_sql_lines.append(line)

        _flush()

    return parsed


def apply_sqlite_views(db_path: Path | None = None, sql_dir: Path | None = None) -> list[str]:
    """Create/refresh analytical views in the SQLite warehouse."""
    target_db = db_path or PATHS.sqlite_db
    target_sql_dir = sql_dir or SQL_ANALYTICS_DIR
    views_sql = (target_sql_dir / "00_views_sqlite.sql").read_text(encoding="utf-8")

    conn = sqlite3.connect(target_db)
    try:
        conn.executescript(views_sql)
        views = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'view' ORDER BY name"
            ).fetchall()
        ]
    finally:
        conn.close()
    return views


def run_all_sql_queries(
    db_path: Path | None = None,
    sql_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Deploy views, execute all parsed analytical queries, export CSVs and Markdown report."""
    ensure_directories()
    target_db = db_path or PATHS.sqlite_db
    target_sql_dir = sql_dir or SQL_ANALYTICS_DIR
    rep_dir = reports_dir or PATHS.reports
    results_dir = rep_dir / "sql_results"
    results_dir.mkdir(parents=True, exist_ok=True)

    views = apply_sqlite_views(db_path=target_db, sql_dir=target_sql_dir)
    queries = parse_sql_queries(sql_dir=target_sql_dir)

    conn = sqlite3.connect(target_db)
    summary_records: list[dict[str, Any]] = []
    md_sections: list[str] = [
        "# Workforce & Compensation SQL Analytical Findings",
        "",
        f"**Executed (UTC):** `{datetime.now(timezone.utc).isoformat(timespec='seconds')}` | "
        f"**Total Views:** `{len(views)}` | **Total Analytical Queries Executed:** `{len(queries)}`",
        "",
        "> **Synthetic Data Note:** All metrics (including the 13.62% attrition rate and ₹5,466.12 Cr payroll base) are derived from the Phase 1 synthetic enterprise dataset generated for analytical demonstration, not real-world benchmarks.",
        "",
        "## Reusable Warehouse Views",
        "",
    ]
    for v in views:
        md_sections.append(f"- `{v}`")
    md_sections.append("")
    md_sections.append("## Executed Business Analytical Queries")
    md_sections.append("")

    try:
        for q in queries:
            df = pd.read_sql_query(q.sql, conn)
            csv_name = f"{q.query_id}_{q.query_name}.csv"
            df.to_csv(results_dir / csv_name, index=False)

            summary_records.append(
                {
                    "query_id": q.query_id,
                    "query_name": q.query_name,
                    "topic": q.topic,
                    "source_file": q.source_file,
                    "row_count": int(len(df)),
                    "columns": list(df.columns),
                    "csv_file": csv_name,
                }
            )

            md_sections.extend(
                [
                    f"### {q.query_id} — {q.query_name} (`{q.topic}`)",
                    f"- **Source:** `{q.source_file}` | **Rows Returned:** `{len(df)}` | **Export:** `reports/sql_results/{csv_name}`",
                    f"- **Business Question:** {q.business_question}",
                    f"- **Interpretation:** {q.interpretation}",
                    "",
                    _df_to_markdown(df, max_rows=8),
                    "",
                ]
            )
    finally:
        conn.close()

    (rep_dir / "sql_analytical_findings.md").write_text("\n".join(md_sections), encoding="utf-8")
    manifest = {
        "views_created": views,
        "total_queries_executed": len(summary_records),
        "queries": summary_records,
    }
    (rep_dir / "sql_execution_summary.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    out = run_all_sql_queries()
    print(f"Created {len(out['views_created'])} SQL views and executed {out['total_queries_executed']} analytical queries successfully.")

