"""Realistic Enterprise HR & Payroll Dataset Generator (25,000+ records).

Generates 5 normalized raw CSV tables matching enterprise HRIS/Payroll exports,
complete with realistic compensation tiers, career progression, probabilistic
attrition drivers, and controlled data-quality defects for DQ testing & ETL.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config.settings import (
    AS_OF_DATE,
    CANONICAL_LOCATIONS,
    DESIGNATION_SALARY_BANDS_INR,
    LEAVE_YEARS,
    NUM_EMPLOYEES,
    PATHS,
    RANDOM_SEED,
    ensure_directories,
)

DEPARTMENT_WEIGHTS: dict[str, float] = {
    "Engineering": 0.28,
    "Operations": 0.22,
    "Sales": 0.16,
    "Data & Analytics": 0.09,
    "Customer Success": 0.09,
    "Product": 0.06,
    "Finance": 0.06,
    "Human Resources": 0.04,
}

DEPARTMENT_DESIGNATIONS: dict[str, tuple[list[str], list[float]]] = {
    "Engineering": (
        ["Software Engineer", "Senior Engineer", "Team Lead", "Manager", "Senior Manager", "Principal", "Director", "VP"],
        [0.34, 0.30, 0.14, 0.09, 0.05, 0.05, 0.022, 0.008],
    ),
    "Data & Analytics": (
        ["Analyst", "Senior Analyst", "Software Engineer", "Senior Engineer", "Team Lead", "Manager", "Senior Manager", "Principal", "Director", "VP"],
        [0.18, 0.22, 0.15, 0.18, 0.10, 0.08, 0.04, 0.03, 0.015, 0.005],
    ),
    "Operations": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Director", "VP"],
        [0.38, 0.25, 0.16, 0.11, 0.06, 0.03, 0.01],
    ),
    "Sales": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Director", "VP"],
        [0.28, 0.27, 0.17, 0.14, 0.08, 0.045, 0.015],
    ),
    "Product": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Principal", "Director", "VP"],
        [0.12, 0.18, 0.16, 0.24, 0.14, 0.09, 0.055, 0.015],
    ),
    "Customer Success": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Director"],
        [0.36, 0.28, 0.17, 0.11, 0.055, 0.025],
    ),
    "Finance": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Director", "VP"],
        [0.26, 0.28, 0.16, 0.15, 0.09, 0.045, 0.015],
    ),
    "Human Resources": (
        ["Analyst", "Senior Analyst", "Team Lead", "Manager", "Senior Manager", "Director", "VP"],
        [0.28, 0.26, 0.15, 0.16, 0.09, 0.045, 0.015],
    ),
}

DEPT_SALARY_MULT: dict[str, float] = {
    "Engineering": 1.15,
    "Data & Analytics": 1.12,
    "Product": 1.12,
    "Sales": 1.02,
    "Finance": 0.98,
    "Human Resources": 0.90,
    "Customer Success": 0.86,
    "Operations": 0.83,
}

LOC_SALARY_MULT: dict[str, float] = {
    "Bengaluru": 1.07,
    "Mumbai": 1.06,
    "Gurugram": 1.03,
    "Hyderabad": 1.01,
    "Pune": 0.97,
    "Chennai": 0.95,
    "Noida": 0.92,
}

DESIGNATION_MIN_AGE: dict[str, int] = {
    "Analyst": 21,
    "Software Engineer": 21,
    "Senior Analyst": 24,
    "Senior Engineer": 25,
    "Team Lead": 26,
    "Manager": 28,
    "Senior Manager": 32,
    "Principal": 31,
    "Director": 35,
    "VP": 39,
}

EDUCATION_CHOICES = ["B.Tech", "B.Sc", "B.Com", "MBA", "M.Tech", "M.Sc", "Diploma", "PhD"]
EDUCATION_PROBS = [0.36, 0.14, 0.11, 0.17, 0.11, 0.05, 0.04, 0.02]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20.0, 20.0)))


def _add_days(base_dates: np.ndarray, days: np.ndarray) -> list[str]:
    return [(d + timedelta(days=int(delta))).isoformat() for d, delta in zip(base_dates, days)]


def generate_raw_datasets(
    num_employees: int = NUM_EMPLOYEES,
    seed: int = RANDOM_SEED,
    as_of_date: date = AS_OF_DATE,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Generate raw HR/Payroll CSV files and return generation summary stats."""
    ensure_directories()
    out_dir = output_dir or PATHS.data_raw
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    # 1. Core Employee Identifiers & Attributes
    emp_ids = np.array([f"EMP{i:05d}" for i in range(1, num_employees + 1)], dtype=object)

    dept_names = list(DEPARTMENT_WEIGHTS.keys())
    dept_probs = list(DEPARTMENT_WEIGHTS.values())
    departments = rng.choice(dept_names, size=num_employees, p=dept_probs)

    locations_list = list(CANONICAL_LOCATIONS.keys())
    loc_probs = [0.29, 0.18, 0.14, 0.13, 0.12, 0.08, 0.06]
    locations = rng.choice(locations_list, size=num_employees, p=loc_probs)

    designations = np.empty(num_employees, dtype=object)
    for dept in dept_names:
        mask = departments == dept
        choices, probs = DEPARTMENT_DESIGNATIONS[dept]
        designations[mask] = rng.choice(choices, size=int(mask.sum()), p=probs)

    employment_types = rng.choice(
        ["Full-Time", "Contract", "Intern"],
        size=num_employees,
        p=[0.885, 0.085, 0.030],
    )
    # Interns hold junior titles
    intern_mask = employment_types == "Intern"
    designations[intern_mask] = np.where(
        np.isin(departments[intern_mask], ["Engineering", "Data & Analytics"]),
        "Software Engineer",
        "Analyst",
    )

    educations = rng.choice(EDUCATION_CHOICES, size=num_employees, p=EDUCATION_PROBS)
    # Masters / MBA more common at senior levels
    senior_mask = np.isin(designations, ["Manager", "Senior Manager", "Principal", "Director", "VP"])
    educations[senior_mask] = rng.choice(
        ["B.Tech", "MBA", "M.Tech", "M.Sc", "PhD", "B.Com"],
        size=int(senior_mask.sum()),
        p=[0.24, 0.42, 0.18, 0.06, 0.05, 0.05],
    )

    # Age and Date of Birth realistic for designation
    min_ages = np.array([DESIGNATION_MIN_AGE[d] for d in designations], dtype=int)
    ages = np.clip(
        min_ages + rng.integers(0, 18, size=num_employees),
        21,
        61,
    )
    ages[intern_mask] = rng.integers(20, 24, size=int(intern_mask.sum()))

    dob_dates = np.array(
        [
            as_of_date - timedelta(days=int(age * 365.25 + rng.integers(0, 360)))
            for age in ages
        ],
        dtype=object,
    )

    # Tenure / Joining Date (between 2012-01-01 and 2026-07-15, always >= age 19 at joining)
    max_possible_tenure_days = np.maximum(
        90,
        np.array([(as_of_date - (dob + timedelta(days=int(19.5 * 365.25)))).days for dob in dob_dates]),
    )
    company_cap_days = (as_of_date - date(2012, 1, 1)).days
    tenure_raw_days = np.minimum(
        max_possible_tenure_days,
        np.minimum(company_cap_days, rng.gamma(shape=2.1, scale=540.0, size=num_employees).astype(int) + 60),
    )
    tenure_raw_days[intern_mask] = rng.integers(30, 270, size=int(intern_mask.sum()))

    joining_dates = np.array(
        [as_of_date - timedelta(days=int(d)) for d in tenure_raw_days],
        dtype=object,
    )
    tenure_years_clean = tenure_raw_days / 365.25

    # Experience years = tenure + prior experience, capped realistically by (age - 20)
    prior_exp = np.clip(
        (ages - 21 - tenure_years_clean) * rng.uniform(0.35, 0.90, size=num_employees),
        0.0,
        25.0,
    )
    prior_exp[intern_mask] = 0.0
    experience_years = np.round(np.minimum(ages - 20.0, tenure_years_clean + prior_exp), 1)

    performance_rating = rng.choice([1, 2, 3, 4, 5], size=num_employees, p=[0.05, 0.13, 0.47, 0.26, 0.09])

    # 2. Career & Promotion History (needed before exit simulation)
    # Expected promotions scale with tenure and performance
    promo_rate = np.clip((tenure_years_clean / 2.9) * (0.65 + 0.15 * performance_rating), 0.0, 5.5)
    promotion_count = np.minimum(
        np.floor(tenure_years_clean / 1.1).astype(int),
        rng.poisson(lam=np.maximum(0.05, promo_rate)),
    )
    promotion_count[intern_mask] = 0

    last_promotion_dates = np.empty(num_employees, dtype=object)
    for idx in range(num_employees):
        if promotion_count[idx] <= 0 or tenure_raw_days[idx] < 365:
            last_promotion_dates[idx] = None
        else:
            # Some employees intentionally suffer long promotion gaps (>2.5 yrs)
            min_promo_offset = 240
            max_promo_offset = max(min_promo_offset + 30, int(tenure_raw_days[idx]) - 30)
            days_since_promo = int(rng.integers(30, max_promo_offset))
            last_promotion_dates[idx] = as_of_date - timedelta(days=days_since_promo)

    training_hours = np.round(
        np.clip(
            rng.normal(loc=26.0 + 4.5 * performance_rating, scale=12.0, size=num_employees),
            2.0,
            110.0,
        ),
        1,
    )
    manager_rating = np.clip(
        performance_rating + rng.choice([-1, 0, 1], size=num_employees, p=[0.14, 0.72, 0.14]),
        1,
        5,
    )

    # 3. Compensation Structure (Annual INR)
    basic_salary = np.zeros(num_employees, dtype=float)
    for desig, (low, high) in DESIGNATION_SALARY_BANDS_INR.items():
        mask = designations == desig
        if not mask.any():
            continue
        # Position within band correlated with experience & performance
        exp_norm = np.clip(experience_years[mask] / 20.0, 0.0, 1.0)
        perf_norm = (performance_rating[mask] - 1) / 4.0
        band_pos = np.clip(0.18 + 0.48 * exp_norm + 0.18 * perf_norm + rng.normal(0, 0.12, mask.sum()), 0.02, 0.98)
        raw_basic = low + band_pos * (high - low)
        dept_m = np.array([DEPT_SALARY_MULT[d] for d in departments[mask]])
        loc_m = np.array([LOC_SALARY_MULT[l] for l in locations[mask]])
        basic_salary[mask] = raw_basic * dept_m * loc_m

    # Interns and contractors adjustment
    basic_salary[intern_mask] = rng.uniform(240_000.0, 420_000.0, size=int(intern_mask.sum()))
    contract_mask = employment_types == "Contract"
    basic_salary[contract_mask] *= rng.uniform(0.92, 1.08, size=int(contract_mask.sum()))
    basic_salary = np.round(basic_salary, -2)

    allowances = np.round(basic_salary * rng.uniform(0.28, 0.40, size=num_employees), -2)
    allowances[intern_mask] = np.round(basic_salary[intern_mask] * 0.15, -2)

    # Bonus scales with performance + Sales variable comp
    sales_bonus_boost = np.where(departments == "Sales", 0.09, 0.0)
    exec_bonus_boost = np.where(np.isin(designations, ["Director", "VP", "Senior Manager"]), 0.06, 0.0)
    bonus_pct = np.clip(
        0.02 + 0.038 * (performance_rating - 1) + sales_bonus_boost + exec_bonus_boost + rng.normal(0, 0.025, num_employees),
        0.0,
        0.38,
    )
    bonus = np.round(basic_salary * bonus_pct, -2)
    bonus[intern_mask] = 0.0

    gross_total = basic_salary + allowances + bonus
    # Realistic Indian tax + PF + insurance deductions (progressive effective rate 8% to 27%)
    eff_ded_rate = np.clip(0.08 + (gross_total / 12_000_000.0) * 0.16 + rng.uniform(-0.015, 0.015, num_employees), 0.05, 0.30)
    deductions = np.round(gross_total * eff_ded_rate, -2)
    net_salary = np.round(gross_total - deductions, -2)

    # Salary increment (annual INR raise amount)
    # Engineering & Operations get slightly tighter raise pools in some segments -> creates attrition pocket
    dept_raise_bias = np.where(np.isin(departments, ["Engineering", "Operations"]), -0.018, 0.005)
    increment_rate = np.clip(
        0.03 + 0.024 * (performance_rating - 1) + dept_raise_bias + rng.normal(0, 0.022, num_employees),
        0.005,
        0.22,
    )
    increment_rate[intern_mask] = 0.0
    # Employees with < 10 months tenure might have 0 or small pro-rated increment
    new_joiner_mask = tenure_years_clean < 0.75
    increment_rate[new_joiner_mask] = np.where(rng.random(int(new_joiner_mask.sum())) < 0.7, 0.0, 0.03)

    prior_base_plus_allow = (basic_salary + allowances) / (1.0 + increment_rate)
    salary_increment = np.round((basic_salary + allowances) - prior_base_plus_allow, -2)

    # Increment dates mostly April 2026 / April 2025
    increment_dates = np.empty(num_employees, dtype=object)
    for idx in range(num_employees):
        j_date = joining_dates[idx]
        if salary_increment[idx] <= 0:
            increment_dates[idx] = j_date
        else:
            candidate = date(2026, 4, 1) if rng.random() < 0.78 else date(2025, 4, 1)
            if candidate <= j_date:
                candidate = min(as_of_date, j_date + timedelta(days=180))
            increment_dates[idx] = candidate

    # 4. Attendance & Leave (2024, 2025, 2026) — build preliminary annual overtime/leave profile first
    # Operations and Engineering carry higher overtime pressure
    base_ot = np.where(
        departments == "Operations",
        rng.gamma(shape=3.2, scale=68.0, size=num_employees),
        np.where(
            departments == "Engineering",
            rng.gamma(shape=2.5, scale=55.0, size=num_employees),
            rng.gamma(shape=1.6, scale=35.0, size=num_employees),
        ),
    )
    emp_overtime_2025 = np.round(np.clip(base_ot, 0.0, 520.0), 1)
    emp_sick_2025 = rng.poisson(lam=np.where(emp_overtime_2025 > 240, 6.2, 3.6))
    emp_casual_2025 = rng.poisson(lam=9.5, size=num_employees)
    emp_unpaid_2025 = rng.poisson(lam=np.where(performance_rating <= 2, 2.4, 0.6))
    emp_leave_2025 = emp_sick_2025 + emp_casual_2025 + emp_unpaid_2025

    # 5. Probabilistic Attrition Model (produces ~12.8% realistic enterprise attrition)
    promo_gap_years = np.array(
        [
            (as_of_date - (lpd if lpd is not None else jd)).days / 365.25
            for lpd, jd in zip(last_promotion_dates, joining_dates)
        ]
    )
    sal_growth_pct_est = (salary_increment / np.maximum(1.0, (basic_salary + allowances) - salary_increment)) * 100.0

    # Department baseline effects (Engineering & Operations higher)
    dept_logodds = np.array(
        [
            {
                "Engineering": 0.74,
                "Operations": 0.42,
                "Sales": 0.34,
                "Customer Success": 0.20,
                "Product": 0.02,
                "Data & Analytics": 0.12,
                "Finance": -0.35,
                "Human Resources": -0.32,
            }[d]
            for d in departments
        ]
    )

    # Avoid artificially penalizing <1 yr new hires for not yet completing an annual raise cycle
    effective_sal_growth = np.where(new_joiner_mask, 8.0, sal_growth_pct_est)

    logit = (
        -3.20
        + dept_logodds
        + 0.62 * np.maximum(0.0, promo_gap_years - 2.0)           # Long promotion gap
        + 0.16 * np.maximum(0.0, 8.0 - effective_sal_growth)      # Low salary growth
        + 0.0052 * np.maximum(0.0, emp_overtime_2025 - 140.0)     # High overtime burnout
        + 0.045 * np.maximum(0.0, emp_leave_2025 - 16.0)          # High leave / disengagement
        + 0.35 * (performance_rating <= 2).astype(float)          # Low performance
        + 0.45 * (manager_rating <= 2).astype(float)              # Poor manager alignment
        - 0.10 * np.maximum(0.0, tenure_years_clean - 5.0)        # Long tenure lowers risk slightly
        + 0.25 * ((tenure_years_clean >= 1.5) & (tenure_years_clean <= 4.0)).astype(float)
        - 0.010 * training_hours                                  # Training investment retains talent
        + rng.normal(0.0, 0.35, size=num_employees)
    )
    # Interns and <9 month new joiners show lower baseline voluntary exit in this cycle
    logit[intern_mask] -= 0.9
    logit[new_joiner_mask] -= 0.55

    attrition_prob = _sigmoid(logit)
    attrition_flag = (rng.random(num_employees) < attrition_prob).astype(int)

    exit_dates = np.empty(num_employees, dtype=object)
    exit_reasons = np.empty(num_employees, dtype=object)

    for idx in range(num_employees):
        if attrition_flag[idx] == 0:
            exit_dates[idx] = None
            exit_reasons[idx] = None
            continue

        # Exit happens in recent window (preserving accumulated promotion gap / tenure signal)
        base_earliest = joining_dates[idx] + timedelta(days=max(45, int(0.65 * tenure_raw_days[idx])))
        if last_promotion_dates[idx] is not None:
            base_earliest = max(base_earliest, last_promotion_dates[idx] + timedelta(days=90))
        earliest_exit = max(date(2023, 1, 1), base_earliest)
        if earliest_exit >= as_of_date - timedelta(days=2):
            earliest_exit = max(joining_dates[idx] + timedelta(days=30), as_of_date - timedelta(days=180))
        span_days = max(5, (as_of_date - earliest_exit).days)
        frac = float(np.clip(rng.beta(1.6, 1.3), 0.0, 1.0))
        ex_date = earliest_exit + timedelta(days=int(frac * span_days))
        exit_dates[idx] = min(ex_date, as_of_date - timedelta(days=1))

        # Choose exit reason aligned with individual's strongest risk factors
        reason_weights = {
            "Compensation": 1.2 + max(0.0, 8.0 - sal_growth_pct_est[idx]) * 0.45,
            "Career Growth": 1.2 + max(0.0, promo_gap_years[idx] - 1.8) * 0.85,
            "Work-Life Balance": 1.0 + max(0.0, emp_overtime_2025[idx] - 120.0) * 0.018,
            "Manager / Culture": 0.9 + (1.8 if manager_rating[idx] <= 2 else 0.0),
            "Performance / Involuntary": 0.3 + (2.4 if performance_rating[idx] == 1 else 0.7 if performance_rating[idx] == 2 else 0.0),
            "Relocation": 0.65,
            "Higher Studies": 0.75 if ages[idx] <= 28 else 0.15,
        }
        reasons = list(reason_weights.keys())
        w = np.array(list(reason_weights.values()), dtype=float)
        w = w / w.sum()
        exit_reasons[idx] = rng.choice(reasons, p=w)

    # Re-align last_promotion_date & increment_date for exited employees so clean rows never exceed exit_date
    for idx in range(num_employees):
        if attrition_flag[idx] == 1:
            ex_d = exit_dates[idx]
            if last_promotion_dates[idx] is not None and last_promotion_dates[idx] >= ex_d:
                if (ex_d - joining_dates[idx]).days > 240:
                    last_promotion_dates[idx] = joining_dates[idx] + timedelta(days=int((ex_d - joining_dates[idx]).days * 0.5))
                else:
                    last_promotion_dates[idx] = None
                    promotion_count[idx] = 0
            if increment_dates[idx] > ex_d:
                increment_dates[idx] = max(joining_dates[idx], ex_d - timedelta(days=30))

    # Build multi-year Attendance / Leave rows for 2024, 2025, 2026
    att_rows: list[dict[str, Any]] = []
    for idx in range(num_employees):
        j_year = joining_dates[idx].year
        ex_year = exit_dates[idx].year if exit_dates[idx] is not None else 9999
        for yr in LEAVE_YEARS:
            if j_year <= yr <= ex_year:
                yr_scale = 0.75 if yr == 2026 else 1.0  # 2026 is YTD through Sep 30
                sick = int(max(0, round(emp_sick_2025[idx] * yr_scale + rng.integers(-1, 2))))
                casual = int(max(0, round(emp_casual_2025[idx] * yr_scale + rng.integers(-2, 3))))
                unpaid = int(max(0, round(emp_unpaid_2025[idx] * yr_scale + (1 if rng.random() < 0.12 else 0))))
                total_leave = sick + casual + unpaid
                ot = round(float(max(0.0, emp_overtime_2025[idx] * yr_scale + rng.normal(0, 14))), 1)
                att_rows.append(
                    {
                        "employee_id": emp_ids[idx],
                        "year": yr,
                        "leave_days": total_leave,
                        "sick_leave": sick,
                        "casual_leave": casual,
                        "unpaid_leave": unpaid,
                        "overtime_hours": ot,
                    }
                )

    # Assemble Clean DataFrames (as object/flexible dtypes before intentional DQ injection)
    df_emp = pd.DataFrame(
        {
            "employee_id": emp_ids,
            "department": departments.astype(object),
            "designation": designations.astype(object),
            "location": locations.astype(object),
            "joining_date": pd.Series([d.isoformat() for d in joining_dates], dtype=object),
            "date_of_birth": pd.Series([d.isoformat() for d in dob_dates], dtype=object),
            "employment_type": employment_types.astype(object),
            "education": educations.astype(object),
            "experience_years": experience_years.astype(float),
            "performance_rating": performance_rating.astype(float),
        }
    )

    df_comp = pd.DataFrame(
        {
            "employee_id": emp_ids,
            "basic_salary": basic_salary.astype(float),
            "allowances": allowances.astype(float),
            "bonus": bonus.astype(float),
            "deductions": deductions.astype(float),
            "net_salary": net_salary.astype(float),
            "salary_increment": salary_increment.astype(float),
            "increment_date": pd.Series([d.isoformat() for d in increment_dates], dtype=object),
        }
    )

    df_att = pd.DataFrame(att_rows)
    df_att["employee_id"] = df_att["employee_id"].astype(object)
    df_att["leave_days"] = df_att["leave_days"].astype(float)
    df_att["sick_leave"] = df_att["sick_leave"].astype(float)
    df_att["casual_leave"] = df_att["casual_leave"].astype(float)
    df_att["unpaid_leave"] = df_att["unpaid_leave"].astype(float)
    df_att["overtime_hours"] = df_att["overtime_hours"].astype(float)

    df_career = pd.DataFrame(
        {
            "employee_id": emp_ids,
            "promotion_count": promotion_count.astype(float),
            "last_promotion_date": pd.Series(
                [d.isoformat() if d is not None else None for d in last_promotion_dates], dtype=object
            ),
            "training_hours": training_hours.astype(float),
            "manager_rating": manager_rating.astype(float),
        }
    )

    df_exit = pd.DataFrame(
        {
            "employee_id": emp_ids,
            "attrition": pd.Series(np.where(attrition_flag == 1, "Yes", "No"), dtype=object),
            "exit_date": pd.Series([d.isoformat() if d is not None else None for d in exit_dates], dtype=object),
            "exit_reason": pd.Series(exit_reasons, dtype=object),
        }
    )

    # =========================================================================
    # 6. Controlled Intentional Data Quality Defect Injection
    # =========================================================================
    # Track disjoint indices per table so anomalies are clean & realistic
    all_idx = np.arange(num_employees)
    rng.shuffle(all_idx)

    # A. Employees table anomalies
    # Missing employee_id (6 rows)
    emp_missing_id_idx = all_idx[0:6]
    df_emp.loc[emp_missing_id_idx, "employee_id"] = None

    # Invalid employee_id formats (7 rows)
    emp_bad_id_idx = all_idx[6:13]
    bad_ids = ["INVALID_01", "12345", "EMP-BAD", "NULL_ID", "E99", "EMP_ERR", "X0001"]
    df_emp.loc[emp_bad_id_idx, "employee_id"] = bad_ids

    # Invalid date strings & future joining dates (18 rows)
    emp_bad_date_idx = all_idx[13:31]
    bad_date_vals = ["31/02/2023", "N/A", "2099-05-01", "invalid-date", "2028-11-15", "99/99/2020"]
    for pos, idx in enumerate(emp_bad_date_idx):
        if pos % 3 == 0:
            df_emp.loc[idx, "date_of_birth"] = bad_date_vals[pos % len(bad_date_vals)]
        else:
            df_emp.loc[idx, "joining_date"] = bad_date_vals[pos % len(bad_date_vals)]

    # Impossible tenure (underage joining < 16 yrs old at hire, 16 rows)
    emp_imp_tenure_idx = all_idx[31:47]
    for idx in emp_imp_tenure_idx:
        dob = date.fromisoformat(str(df_emp.loc[idx, "date_of_birth"]))
        df_emp.loc[idx, "joining_date"] = (dob + timedelta(days=365 * 11)).isoformat()

    # Department inconsistencies (420 rows)
    messy_dept_pool = {
        "Engineering": ["Engg", "engineering ", "ENG", "R&D Engineering"],
        "Operations": ["OPS", "ops ", "Operation"],
        "Sales": ["Sales & BD", "sales ", "Business Development"],
        "Data & Analytics": ["Data Science", "Analytics", "data & analytics "],
        "Human Resources": ["HR", "hr ", "People Ops"],
        "Finance": ["Fin", "finance ", "Finance & Accounts"],
        "Customer Success": ["CS", "Cust Success"],
        "Product": ["Product Mgmt", "product "],
    }
    dept_mess_idx = all_idx[100:520]
    for idx in dept_mess_idx:
        canon = str(df_emp.loc[idx, "department"])
        df_emp.loc[idx, "department"] = rng.choice(messy_dept_pool[canon])

    # Location inconsistencies (360 rows)
    messy_loc_pool = {
        "Bengaluru": ["Bangalore", "bengaluru ", "BLR"],
        "Hyderabad": ["hyd", "Hyderabad "],
        "Gurugram": ["Gurgaon", "gurugram "],
        "Mumbai": ["Bombay", "mumbai "],
        "Chennai": ["Madras", "chennai "],
        "Pune": ["pune "],
        "Noida": ["noida "],
    }
    loc_mess_idx = all_idx[520:880]
    for idx in loc_mess_idx:
        canon = str(df_emp.loc[idx, "location"])
        df_emp.loc[idx, "location"] = rng.choice(messy_loc_pool[canon])

    # Employment type casing inconsistencies (90 rows)
    emp_type_mess_idx = all_idx[880:970]
    for idx in emp_type_mess_idx:
        et = str(df_emp.loc[idx, "employment_type"])
        if et == "Full-Time":
            df_emp.loc[idx, "employment_type"] = rng.choice(["full time", "FT", "Permanent"])
        elif et == "Contract":
            df_emp.loc[idx, "employment_type"] = "contractor"

    # Duplicate employee records (137 rows) — pick clean rows beyond index 1000
    dup_emp_sample = df_emp.iloc[all_idx[1000:1137]].copy()
    df_emp = pd.concat([df_emp, dup_emp_sample], ignore_index=True)

    # B. Compensation table anomalies
    rng.shuffle(all_idx)
    # Missing / negative / zero basic_salary (42 rows)
    comp_missing_sal_idx = all_idx[0:22]
    df_comp.loc[comp_missing_sal_idx, "basic_salary"] = np.nan
    comp_neg_sal_idx = all_idx[22:42]
    df_comp.loc[comp_neg_sal_idx, "basic_salary"] = rng.choice([-450000.0, -120000.0, 0.0], size=20)

    # Negative deductions (24 rows)
    comp_neg_ded_idx = all_idx[42:66]
    df_comp.loc[comp_neg_ded_idx, "deductions"] = -rng.uniform(15_000.0, 95_000.0, size=24).round(2)

    # Salary anomalies > expected designation range (91 rows)
    comp_anom_idx = all_idx[66:157]
    for idx in comp_anom_idx:
        desig = str(designations[idx])
        _, high = DESIGNATION_SALARY_BANDS_INR[desig]
        anom_basic = round(float(high * rng.uniform(3.2, 9.5)), -2)
        df_comp.loc[idx, "basic_salary"] = anom_basic
        df_comp.loc[idx, "net_salary"] = round(
            anom_basic + float(df_comp.loc[idx, "allowances"]) + float(df_comp.loc[idx, "bonus"]) - float(df_comp.loc[idx, "deductions"]),
            -2,
        )

    # Net salary mismatch (38 rows)
    comp_mismatch_idx = all_idx[157:195]
    df_comp.loc[comp_mismatch_idx, "net_salary"] = df_comp.loc[comp_mismatch_idx, "net_salary"] + rng.uniform(85_000.0, 320_000.0, size=38).round(-2)

    # Missing employee_id in compensation (5 rows)
    df_comp.loc[all_idx[195:200], "employee_id"] = None

    # Duplicate payroll records (85 rows)
    dup_comp_sample = df_comp.iloc[all_idx[1000:1085]].copy()
    df_comp = pd.concat([df_comp, dup_comp_sample], ignore_index=True)

    # C. Career anomalies (promotion date before joining, missing IDs)
    rng.shuffle(all_idx)
    career_bad_promo_idx = all_idx[0:12]
    for idx in career_bad_promo_idx:
        jd = joining_dates[idx]
        df_career.loc[idx, "promotion_count"] = max(1.0, float(df_career.loc[idx, "promotion_count"]))
        df_career.loc[idx, "last_promotion_date"] = (jd - timedelta(days=300)).isoformat()

    # D. Exit anomalies (missing attrition labels, exit before join, inconsistent labels)
    rng.shuffle(all_idx)
    # Missing attrition labels (54 rows)
    df_exit.loc[all_idx[0:54], "attrition"] = None

    # Impossible exit date before joining (12 rows among exited)
    exited_indices = df_exit.index[df_exit["attrition"] == "Yes"].to_numpy()
    if len(exited_indices) >= 12:
        bad_ex_idx = exited_indices[:12]
        for idx in bad_ex_idx:
            df_exit.loc[idx, "exit_date"] = (joining_dates[idx] - timedelta(days=120)).isoformat()

    # Inconsistent boolean formats in attrition (120 rows)
    fmt_idx = all_idx[100:220]
    for idx in fmt_idx:
        val = df_exit.loc[idx, "attrition"]
        if val == "Yes":
            df_exit.loc[idx, "attrition"] = rng.choice(["Y", "1", "yes"])
        elif val == "No":
            df_exit.loc[idx, "attrition"] = rng.choice(["N", "0", "no"])

    # E. Attendance/Leave anomalies (32 rows: negative leave, >365 leave, component mismatch)
    att_idx = np.arange(len(df_att))
    rng.shuffle(att_idx)
    df_att.loc[att_idx[0:12], "leave_days"] = -rng.integers(2, 15, size=12).astype(float)
    df_att.loc[att_idx[12:22], "leave_days"] = rng.integers(380, 520, size=10).astype(float)
    df_att.loc[att_idx[22:32], "overtime_hours"] = -rng.uniform(10.0, 80.0, size=10).round(1)

    # Shuffle raw rows slightly (optional, preserves realistic export disorder)
    df_emp = df_emp.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    df_comp = df_comp.sample(frac=1.0, random_state=seed + 1).reset_index(drop=True)
    df_att = df_att.sample(frac=1.0, random_state=seed + 2).reset_index(drop=True)
    df_career = df_career.sample(frac=1.0, random_state=seed + 3).reset_index(drop=True)
    df_exit = df_exit.sample(frac=1.0, random_state=seed + 4).reset_index(drop=True)

    # Save raw CSV files
    df_emp.to_csv(out_dir / "employees.csv", index=False)
    df_comp.to_csv(out_dir / "compensation.csv", index=False)
    df_att.to_csv(out_dir / "attendance_leave.csv", index=False)
    df_career.to_csv(out_dir / "career.csv", index=False)
    df_exit.to_csv(out_dir / "exit.csv", index=False)

    return {
        "target_unique_employees": num_employees,
        "raw_rows": {
            "employees": len(df_emp),
            "compensation": len(df_comp),
            "attendance_leave": len(df_att),
            "career": len(df_career),
            "exit": len(df_exit),
        },
        "output_dir": str(out_dir),
    }


if __name__ == "__main__":
    summary = generate_raw_datasets()
    print("Generated Raw HR/Payroll Datasets:", summary)

