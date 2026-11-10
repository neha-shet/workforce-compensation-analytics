"""Enterprise HR & Payroll Data Quality Assessor.

Performs pre-ETL validation across all 5 raw CSV tables to quantify completeness,
uniqueness, validity, consistency, and referential/temporal integrity issues.
Produces both JSON and Markdown Data Quality Assessment Reports.
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
    AS_OF_DATE,
    CANONICAL_DEPARTMENTS,
    CANONICAL_LOCATIONS,
    DESIGNATION_SALARY_BANDS_INR,
    PATHS,
    SALARY_ANOMALY_LOWER_MULTIPLIER,
    SALARY_ANOMALY_UPPER_MULTIPLIER,
    ensure_directories,
)

EMP_ID_PATTERN = re.compile(r"^EMP\d{5}$")


def _parse_iso_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%Y-%m-%d", errors="coerce")


def _is_valid_emp_id(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().str.match(EMP_ID_PATTERN)


def assess_data_quality(
    raw_dir: Path | None = None,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Run comprehensive data quality assessment on raw HR & payroll CSV files."""
    ensure_directories()
    r_dir = raw_dir or PATHS.data_raw
    rep_dir = reports_dir or PATHS.reports
    rep_dir.mkdir(parents=True, exist_ok=True)

    df_emp = pd.read_csv(r_dir / "employees.csv")
    df_comp = pd.read_csv(r_dir / "compensation.csv")
    df_att = pd.read_csv(r_dir / "attendance_leave.csv")
    df_career = pd.read_csv(r_dir / "career.csv")
    df_exit = pd.read_csv(r_dir / "exit.csv")

    tables = {
        "employees": df_emp,
        "compensation": df_comp,
        "attendance_leave": df_att,
        "career": df_career,
        "exit": df_exit,
    }

    # 1. Missing & Invalid Employee IDs
    missing_id_by_table = {name: int(df["employee_id"].isna().sum()) for name, df in tables.items()}
    invalid_id_by_table = {
        name: int((df["employee_id"].notna() & ~_is_valid_emp_id(df["employee_id"])).sum())
        for name, df in tables.items()
    }

    # 2. Duplicate Records
    emp_valid_ids = df_emp.loc[_is_valid_emp_id(df_emp["employee_id"]), "employee_id"]
    dup_emp_ids = int(emp_valid_ids.duplicated().sum())

    comp_valid_ids = df_comp.loc[_is_valid_emp_id(df_comp["employee_id"]), "employee_id"]
    dup_payroll_records = int(comp_valid_ids.duplicated().sum())

    att_valid = df_att.loc[_is_valid_emp_id(df_att["employee_id"])]
    dup_att_records = int(att_valid.duplicated(subset=["employee_id", "year"]).sum())

    career_dup = int(df_career.loc[_is_valid_emp_id(df_career["employee_id"]), "employee_id"].duplicated().sum())
    exit_dup = int(df_exit.loc[_is_valid_emp_id(df_exit["employee_id"]), "employee_id"].duplicated().sum())

    total_duplicates = dup_emp_ids + dup_payroll_records + dup_att_records + career_dup + exit_dup

    # 3. Compensation Checks
    missing_basic_salary = int(df_comp["basic_salary"].isna().sum())
    non_positive_salary = int((df_comp["basic_salary"].notna() & (df_comp["basic_salary"] <= 0)).sum())
    invalid_salaries_total = missing_basic_salary + non_positive_salary

    negative_deductions = int((df_comp["deductions"].notna() & (df_comp["deductions"] < 0)).sum())

    expected_net = (
        df_comp["basic_salary"].fillna(0)
        + df_comp["allowances"].fillna(0)
        + df_comp["bonus"].fillna(0)
        - df_comp["deductions"].fillna(0)
    )
    valid_sal_mask = df_comp["basic_salary"].notna() & (df_comp["basic_salary"] > 0) & df_comp["net_salary"].notna()
    net_salary_mismatches = int((valid_sal_mask & ((df_comp["net_salary"] - expected_net).abs() > 100.0)).sum())

    # Salary > expected range (join valid deduplicated emp designation & employment type)
    emp_desig_map = (
        df_emp.loc[_is_valid_emp_id(df_emp["employee_id"]), ["employee_id", "designation", "employment_type"]]
        .drop_duplicates(subset=["employee_id"])
    )
    comp_with_desig = df_comp.merge(emp_desig_map, on="employee_id", how="left")
    is_intern = comp_with_desig["employment_type"].astype("string").str.lower().str.contains("intern", na=False)
    band_min = comp_with_desig["designation"].map(
        lambda d: DESIGNATION_SALARY_BANDS_INR.get(str(d), (200_000.0, 20_000_000.0))[0] * SALARY_ANOMALY_LOWER_MULTIPLIER
    )
    band_max = comp_with_desig["designation"].map(
        lambda d: DESIGNATION_SALARY_BANDS_INR.get(str(d), (200_000.0, 20_000_000.0))[1] * SALARY_ANOMALY_UPPER_MULTIPLIER
    )
    band_min = np.where(is_intern, 150_000.0, band_min)
    band_max = np.where(is_intern, 650_000.0, band_max)
    salary_anomaly_mask = (
        comp_with_desig["basic_salary"].notna()
        & (comp_with_desig["basic_salary"] > 0)
        & ((comp_with_desig["basic_salary"] < band_min) | (comp_with_desig["basic_salary"] > band_max))
    )
    salary_anomalies = int(salary_anomaly_mask.sum())

    # 4. Date Validity Checks
    as_of_ts = pd.Timestamp(AS_OF_DATE)

    emp_join_dt = _parse_iso_dates(df_emp["joining_date"])
    emp_dob_dt = _parse_iso_dates(df_emp["date_of_birth"])
    comp_inc_dt = _parse_iso_dates(df_comp["increment_date"])
    career_promo_dt = _parse_iso_dates(df_career["last_promotion_date"])
    exit_dt = _parse_iso_dates(df_exit["exit_date"])

    invalid_joining_dates = int((emp_join_dt.isna() | (emp_join_dt > as_of_ts)).sum())
    invalid_dob_dates = int((emp_dob_dt.isna() | (emp_dob_dt > as_of_ts)).sum())
    invalid_inc_dates = int((df_comp["increment_date"].notna() & (comp_inc_dt.isna() | (comp_inc_dt > as_of_ts))).sum())
    invalid_promo_dates = int((df_career["last_promotion_date"].notna() & (career_promo_dt.isna() | (career_promo_dt > as_of_ts))).sum())
    invalid_exit_dates = int((df_exit["exit_date"].notna() & (exit_dt.isna() | (exit_dt > as_of_ts))).sum())
    total_invalid_dates = invalid_joining_dates + invalid_dob_dates + invalid_inc_dates + invalid_promo_dates + invalid_exit_dates

    # 5. Impossible Tenure & Temporal Integrity Checks
    age_at_joining = (emp_join_dt - emp_dob_dt).dt.days / 365.25
    underage_or_before_dob = int((emp_join_dt.notna() & emp_dob_dt.notna() & (age_at_joining < 16.0)).sum())

    emp_clean_dates = (
        df_emp.assign(join_dt=emp_join_dt)
        .loc[_is_valid_emp_id(df_emp["employee_id"]) & emp_join_dt.notna(), ["employee_id", "join_dt"]]
        .drop_duplicates(subset=["employee_id"])
    )

    career_merged = df_career.assign(promo_dt=career_promo_dt).merge(emp_clean_dates, on="employee_id", how="inner")
    promo_before_join = int(
        (career_merged["promo_dt"].notna() & (career_merged["promo_dt"] < career_merged["join_dt"])).sum()
    )

    exit_merged = df_exit.assign(ex_dt=exit_dt).merge(emp_clean_dates, on="employee_id", how="inner")
    exit_before_join = int(
        (exit_merged["ex_dt"].notna() & (exit_merged["ex_dt"] < exit_merged["join_dt"])).sum()
    )

    impossible_tenure_total = underage_or_before_dob + promo_before_join + exit_before_join

    # 6. Standardization / Consistency Checks
    dept_inconsistencies = int((~df_emp["department"].isin(CANONICAL_DEPARTMENTS.keys())).sum())
    loc_inconsistencies = int((~df_emp["location"].isin(CANONICAL_LOCATIONS.keys())).sum())
    emp_type_inconsistencies = int((~df_emp["employment_type"].isin(["Full-Time", "Contract", "Intern"])).sum())

    # 7. Exit & Attrition Label Checks
    missing_attrition_labels = int(df_exit["attrition"].isna().sum())
    nonstandard_attrition_labels = int(
        (df_exit["attrition"].notna() & ~df_exit["attrition"].astype(str).isin(["Yes", "No"])).sum()
    )

    # 8. Attendance / Leave Checks
    neg_or_gt365_leave = int(((df_att["leave_days"] < 0) | (df_att["leave_days"] > 365)).sum())
    neg_overtime = int((df_att["overtime_hours"] < 0).sum())
    comp_sum_mismatch = int(
        (
            (df_att["leave_days"] >= 0)
            & (df_att["leave_days"] <= 365)
            & ((df_att["sick_leave"] + df_att["casual_leave"] + df_att["unpaid_leave"] - df_att["leave_days"]).abs() > 0.01)
        ).sum()
    )
    leave_anomalies_total = neg_or_gt365_leave + neg_overtime + comp_sum_mismatch

    # 9. Compute Quality Dimension Scores (0 - 100%)
    total_raw_rows = sum(len(df) for df in tables.values())
    emp_rows = len(df_emp)
    comp_rows = len(df_comp)
    att_rows = len(df_att)
    exit_rows = len(df_exit)

    completeness_defects = sum(missing_id_by_table.values()) + missing_basic_salary + missing_attrition_labels
    uniqueness_defects = total_duplicates
    validity_defects = (
        sum(invalid_id_by_table.values())
        + non_positive_salary
        + negative_deductions
        + salary_anomalies
        + total_invalid_dates
        + leave_anomalies_total
    )
    consistency_defects = dept_inconsistencies + loc_inconsistencies + emp_type_inconsistencies + nonstandard_attrition_labels + net_salary_mismatches
    integrity_defects = impossible_tenure_total

    completeness_score = round(max(0.0, 100.0 * (1.0 - completeness_defects / max(1, total_raw_rows))), 2)
    uniqueness_score = round(max(0.0, 100.0 * (1.0 - uniqueness_defects / max(1, total_raw_rows))), 2)
    validity_score = round(max(0.0, 100.0 * (1.0 - validity_defects / max(1, total_raw_rows))), 2)
    consistency_score = round(max(0.0, 100.0 * (1.0 - consistency_defects / max(1, emp_rows + comp_rows + exit_rows))), 2)
    integrity_score = round(max(0.0, 100.0 * (1.0 - integrity_defects / max(1, emp_rows + exit_rows))), 2)

    overall_dq_score = round(
        0.22 * completeness_score
        + 0.20 * uniqueness_score
        + 0.25 * validity_score
        + 0.15 * consistency_score
        + 0.18 * integrity_score,
        2,
    )

    report: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of_date": AS_OF_DATE.isoformat(),
        "table_row_counts": {name: int(len(df)) for name, df in tables.items()},
        "total_raw_records_all_tables": int(total_raw_rows),
        "headline_summary": {
            "total_employee_records": int(emp_rows),
            "unique_valid_employees": int(emp_valid_ids.nunique()),
            "duplicate_employee_records": dup_emp_ids,
            "duplicate_payroll_records": dup_payroll_records,
            "missing_employee_ids": int(sum(missing_id_by_table.values())),
            "invalid_employee_ids": int(sum(invalid_id_by_table.values())),
            "missing_or_invalid_salaries": invalid_salaries_total,
            "negative_deductions": negative_deductions,
            "net_salary_mismatches": net_salary_mismatches,
            "salary_anomalies": salary_anomalies,
            "invalid_dates": total_invalid_dates,
            "impossible_tenure_records": impossible_tenure_total,
            "department_inconsistencies": dept_inconsistencies,
            "location_inconsistencies": loc_inconsistencies,
            "employment_type_inconsistencies": emp_type_inconsistencies,
            "missing_attrition_labels": missing_attrition_labels,
            "nonstandard_attrition_labels": nonstandard_attrition_labels,
            "leave_and_overtime_anomalies": leave_anomalies_total,
        },
        "detailed_breakdown": {
            "missing_employee_id_by_table": missing_id_by_table,
            "invalid_employee_id_by_table": invalid_id_by_table,
            "duplicates_by_table": {
                "employees": dup_emp_ids,
                "compensation": dup_payroll_records,
                "attendance_leave": dup_att_records,
                "career": career_dup,
                "exit": exit_dup,
            },
            "salary_breakdown": {
                "missing_basic_salary": missing_basic_salary,
                "non_positive_basic_salary": non_positive_salary,
                "negative_deductions": negative_deductions,
                "net_salary_mismatches": net_salary_mismatches,
                "salary_outside_expected_band": salary_anomalies,
            },
            "date_breakdown": {
                "invalid_joining_dates": invalid_joining_dates,
                "invalid_dob_dates": invalid_dob_dates,
                "invalid_increment_dates": invalid_inc_dates,
                "invalid_promotion_dates": invalid_promo_dates,
                "invalid_exit_dates": invalid_exit_dates,
            },
            "temporal_integrity_breakdown": {
                "underage_or_joined_before_dob": underage_or_before_dob,
                "promotion_before_joining": promo_before_join,
                "exit_before_joining": exit_before_join,
            },
            "attendance_breakdown": {
                "leave_negative_or_over_365": neg_or_gt365_leave,
                "negative_overtime_hours": neg_overtime,
                "leave_component_sum_mismatch": comp_sum_mismatch,
            },
        },
        "quality_scores_pct": {
            "completeness": completeness_score,
            "uniqueness": uniqueness_score,
            "validity": validity_score,
            "consistency": consistency_score,
            "integrity": integrity_score,
            "overall_data_quality_score": overall_dq_score,
        },
        "sample_messy_departments": sorted(
            [str(v) for v in df_emp.loc[~df_emp["department"].isin(CANONICAL_DEPARTMENTS.keys()), "department"].dropna().unique()]
        ),
        "sample_messy_locations": sorted(
            [str(v) for v in df_emp.loc[~df_emp["location"].isin(CANONICAL_LOCATIONS.keys()), "location"].dropna().unique()]
        ),
    }

    # Save JSON
    json_path = rep_dir / "data_quality_report.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Save Markdown report
    hs = report["headline_summary"]
    qs = report["quality_scores_pct"]
    md_lines = [
        "# Workforce & Compensation Data Quality Assessment Report",
        "",
        f"**Generated (UTC):** `{report['generated_at_utc']}` | **Reference As-Of Date:** `{report['as_of_date']}`",
        "",
        f"## Overall Data Quality Score: **{qs['overall_data_quality_score']:.2f}%**",
        "",
        "### Quality Dimension Scores",
        "",
        "| Dimension | Score (%) | Description |",
        "|---|---:|---|",
        f"| Completeness | {qs['completeness']:.2f}% | Presence of required IDs, salaries, and attrition labels |",
        f"| Uniqueness | {qs['uniqueness']:.2f}% | Absence of duplicate employee, payroll, and attendance keys |",
        f"| Validity | {qs['validity']:.2f}% | Conformance to ID regex, positive money/dates, and expected salary bands |",
        f"| Consistency | {qs['consistency']:.2f}% | Canonical departments, locations, labels, and net-pay reconciliation |",
        f"| Temporal Integrity | {qs['integrity']:.2f}% | Valid age at hire, promotions & exits occurring after joining date |",
        "",
        "### Executive Defect Summary",
        "",
        "```text",
        f"Total Employee Rows (Raw)    : {hs['total_employee_records']:,}",
        f"Unique Valid Employee IDs    : {hs['unique_valid_employees']:,}",
        f"Total Records (All 5 Tables) : {report['total_raw_records_all_tables']:,}",
        f"Duplicate Employee Records   : {hs['duplicate_employee_records']:,}",
        f"Duplicate Payroll Records    : {hs['duplicate_payroll_records']:,}",
        f"Missing Employee IDs         : {hs['missing_employee_ids']:,}",
        f"Invalid Employee IDs         : {hs['invalid_employee_ids']:,}",
        f"Missing / Invalid Salaries   : {hs['missing_or_invalid_salaries']:,}",
        f"Negative Deductions          : {hs['negative_deductions']:,}",
        f"Net Salary Mismatches        : {hs['net_salary_mismatches']:,}",
        f"Salary Anomalies (Out-of-Band): {hs['salary_anomalies']:,}",
        f"Invalid Dates                : {hs['invalid_dates']:,}",
        f"Impossible Tenure / Dates    : {hs['impossible_tenure_records']:,}",
        f"Department Inconsistencies   : {hs['department_inconsistencies']:,}",
        f"Location Inconsistencies     : {hs['location_inconsistencies']:,}",
        f"Missing Attrition Labels     : {hs['missing_attrition_labels']:,}",
        f"Leave & Overtime Anomalies   : {hs['leave_and_overtime_anomalies']:,}",
        "```",
        "",
        "### Raw Table Volumes",
        "",
        "| Table | Raw Row Count |",
        "|---|---:|",
    ]
    for t_name, cnt in report["table_row_counts"].items():
        md_lines.append(f"| `{t_name}.csv` | {cnt:,} |")

    md_lines.extend(
        [
            "",
            "### Detected Non-Canonical Categories (Standardized in ETL)",
            f"- **Departments:** {', '.join(f'`{d}`' for d in report['sample_messy_departments']) or 'None'}",
            f"- **Locations:** {', '.join(f'`{l}`' for l in report['sample_messy_locations']) or 'None'}",
            "",
        ]
    )

    md_path = rep_dir / "data_quality_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return report


if __name__ == "__main__":
    res = assess_data_quality()
    print("Overall Data Quality Score:", res["quality_scores_pct"]["overall_data_quality_score"], "%")
    for k, v in res["headline_summary"].items():
        print(f"  {k}: {v:,}")

