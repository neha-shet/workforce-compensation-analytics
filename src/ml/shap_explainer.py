"""Phase 5: SHAP Explainability Pipeline & Single-Employee Explainer.

Generates global SHAP feature importance, beeswarm summary plots, feature
impact dependence plots, and per-employee risk factor attributions.
Clearly distinguishes predictive feature contribution from causal proof.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from config.settings import PATHS, RANDOM_SEED, ensure_directories
from src.ml.train_models import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FEATURE_DISPLAY_NAMES,
    NUMERIC_FEATURES,
    load_ml_dataset,
)


def _create_explainer(clf: Any, X_bg_trans: np.ndarray) -> tuple[Any, str]:
    """Create appropriate SHAP explainer for XGBoost, Random Forest, or Logistic Regression."""
    cls_name = type(clf).__name__
    if "XGB" in cls_name or "RandomForest" in cls_name:
        try:
            explainer = shap.TreeExplainer(clf)
            # Smoke test 2 rows to ensure XGBoost base_score / format compatibility
            _ = explainer.shap_values(X_bg_trans[:2])
            return explainer, "TreeExplainer"
        except Exception:
            pass
    if "LogisticRegression" in cls_name:
        try:
            explainer = shap.LinearExplainer(clf, X_bg_trans)
            return explainer, "LinearExplainer"
        except Exception:
            pass

    # Model-agnostic fallback using predict_proba for positive class
    bg_small = shap.sample(X_bg_trans, min(100, len(X_bg_trans)), random_state=RANDOM_SEED)
    explainer = shap.Explainer(lambda x: clf.predict_proba(x)[:, 1], bg_small)
    return explainer, "PermutationExplainer"


def _extract_positive_shap_values(explainer: Any, mode: str, X_trans: np.ndarray) -> tuple[np.ndarray, float]:
    """Extract 2D (n_samples, n_features) SHAP array for class 1 (attrition=1) and base value."""
    if mode in ("TreeExplainer", "LinearExplainer"):
        sv = explainer.shap_values(X_trans)
        if isinstance(sv, list):
            sv_pos = np.asarray(sv[1], dtype=float)
            ev = explainer.expected_value
            base = float(ev[1]) if isinstance(ev, (list, np.ndarray)) else float(ev)
        elif isinstance(sv, np.ndarray) and sv.ndim == 3:
            sv_pos = sv[:, :, 1].astype(float)
            ev = explainer.expected_value
            base = float(ev[1]) if isinstance(ev, (list, np.ndarray)) else float(ev)
        else:
            sv_pos = np.asarray(sv, dtype=float)
            ev = explainer.expected_value
            base = float(ev[0]) if isinstance(ev, (list, np.ndarray)) else float(ev)
        return sv_pos, base

    exp = explainer(X_trans)
    sv_pos = np.asarray(exp.values, dtype=float)
    base = float(np.mean(exp.base_values))
    return sv_pos, base


def _aggregate_domain_shap(sv_row_or_mat: np.ndarray, pretty_names: list[str]) -> tuple[np.ndarray, list[str]]:
    """Aggregate one-hot encoded SHAP columns back to original business feature names."""
    is_1d = sv_row_or_mat.ndim == 1
    mat = sv_row_or_mat.reshape(1, -1) if is_1d else sv_row_or_mat

    grouped_cols: dict[str, list[int]] = {}
    for idx, name in enumerate(pretty_names):
        base = name.split(":", 1)[0].strip() if ":" in name else name
        grouped_cols.setdefault(base, []).append(idx)

    domain_names = list(grouped_cols.keys())
    agg = np.zeros((mat.shape[0], len(domain_names)), dtype=float)
    for j, dname in enumerate(domain_names):
        agg[:, j] = mat[:, grouped_cols[dname]].sum(axis=1)

    return (agg[0], domain_names) if is_1d else (agg, domain_names)


def explain_single_employee_row(
    bundle: dict[str, Any],
    row_df: pd.DataFrame,
    explainer: Any | None = None,
    mode: str | None = None,
    X_bg_trans: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute attrition probability and top contributing SHAP factors for a single employee."""
    pipe = bundle["pipeline"]
    prep = pipe.named_steps["prep"]
    clf = pipe.named_steps["clf"]
    pretty_names: list[str] = bundle["transformed_feature_names"]
    threshold = float(bundle["threshold"])

    row_features = row_df[FEATURE_COLUMNS].iloc[[0]]
    prob = float(pipe.predict_proba(row_features)[0, 1])
    X_trans = prep.transform(row_features)

    if explainer is None or mode is None:
        bg = X_bg_trans if X_bg_trans is not None else X_trans
        explainer, mode = _create_explainer(clf, bg)

    sv_pos, base_val = _extract_positive_shap_values(explainer, mode, X_trans)
    sv_1d = sv_pos[0]

    # Map back to original feature level with actual employee value
    grouped_sv, domain_names = _aggregate_domain_shap(sv_1d, pretty_names)
    raw_row = row_features.iloc[0]
    disp_to_col = {v: k for k, v in FEATURE_DISPLAY_NAMES.items()}

    factors: list[dict[str, Any]] = []
    for dname, shap_val in zip(domain_names, grouped_sv):
        raw_col = disp_to_col.get(dname, dname)
        val = raw_row[raw_col] if raw_col in raw_row.index else ""
        if isinstance(val, float) and np.isnan(val):
            val_str = "N/A"
        elif isinstance(val, (int, float, np.number)):
            val_str = f"{float(val):,.2f}" if abs(float(val)) < 1000 else f"{float(val):,.0f}"
        else:
            val_str = str(val)

        factors.append(
            {
                "feature": dname,
                "feature_col": raw_col,
                "value": val_str,
                "shap_contribution": round(float(shap_val), 4),
                "abs_contribution": round(abs(float(shap_val)), 4),
                "direction": "Increases Risk" if shap_val > 0 else "Reduces Risk",
            }
        )

    factors.sort(key=lambda x: x["abs_contribution"], reverse=True)
    risk_tier = "HIGH" if prob >= 0.65 else ("MEDIUM" if prob >= threshold else "LOW")

    return {
        "attrition_probability": round(prob, 4),
        "risk_tier": risk_tier,
        "decision_threshold": threshold,
        "base_value": round(float(base_val), 4),
        "explainer_type": mode,
        "top_factors": factors[:8],
        "all_factors": factors,
    }


