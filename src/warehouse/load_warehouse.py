"""Dimensional Data Warehouse Loader (SQLite & PostgreSQL).

Loads normalized star-schema dimension & fact tables from ETL exports into:
1. Local SQLite Data Warehouse (zero external server dependencies)
2. PostgreSQL 16 Data Warehouse (when psycopg2/sqlalchemy & Postgres are running)
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import (
    DB_BACKEND,
    PATHS,
    PG_DB,
    PG_HOST,
    PG_PASSWORD,
    PG_PORT,
    PG_SCHEMA,
    PG_USER,
    ensure_directories,
)

LOAD_ORDER: tuple[str, ...] = (
    "dim_department",
    "dim_location",
    "dim_date",
    "dim_employee",
    "fact_compensation",
    "fact_leave",
    "fact_performance",
    "fact_attrition",
)


def _to_python_scalar(val: Any) -> Any:
    """Convert numpy/pandas scalars and NA values to native Python types for DB drivers."""
    if val is None or pd.isna(val):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


def _df_to_records(df: pd.DataFrame) -> list[tuple[Any, ...]]:
    cols = [df[col].tolist() for col in df.columns]
    return [tuple(_to_python_scalar(col_vals[i]) for col_vals in cols) for i in range(len(df))]


def _build_dq_metrics_df(reports_dir: Path) -> pd.DataFrame:
    dq_path = reports_dir / "data_quality_report.json"
    if not dq_path.exists():
        return pd.DataFrame(
            columns=["metric_id", "metric_category", "metric_name", "metric_value", "assessed_at_utc"]
        )
    dq = json.loads(dq_path.read_text(encoding="utf-8"))
    assessed_at = str(dq.get("generated_at_utc", ""))

    rows: list[dict[str, Any]] = []
    metric_id = 1
    for name, val in dq.get("quality_scores_pct", {}).items():
        rows.append(
            {
                "metric_id": metric_id,
                "metric_category": "quality_score_pct",
                "metric_name": name,
                "metric_value": float(val),
                "assessed_at_utc": assessed_at,
            }
        )
        metric_id += 1

    for name, val in dq.get("headline_summary", {}).items():
        rows.append(
            {
                "metric_id": metric_id,
                "metric_category": "defect_count",
                "metric_name": name,
                "metric_value": float(val),
                "assessed_at_utc": assessed_at,
            }
        )
        metric_id += 1

    return pd.DataFrame(rows)


def _load_star_dataframes(warehouse_export_dir: Path, reports_dir: Path) -> dict[str, pd.DataFrame]:
    tables: dict[str, pd.DataFrame] = {}
    for table_name in LOAD_ORDER:
        pq_path = warehouse_export_dir / f"{table_name}.parquet"
        csv_path = warehouse_export_dir / f"{table_name}.csv"
        if pq_path.exists():
            tables[table_name] = pd.read_parquet(pq_path)
        elif csv_path.exists():
            tables[table_name] = pd.read_csv(csv_path)
        else:
            raise FileNotFoundError(f"Missing ETL warehouse export for {table_name} in {warehouse_export_dir}")
    tables["meta_data_quality_metrics"] = _build_dq_metrics_df(reports_dir)
    return tables


def load_sqlite_warehouse(
    warehouse_export_dir: Path | None = None,
    sqlite_path: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Create schema and bulk load star-schema tables into local SQLite database."""
    ensure_directories()
    export_dir = warehouse_export_dir or PATHS.data_warehouse_exports
    db_path = sqlite_path or PATHS.sqlite_db
    rep_dir = reports_dir or PATHS.reports
    ddl_path = PATHS.sql_warehouse / "02_ddl_sqlite.sql"

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tables = _load_star_dataframes(export_dir, rep_dir)

    ddl_sql = ddl_path.read_text(encoding="utf-8")
    loaded_counts: dict[str, int] = {}

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(ddl_sql)
        conn.execute("PRAGMA foreign_keys = ON;")

        with conn:
            for table_name in (*LOAD_ORDER, "meta_data_quality_metrics"):
                df = tables[table_name]
                if df.empty:
                    loaded_counts[table_name] = 0
                    continue
                cols = ", ".join(df.columns)
                placeholders = ", ".join(["?"] * len(df.columns))
                sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
                records = _df_to_records(df)
                conn.executemany(sql, records)
                loaded_counts[table_name] = len(records)

        # Sanity KPI verification directly from SQLite warehouse
        kpi_row = conn.execute(
            """
            SELECT
                COUNT(DISTINCT e.employee_key) AS total_employees,
                ROUND(SUM(c.total_compensation) / 10000000.0, 2) AS total_payroll_inr_cr,
                ROUND(AVG(c.total_compensation), 0) AS avg_total_comp_inr,
                ROUND(100.0 * AVG(a.attrition_flag), 2) AS attrition_rate_pct,
                ROUND(AVG(e.tenure_years), 2) AS avg_tenure_years
            FROM dim_employee e
            LEFT JOIN fact_compensation c ON e.employee_key = c.employee_key
            LEFT JOIN fact_attrition a ON e.employee_key = a.employee_key
            """
        ).fetchone()
    finally:
        conn.close()

    return {
        "backend": "sqlite",
        "database_path": str(db_path),
        "table_row_counts": loaded_counts,
        "kpi_sanity_check": {
            "total_employees": int(kpi_row[0]),
            "total_payroll_inr_cr": float(kpi_row[1]),
            "avg_total_comp_inr": float(kpi_row[2]),
            "attrition_rate_pct": float(kpi_row[3]),
            "avg_tenure_years": float(kpi_row[4]),
        },
    }


