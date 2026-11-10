"""Database, Artifact, and Formatting Helpers for the Streamlit Application.

Centralizes SQLite warehouse queries, model/SHAP/DQ/recommendation artifact loading,
and Indian Rupee (INR / Lakhs / Crores) formatting so both the UI and automated tests
can verify data loading cleanly.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config.settings import PATHS
from src.analytics.sql_runner import apply_sqlite_views


def format_inr(amount: float | int | None) -> str:
    """Format INR numeric value using Indian comma grouping (e.g. ₹21,94,698)."""
    if amount is None or pd.isna(amount):
        return "₹0"
    neg = amount < 0
    n = round(abs(float(amount)))
    s = str(n)
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        groups: list[str] = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        formatted = ",".join(reversed(groups)) + "," + last3
    return f"{'-' if neg else ''}₹{formatted}"


def format_inr_crore(amount_inr: float | None, already_in_crores: bool = False) -> str:
    """Format monetary value in INR Crores (e.g. ₹5,466.12 Cr)."""
    if amount_inr is None or pd.isna(amount_inr):
        return "₹0.00 Cr"
    cr = float(amount_inr) if already_in_crores else float(amount_inr) / 1e7
    return f"₹{cr:,.2f} Cr"


def format_inr_lakhs(amount_inr: float | None) -> str:
    """Format monetary value in INR Lakhs (e.g. ₹21.95 L)."""
    if amount_inr is None or pd.isna(amount_inr):
        return "₹0.00 L"
    return f"₹{float(amount_inr) / 1e5:,.2f} L"


def check_warehouse_ready(db_path: Path | None = None) -> Path:
    target_db = db_path or PATHS.sqlite_db
    if not target_db.exists():
        raise FileNotFoundError(
            f"SQLite warehouse not found at {target_db}. Run Phase 1 (`python scripts/run_phase1.py`) first."
        )
    return target_db


def fetch_workforce_360(db_path: Path | None = None) -> pd.DataFrame:
    """Load unified employee 360 analytical dataset from SQLite warehouse views."""
    target_db = check_warehouse_ready(db_path)
    apply_sqlite_views(db_path=target_db)
    query = """
    SELECT
        v.*,
        CASE WHEN v.latest_leave_year = 2026 THEN ROUND(v.sick_leave / 0.75, 1) ELSE v.sick_leave END AS annualized_sick_leave,
        CASE WHEN v.latest_leave_year = 2026 THEN ROUND(v.casual_leave / 0.75, 1) ELSE v.casual_leave END AS annualized_casual_leave,
        CASE WHEN v.latest_leave_year = 2026 THEN ROUND(v.unpaid_leave / 0.75, 1) ELSE v.unpaid_leave END AS annualized_unpaid_leave
    FROM vw_employee_workforce_360 v
    """
    conn = sqlite3.connect(target_db)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # Merge precomputed ML risk scores if available
    risk_path = PATHS.data_processed / "employee_risk_scores.parquet"
    if risk_path.exists():
        rs = pd.read_parquet(risk_path)[["employee_id", "attrition_probability", "predicted_high_risk_flag", "risk_tier"]]
        df = df.merge(rs, on="employee_id", how="left")
    return df


def fetch_department_kpi(db_path: Path | None = None) -> pd.DataFrame:
    target_db = check_warehouse_ready(db_path)
    conn = sqlite3.connect(target_db)
    try:
        return pd.read_sql_query("SELECT * FROM vw_department_kpi_summary ORDER BY total_payroll_cr DESC", conn)
    finally:
        conn.close()


def fetch_monthly_trends(db_path: Path | None = None) -> pd.DataFrame:
    target_db = check_warehouse_ready(db_path)
    conn = sqlite3.connect(target_db)
    try:
        return pd.read_sql_query("SELECT * FROM vw_monthly_hiring_and_attrition ORDER BY year_month", conn)
    finally:
        conn.close()


def fetch_leave_history(db_path: Path | None = None) -> pd.DataFrame:
    target_db = check_warehouse_ready(db_path)
    conn = sqlite3.connect(target_db)
    try:
        return pd.read_sql_query(
            """
            SELECT
                d.department_name,
                fl.year,
                COUNT(*) AS records,
                ROUND(AVG(CASE WHEN fl.year = 2026 THEN fl.leave_days / 0.75 ELSE fl.leave_days END), 1) AS avg_ann_leave_days,
                ROUND(AVG(fl.sick_leave), 1) AS avg_sick_leave,
                ROUND(AVG(fl.casual_leave), 1) AS avg_casual_leave,
                ROUND(AVG(fl.unpaid_leave), 1) AS avg_unpaid_leave,
                ROUND(AVG(CASE WHEN fl.year = 2026 THEN fl.overtime_hours / 0.75 ELSE fl.overtime_hours END), 1) AS avg_ann_overtime_hrs
            FROM fact_leave fl
            JOIN dim_department d ON fl.department_key = d.department_key
            GROUP BY d.department_name, fl.year
            ORDER BY fl.year, d.department_name
            """,
            conn,
        )
    finally:
        conn.close()


def fetch_data_quality_artifacts() -> dict[str, Any]:
    """Load pre-ETL Data Quality Report, ETL Run Summary, and sample quarantine rows."""
    dq_json_path = PATHS.reports / "data_quality_report.json"
    etl_json_path = PATHS.reports / "etl_run_summary.json"
    dq = json.loads(dq_json_path.read_text(encoding="utf-8")) if dq_json_path.exists() else {}
    etl = json.loads(etl_json_path.read_text(encoding="utf-8")) if etl_json_path.exists() else {}

    quarantine_samples: dict[str, pd.DataFrame] = {}
    for fname in ("salary_anomalies_flagged.csv", "quarantine_employees.csv", "quarantine_compensation.csv", "quarantine_exit.csv", "quarantine_attendance.csv"):
        p = PATHS.data_quarantine / fname
        if p.exists():
            quarantine_samples[fname] = pd.read_csv(p)

    return {"dq_report": dq, "etl_summary": etl, "quarantine_files": quarantine_samples}


def fetch_ml_and_shap_artifacts() -> dict[str, Any]:
    """Load trained ML champion bundle, comparison metrics, and SHAP metadata."""
    model_path = PATHS.root / "models" / "best_attrition_model.joblib"
    comp_path = PATHS.root / "models" / "model_comparison.json"
    shap_path = PATHS.root / "models" / "shap_global_importance.json"

    return {
        "bundle": joblib.load(model_path) if model_path.exists() else None,
        "comparison": json.loads(comp_path.read_text(encoding="utf-8")) if comp_path.exists() else {},
        "shap_summary": json.loads(shap_path.read_text(encoding="utf-8")) if shap_path.exists() else {},
    }


def fetch_recommendations() -> dict[str, Any]:
    rec_path = PATHS.reports / "business_recommendations.json"
    if rec_path.exists():
        return json.loads(rec_path.read_text(encoding="utf-8"))
    return {"recommendations": []}

