# 3–5 Minute Portfolio & Interview Demonstration Script

**Project:** Workforce & Compensation Analytics Engine  
**Target Roles:** Data Analyst / Business Intelligence Engineer / Analytics Engineer (Amazon, IBM, enterprise People Analytics teams)  
**Target Live URL:** `http://localhost:8501` (launched via `streamlit run app/streamlit_app.py`)

---

## 0:00 – 0:45 | Business Problem & Architecture Opening
- **What to show:** Open [`README.md`](../README.md) (Architecture Diagram & Star Schema).
- **Script:**
  > "Enterprise HR and compensation teams often struggle because payroll budgets, leave logs, performance calibration, and exit tracking sit in disconnected exports—making it hard to spot why critical talent leaves before exits happen.
  >
  > To solve this end to end, I built the **Workforce & Compensation Analytics Engine**. Rather than starting with a tiny clean Kaggle CSV, I engineered a `25,000+` employee synthetic HR/payroll pipeline with realistic real-world data defects, built a data quality quarantine and dimensional star schema warehouse (`SQLite` + `PostgreSQL 16`), wrote `38` analytical SQL queries, trained leakage-controlled attrition models with `XGBoost` and `SHAP`, and surfaced the insights inside a `7-page` interactive Streamlit decision-support application."
  >
  > *(Key clarity check)*: "Important note: all `₹5,466.12 Cr` payroll and `13.62%` attrition figures come from this synthetic dataset so every correlation and scenario calculation is reproducible without exposing proprietary employee PII."

---

## 0:45 – 1:30 | Data Quality & Python ETL + Dimensional Star Schema
- **What to show:** Switch to **Page 5 — Data Quality** (`05_data_quality.png`).
- **Script:**
  > "Any analytical model is only as trustworthy as its upstream data. Before loading our warehouse, my Data Quality assessor audits `165,163` raw rows across 5 tables, achieving a `99.71%` baseline score while explicitly surfacing issues: `137` duplicate employee records, `85` duplicate payroll rows, `90` out-of-band salary anomalies, `420` messy department strings like `'Engg'` or `'R&D Engineering'`, and `62` net-pay arithmetic mismatches.
  >
  > The ETL pipeline standardizes valid master taxonomies, quarantines irremediable anomalies into audit CSVs, annualizes 2026 9-month YTD leave/overtime data (`÷ 0.75`), engineers analytical ratios like `promotion_gap` and `salary_growth_pct`, and loads `24,953` clean employees into a 4-dimension, 4-fact Star Schema with enforced foreign keys."

---

## 1:30 – 2:15 | SQL Analytics, Executive Overview & Attrition Drivers
- **What to show:** Switch to **Page 1 — Executive Overview** (`01_executive_overview.png`), then demonstrate compact sidebar filters (e.g., filtering `Department = Engineering`), then switch to **Page 4 — Attrition Analytics** (`04_attrition_analytics.png`).
- **Script:**
  > "At the warehouse layer, `5` reusable SQL views and `38` CTE/window-function queries answer compensation equity, budget overrun, and turnover questions.
  >
  > In the dashboard Executive Overview, we track `24,953` employees, `₹5,466.12 Cr` gross payroll, and `13.62%` overall attrition. Look at two standout patterns in **Attrition Analytics**:
  > 1. **Department Hotspots:** Operations (`18.91%`) and Engineering (`18.12%`) exceed their `13.5%` / `13.0%` targets and generate `67.4%` of all exits.
  > 2. **Promotion Stagnation & Overtime Burnout:** Attrition climbs from `11.15%` for employees promoted within `1.5 years` to `25.58%` beyond `4 years` without promotion (`chi-square = 259.7`, `p = 2.01e-58`), while `250+` annualized overtime hours track `28.08%` attrition—nearly `2.8x` the `<80 hr` baseline."

---

## 2:15 – 3:15 | Predictive Attrition ML & SHAP Explainability
- **What to show:** Switch to **Page 6 — Predictive Analytics & SHAP** (`06_predictive_analytics_shap.png`). Scroll briefly to Global SHAP and Individual Live Explanation.
- **Script:**
  > "For proactive risk screening, I strictly excluded post-exit columns (`exit_date`, `exit_reason`, `is_active`, `tenure_at_exit_years`) to prevent target leakage, then compared Logistic Regression, Random Forest, and XGBoost on an 80/20 stratified split using `scale_pos_weight` and OOF recall-oriented threshold calibration.
  >
  > Because missing a flight-risk high performer is costlier than a false alert, we evaluate ROC-AUC, Recall, and PR-AUC rather than accuracy alone. **XGBoost** led with **`0.7920` Test ROC-AUC** (`0.8026` 5-fold CV), **`64.2%` Recall**, and **`0.4847` PR-AUC**, identifying `1,697` active high-risk employees (`prob >= 65%`).
  >
  > With `SHAP TreeExplainer`, HRBPs don't just see a probability score—they see individual log-odds contributors such as `Promotion Gap`, `Annualized Overtime`, and `Salary Growth %`. I explicitly frame SHAP as predictive attribution, not causal proof, so retention reviews focus on human context."

---

## 3:15 – 4:15 | Interactive Scenario Simulator & Business Recommendations
- **What to show:** Switch to **Page 7 — Workforce Scenario Simulator** (`07_scenario_simulator.png`), adjust `Target Department Scope = Engineering` or overtime/promotion sliders briefly, then conclude on Executive Recommendation cards / CSV export.
- **Script:**
  > "Finally, analytics must connect to budgets. In the **Scenario Simulator**, HR and FP&A leaders test policy levers—such as a `+5%` budget uplift, `+2%` merit raises, `15%` excess overtime reduction, `10%` promotion catch-up for stagnant staff, and `25%` retention grants for high-risk staff.
  >
  > Payroll costs (`+₹334.24 Cr`, `94.7%` projected budget utilization, `-₹12.44 Cr` overtime savings) are **100% deterministic**, while optional ML risk shifts (`-3.32 pp`) carry an explicit non-causal guardrail. Paired with our `7` dynamically generated recommendations—like rebalancing Operations capacity within its `89.2%` budget utilization and targeting raises to `1,055` under-indexed high performers—this closes the loop from raw SQL governance to CFO/VP HR decision support."