def load_postgres_warehouse(
    warehouse_export_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Create schema and bulk load star-schema tables into PostgreSQL 16."""
    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import execute_values  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "psycopg2 is not installed. Run `pip install psycopg2-binary` (or `pip install -r requirements.txt`) to load PostgreSQL."
        ) from exc

    if not PG_PASSWORD:
        raise ValueError(
            "PG_PASSWORD environment variable is empty. Set PG_PASSWORD in .env or environment before using PostgreSQL."
        )

    export_dir = warehouse_export_dir or PATHS.data_warehouse_exports
    rep_dir = reports_dir or PATHS.reports
    ddl_path = PATHS.sql_warehouse / "01_ddl_postgres.sql"
    tables = _load_star_dataframes(export_dir, rep_dir)
    ddl_sql = ddl_path.read_text(encoding="utf-8")

    loaded_counts: dict[str, int] = {}
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(ddl_sql)
                for table_name in (*LOAD_ORDER, "meta_data_quality_metrics"):
                    df = tables[table_name]
                    if df.empty:
                        loaded_counts[table_name] = 0
                        continue
                    cols = ", ".join(df.columns)
                    sql = f"INSERT INTO {PG_SCHEMA}.{table_name} ({cols}) VALUES %s"
                    records = _df_to_records(df)
                    execute_values(cur, sql, records, page_size=2000)
                    loaded_counts[table_name] = len(records)
    finally:
        conn.close()

    return {
        "backend": "postgres",
        "dsn": f"postgresql://{PG_USER}@{PG_HOST}:{PG_PORT}/{PG_DB}?schema={PG_SCHEMA}",
        "table_row_counts": loaded_counts,
    }


def load_warehouse(backend: str | None = None) -> list[dict[str, Any]]:
    """Load warehouse using configured backend ('sqlite', 'postgres', or 'both')."""
    target = (backend or DB_BACKEND).lower()
    results: list[dict[str, Any]] = []

    if target in ("sqlite", "both"):
        results.append(load_sqlite_warehouse())

    if target in ("postgres", "both"):
        try:
            results.append(load_postgres_warehouse())
        except Exception as exc:
            if target == "postgres":
                raise
            results.append({"backend": "postgres", "status": "skipped", "reason": str(exc)})

    return results


if __name__ == "__main__":
    res = load_warehouse()
    print(json.dumps(res, indent=2))

