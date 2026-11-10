# Resume & Interview Project Summary — Workforce & Compensation Analytics Engine

---

## Concise Resume Entry

**Workforce & Compensation Analytics Engine** | *Python, SQL (SQLite/PostgreSQL), XGBoost, SHAP, Plotly, Streamlit*  
*End-to-End People Analytics Warehouse, Predictive Attrition Engine & Decision-Support Dashboard*

- Architected an automated Python ETL and pre-load Data Quality engine validating **165,163 raw HR/payroll rows** across 5 tables (**99.71% baseline DQ score**), quarantining 455 anomalous/duplicate records and loading **24,953 cleaned synthetic employees** (`₹5,466.12 Cr` payroll) into a **Kimball Star Schema** (`4` dimensions, `4` facts) compatible with SQLite and PostgreSQL 16.
- Authored **5 reusable SQL views and 38 ANSI SQL analytical queries** (`CTEs`, `RANK`/`DENSE_RANK`, `NTILE`, `LAG`, conditional aggregation) plus statistical EDA (**SciPy** chi-square / Pearson tests across **10 visualizations**), uncovering that `>2.5 yr` promotion stagnation (`19.76%` vs `11.15%` attrition, `p = 2.01e-58`) and `250+ hr` overtime (`28.08%` vs `10.18%`, `p = 5.17e-129`) drive **67.4% of exits** across Engineering and Operations.
- Trained and compared leakage-controlled attrition classifiers (**XGBoost champion: `0.7920` Test ROC-AUC, `0.8026` 5-fold CV, `64.2%` Recall, `0.4847` PR-AUC**) paired with **SHAP TreeExplainer** risk drivers, deterministic **Workforce Scenario Simulation**, a **7-page Streamlit/Plotly UI**, and **12 automated pytest / Streamlit AppTest suites**.

---

## Technical Skills Demonstrated

- **Data Engineering & Warehousing:** Dimensional Star Schema modeling (`dim_*`, `fact_*`), Python ETL (`Pandas`, `PyArrow`, regex/taxonomy canonicalization), Data Quarantine auditing, SQLite & PostgreSQL 16 DDL (`docker-compose`), parameter-safe SQL.
- **SQL & Statistical Analytics:** 38 production-grade SQL analytical queries (`CTEs`, window functions, compa-ratios, cohort rolling trends, YoY overtime deltas), hypothesis testing (`chi2_contingency`, `pearsonr`), YTD annualization normalization.
- **Machine Learning & Explainable AI:** Target-leakage auditing, stratified CV hyperparameter tuning (`GridSearchCV`), class-imbalance calibration (`scale_pos_weight`, OOF F1.5 recall thresholding), ROC-AUC & PR-AUC trade-offs, global & local `SHAP` attribution.
- **BI Product Engineering & QA:** Custom-styled responsive 7-page `Streamlit` + `Plotly` enterprise dashboard, searchable sidebar filters, deterministic payroll what-if modeling, automated unit + integration + `AppTest` UI verification.

---

## Short Interview Walkthrough (Amazon / IBM Behavioral & Technical Fit)

- **Why did you design a Star Schema and Data Quality engine instead of jumping straight into a model?**  
  *"In real HR/payroll analytics, messy source joins, duplicate payroll runs, and partial YTD attendance rows (`2026` 9-month data) silently corrupt both executive headcount/budget numbers and ML features. Separating a `99.71%`-audited quarantine stage from normalized `dim_*`/`fact_*` tables guarantees every SQL view, EDA stat, and ML model reads one reconciled source of truth."*
- **How did you avoid data leakage and misleading accuracy metrics?**  
  *"Because attrition was `13.62%` on our synthetic dataset, predicting 'all active' gives `86.4%` accuracy while catching zero leavers. I strictly blocked post-exit fields (`exit_date`, `exit_reason`, `is_active`, `tenure_at_exit_years`), calibrated thresholds on 5-fold OOF probabilities for **Recall (`64.2%`)** and **ROC-AUC (`0.7920`) / PR-AUC (`0.4847`)**, and separated SHAP feature attribution from causal claims."*
- **How do stakeholders use the output without overfitting to ML assumptions?**  
  *"Leadership needs budget certainty first: the Scenario Simulator computes deterministic payroll cost deltas (`+₹334.24 Cr`, `-₹12.44 Cr` overtime savings under baseline defaults) and keeps optional ML risk shifts (`-3.32 pp`) isolated behind an explicit non-causal guardrail for pilot validation."*