def run_shap_explainability(
    db_path: Path | None = None,
    models_dir: Path | None = None,
    reports_dir: Path | None = None,
    sample_size: int = 2000,
) -> dict[str, Any]:
    """Run global and local SHAP explainability and save plots + report."""
    ensure_directories()
    m_dir = models_dir or (PATHS.root / "models")
    rep_dir = reports_dir or PATHS.reports
    fig_dir = rep_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    bundle = joblib.load(m_dir / "best_attrition_model.joblib")
    pipe = bundle["pipeline"]
    prep = pipe.named_steps["prep"]
    clf = pipe.named_steps["clf"]
    pretty_names: list[str] = bundle["transformed_feature_names"]

    df_all = load_ml_dataset(db_path=db_path)
    df_sample = df_all.sample(n=min(sample_size, len(df_all)), random_state=RANDOM_SEED).reset_index(drop=True)
    X_sample = df_sample[FEATURE_COLUMNS]
    X_trans = prep.transform(X_sample)

    explainer, mode = _create_explainer(clf, X_trans)
    sv_pos, base_val = _extract_positive_shap_values(explainer, mode, X_trans)

    # 1. Global SHAP Importance (Encoded & Domain-Aggregated)
    mean_abs_encoded = np.mean(np.abs(sv_pos), axis=0)
    encoded_imp_df = pd.DataFrame(
        {
            "encoded_feature": pretty_names,
            "mean_abs_shap": mean_abs_encoded,
            "mean_signed_shap": np.mean(sv_pos, axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False)

    sv_domain, domain_names = _aggregate_domain_shap(sv_pos, pretty_names)
    domain_imp_df = pd.DataFrame(
        {
            "feature": domain_names,
            "mean_abs_shap": np.mean(np.abs(sv_domain), axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False)

    # 2. Plot 13: SHAP Summary Beeswarm (Top 15 Encoded Features)
    plt.figure(figsize=(10.5, 6.5))
    shap.summary_plot(
        sv_pos,
        features=X_trans,
        feature_names=pretty_names,
        max_display=15,
        show=False,
    )
    plt.title(f"SHAP Summary Beeswarm — {bundle['best_model_name']} (Top 15 Encoded Features)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(fig_dir / "13_shap_summary_beeswarm.png", dpi=200, bbox_inches="tight")
    plt.close()

    # 3. Plot 14: SHAP Global Importance Bar (Domain Features)
    top_dom = domain_imp_df.head(14).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    bars = ax.barh(top_dom["feature"], top_dom["mean_abs_shap"], color="#1E3A5F", alpha=0.92)
    for b, val in zip(bars, top_dom["mean_abs_shap"]):
        ax.text(val + top_dom["mean_abs_shap"].max() * 0.015, b.get_y() + b.get_height() / 2, f"{val:.4f}", va="center", fontsize=8.5)
    ax.set_xlim(0, top_dom["mean_abs_shap"].max() * 1.18)
    ax.set_title(f"Global Feature Importance (Mean |SHAP Value|) — {bundle['best_model_name']}")
    ax.set_xlabel("Mean |SHAP Contribution to Model Log-Odds / Probability|")
    ax.grid(axis="x", alpha=0.35, linestyle="--")
    fig.tight_layout()
    fig.savefig(fig_dir / "14_shap_feature_importance_bar.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # 4. Plot 15: Feature Impact Dependence Plots for Top 3 Numeric Drivers
    top_num_drivers = [
        ("promotion_gap", "Promotion Gap (Years)"),
        ("salary_growth_pct", "Salary Growth (%)"),
        ("annualized_overtime_hours", "Annualized Overtime Hours"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    for ax, (raw_col, disp_name) in zip(axes, top_num_drivers):
        if disp_name in domain_names:
            j = domain_names.index(disp_name)
            x_vals = pd.to_numeric(X_sample[raw_col], errors="coerce")
            y_shap = sv_domain[:, j]
            valid = x_vals.notna()
            ax.scatter(x_vals[valid], y_shap[valid], alpha=0.35, s=14, color="#2B6CB0")
            ax.axhline(0.0, color="#DC2626", linestyle="--", linewidth=1.2)
            ax.set_title(f"SHAP Impact: {disp_name}")
            ax.set_xlabel(disp_name)
            ax.set_ylabel("SHAP Contribution")
            ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_dir / "15_shap_dependence_top_drivers.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # 5. Generate Example Individual Employee Explanations (High, Medium, Low Risk)
    probs_sample = pipe.predict_proba(X_sample)[:, 1]
    df_sample["pred_prob"] = probs_sample
    high_ex = df_sample.sort_values("pred_prob", ascending=False).iloc[[0]]
    med_idx = int(np.argmin(np.abs(probs_sample - 0.50)))
    med_ex = df_sample.iloc[[med_idx]]
    low_ex = df_sample.sort_values("pred_prob", ascending=True).iloc[[0]]

    sample_explanations: list[dict[str, Any]] = []
    for ex_df in (high_ex, med_ex, low_ex):
        res = explain_single_employee_row(bundle, ex_df, explainer=explainer, mode=mode, X_bg_trans=X_trans)
        res["employee_id"] = str(ex_df["employee_id"].iloc[0])
        res["department_name"] = str(ex_df["department_name"].iloc[0])
        res["designation"] = str(ex_df["designation"].iloc[0])
        sample_explanations.append(res)

    # Save global SHAP metadata
    shap_summary_json = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_name": bundle["best_model_name"],
        "explainer_type": mode,
        "sample_size": int(len(df_sample)),
        "base_value": round(float(base_val), 4),
        "domain_feature_importance": domain_imp_df.round(5).to_dict(orient="records"),
        "top_encoded_features": encoded_imp_df.head(20).round(5).to_dict(orient="records"),
        "sample_individual_explanations": sample_explanations,
    }
    (m_dir / "shap_global_importance.json").write_text(json.dumps(shap_summary_json, indent=2), encoding="utf-8")

    # Save Markdown SHAP Explainability Report
    md_lines = [
        "# SHAP Model Explainability Report",
        "",
        f"**Generated (UTC):** `{shap_summary_json['generated_at_utc']}` | **Model:** `{bundle['best_model_name']}` | **Explainer:** `{mode}` (`n={len(df_sample):,}` sample)",
        "",
        "> **Interpretability & Causality Note:** SHAP (SHapley Additive exPlanations) values quantify how strongly each feature contributed to the **model's prediction** for an employee relative to the baseline expected risk. **They do not establish real-world causal proof** and are intended to support human HR review alongside domain context.",
        "",
        "## Global Feature Importance (Aggregated to Business Features)",
        "",
        "| Rank | Feature | Mean |SHAP Contribution| |",
        "|---:|---|---:|",
    ]
    for rank, row in enumerate(domain_imp_df.head(12).itertuples(), start=1):
        md_lines.append(f"| {rank} | {row.feature} | {row.mean_abs_shap:.4f} |")

    md_lines.extend(["", "## Representative Individual Employee Explanations", ""])
    for ex in sample_explanations:
        md_lines.extend(
            [
                f"### Employee `{ex['employee_id']}` ({ex['department_name']} — {ex['designation']})",
                f"- **Predicted Attrition Probability:** `{ex['attrition_probability']*100:.1f}%` | **Risk Tier:** **{ex['risk_tier']}**",
                "- **Top Factors Contributing to Prediction:**",
            ]
        )
        for fac in ex["top_factors"][:5]:
            arrow = "↑ Increases Risk" if fac["shap_contribution"] > 0 else "↓ Reduces Risk"
            md_lines.append(
                f"  - `{fac['feature']}` (`{fac['value']}`): `{fac['shap_contribution']:+.4f}` ({arrow})"
            )
        md_lines.append("")

    md_lines.extend(
        [
            "## Generated SHAP Figures",
            "- `reports/figures/13_shap_summary_beeswarm.png`",
            "- `reports/figures/14_shap_feature_importance_bar.png`",
            "- `reports/figures/15_shap_dependence_top_drivers.png`",
            "",
        ]
    )

    (rep_dir / "shap_explainability_report.md").write_text("\n".join(md_lines), encoding="utf-8")
    return shap_summary_json


if __name__ == "__main__":
    res = run_shap_explainability()
    print(f"SHAP Explainability complete using {res['explainer_type']}. Top 5 drivers:")
    for item in res["domain_feature_importance"][:5]:
        print(f"  - {item['feature']}: {item['mean_abs_shap']:.4f}")

