# Workforce & Compensation Exploratory Data Analysis (EDA) Report

**Generated (UTC):** `2026-11-10T12:05:30+00:00` | **Records Analyzed:** `24,953` (`24,893` labeled for attrition)

> **Synthetic Data Disclaimer:** All statistics, correlations, payroll figures (₹5,466.12 Cr), and attrition rates (13.62% overall) reported here are observed strictly from the Phase 1 synthetic enterprise dataset generated for portfolio demonstration, not real-world corporate benchmarks.

## Executive Summary Snapshot

- **Total Clean Workforce:** `24,953` employees (`21,562` active, `3,391` exited)
- **Total Annual Payroll (Synthetic):** `₹5,466.12 Cr` (Mean: `₹2,194,698`, Median: `₹1,613,450`)
- **Overall Attrition Rate:** `13.62%` | **Mean Tenure:** `3.04 yrs`
- **Visualizations Generated:** `10` charts in `reports/figures/`

## 8 Evidence-Backed Analytical Findings

### F1. Promotion Stagnation Strongly Escalates Attrition Risk
- **Observed Metric:** Attrition rises from 11.15% (<=1.5 yrs gap) to 19.76% (>2.5 yrs gap) and 25.58% (4.0+ yrs gap)
- **Statistical Evidence:** Chi-square=259.7, p=2.01e-58
- **Analytical Interpretation:** Employees waiting over 2.5 years for promotion experience roughly 1.77x the attrition rate of recently promoted peers.

### F2. Engineering & Operations Account for Over Half of Workforce Exits
- **Observed Metric:** Operations: 18.91% attrition | Engineering: 18.12% attrition (vs 5.28% in Human Resources)
- **Statistical Evidence:** Combined share of exits: 67.4%
- **Analytical Interpretation:** Engineering exhibits high Career Growth and Compensation exits alongside long promotion gaps, while Operations faces acute overtime pressure.

### F3. Severe Overtime (250+ Annualized Hours) Nearly Triples Attrition
- **Observed Metric:** Attrition jumps from 10.18% (<80 hrs) to 28.08% (250+ hrs)
- **Statistical Evidence:** Chi-square=584.0, p=5.17e-129
- **Analytical Interpretation:** Operations averages 216.2 annualized overtime hrs/year, driving Work-Life Balance burnout.

### F4. Low Salary Increments (<4%) Significantly Increase Departure Rates
- **Observed Metric:** Attrition is 31.24% for <4% raises vs 9.28% for 8-12% competitive raises
- **Statistical Evidence:** Chi-square=807.6, p=1.22e-177
- **Analytical Interpretation:** Even among high performers (rating 4-5), lagging annual increments correspond to materially elevated exit rates.

### F5. Pay-for-Performance Alignment Exists, But With Retention Outliers
- **Observed Metric:** Pearson r(Performance Rating, Salary Growth %) = 0.678 (p=0.00e+00); Rating 5 avg growth 11.11% vs Rating 1 2.48%
- **Statistical Evidence:** Rating<=2 attrition: 27.29% vs Rating>=4: 8.91%
- **Analytical Interpretation:** Poor manager ratings (<=2) compound attrition across every performance tier, confirming manager alignment as an independent retention lever.

### F6. Elevated Leave & Unpaid Leave Signal Disengagement Prior to Exit
- **Observed Metric:** Attrition for 3+ unpaid leave days: 30.93% vs 10.97% for 0 unpaid days
- **Statistical Evidence:** 28+ annualized leave days attrition: 24.62% vs <12 days: 11.16%
- **Analytical Interpretation:** High combined sick/unpaid leave patterns track strongly with elevated overtime and higher exit probability.

### F7. Exit Volume Peaks at 1-3 Years Tenure While Attrition Rate Escalates in Unpromoted Veteran Bands
- **Observed Metric:** 1-3 yrs tenure accounts for 44.4% of total exits (13.41% rate), whereas attrition rate rises from 8.04% (<1 yr) to 16.56% (5-10 yrs)
- **Statistical Evidence:** Active median tenure: 2.58 yrs vs Exited median tenure: 2.92 yrs
- **Analytical Interpretation:** While 1-3 yr staff produce the largest absolute exit volume, multi-year unpromoted veterans (5+ yrs) reach the highest exit rate when promotion gaps accumulate.

### F8. Payroll Concentration & Budget Overruns in Revenue and Product Units
- **Observed Metric:** Total synthetic payroll: ₹5,466.12 Cr across 24,906 compensated staff; 6 of 8 departments exceed 100% budget
- **Statistical Evidence:** Sales (111.8%) and Product (111.1%) show highest budget overrun
- **Analytical Interpretation:** Engineering alone represents over 33% of enterprise payroll while Sales & Product exceed allocated budgets by >11%.

## Generated Visualization Index

- `reports/figures/01_salary_distribution.png`
- `reports/figures/02_department_payroll_and_budget.png`
- `reports/figures/03_workforce_distribution.png`
- `reports/figures/04_attrition_by_department.png`
- `reports/figures/05_attrition_by_tenure.png`
- `reports/figures/06_salary_growth_vs_attrition.png`
- `reports/figures/07_leave_vs_attrition.png`
- `reports/figures/08_performance_distribution.png`
- `reports/figures/09_promotion_gap_analysis.png`
- `reports/figures/10_overtime_trends.png`