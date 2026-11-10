# Employee Attrition Prediction — Model Evaluation Report

**Generated (UTC):** `2026-11-10T11:55:19+00:00` | **Selected Champion Model:** **XGBoost**

> **Synthetic Data & Leakage Control Note:** Metrics reflect performance on the Phase 1 synthetic dataset (`24,893` labeled records, `13.62%` positive class). All post-exit and temporal-leakage columns (`exit_date`, `exit_reason`, `is_active`, `latest_leave_year`) were strictly excluded, and 2026 YTD leave/overtime metrics were annualized prior to modeling.

## Experimental Setup

- **Train / Test Split:** 80% / 20% Stratified (`19,914` train / `4,979` test)
- **Cross-Validation:** 3-Fold GridSearchCV hyperparameter tuning + 5-Fold Stratified OOF threshold calibration
- **Class Imbalance Handling:** `class_weight='balanced'` (Logistic Regression / Random Forest) & `scale_pos_weight=6.34` (XGBoost)
- **Decision Metric Priority:** Recall and ROC-AUC (with F1.5 recall-oriented threshold selection on OOF training probabilities to minimize missed high-risk employees)

## Model Comparison (Held-Out Test Set)

### Recall-Optimized Operating Point (OOF-Calibrated Threshold)

| Model | Threshold | Accuracy | Precision | Recall | F1-Score | ROC-AUC | PR-AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Logistic Regression** | 0.48 | 0.6425 | 0.2261 | **0.6711** | 0.3383 | **0.7176** | 0.3305 |
| **Random Forest** | 0.45 | 0.7421 | 0.2863 | **0.5988** | 0.3874 | **0.7402** | 0.3379 |
| **XGBoost** | 0.51 | 0.7658 | 0.3203 | **0.6416** | 0.4273 | **0.7920** | 0.4847 |

### Standard 0.50 Threshold Comparison & 5-Fold CV ROC-AUC

| Model | 5-Fold CV ROC-AUC | Test Accuracy (@0.50) | Test Precision (@0.50) | Test Recall (@0.50) | Test F1 (@0.50) |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 0.7314 | 0.6634 | 0.2303 | 0.6283 | 0.3370 |
| Random Forest | 0.7462 | 0.7963 | 0.3293 | 0.4779 | 0.3899 |
| XGBoost | 0.8026 | 0.7566 | 0.3114 | 0.6504 | 0.4212 |

## Champion Model Details: XGBoost
- **Best Hyperparameters:** `{'learning_rate': 0.08, 'max_depth': 3, 'n_estimators': 260}`
- **Confusion Matrix (Test Set, threshold=0.51):** `TN=3,378`, `FP=923`, `FN=243`, `TP=435`
- **Active Workforce Risk Screening:** `1,697` active employees in **High Risk tier (prob >= 0.65)**, `4,273` flagged at calibrated threshold (`>= 0.51`).

## Evaluation Figures
- `reports/figures/11_model_roc_and_pr_curves.png`
- `reports/figures/12_confusion_matrices.png`
