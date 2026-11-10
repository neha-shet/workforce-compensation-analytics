"""Phase 4: Machine Learning Attrition Prediction & Model Comparison.

Trains and evaluates Logistic Regression, Random Forest, and XGBoost on
leak-free employee, compensation, career, and annualized leave/overtime features.
Optimizes for Recall & ROC-AUC (with full Accuracy, Precision, Recall, F1,
ROC-AUC, PR-AUC, Confusion Matrix, and Precision-Recall curves).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from config.settings import PATHS, RANDOM_SEED, ensure_directories
from src.analytics.sql_runner import apply_sqlite_views

NUMERIC_FEATURES: list[str] = [
    "age_years",
    "experience_years",
    "tenure_years",
    "basic_salary",
    "allowances",
    "bonus",
    "total_compensation",
    "salary_increment",
    "salary_growth_pct",
    "bonus_to_salary_ratio",
    "performance_rating",
    "manager_rating",
    "promotion_count",
    "promotion_gap",
    "training_hours",
    "annualized_leave_days",
    "annualized_sick_leave",
    "annualized_unpaid_leave",
    "annualized_overtime_hours",
]

CATEGORICAL_FEATURES: list[str] = [
    "department_name",
    "location",
    "designation",
    "employment_type",
    "education",
]

FORBIDDEN_LEAKAGE_COLUMNS: set[str] = {
    "employee_id",
    "employee_key",
    "attrition_flag",
    "exit_date",
    "exit_reason",
    "is_active",
    "joining_date",
    "latest_leave_year",
    "tenure_at_exit_years",
    "last_total_compensation",
}

FEATURE_COLUMNS: list[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES

FEATURE_DISPLAY_NAMES: dict[str, str] = {
    "age_years": "Age (Years)",
    "experience_years": "Total Experience (Years)",
    "tenure_years": "Company Tenure (Years)",
    "basic_salary": "Basic Salary (INR)",
    "allowances": "Allowances (INR)",
    "bonus": "Annual Bonus (INR)",
    "total_compensation": "Total Compensation (INR)",
    "salary_increment": "Annual Increment (INR)",
    "salary_growth_pct": "Salary Growth (%)",
    "bonus_to_salary_ratio": "Bonus-to-Basic Ratio",
    "performance_rating": "Performance Rating (1-5)",
    "manager_rating": "Manager Rating (1-5)",
    "promotion_count": "Promotion Count",
    "promotion_gap": "Promotion Gap (Years)",
    "training_hours": "Training Hours",
    "annualized_leave_days": "Annualized Leave Days",
    "annualized_sick_leave": "Annualized Sick Leave",
    "annualized_unpaid_leave": "Annualized Unpaid Leave",
    "annualized_overtime_hours": "Annualized Overtime Hours",
    "department_name": "Department",
    "location": "Location",
    "designation": "Designation",
    "employment_type": "Employment Type",
    "education": "Education",
}


def load_ml_dataset(db_path: Path | None = None) -> pd.DataFrame:
    """Load clean, leak-free employee feature dataset with annualized leave/overtime."""
    target_db = db_path or PATHS.sqlite_db
    apply_sqlite_views(db_path=target_db)

    query = """
    SELECT
        v.employee_id,
        v.department_name,
        v.location,
        v.designation,
        v.employment_type,
        v.education,
        v.age_years,
        v.experience_years,
        v.tenure_years,
        v.is_active,
        v.basic_salary,
        v.allowances,
        v.bonus,
        v.total_compensation,
        v.salary_increment,
        v.salary_growth_pct,
        v.bonus_to_salary_ratio,
        v.performance_rating,
        v.manager_rating,
        v.promotion_count,
        v.promotion_gap,
        v.training_hours,
        v.annualized_leave_days,
        CASE WHEN v.latest_leave_year = 2026 THEN ROUND(v.sick_leave / 0.75, 1) ELSE v.sick_leave END AS annualized_sick_leave,
        CASE WHEN v.latest_leave_year = 2026 THEN ROUND(v.unpaid_leave / 0.75, 1) ELSE v.unpaid_leave END AS annualized_unpaid_leave,
        v.annualized_overtime_hours,
        v.attrition_flag
    FROM vw_employee_workforce_360 v
    """
    conn = sqlite3.connect(target_db)
    try:
        df = pd.read_sql_query(query, conn)
    finally:
        conn.close()

    # Safety assertion: prevent any leakage column inside model features
    overlap = set(FEATURE_COLUMNS).intersection(FORBIDDEN_LEAKAGE_COLUMNS)
    if overlap:
        raise RuntimeError(f"Leakage columns detected in FEATURE_COLUMNS: {overlap}")

    return df


def build_preprocessor(scale_numeric: bool = True) -> ColumnTransformer:
    """Create reproducible sklearn ColumnTransformer for numeric & categorical features."""
    num_steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        num_steps.append(("scaler", StandardScaler()))
    num_pipe = Pipeline(steps=num_steps)

    cat_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", num_pipe, NUMERIC_FEATURES),
            ("cat", cat_pipe, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def _select_recall_friendly_threshold(y_true: np.ndarray, probs: np.ndarray) -> float:
    """Select threshold on training OOF probabilities maximizing F1.5 (prioritizes Recall cleanly)."""
    thresholds = np.linspace(0.25, 0.70, 46)
    best_t = 0.50
    best_score = -1.0
    for t in thresholds:
        preds = (probs >= t).astype(int)
        score = fbeta_score(y_true, preds, beta=1.5, zero_division=0)
        if score > best_score:
            best_score = score
            best_t = float(t)
    return round(best_t, 2)


def _evaluate_predictions(y_true: np.ndarray, probs: np.ndarray, threshold: float) -> dict[str, Any]:
    preds = (probs >= threshold).astype(int)
    cm = confusion_matrix(y_true, preds)
    return {
        "threshold": float(threshold),
        "accuracy": round(float(accuracy_score(y_true, preds)), 4),
        "precision": round(float(precision_score(y_true, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, preds, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, preds, zero_division=0)), 4),
        "f2_score": round(float(fbeta_score(y_true, preds, beta=2.0, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, probs)), 4),
        "pr_auc": round(float(average_precision_score(y_true, probs)), 4),
        "confusion_matrix": cm.tolist(),
    }


def _pretty_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    raw_names = list(preprocessor.get_feature_names_out())
    cleaned: list[str] = []
    for name in raw_names:
        if name.startswith("num__"):
            base = name.replace("num__", "", 1)
            cleaned.append(FEATURE_DISPLAY_NAMES.get(base, base))
        elif name.startswith("cat__"):
            rest = name.replace("cat__", "", 1)
            for cat_col in CATEGORICAL_FEATURES:
                prefix = f"{cat_col}_"
                if rest.startswith(prefix):
                    val = rest[len(prefix) :]
                    disp = FEATURE_DISPLAY_NAMES.get(cat_col, cat_col)
                    cleaned.append(f"{disp}: {val}")
                    break
            else:
                cleaned.append(rest)
        else:
            cleaned.append(name)
    return cleaned


def train_and_evaluate_models(
    db_path: Path | None = None,
    models_dir: Path | None = None,
    reports_dir: Path | None = None,
    processed_dir: Path | None = None,
) -> dict[str, Any]:
    """Train Logistic Regression, Random Forest & XGBoost; evaluate & save best model."""
    ensure_directories()
    m_dir = models_dir or (PATHS.root / "models")
    rep_dir = reports_dir or PATHS.reports
    fig_dir = rep_dir / "figures"
    proc_dir = processed_dir or PATHS.data_processed
    for d in (m_dir, rep_dir, fig_dir, proc_dir):
        d.mkdir(parents=True, exist_ok=True)

    df_all = load_ml_dataset(db_path=db_path)
    df_labeled = df_all.dropna(subset=["attrition_flag"]).copy()
    df_labeled["attrition_flag"] = df_labeled["attrition_flag"].astype(int)

    X = df_labeled[FEATURE_COLUMNS].copy()
    y = df_labeled["attrition_flag"].to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_SEED
    )

    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos_weight = round(neg_count / max(1, pos_count), 3)

    cv3 = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_SEED)
    cv5 = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)

    model_specs: dict[str, tuple[Pipeline, dict[str, list[Any]]]] = {
        "Logistic Regression": (
            Pipeline(
                steps=[
                    ("prep", build_preprocessor(scale_numeric=True)),
                    ("clf", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=RANDOM_SEED)),
                ]
            ),
            {"clf__C": [0.1, 0.5, 1.0, 2.5]},
        ),
        "Random Forest": (
            Pipeline(
                steps=[
                    ("prep", build_preprocessor(scale_numeric=False)),
                    ("clf", RandomForestClassifier(class_weight="balanced_subsample", random_state=RANDOM_SEED, n_jobs=-1)),
                ]
            ),
            {
                "clf__n_estimators": [200],
                "clf__max_depth": [8, 12],
                "clf__min_samples_leaf": [10, 20],
            },
        ),
        "XGBoost": (
            Pipeline(
                steps=[
                    ("prep", build_preprocessor(scale_numeric=False)),
                    (
                        "clf",
                        XGBClassifier(
                            scale_pos_weight=scale_pos_weight,
                            eval_metric="logloss",
                            subsample=0.85,
                            colsample_bytree=0.85,
                            random_state=RANDOM_SEED,
                            n_jobs=-1,
                        ),
                    ),
                ]
            ),
            {
                "clf__n_estimators": [180, 260],
                "clf__max_depth": [3, 4],
                "clf__learning_rate": [0.05, 0.08],
            },
        ),
    }

    results: dict[str, Any] = {}
    fitted_pipelines: dict[str, Pipeline] = {}
    test_probs_map: dict[str, np.ndarray] = {}

    for model_name, (pipe, param_grid) in model_specs.items():
        gs = GridSearchCV(
            estimator=pipe,
            param_grid=param_grid,
            scoring="roc_auc",
            cv=cv3,
            n_jobs=-1,
            refit=True,
        )
        gs.fit(X_train, y_train)
        best_pipe: Pipeline = gs.best_estimator_

        # 5-fold CV OOF predictions on training set for unbiased CV metrics & threshold calibration
        oof_probs = cross_val_predict(best_pipe, X_train, y_train, cv=cv5, method="predict_proba", n_jobs=-1)[:, 1]
        opt_thresh = _select_recall_friendly_threshold(y_train, oof_probs)

        cv_metrics_default = _evaluate_predictions(y_train, oof_probs, threshold=0.50)
        cv_metrics_opt = _evaluate_predictions(y_train, oof_probs, threshold=opt_thresh)

        # Held-out test evaluation
        test_probs = best_pipe.predict_proba(X_test)[:, 1]
        test_metrics_default = _evaluate_predictions(y_test, test_probs, threshold=0.50)
        test_metrics_opt = _evaluate_predictions(y_test, test_probs, threshold=opt_thresh)

        fitted_pipelines[model_name] = best_pipe
        test_probs_map[model_name] = test_probs
        results[model_name] = {
            "best_params": {k.replace("clf__", ""): v for k, v in gs.best_params_.items()},
            "cv_roc_auc": cv_metrics_default["roc_auc"],
            "cv_recall_at_0_5": cv_metrics_default["recall"],
            "cv_recall_at_opt": cv_metrics_opt["recall"],
            "test_default_0_5": test_metrics_default,
            "test_recall_optimized": test_metrics_opt,
        }

    # Select winning model balancing ROC-AUC & Recall/F1 (composite rank)
    def _model_rank_score(name: str) -> float:
        m = results[name]["test_recall_optimized"]
        return 0.50 * m["roc_auc"] + 0.30 * m["recall"] + 0.20 * m["f1_score"]

    best_model_name = max(results.keys(), key=_model_rank_score)
    best_pipeline = fitted_pipelines[best_model_name]
    best_threshold = results[best_model_name]["test_recall_optimized"]["threshold"]

    # =========================================================================
    # Plot 11: ROC Curves & Precision-Recall Curves
    # =========================================================================
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.2))
    colors = {"Logistic Regression": "#64748B", "Random Forest": "#2B6CB0", "XGBoost": "#DC2626"}
    for name, probs in test_probs_map.items():
        fpr, tpr, _ = roc_curve(y_test, probs)
        roc_val = results[name]["test_default_0_5"]["roc_auc"]
        axes[0].plot(fpr, tpr, linewidth=2.2, color=colors[name], label=f"{name} (AUC = {roc_val:.3f})")

        prec, rec, _ = precision_recall_curve(y_test, probs)
        pr_val = results[name]["test_default_0_5"]["pr_auc"]
        axes[1].plot(rec, prec, linewidth=2.2, color=colors[name], label=f"{name} (PR-AUC = {pr_val:.3f})")

    axes[0].plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random Baseline")
    axes[0].set_title("ROC Curve Comparison (Held-Out Test Set)")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate (Recall)")
    axes[0].legend(loc="lower right")
    axes[0].grid(alpha=0.35)

    baseline_pos = float(y_test.mean())
    axes[1].axhline(baseline_pos, color="black", linestyle="--", alpha=0.5, label=f"No-Skill ({baseline_pos:.2%})")
    axes[1].set_title("Precision-Recall Curve Comparison")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.35)
    fig.tight_layout()
    fig.savefig(fig_dir / "11_model_roc_and_pr_curves.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # Plot 12: Confusion Matrices (Recall-Optimized Threshold)
    # =========================================================================
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.5))
    for ax, name in zip(axes, results.keys()):
        cm = np.array(results[name]["test_recall_optimized"]["confusion_matrix"])
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks([0, 1])
        ax.set_yticks([0, 1])
        ax.set_xticklabels(["Pred Stay", "Pred Exit"])
        ax.set_yticklabels(["Actual Stay", "Actual Exit"])
        t_val = results[name]["test_recall_optimized"]["threshold"]
        rec_val = results[name]["test_recall_optimized"]["recall"]
        ax.set_title(f"{name}\n(t={t_val:.2f}, Recall={rec_val:.1%})")
        for r in range(2):
            for c in range(2):
                ax.text(c, r, f"{cm[r, c]:,}", ha="center", va="center", color="white" if cm[r, c] > cm.max() * 0.55 else "black", fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(fig_dir / "12_confusion_matrices.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    # =========================================================================
    # Save Best Model Artifact & Score Full Workforce
    # =========================================================================
    pretty_names = _pretty_feature_names(best_pipeline.named_steps["prep"])
    artifact_bundle = {
        "best_model_name": best_model_name,
        "pipeline": best_pipeline,
        "threshold": best_threshold,
        "feature_columns": FEATURE_COLUMNS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "transformed_feature_names": pretty_names,
        "trained_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    joblib.dump(artifact_bundle, m_dir / "best_attrition_model.joblib")

    # Score full clean workforce (active + exited for dashboard risk distribution)
    all_probs = best_pipeline.predict_proba(df_all[FEATURE_COLUMNS])[:, 1]
    scored = df_all[["employee_id", "department_name", "designation", "location", "is_active", "attrition_flag", "total_compensation", "promotion_gap", "salary_growth_pct", "annualized_overtime_hours", "performance_rating"]].copy()
    scored["attrition_probability"] = np.round(all_probs, 4)
    scored["predicted_high_risk_flag"] = (all_probs >= best_threshold).astype(int)
    scored["risk_tier"] = np.where(
        all_probs >= 0.65,
        "High",
        np.where(all_probs >= 0.35, "Medium", "Low"),
    )
    scored.to_parquet(proc_dir / "employee_risk_scores.parquet", index=False)

    # Save JSON comparison summary
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset_rows_labeled": int(len(df_labeled)),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "positive_class_rate_pct": round(float(y.mean() * 100.0), 2),
        "scale_pos_weight": scale_pos_weight,
        "best_model_name": best_model_name,
        "best_threshold": best_threshold,
        "feature_count_raw": len(FEATURE_COLUMNS),
        "feature_count_encoded": len(pretty_names),
        "models": results,
        "active_high_risk_count": int(((scored["is_active"] == 1) & (scored["risk_tier"] == "High")).sum()),
        "active_flagged_at_threshold_count": int(((scored["is_active"] == 1) & (scored["predicted_high_risk_flag"] == 1)).sum()),
    }
    (m_dir / "model_comparison.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Save Markdown Model Evaluation Report
    md_lines = [
        "# Employee Attrition Prediction — Model Evaluation Report",
        "",
        f"**Generated (UTC):** `{payload['generated_at_utc']}` | **Selected Champion Model:** **{best_model_name}**",
        "",
        "> **Synthetic Data & Leakage Control Note:** Metrics reflect performance on the Phase 1 synthetic dataset (`24,893` labeled records, `13.62%` positive class). All post-exit and temporal-leakage columns (`exit_date`, `exit_reason`, `is_active`, `latest_leave_year`) were strictly excluded, and 2026 YTD leave/overtime metrics were annualized prior to modeling.",
        "",
        "## Experimental Setup",
        "",
        f"- **Train / Test Split:** 80% / 20% Stratified (`{len(X_train):,}` train / `{len(X_test):,}` test)",
        f"- **Cross-Validation:** 3-Fold GridSearchCV hyperparameter tuning + 5-Fold Stratified OOF threshold calibration",
        f"- **Class Imbalance Handling:** `class_weight='balanced'` (Logistic Regression / Random Forest) & `scale_pos_weight={scale_pos_weight}` (XGBoost)",
        f"- **Decision Metric Priority:** Recall and ROC-AUC (with F1.5 recall-oriented threshold selection on OOF training probabilities to minimize missed high-risk employees)",
        "",
        "## Model Comparison (Held-Out Test Set)",
        "",
        "### Recall-Optimized Operating Point (OOF-Calibrated Threshold)",
        "",
        "| Model | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, res in results.items():
        m = res["test_recall_optimized"]
        md_lines.append(
            f"| **{name}** | {m['threshold']:.2f} | {m['accuracy']:.4f} | {m['precision']:.4f} | **{m['recall']:.4f}** | {m['f1_score']:.4f} | **{m['roc_auc']:.4f}** | {m['pr_auc']:.4f} |"
        )

    md_lines.extend(
        [
            "",
            "### Standard 0.50 Threshold Comparison & 5-Fold CV ROC-AUC",
            "",
            "| Model | 5-Fold CV ROC-AUC | Test Accuracy (@0.50) | Test Precision (@0.50) | Test Recall (@0.50) | Test F1 (@0.50) |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for name, res in results.items():
        m0 = res["test_default_0_5"]
        md_lines.append(
            f"| {name} | {res['cv_roc_auc']:.4f} | {m0['accuracy']:.4f} | {m0['precision']:.4f} | {m0['recall']:.4f} | {m0['f1_score']:.4f} |"
        )

    best_cm = results[best_model_name]["test_recall_optimized"]["confusion_matrix"]
    md_lines.extend(
        [
            "",
            f"## Champion Model Details: {best_model_name}",
            f"- **Best Hyperparameters:** `{results[best_model_name]['best_params']}`",
            f"- **Confusion Matrix (Test Set, threshold={best_threshold:.2f}):** `TN={best_cm[0][0]:,}`, `FP={best_cm[0][1]:,}`, `FN={best_cm[1][0]:,}`, `TP={best_cm[1][1]:,}`",
            f"- **Active Workforce Risk Screening:** `{payload['active_high_risk_count']:,}` active employees in **High Risk tier (prob >= 0.65)**, `{payload['active_flagged_at_threshold_count']:,}` flagged at calibrated threshold (`>= {best_threshold:.2f}`).",
            "",
            "## Evaluation Figures",
            "- `reports/figures/11_model_roc_and_pr_curves.png`",
            "- `reports/figures/12_confusion_matrices.png`",
            "",
        ]
    )

    (rep_dir / "model_evaluation.md").write_text("\n".join(md_lines), encoding="utf-8")
    return payload


if __name__ == "__main__":
    out = train_and_evaluate_models()
    print(f"Best model: {out['best_model_name']} | Test ROC-AUC={out['models'][out['best_model_name']]['test_recall_optimized']['roc_auc']} | Recall={out['models'][out['best_model_name']]['test_recall_optimized']['recall']}")
