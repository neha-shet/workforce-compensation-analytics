"""Python ETL & Feature Engineering Pipeline.

Transforms raw HR/Payroll CSVs into:
1. Audited quarantine datasets for rejected/anomalous records
2. Cleaned & feature-enriched master workforce dataset (Parquet + CSV)
3. Normalized Star Schema dimension & fact tables ready for PostgreSQL / SQLite / Power BI
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import (
    ANNUAL_LEAVE_ENTITLEMENT,
    AS_OF_DATE,
    CANONICAL_DEPARTMENTS,
    CANONICAL_LOCATIONS,
    DEPARTMENT_ALIASES,
    DESIGNATION_SALARY_BANDS_INR,
    EMPLOYMENT_TYPE_ALIASES,
    LOCATION_ALIASES,
    PATHS,
    SALARY_ANOMALY_LOWER_MULTIPLIER,
    SALARY_ANOMALY_UPPER_MULTIPLIER,
    STANDARD_ANNUAL_WORK_HOURS,
    ensure_directories,
)

EMP_ID_PATTERN = re.compile(r"^EMP\d{5}$")


def _clean_text_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.lower()


def _date_to_key(dt_series: pd.Series) -> pd.Series:
    """Convert Timestamp series to YYYYMMDD nullable Int64 keys."""
    valid = dt_series.notna()
    out = pd.Series(pd.NA, index=dt_series.index, dtype="Int64")
    if valid.any():
        out.loc[valid] = dt_series.loc[valid].dt.strftime("%Y%m%d").astype("int64")
    return out


def _assign_salary_band(total_comp: pd.Series) -> pd.Series:
    bins = [-np.inf, 800_000, 1_500_000, 2_500_000, 4_000_000, np.inf]
    labels = ["<8L", "8L-15L", "15L-25L", "25L-40L", "40L+"]
    return pd.cut(total_comp, bins=bins, labels=labels).astype(str)


def _assign_tenure_band(tenure: pd.Series) -> pd.Series:
    bins = [-np.inf, 1.0, 3.0, 5.0, 10.0, np.inf]
    labels = ["<1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
    return pd.cut(tenure, bins=bins, labels=labels).astype(str)


def _build_dim_date(start: str = "2010-01-01", end: str = "2026-12-31") -> pd.DataFrame:
    dates = pd.date_range(start=start, end=end, freq="D")
    # Indian Fiscal Year: Apr-Mar (e.g., Apr 2025..Mar 2026 = FY2025-26)
    fy_start = np.where(dates.month >= 4, dates.year, dates.year - 1)
    fiscal_year = [f"FY{y}-{str(y + 1)[-2:]}" for y in fy_start]
    return pd.DataFrame(
        {
            "date_key": dates.strftime("%Y%m%d").astype(int),
            "full_date": dates.strftime("%Y-%m-%d"),
            "year": dates.year,
            "quarter": dates.quarter,
            "month": dates.month,
            "month_name": dates.strftime("%b"),
            "day_of_week": dates.strftime("%a"),
            "fiscal_year": fiscal_year,
            "is_weekend": (dates.dayofweek >= 5).astype(int),
        }
    )


def run_etl_pipeline(
    raw_dir: Path | None = None,
    quarantine_dir: Path | None = None,
    processed_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Execute full Extract -> Validate -> Clean -> Transform -> Star Schema Export."""
    ensure_directories()
    r_dir = raw_dir or PATHS.data_raw
    q_dir = quarantine_dir or PATHS.data_quarantine
    p_dir = processed_dir or PATHS.data_processed
    w_dir = p_dir / "warehouse"
    rep_dir = reports_dir or PATHS.reports

    for d in (q_dir, p_dir, w_dir, rep_dir):
        d.mkdir(parents=True, exist_ok=True)

    as_of_ts = pd.Timestamp(AS_OF_DATE)
    audit: dict[str, Any] = {
        "run_timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_date": AS_OF_DATE.isoformat(),
        "quarantined_counts": {},
        "repaired_counts": {},
        "output_counts": {},
    }

    # =========================================================================
    # 1. EXTRACT
    # =========================================================================
    df_emp_raw = pd.read_csv(r_dir / "employees.csv")
    df_comp_raw = pd.read_csv(r_dir / "compensation.csv")
    df_att_raw = pd.read_csv(r_dir / "attendance_leave.csv")
    df_career_raw = pd.read_csv(r_dir / "career.csv")
    df_exit_raw = pd.read_csv(r_dir / "exit.csv")

    # =========================================================================
    # 2. CLEAN EMPLOYEES
    # =========================================================================
    emp = df_emp_raw.copy()
    emp["employee_id"] = emp["employee_id"].astype("string").str.strip()
    valid_id_mask = emp["employee_id"].notna() & emp["employee_id"].str.match(EMP_ID_PATTERN, na=False)

    emp_bad_id = emp.loc[~valid_id_mask].copy()
    emp_bad_id["quarantine_reason"] = "missing_or_invalid_employee_id"
    emp = emp.loc[valid_id_mask].copy()

    # Parse dates before deduplicating so we prefer valid date rows
    emp["joining_dt"] = pd.to_datetime(emp["joining_date"], format="%Y-%m-%d", errors="coerce")
    emp["dob_dt"] = pd.to_datetime(emp["date_of_birth"], format="%Y-%m-%d", errors="coerce")
    emp["_completeness_score"] = emp["joining_dt"].notna().astype(int) + emp["dob_dt"].notna().astype(int)
    emp = emp.sort_values(by=["employee_id", "_completeness_score"], ascending=[True, False])

    dup_mask = emp.duplicated(subset=["employee_id"], keep="first")
    emp_dups = emp.loc[dup_mask].drop(columns=["joining_dt", "dob_dt", "_completeness_score"]).copy()
    emp_dups["quarantine_reason"] = "duplicate_employee_id"
    emp = emp.loc[~dup_mask].drop(columns=["_completeness_score"]).copy()

    # Temporal / date validation
    age_at_join = (emp["joining_dt"] - emp["dob_dt"]).dt.days / 365.25
    invalid_emp_dates_mask = (
        emp["joining_dt"].isna()
        | emp["dob_dt"].isna()
        | (emp["joining_dt"] > as_of_ts)
        | (emp["dob_dt"] > as_of_ts)
        | (age_at_join < 16.0)
    )
    emp_bad_dates = emp.loc[invalid_emp_dates_mask].drop(columns=["joining_dt", "dob_dt"]).copy()
    emp_bad_dates["quarantine_reason"] = "invalid_date_or_impossible_tenure"
    emp = emp.loc[~invalid_emp_dates_mask].copy()

    quarantine_emp = pd.concat([emp_bad_id, emp_dups, emp_bad_dates], ignore_index=True)
    quarantine_emp.to_csv(q_dir / "quarantine_employees.csv", index=False)
    audit["quarantined_counts"]["employees"] = int(len(quarantine_emp))

    # Standardize categoricals
    raw_dept_clean = _clean_text_series(emp["department"])
    emp["department"] = raw_dept_clean.map(DEPARTMENT_ALIASES).fillna(emp["department"].astype(str).str.strip())
    audit["repaired_counts"]["departments_standardized"] = int(
        (~df_emp_raw["department"].isin(CANONICAL_DEPARTMENTS.keys())).sum()
    )

    raw_loc_clean = _clean_text_series(emp["location"])
    emp["location"] = raw_loc_clean.map(LOCATION_ALIASES).fillna(emp["location"].astype(str).str.strip())
    audit["repaired_counts"]["locations_standardized"] = int(
        (~df_emp_raw["location"].isin(CANONICAL_LOCATIONS.keys())).sum()
    )

    raw_et_clean = _clean_text_series(emp["employment_type"])
    emp["employment_type"] = raw_et_clean.map(EMPLOYMENT_TYPE_ALIASES).fillna("Full-Time")

    emp["designation"] = emp["designation"].astype(str).str.strip()
    emp["education"] = emp["education"].astype(str).str.strip()
    emp["performance_rating"] = pd.to_numeric(emp["performance_rating"], errors="coerce").fillna(3).clip(1, 5).astype(int)
    emp["age_years"] = ((as_of_ts - emp["dob_dt"]).dt.days / 365.25).round(1)
    emp["experience_years"] = np.minimum(
        pd.to_numeric(emp["experience_years"], errors="coerce").fillna(0.0).clip(lower=0.0),
        np.maximum(0.0, emp["age_years"] - 18.0),
    ).round(1)

    valid_emp_ids = set(emp["employee_id"].tolist())

    # =========================================================================
    # 3. CLEAN EXIT (Needed early to compute exact effective end date for tenure)
    # =========================================================================
    ex = df_exit_raw.copy()
    ex["employee_id"] = ex["employee_id"].astype("string").str.strip()
    ex = ex.loc[ex["employee_id"].isin(valid_emp_ids)].copy()

    ex_dup_mask = ex.duplicated(subset=["employee_id"], keep="first")
    ex_dups = ex.loc[ex_dup_mask].copy()
    ex_dups["quarantine_reason"] = "duplicate_exit_record"
    ex = ex.loc[~ex_dup_mask].copy()

    ex["exit_dt"] = pd.to_datetime(ex["exit_date"], format="%Y-%m-%d", errors="coerce")

    attr_map = {"yes": 1, "y": 1, "1": 1, "true": 1, "no": 0, "n": 0, "0": 0, "false": 0}
    attr_norm = ex["attrition"].astype("string").str.strip().str.lower().map(attr_map)
    # Infer if missing but exit_dt clearly present
    inferred_mask = attr_norm.isna() & ex["exit_dt"].notna()
    attr_norm.loc[inferred_mask] = 1

    missing_attr_mask = attr_norm.isna()
    ex_missing = ex.loc[missing_attr_mask].drop(columns=["exit_dt"]).copy()
    ex_missing["quarantine_reason"] = "missing_attrition_label"
    ex = ex.loc[~missing_attr_mask].copy()
    ex["attrition_flag"] = attr_norm.loc[~missing_attr_mask].astype(int)

    # Check exit_dt >= joining_dt
    ex = ex.merge(emp[["employee_id", "joining_dt"]], on="employee_id", how="left")
    bad_exit_dt_mask = (ex["attrition_flag"] == 1) & (
        ex["exit_dt"].isna() | (ex["exit_dt"] < ex["joining_dt"]) | (ex["exit_dt"] > as_of_ts)
    )
    ex_bad_dt = ex.loc[bad_exit_dt_mask].drop(columns=["exit_dt", "joining_dt", "attrition_flag"]).copy()
    ex_bad_dt["quarantine_reason"] = "invalid_or_pre_joining_exit_date"
    ex = ex.loc[~bad_exit_dt_mask].copy()

    # For active employees, ensure exit_dt & exit_reason are null
    ex.loc[ex["attrition_flag"] == 0, "exit_dt"] = pd.NaT
    ex.loc[ex["attrition_flag"] == 0, "exit_reason"] = None

    quarantine_exit = pd.concat([ex_dups, ex_missing, ex_bad_dt], ignore_index=True)
    quarantine_exit.to_csv(q_dir / "quarantine_exit.csv", index=False)
    audit["quarantined_counts"]["exit"] = int(len(quarantine_exit))

    # =========================================================================
    # 4. CLEAN COMPENSATION & SALARY ANOMALIES
    # =========================================================================
    comp = df_comp_raw.copy()
    comp["employee_id"] = comp["employee_id"].astype("string").str.strip()
    comp_valid_id = comp["employee_id"].isin(valid_emp_ids)
    comp_bad_id = comp.loc[~comp_valid_id].copy()
    comp_bad_id["quarantine_reason"] = "missing_invalid_or_orphan_employee_id"
    comp = comp.loc[comp_valid_id].copy()

    # Prefer valid positive salary rows when deduplicating payroll records
    comp["basic_salary"] = pd.to_numeric(comp["basic_salary"], errors="coerce")
    comp["_sal_valid"] = (comp["basic_salary"].notna() & (comp["basic_salary"] > 0)).astype(int)
    comp = comp.sort_values(by=["employee_id", "_sal_valid"], ascending=[True, False])

    comp_dup_mask = comp.duplicated(subset=["employee_id"], keep="first")
    comp_dups = comp.loc[comp_dup_mask].drop(columns=["_sal_valid"]).copy()
    comp_dups["quarantine_reason"] = "duplicate_payroll_record"
    comp = comp.loc[~comp_dup_mask].drop(columns=["_sal_valid"]).copy()

    # Quarantine missing or non-positive basic_salary
    bad_sal_mask = comp["basic_salary"].isna() | (comp["basic_salary"] <= 0)
    comp_bad_sal = comp.loc[bad_sal_mask].copy()
    comp_bad_sal["quarantine_reason"] = "missing_or_non_positive_basic_salary"
    comp = comp.loc[~bad_sal_mask].copy()

    quarantine_comp = pd.concat([comp_bad_id, comp_dups, comp_bad_sal], ignore_index=True)
    quarantine_comp.to_csv(q_dir / "quarantine_compensation.csv", index=False)
    audit["quarantined_counts"]["compensation"] = int(len(quarantine_comp))

    # Merge designation/department/employment_type to detect & normalize extreme salary entry errors
    comp = comp.merge(emp[["employee_id", "department", "designation", "employment_type", "joining_dt"]], on="employee_id", how="left")
    comp["allowances"] = pd.to_numeric(comp["allowances"], errors="coerce").fillna(0.0).clip(lower=0.0)
    comp["bonus"] = pd.to_numeric(comp["bonus"], errors="coerce").fillna(0.0).clip(lower=0.0)
    comp["deductions"] = pd.to_numeric(comp["deductions"], errors="coerce").fillna(0.0)
    comp["salary_increment"] = pd.to_numeric(comp["salary_increment"], errors="coerce").fillna(0.0).clip(lower=0.0)

    # Fix negative deductions (sign/export error -> recompute from typical effective deduction rate)
    neg_ded_mask = comp["deductions"] < 0
    audit["repaired_counts"]["negative_deductions_repaired"] = int(neg_ded_mask.sum())
    comp.loc[neg_ded_mask, "deductions"] = comp.loc[neg_ded_mask, "deductions"].abs()

    # Flag & normalize extreme salary anomalies outside expected designation band
    is_intern = comp["employment_type"] == "Intern"
    band_low = np.where(
        is_intern,
        150_000.0,
        comp["designation"].map(lambda d: DESIGNATION_SALARY_BANDS_INR[d][0] * SALARY_ANOMALY_LOWER_MULTIPLIER),
    )
    band_high = np.where(
        is_intern,
        650_000.0,
        comp["designation"].map(lambda d: DESIGNATION_SALARY_BANDS_INR[d][1] * SALARY_ANOMALY_UPPER_MULTIPLIER),
    )
    anom_mask = (comp["basic_salary"] < band_low) | (comp["basic_salary"] > band_high)
    comp["is_salary_anomaly"] = anom_mask.astype(int)

    if anom_mask.any():
        comp.loc[anom_mask].to_csv(q_dir / "salary_anomalies_flagged.csv", index=False)
        # Replace corrupted data-entry salary outliers with clean department+designation median
        clean_medians = (
            comp.loc[~anom_mask]
            .groupby(["department", "designation"])["basic_salary"]
            .median()
        )
        desig_medians = comp.loc[~anom_mask].groupby("designation")["basic_salary"].median()
        for idx in comp.index[anom_mask]:
            key = (comp.loc[idx, "department"], comp.loc[idx, "designation"])
            replacement = clean_medians.get(key, desig_medians.get(comp.loc[idx, "designation"], 1_000_000.0))
            comp.loc[idx, "basic_salary"] = round(float(replacement), -2)
            # Realign deductions proportionately if inflated along with anomaly
            comp.loc[idx, "deductions"] = round(float(replacement * 0.16), -2)
    audit["repaired_counts"]["salary_anomalies_normalized"] = int(anom_mask.sum())

    # Recompute reconciled net_salary & derived compensation variables
    comp["total_compensation"] = (comp["basic_salary"] + comp["allowances"] + comp["bonus"]).round(2)
    recomputed_net = (comp["total_compensation"] - comp["deductions"]).round(2)
    net_mismatch_count = int((comp["net_salary"].notna() & ((comp["net_salary"] - recomputed_net).abs() > 100.0)).sum())
    comp["net_salary"] = recomputed_net
    audit["repaired_counts"]["net_salary_reconciled"] = net_mismatch_count

    prior_base = np.maximum(1.0, (comp["basic_salary"] + comp["allowances"]) - comp["salary_increment"])
    comp["salary_growth_pct"] = np.round((comp["salary_increment"] / prior_base) * 100.0, 2)
    comp["bonus_to_salary_ratio"] = np.round(comp["bonus"] / np.maximum(1.0, comp["basic_salary"]), 4)
    comp["salary_band"] = _assign_salary_band(comp["total_compensation"])

    comp["increment_dt"] = pd.to_datetime(comp["increment_date"], format="%Y-%m-%d", errors="coerce")
    comp["increment_dt"] = comp["increment_dt"].fillna(comp["joining_dt"]).clip(upper=as_of_ts)

    # =========================================================================
    # 5. CLEAN CAREER
    # =========================================================================
    career = df_career_raw.copy()
    career["employee_id"] = career["employee_id"].astype("string").str.strip()
    career = career.loc[career["employee_id"].isin(valid_emp_ids)].drop_duplicates(subset=["employee_id"]).copy()
    career["promotion_count"] = pd.to_numeric(career["promotion_count"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    career["training_hours"] = pd.to_numeric(career["training_hours"], errors="coerce").fillna(0.0).clip(lower=0.0).round(1)
    career["manager_rating"] = pd.to_numeric(career["manager_rating"], errors="coerce").fillna(3).clip(1, 5).astype(int)

    career["last_promotion_dt"] = pd.to_datetime(career["last_promotion_date"], format="%Y-%m-%d", errors="coerce")
    career = career.merge(emp[["employee_id", "joining_dt"]], on="employee_id", how="left")
    bad_promo_mask = career["last_promotion_dt"].notna() & (
        (career["last_promotion_dt"] < career["joining_dt"]) | (career["last_promotion_dt"] > as_of_ts)
    )
    audit["repaired_counts"]["invalid_promotion_dates_reset"] = int(bad_promo_mask.sum())
    career.loc[bad_promo_mask, "last_promotion_dt"] = pd.NaT

    # =========================================================================
    # 6. CLEAN ATTENDANCE / LEAVE
    # =========================================================================
    att = df_att_raw.copy()
    att["employee_id"] = att["employee_id"].astype("string").str.strip()
    att = att.loc[att["employee_id"].isin(valid_emp_ids)].copy()

    att_dup_mask = att.duplicated(subset=["employee_id", "year"], keep="first")
    att_dups = att.loc[att_dup_mask].copy()
    att_dups["quarantine_reason"] = "duplicate_employee_year"
    att = att.loc[~att_dup_mask].copy()

    bad_att_mask = (
        att["leave_days"].isna()
        | (att["leave_days"] < 0)
        | (att["leave_days"] > 365)
        | (att["overtime_hours"].isna())
        | (att["overtime_hours"] < 0)
    )
    att_bad = att.loc[bad_att_mask].copy()
    att_bad["quarantine_reason"] = "invalid_leave_or_negative_overtime"
    att = att.loc[~bad_att_mask].copy()

    quarantine_att = pd.concat([att_dups, att_bad], ignore_index=True)
    quarantine_att.to_csv(q_dir / "quarantine_attendance.csv", index=False)
    audit["quarantined_counts"]["attendance_leave"] = int(len(quarantine_att))

    att["sick_leave"] = pd.to_numeric(att["sick_leave"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    att["casual_leave"] = pd.to_numeric(att["casual_leave"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    att["unpaid_leave"] = pd.to_numeric(att["unpaid_leave"], errors="coerce").fillna(0).clip(lower=0).astype(int)
    att["leave_days"] = att["sick_leave"] + att["casual_leave"] + att["unpaid_leave"]
    att["overtime_hours"] = pd.to_numeric(att["overtime_hours"], errors="coerce").fillna(0.0).round(1)
    att["leave_utilization"] = np.round(att["leave_days"] / ANNUAL_LEAVE_ENTITLEMENT, 4)
    att["overtime_ratio"] = np.round(att["overtime_hours"] / STANDARD_ANNUAL_WORK_HOURS, 4)
    att["year"] = att["year"].astype(int)

    # =========================================================================
    # 7. DERIVE WORKFORCE TENURE & PROMOTION GAP USING EFFECTIVE END DATE
    # =========================================================================
    end_date_map = ex.set_index("employee_id")["exit_dt"].to_dict()
    attr_flag_map = ex.set_index("employee_id")["attrition_flag"].to_dict()

    emp["attrition_flag"] = emp["employee_id"].map(attr_flag_map).fillna(0).astype(int)
    emp["effective_end_dt"] = emp["employee_id"].map(end_date_map)
    emp["effective_end_dt"] = emp["effective_end_dt"].fillna(as_of_ts)
    emp["tenure_years"] = np.round(np.maximum(0.0, (emp["effective_end_dt"] - emp["joining_dt"]).dt.days / 365.25), 2)
    emp["tenure_band"] = _assign_tenure_band(emp["tenure_years"])
    emp["is_active"] = (emp["attrition_flag"] == 0).astype(int)

    career = career.merge(emp[["employee_id", "effective_end_dt"]], on="employee_id", how="left")
    promo_ref_dt = career["last_promotion_dt"].fillna(career["joining_dt"])
    career["promotion_gap"] = np.round(np.maximum(0.0, (career["effective_end_dt"] - promo_ref_dt).dt.days / 365.25), 2)

    # =========================================================================
    # 8. BUILD STAR SCHEMA DIMENSIONS & FACTS
    # =========================================================================
    # Dimension: dim_department
    dim_department = pd.DataFrame(
        [
            {
                "department_key": idx,
                "department_name": dept,
                "department_head_function": meta["head_function"],
                "annual_budget_inr": float(meta["budget_inr"]),
                "target_attrition_pct": float(meta["target_attrition"]),
            }
            for idx, (dept, meta) in enumerate(CANONICAL_DEPARTMENTS.items(), start=1)
        ]
    )
    dept_key_map = dim_department.set_index("department_name")["department_key"].to_dict()

    # Dimension: dim_location
    dim_location = pd.DataFrame(
        [
            {
                "location_key": idx,
                "city": city,
                "region": meta["region"],
                "country": meta["country"],
                "cost_of_living_tier": meta["tier"],
            }
            for idx, (city, meta) in enumerate(CANONICAL_LOCATIONS.items(), start=1)
        ]
    )
    loc_key_map = dim_location.set_index("city")["location_key"].to_dict()

    # Dimension: dim_date
    dim_date = _build_dim_date("2010-01-01", "2026-12-31")

    # Dimension: dim_employee
    emp = emp.sort_values("employee_id").reset_index(drop=True)
    emp["employee_key"] = np.arange(1, len(emp) + 1)
    emp["department_key"] = emp["department"].map(dept_key_map).astype(int)
    emp["location_key"] = emp["location"].map(loc_key_map).astype(int)
    emp_key_map = emp.set_index("employee_id")["employee_key"].to_dict()

    dim_employee = emp[
        [
            "employee_key",
            "employee_id",
            "department_key",
            "location_key",
            "designation",
            "employment_type",
            "education",
            "date_of_birth",
            "age_years",
            "joining_date",
            "experience_years",
            "tenure_years",
            "tenure_band",
            "is_active",
        ]
    ].copy()
    dim_employee["joining_date"] = emp["joining_dt"].dt.strftime("%Y-%m-%d")
    dim_employee["date_of_birth"] = emp["dob_dt"].dt.strftime("%Y-%m-%d")

    # Fact: fact_compensation
    comp = comp.sort_values("employee_id").reset_index(drop=True)
    fact_compensation = pd.DataFrame(
        {
            "compensation_key": np.arange(1, len(comp) + 1),
            "employee_key": comp["employee_id"].map(emp_key_map).astype(int),
            "department_key": comp["department"].map(dept_key_map).astype(int),
            "location_key": comp["employee_id"].map(emp.set_index("employee_id")["location_key"]).astype(int),
            "increment_date_key": _date_to_key(comp["increment_dt"]),
            "basic_salary": comp["basic_salary"].round(2),
            "allowances": comp["allowances"].round(2),
            "bonus": comp["bonus"].round(2),
            "deductions": comp["deductions"].round(2),
            "net_salary": comp["net_salary"].round(2),
            "total_compensation": comp["total_compensation"].round(2),
            "salary_increment": comp["salary_increment"].round(2),
            "salary_growth_pct": comp["salary_growth_pct"],
            "bonus_to_salary_ratio": comp["bonus_to_salary_ratio"],
            "salary_band": comp["salary_band"],
            "is_salary_anomaly": comp["is_salary_anomaly"],
        }
    )

    # Fact: fact_leave
    att = att.sort_values(["employee_id", "year"]).reset_index(drop=True)
    att_dept_map = emp.set_index("employee_id")["department_key"].to_dict()
    leave_date_key_map = {2024: 20241231, 2025: 20251231, 2026: int(AS_OF_DATE.strftime("%Y%m%d"))}
    fact_leave = pd.DataFrame(
        {
            "leave_key": np.arange(1, len(att) + 1),
            "employee_key": att["employee_id"].map(emp_key_map).astype(int),
            "department_key": att["employee_id"].map(att_dept_map).astype(int),
            "date_key": att["year"].map(leave_date_key_map).astype(int),
            "year": att["year"].astype(int),
            "leave_days": att["leave_days"].astype(int),
            "sick_leave": att["sick_leave"].astype(int),
            "casual_leave": att["casual_leave"].astype(int),
            "unpaid_leave": att["unpaid_leave"].astype(int),
            "overtime_hours": att["overtime_hours"],
            "leave_utilization": att["leave_utilization"],
            "overtime_ratio": att["overtime_ratio"],
        }
    )

    # Fact: fact_performance
    career = career.sort_values("employee_id").reset_index(drop=True)
    perf_rating_map = emp.set_index("employee_id")["performance_rating"].to_dict()
    fact_performance = pd.DataFrame(
        {
            "performance_key": np.arange(1, len(career) + 1),
            "employee_key": career["employee_id"].map(emp_key_map).astype(int),
            "department_key": career["employee_id"].map(att_dept_map).astype(int),
            "last_promotion_date_key": _date_to_key(career["last_promotion_dt"]),
            "performance_rating": career["employee_id"].map(perf_rating_map).astype(int),
            "manager_rating": career["manager_rating"].astype(int),
            "promotion_count": career["promotion_count"].astype(int),
            "training_hours": career["training_hours"],
            "promotion_gap": career["promotion_gap"],
        }
    )

    # Fact: fact_attrition
    ex = ex.sort_values("employee_id").reset_index(drop=True)
    comp_tot_map = comp.set_index("employee_id")["total_compensation"].to_dict()
    tenure_map = emp.set_index("employee_id")["tenure_years"].to_dict()
    loc_emp_map = emp.set_index("employee_id")["location_key"].to_dict()
    fact_attrition = pd.DataFrame(
        {
            "attrition_key": np.arange(1, len(ex) + 1),
            "employee_key": ex["employee_id"].map(emp_key_map).astype(int),
            "department_key": ex["employee_id"].map(att_dept_map).astype(int),
            "location_key": ex["employee_id"].map(loc_emp_map).astype(int),
            "exit_date_key": _date_to_key(ex["exit_dt"]),
            "attrition_flag": ex["attrition_flag"].astype(int),
            "exit_reason": ex["exit_reason"],
            "tenure_at_exit_years": np.where(
                ex["attrition_flag"] == 1,
                ex["employee_id"].map(tenure_map),
                np.nan,
            ),
            "last_total_compensation": ex["employee_id"].map(comp_tot_map),
        }
    )

    # =========================================================================
    # 9. BUILD MASTER ANALYTICAL TABLE (For Phase 2 EDA & Phase 4 ML)
    # =========================================================================
    # Latest leave year snapshot per employee + career & comp & exit
    latest_att = att.sort_values("year").drop_duplicates(subset=["employee_id"], keep="last")
    master = (
        emp[
            [
                "employee_id",
                "department",
                "designation",
                "location",
                "joining_date",
                "date_of_birth",
                "employment_type",
                "education",
                "age_years",
                "experience_years",
                "tenure_years",
                "tenure_band",
                "performance_rating",
                "is_active",
            ]
        ]
        .copy()
    )
    master["joining_date"] = emp["joining_dt"].dt.strftime("%Y-%m-%d")
    master["date_of_birth"] = emp["dob_dt"].dt.strftime("%Y-%m-%d")

    master = master.merge(
        comp[
            [
                "employee_id",
                "basic_salary",
                "allowances",
                "bonus",
                "deductions",
                "net_salary",
                "total_compensation",
                "salary_increment",
                "salary_growth_pct",
                "bonus_to_salary_ratio",
                "salary_band",
                "is_salary_anomaly",
            ]
        ],
        on="employee_id",
        how="left",
    )
    master = master.merge(
        latest_att[
            [
                "employee_id",
                "year",
                "leave_days",
                "sick_leave",
                "casual_leave",
                "unpaid_leave",
                "overtime_hours",
                "leave_utilization",
                "overtime_ratio",
            ]
        ].rename(columns={"year": "latest_leave_year"}),
        on="employee_id",
        how="left",
    )
    master = master.merge(
        career[
            [
                "employee_id",
                "promotion_count",
                "training_hours",
                "manager_rating",
                "promotion_gap",
            ]
        ],
        on="employee_id",
        how="left",
    )
    ex_master = ex[["employee_id", "attrition_flag", "exit_reason"]].copy()
    ex_master["exit_date"] = ex["exit_dt"].dt.strftime("%Y-%m-%d")
    master = master.merge(ex_master, on="employee_id", how="left")

    # =========================================================================
    # 10. EXPORT PROCESSED DATASETS & STAR SCHEMA TABLES
    # =========================================================================
    star_tables: dict[str, pd.DataFrame] = {
        "dim_department": dim_department,
        "dim_location": dim_location,
        "dim_date": dim_date,
        "dim_employee": dim_employee,
        "fact_compensation": fact_compensation,
        "fact_leave": fact_leave,
        "fact_performance": fact_performance,
        "fact_attrition": fact_attrition,
    }

    for name, df in star_tables.items():
        df.to_csv(w_dir / f"{name}.csv", index=False)
        df.to_parquet(w_dir / f"{name}.parquet", index=False)
        audit["output_counts"][name] = int(len(df))

    master.to_csv(p_dir / "master_workforce.csv", index=False)
    master.to_parquet(p_dir / "master_workforce.parquet", index=False)
    audit["output_counts"]["master_workforce"] = int(len(master))

    (rep_dir / "etl_run_summary.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    return audit


if __name__ == "__main__":
    summary = run_etl_pipeline()
    print("ETL Complete:")
    print(json.dumps(summary, indent=2))
