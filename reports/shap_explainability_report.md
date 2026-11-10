# SHAP Model Explainability Report

**Generated (UTC):** `2026-11-10T11:56:06+00:00` | **Model:** `XGBoost` | **Explainer:** `TreeExplainer` (`n=2,000` sample)

> **Interpretability & Causality Note:** SHAP (SHapley Additive exPlanations) values quantify how strongly each feature contributed to the **model's prediction** for an employee relative to the baseline expected risk. **They do not establish real-world causal proof** and are intended to support human HR review alongside domain context.

## Global Feature Importance (Aggregated to Business Features)

| Rank | Feature | Mean |SHAP Contribution| |
|---:|---|---:|
| 1 | Promotion Gap (Years) | 0.3380 |
| 2 | Annualized Overtime Hours | 0.2813 |
| 3 | Salary Growth (%) | 0.2796 |
| 4 | Company Tenure (Years) | 0.2740 |
| 5 | Department | 0.1817 |
| 6 | Performance Rating (1-5) | 0.1801 |
| 7 | Total Experience (Years) | 0.1332 |
| 8 | Training Hours | 0.1096 |
| 9 | Manager Rating (1-5) | 0.1094 |
| 10 | Promotion Count | 0.1080 |
| 11 | Annualized Unpaid Leave | 0.1071 |
| 12 | Annualized Sick Leave | 0.1007 |

## Representative Individual Employee Explanations

### Employee `EMP05045` (Engineering — Manager)
- **Predicted Attrition Probability:** `98.9%` | **Risk Tier:** **HIGH**
- **Top Factors Contributing to Prediction:**
  - `Annualized Overtime Hours` (`469.40`): `+1.3775` (↑ Increases Risk)
  - `Promotion Count` (`4.00`): `+0.9228` (↑ Increases Risk)
  - `Annualized Unpaid Leave` (`2.00`): `+0.7182` (↑ Increases Risk)
  - `Salary Growth (%)` (`0.75`): `+0.5442` (↑ Increases Risk)
  - `Annualized Sick Leave` (`7.00`): `+0.5168` (↑ Increases Risk)

### Employee `EMP10335` (Engineering — Director)
- **Predicted Attrition Probability:** `50.0%` | **Risk Tier:** **LOW**
- **Top Factors Contributing to Prediction:**
  - `Promotion Gap (Years)` (`4.28`): `+0.5439` (↑ Increases Risk)
  - `Department` (`Engineering`): `+0.2745` (↑ Increases Risk)
  - `Salary Growth (%)` (`11.44`): `-0.2354` (↓ Reduces Risk)
  - `Total Experience (Years)` (`21.80`): `+0.2281` (↑ Increases Risk)
  - `Education` (`M.Sc`): `+0.2207` (↑ Increases Risk)

### Employee `EMP24838` (Customer Success — Analyst)
- **Predicted Attrition Probability:** `0.9%` | **Risk Tier:** **LOW**
- **Top Factors Contributing to Prediction:**
  - `Allowances (INR)` (`45,000`): `-1.3023` (↓ Reduces Risk)
  - `Promotion Gap (Years)` (`0.19`): `-0.9357` (↓ Reduces Risk)
  - `Salary Growth (%)` (`0.00`): `-0.7771` (↓ Reduces Risk)
  - `Total Experience (Years)` (`0.20`): `-0.4095` (↓ Reduces Risk)
  - `Annualized Overtime Hours` (`12.50`): `-0.2704` (↓ Reduces Risk)

## Generated SHAP Figures
- `reports/figures/13_shap_summary_beeswarm.png`
- `reports/figures/14_shap_feature_importance_bar.png`
- `reports/figures/15_shap_dependence_top_drivers.png`
