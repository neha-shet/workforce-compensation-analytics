"""Workforce Scenario Simulator Engine.

Simulates financial payroll impacts (INR & Crores) across active employees under
configurable HR levers:
1. Compensation budget increase (%)
2. Additional salary increment (%)
3. Overtime reduction (%)
4. Promotion rate expansion (%)
5. Targeted retention intervention coverage (%) for high-risk staff

Separates deterministic payroll expenditure math from optional, non-causal
ML risk-score sensitivity estimates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.ml.train_models import FEATURE_COLUMNS


@dataclass(frozen=True)
class ScenarioParams:
    department_filter: str = "All"
    budget_increase_pct: float = 0.0           # Overall compensation budget uplift (%)
    salary_increment_pct: float = 0.0          # Incremental base merit raise (%)
    overtime_reduction_pct: float = 0.0        # Reduction in excess overtime hours (%)
    promotion_rate_boost_pct: float = 0.0      # Share of promotion-stagnant staff (>2.5y) promoted (%)
    retention_intervention_pct: float = 0.0    # Coverage of high-risk active staff receiving retention package (%)
    retention_bonus_pct_of_basic: float = 8.0  # Fixed assumption: targeted retention grant as % of basic
    promotion_raise_pct: float = 12.0          # Fixed assumption: average pay lift per promotion (%)
    overtime_hourly_cost_factor: float = 1.25  # Fixed assumption: hourly OT rate multiplier on basic/2080


def simulate_workforce_scenario(
    active_df: pd.DataFrame,
    params: ScenarioParams,
    model_bundle: dict[str, Any] | None = None,
    include_ml_sensitivity: bool = False,
) -> dict[str, Any]:
    """Run deterministic financial simulation and optional non-causal ML sensitivity."""
    df = active_df.copy()
    if params.department_filter != "All":
        df = df[df["department_name"] == params.department_filter].copy()

    df = df.dropna(subset=["basic_salary", "total_compensation"]).copy()
    if df.empty:
        raise ValueError("No eligible active employees found for selected scenario filter.")

    # Baseline Payroll (Annual INR)
    baseline_payroll_inr = float(df["total_compensation"].sum())
    baseline_budget_inr = float(
        df.groupby("department_name")["annual_budget_inr"].first().sum()
    )

    # 1. Compensation Budget Increase (applies proportionally to total_compensation)
    budget_uplift_inr = df["total_compensation"] * (params.budget_increase_pct / 100.0)
    budget_affected = np.where(params.budget_increase_pct > 0, True, False)

    # 2. Additional Salary Increment (% applied to basic_salary + allowances)
    base_plus_allow = df["basic_salary"] + df["allowances"].fillna(0.0)
    non_intern = df["employment_type"] != "Intern"
    salary_inc_inr = np.where(
        non_intern,
        base_plus_allow * (params.salary_increment_pct / 100.0),
        0.0,
    )
    inc_affected = (params.salary_increment_pct > 0) & non_intern.to_numpy()

    # 3. Overtime Reduction (% reduction on annualized overtime hours above 80 hrs)
    ot_hours = df["annualized_overtime_hours"].fillna(0.0)
    hourly_rate = df["basic_salary"] / 2080.0
    reducible_ot = np.maximum(0.0, ot_hours - 80.0) * (params.overtime_reduction_pct / 100.0)
    ot_cost_savings_inr = reducible_ot * hourly_rate * params.overtime_hourly_cost_factor
    ot_affected = (params.overtime_reduction_pct > 0) & (ot_hours > 80.0).to_numpy()

    # 4. Promotion Rate Boost (% of stagnant eligible staff with promotion_gap >= 2.5 yrs promoted)
    promo_eligible = (non_intern & (df["promotion_gap"].fillna(0.0) >= 2.5)).to_numpy()
    n_promo_eligible = int(promo_eligible.sum())
    n_promoted = int(round(n_promo_eligible * (params.promotion_rate_boost_pct / 100.0)))
    promo_cost_inr = np.zeros(len(df), dtype=float)
    promo_affected = np.zeros(len(df), dtype=bool)
    if n_promoted > 0:
        eligible_idx = df.index[promo_eligible]
        # Prioritize highest performing stagnant employees deterministically
        ranked_elig = (
            df.loc[eligible_idx]
            .sort_values(by=["performance_rating", "promotion_gap"], ascending=[False, False])
            .index[:n_promoted]
        )
        promo_mask = df.index.isin(ranked_elig)
        promo_cost_inr = np.where(promo_mask, base_plus_allow * (params.promotion_raise_pct / 100.0), 0.0)
        promo_affected = promo_mask

    # 5. Targeted Retention Intervention (% coverage of High/Elevated-Risk active employees)
    risk_col = "attrition_probability" if "attrition_probability" in df.columns else None
    if risk_col is not None:
        high_risk_mask = (df[risk_col].fillna(0.0) >= 0.50).to_numpy()
    else:
        high_risk_mask = ((df["promotion_gap"].fillna(0.0) >= 2.5) | (df["annualized_overtime_hours"].fillna(0.0) >= 200)).to_numpy()

    n_high_risk = int(high_risk_mask.sum())
    n_ret_covered = int(round(n_high_risk * (params.retention_intervention_pct / 100.0)))
    retention_cost_inr = np.zeros(len(df), dtype=float)
    ret_affected = np.zeros(len(df), dtype=bool)
    if n_ret_covered > 0:
        hr_idx = df.index[high_risk_mask]
        if risk_col is not None:
            selected_ret = df.loc[hr_idx].sort_values(by=risk_col, ascending=False).index[:n_ret_covered]
        else:
            selected_ret = hr_idx[:n_ret_covered]
        ret_mask = df.index.isin(selected_ret)
        retention_cost_inr = np.where(ret_mask, df["basic_salary"] * (params.retention_bonus_pct_of_basic / 100.0), 0.0)
        ret_affected = ret_mask

    # Aggregate Financial Totals
    df["sim_budget_uplift_inr"] = budget_uplift_inr
    df["sim_salary_inc_inr"] = salary_inc_inr
    df["sim_promo_cost_inr"] = promo_cost_inr
    df["sim_retention_cost_inr"] = retention_cost_inr
    df["sim_ot_savings_inr"] = ot_cost_savings_inr
    df["sim_net_delta_inr"] = (
        df["sim_budget_uplift_inr"]
        + df["sim_salary_inc_inr"]
        + df["sim_promo_cost_inr"]
        + df["sim_retention_cost_inr"]
        - df["sim_ot_savings_inr"]
    )
    df["projected_total_compensation_inr"] = df["total_compensation"] + df["sim_net_delta_inr"]

    any_affected = budget_affected | inc_affected | ot_affected | promo_affected | ret_affected
    employees_affected = int(any_affected.sum())

    projected_payroll_inr = float(df["projected_total_compensation_inr"].sum())
    net_financial_impact_inr = projected_payroll_inr - baseline_payroll_inr
    net_impact_pct = (net_financial_impact_inr / max(1.0, baseline_payroll_inr)) * 100.0

    # Department breakdown
    dept_summary = (
        df.groupby("department_name", as_index=False)
        .agg(
            active_employees=("employee_id", "count"),
            baseline_payroll_cr=("total_compensation", lambda s: round(float(s.sum()) / 1e7, 2)),
            projected_payroll_cr=("projected_total_compensation_inr", lambda s: round(float(s.sum()) / 1e7, 2)),
            net_delta_cr=("sim_net_delta_inr", lambda s: round(float(s.sum()) / 1e7, 2)),
            annual_budget_cr=("annual_budget_inr", lambda s: round(float(s.iloc[0]) / 1e7, 2)),
        )
        .sort_values("net_delta_cr", ascending=False)
    )
    dept_summary["projected_budget_util_pct"] = np.round(
        100.0 * dept_summary["projected_payroll_cr"] / dept_summary["annual_budget_cr"].replace(0, np.nan),
        1,
    )

    assumptions = [
        f"Scope: {len(df):,} active compensated employees ({params.department_filter} department scope).",
        f"Budget uplift (+{params.budget_increase_pct:.1f}%) applies uniformly across active total compensation.",
        f"Additional salary increment (+{params.salary_increment_pct:.1f}%) applies to Full-Time and Contract base+allowances (excludes Interns).",
        f"Overtime reduction (-{params.overtime_reduction_pct:.1f}%) applies to annualized hours above 80 hrs/yr valued at {params.overtime_hourly_cost_factor:.2f}x hourly basic rate.",
        f"Promotion boost ({params.promotion_rate_boost_pct:.1f}% of {n_promo_eligible:,} stagnant eligible staff >=2.5y gap) adds {params.promotion_raise_pct:.1f}% average promotion pay lift for {n_promoted:,} top-rated eligible employees.",
        f"Retention intervention ({params.retention_intervention_pct:.1f}% of {n_high_risk:,} elevated-risk staff) provides a targeted {params.retention_bonus_pct_of_basic:.1f}% of basic pay grant for {n_ret_covered:,} employees.",
    ]

    result: dict[str, Any] = {
        "params": asdict(params),
        "active_headcount": int(len(df)),
        "employees_affected": employees_affected,
        "promoted_employees_count": n_promoted,
        "retention_covered_count": n_ret_covered,
        "baseline_payroll_cr": round(baseline_payroll_inr / 1e7, 2),
        "projected_payroll_cr": round(projected_payroll_inr / 1e7, 2),
        "net_financial_impact_cr": round(net_financial_impact_inr / 1e7, 2),
        "net_impact_pct": round(net_impact_pct, 2),
        "baseline_budget_cr": round(baseline_budget_inr / 1e7, 2),
        "projected_budget_utilization_pct": round(100.0 * projected_payroll_inr / max(1.0, baseline_budget_inr), 2),
        "cost_breakdown_cr": {
            "budget_uplift_cr": round(float(df["sim_budget_uplift_inr"].sum()) / 1e7, 2),
            "salary_increment_cr": round(float(df["sim_salary_inc_inr"].sum()) / 1e7, 2),
            "promotion_cost_cr": round(float(df["sim_promo_cost_inr"].sum()) / 1e7, 2),
            "retention_grant_cr": round(float(df["sim_retention_cost_inr"].sum()) / 1e7, 2),
            "overtime_savings_cr": round(float(df["sim_ot_savings_inr"].sum()) / 1e7, 2),
        },
        "assumptions": assumptions,
        "department_breakdown": dept_summary,
        "ml_risk_sensitivity": None,
    }

    # Optional Non-Causal Exploratory ML Risk Sensitivity (ONLY via validated pipeline)
    if include_ml_sensitivity and model_bundle is not None:
        pipe = model_bundle["pipeline"]
        threshold = float(model_bundle["threshold"])
        sim_features = df[FEATURE_COLUMNS].copy()

        base_probs = pipe.predict_proba(sim_features)[:, 1]

        # Apply simulated lever adjustments cleanly to model input features
        total_raise_pct = params.budget_increase_pct + params.salary_increment_pct
        if total_raise_pct > 0:
            sim_features["salary_growth_pct"] = sim_features["salary_growth_pct"] + np.where(non_intern, total_raise_pct, 0.0)
            sim_features["basic_salary"] = sim_features["basic_salary"] * (1.0 + params.budget_increase_pct / 100.0)
            sim_features["total_compensation"] = df["projected_total_compensation_inr"].values

        if params.overtime_reduction_pct > 0:
            sim_features["annualized_overtime_hours"] = np.maximum(
                0.0,
                sim_features["annualized_overtime_hours"] - reducible_ot,
            )

        if n_promoted > 0:
            sim_features.loc[promo_affected, "promotion_count"] += 1
            sim_features.loc[promo_affected, "promotion_gap"] = 0.25
            sim_features.loc[promo_affected, "salary_growth_pct"] += params.promotion_raise_pct

        sim_probs = pipe.predict_proba(sim_features)[:, 1]
        base_high = int((base_probs >= threshold).sum())
        sim_high = int((sim_probs >= threshold).sum())

        result["ml_risk_sensitivity"] = {
            "baseline_mean_pred_prob_pct": round(float(base_probs.mean()) * 100.0, 2),
            "simulated_mean_pred_prob_pct": round(float(sim_probs.mean()) * 100.0, 2),
            "risk_score_shift_pp": round((float(sim_probs.mean()) - float(base_probs.mean())) * 100.0, 2),
            "baseline_flagged_high_risk": base_high,
            "simulated_flagged_high_risk": sim_high,
            "net_flagged_reduction": base_high - sim_high,
            "disclaimer": (
                "Non-causal model sensitivity only: reflects how the validated predictive classifier scores "
                "adjusted feature inputs based on historical correlations. Real-world attrition changes must be "
                "verified via controlled HR pilots."
            ),
        }

    return result

