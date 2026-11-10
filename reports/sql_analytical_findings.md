# Workforce & Compensation SQL Analytical Findings

**Executed (UTC):** `2026-11-10T11:51:35+00:00` | **Total Views:** `5` | **Total Analytical Queries Executed:** `38`

> **Synthetic Data Note:** All metrics (including the 13.62% attrition rate and ₹5,466.12 Cr payroll base) are derived from the Phase 1 synthetic enterprise dataset generated for analytical demonstration, not real-world benchmarks.

## Reusable Warehouse Views

- `vw_data_quality_audit`
- `vw_department_kpi_summary`
- `vw_employee_workforce_360`
- `vw_high_risk_compensation_pockets`
- `vw_monthly_hiring_and_attrition`

## Executed Business Analytical Queries

### Q01 — enterprise_workforce_overview (`Workforce Distribution`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `1` | **Export:** `reports/sql_results/Q01_enterprise_workforce_overview.csv`
- **Business Question:** What are the top-level synthetic enterprise workforce, payroll, attrition, and tenure KPIs?
- **Interpretation:** Establishes baseline executive metrics across the 24,953 clean employee records in the warehouse.

| total_employees | active_employees | exited_employees | attrition_rate_pct | total_payroll_cr | avg_total_comp_inr | avg_tenure_years | avg_age_years |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24953.0 | 21562.0 | 3391.0 | 13.62 | 5466.12 | 2194698.0 | 3.04 | 33.7 |

### Q02 — department_headcount_and_share (`Department-wise Headcount`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q02_department_headcount_and_share.csv`
- **Business Question:** How is headcount distributed across departments and what percentage share does each represent?
- **Interpretation:** Uses window SUM() OVER() to compute exact workforce share alongside active vs exited breakdown.

| size_rank | department_name | department_head_function | total_headcount | active_headcount | exited_headcount | workforce_share_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Engineering | Technology & R&D | 7027 | 5757 | 1270 | 28.16 |
| 2 | Operations | Business Operations | 5390 | 4373 | 1017 | 21.6 |
| 3 | Sales | Revenue & Growth | 4055 | 3636 | 419 | 16.25 |
| 4 | Customer Success | Revenue & Growth | 2291 | 2070 | 221 | 9.18 |
| 5 | Data & Analytics | Technology & R&D | 2241 | 2047 | 194 | 8.98 |
| 6 | Finance | Corporate Functions | 1481 | 1388 | 93 | 5.94 |
| 6 | Product | Technology & R&D | 1481 | 1356 | 125 | 5.94 |
| 7 | Human Resources | Corporate Functions | 987 | 935 | 52 | 3.96 |

### Q03 — location_workforce_distribution (`Workforce Distribution`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `7` | **Export:** `reports/sql_results/Q03_location_workforce_distribution.csv`
- **Business Question:** Which office locations concentrate the workforce and how do they rank by active headcount and pay?
- **Interpretation:** Evaluates geographic footprint across Indian hubs and regional tiers.

| location_rank | location | region | cost_of_living_tier | total_employees | active_employees | headcount_share_pct | avg_total_comp_inr | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Bengaluru | South | Tier-1 | 7208 | 6215 | 28.89 | 2294217.0 | 13.81 |
| 2 | Hyderabad | South | Tier-1 | 4397 | 3781 | 17.62 | 2159352.0 | 14.04 |
| 3 | Pune | West | Tier-1 | 3546 | 3082 | 14.21 | 2126326.0 | 13.13 |
| 4 | Mumbai | West | Tier-1 | 3286 | 2834 | 13.17 | 2326168.0 | 13.8 |
| 5 | Gurugram | North | Tier-1 | 3021 | 2637 | 12.11 | 2217545.0 | 12.73 |
| 6 | Chennai | South | Tier-1 | 1984 | 1719 | 7.95 | 1978570.0 | 13.4 |
| 7 | Noida | North | Tier-2 | 1511 | 1294 | 6.06 | 1936291.0 | 14.38 |

### Q04 — monthly_hiring_trends_with_lag (`Monthly Hiring Trends`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `24` | **Export:** `reports/sql_results/Q04_monthly_hiring_trends_with_lag.csv`
- **Business Question:** How have monthly hiring volumes evolved since 2022 and what is the month-over-month momentum?
- **Interpretation:** Uses LAG() and cumulative window SUM() to track hiring velocity and net headcount expansion.

| year_month | hires_count | prev_month_hires | mom_hire_delta | exits_count | net_headcount_change | cumulative_hires |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09 | 0 | 85 | -85 | 378 | -378 | 20279 |
| 2026-08 | 85 | 111 | -26 | 414 | -329 | 20279 |
| 2026-07 | 111 | 170 | -59 | 388 | -277 | 20194 |
| 2026-06 | 170 | 220 | -50 | 327 | -157 | 20083 |
| 2026-05 | 220 | 303 | -83 | 288 | -68 | 19913 |
| 2026-04 | 303 | 307 | -4 | 222 | 81 | 19693 |
| 2026-03 | 307 | 351 | -44 | 192 | 115 | 19390 |
| 2026-02 | 351 | 384 | -33 | 160 | 191 | 19083 |

_Showing first 8 of 24 rows._

### Q05 — quarterly_hiring_vs_exits (`Monthly Hiring Trends`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `15` | **Export:** `reports/sql_results/Q05_quarterly_hiring_vs_exits.csv`
- **Business Question:** What is the quarterly hiring, attrition, and net growth trajectory across 2023-2026?
- **Interpretation:** Joins dim_date directly for fiscal/calendar quarter aggregation with LEAD() next-quarter comparison.

| year | quarter | hires | exits | net_change | next_quarter_hires |
| --- | --- | --- | --- | --- | --- |
| 2023.0 | 1.0 | 936.0 | 2.0 | 934.0 | 1076.0 |
| 2023.0 | 2.0 | 1076.0 | 2.0 | 1074.0 | 1223.0 |
| 2023.0 | 3.0 | 1223.0 | 5.0 | 1218.0 | 1229.0 |
| 2023.0 | 4.0 | 1229.0 | 6.0 | 1223.0 | 1281.0 |
| 2024.0 | 1.0 | 1281.0 | 13.0 | 1268.0 | 1387.0 |
| 2024.0 | 2.0 | 1387.0 | 21.0 | 1366.0 | 1505.0 |
| 2024.0 | 3.0 | 1505.0 | 36.0 | 1469.0 | 1488.0 |
| 2024.0 | 4.0 | 1488.0 | 47.0 | 1441.0 | 1470.0 |

_Showing first 8 of 15 rows._

### Q06 — designation_and_employment_type_mix (`Workforce Distribution`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `10` | **Export:** `reports/sql_results/Q06_designation_and_employment_type_mix.csv`
- **Business Question:** What is the workforce pyramid by designation and employment type?
- **Interpretation:** Uses conditional aggregation across Full-Time, Contract, and Intern cohorts per seniority level.

| designation | total_employees | full_time_count | contract_count | intern_count | share_pct | avg_experience_years |
| --- | --- | --- | --- | --- | --- | --- |
| VP | 223 | 200 | 23 | 0 | 0.89 | 18.4 |
| Director | 769 | 700 | 69 | 0 | 3.08 | 15.2 |
| Principal | 544 | 486 | 58 | 0 | 2.18 | 13.1 |
| Senior Manager | 1625 | 1488 | 137 | 0 | 6.51 | 13.2 |
| Manager | 2814 | 2564 | 250 | 0 | 11.28 | 10.9 |
| Senior Engineer | 2448 | 2230 | 218 | 0 | 9.81 | 9.0 |
| Team Lead | 3702 | 3353 | 349 | 0 | 14.84 | 9.7 |
| Senior Analyst | 4449 | 4078 | 371 | 0 | 17.83 | 8.4 |

_Showing first 8 of 10 rows._

### Q07 — tenure_distribution_and_experience_gap (`Employee Tenure`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `5` | **Export:** `reports/sql_results/Q07_tenure_distribution_and_experience_gap.csv`
- **Business Question:** How is the workforce distributed across tenure bands and how does internal tenure compare to total experience?
- **Interpretation:** Distinguishes early-tenure employees from veteran staff and quantifies prior external experience.

| tenure_band | employee_count | share_pct | avg_tenure_years | avg_total_experience_years | avg_prior_experience_years | avg_total_comp_inr |
| --- | --- | --- | --- | --- | --- | --- |
| <1 yr | 3108 | 12.46 | 0.64 | 6.14 | 5.5 | 1730528.0 |
| 1-3 yrs | 11243 | 45.06 | 1.99 | 8.49 | 6.5 | 2204110.0 |
| 3-5 yrs | 6817 | 27.32 | 3.87 | 9.49 | 5.62 | 2280960.0 |
| 5-10 yrs | 3622 | 14.52 | 6.42 | 10.84 | 4.42 | 2382342.0 |
| 10+ yrs | 163 | 0.65 | 11.42 | 14.15 | 2.73 | 2620986.0 |

### Q08 — age_demographics_by_department (`Workforce Distribution`)
- **Source:** `01_workforce_hiring_and_tenure.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q08_age_demographics_by_department.csv`
- **Business Question:** What are the age demographics and education mix across departments?
- **Interpretation:** Uses CASE age cohorts and conditional aggregation to inspect talent maturity across functions.

| department_name | headcount | avg_age | pct_under_28 | pct_28_to_38 | pct_over_38 | pct_postgrad |
| --- | --- | --- | --- | --- | --- | --- |
| Product | 1481 | 36.1 | 12.0 | 47.4 | 40.6 | 54.2 |
| Sales | 4055 | 34.3 | 20.6 | 49.6 | 29.8 | 45.3 |
| Finance | 1481 | 34.2 | 19.9 | 51.0 | 29.1 | 44.4 |
| Human Resources | 987 | 34.2 | 22.2 | 47.9 | 29.9 | 48.1 |
| Engineering | 7027 | 33.5 | 22.5 | 51.5 | 26.1 | 42.9 |
| Operations | 5390 | 33.3 | 23.7 | 52.0 | 24.3 | 41.2 |
| Customer Success | 2291 | 33.0 | 23.2 | 53.5 | 23.3 | 41.0 |
| Data & Analytics | 2241 | 33.0 | 24.7 | 52.3 | 23.0 | 42.5 |

### Q09 — department_payroll_and_budget_utilization (`Department Budget Utilization`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q09_department_payroll_and_budget_utilization.csv`
- **Business Question:** Which departments have the highest payroll expenditure and which exceed annual budget allocations?
- **Interpretation:** Compares actual total compensation against dim_department budgets with RANK() and variance status.

| payroll_rank | department_name | headcount | total_payroll_cr | annual_budget_cr | variance_cr | budget_utilization_pct | budget_status | avg_total_comp_inr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Engineering | 7027 | 1821.65 | 1780.0 | 41.65 | 102.34 | Over Budget (100-105%) | 2595307.0 |
| 2 | Sales | 4055 | 978.43 | 875.0 | 103.43 | 111.82 | Critical Overrun (>105%) | 2417063.0 |
| 3 | Operations | 5390 | 833.67 | 935.0 | -101.33 | 89.16 | Within Budget | 1550445.0 |
| 4 | Product | 1481 | 505.53 | 455.0 | 50.53 | 111.11 | Critical Overrun (>105%) | 3418082.0 |
| 5 | Data & Analytics | 2241 | 466.25 | 465.0 | 1.25 | 100.27 | Over Budget (100-105%) | 2088952.0 |
| 6 | Customer Success | 2291 | 336.49 | 345.0 | -8.51 | 97.53 | Within Budget | 1470692.0 |
| 7 | Finance | 1481 | 322.2 | 295.0 | 27.2 | 109.22 | Critical Overrun (>105%) | 2178479.0 |
| 8 | Human Resources | 987 | 201.89 | 188.0 | 13.89 | 107.39 | Critical Overrun (>105%) | 2051706.0 |

### Q10 — compensation_component_decomposition (`Payroll Expenditure`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q10_compensation_component_decomposition.csv`
- **Business Question:** How does total payroll decompose into Basic Salary, Allowances, Bonus, Deductions, and Net Salary per department?
- **Interpretation:** Reconciles gross-to-net payroll waterfall across all departments in INR Crores.

| department_name | basic_cr | allowances_cr | bonus_cr | gross_total_comp_cr | deductions_cr | net_salary_cr | bonus_share_pct | effective_deduction_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Engineering | 1252.02 | 424.08 | 145.55 | 1821.65 | 240.23 | 1581.41 | 7.99 | 13.19 |
| Sales | 628.39 | 213.76 | 136.28 | 978.43 | 137.53 | 840.9 | 13.93 | 14.06 |
| Operations | 570.71 | 193.04 | 69.92 | 833.67 | 100.2 | 733.47 | 8.39 | 12.02 |
| Product | 344.22 | 116.94 | 44.37 | 505.53 | 74.55 | 430.99 | 8.78 | 14.75 |
| Data & Analytics | 320.13 | 108.69 | 37.44 | 466.25 | 58.79 | 407.46 | 8.03 | 12.61 |
| Customer Success | 231.38 | 77.77 | 27.34 | 336.49 | 37.85 | 298.64 | 8.13 | 11.25 |
| Finance | 220.06 | 74.33 | 27.81 | 322.2 | 42.69 | 279.51 | 8.63 | 13.25 |
| Human Resources | 137.78 | 46.63 | 17.48 | 201.89 | 26.44 | 175.45 | 8.66 | 13.09 |

### Q11 — compensation_by_designation (`Compensation Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `10` | **Export:** `reports/sql_results/Q11_compensation_by_designation.csv`
- **Business Question:** What are the average, minimum, maximum, and variable bonus shares across designations?
- **Interpretation:** Benchmarks career-ladder pay progression from Analyst/Software Engineer to VP.

| pay_tier_rank | designation | headcount | avg_basic_inr | avg_allowances_inr | avg_bonus_inr | avg_total_comp_inr | min_total_comp_inr | max_total_comp_inr | avg_bonus_to_basic_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | VP | 222 | 8045049.0 | 2740667.0 | 1556209.0 | 12341925.0 | 7544500.0 | 17237800.0 | 19.21 |
| 2 | Director | 766 | 5050557.0 | 1727230.0 | 943601.0 | 7721387.0 | 4328400.0 | 11963600.0 | 18.53 |
| 3 | Principal | 544 | 4075848.0 | 1374810.0 | 432383.0 | 5883041.0 | 3623500.0 | 8217000.0 | 10.55 |
| 4 | Senior Manager | 1621 | 3057541.0 | 1040294.0 | 559188.0 | 4657023.0 | 2719200.0 | 7033500.0 | 18.18 |
| 5 | Manager | 2807 | 2088733.0 | 710836.0 | 255753.0 | 3055322.0 | 1615900.0 | 5228900.0 | 12.06 |
| 6 | Senior Engineer | 2443 | 1624412.0 | 552840.0 | 169320.0 | 2346573.0 | 1372200.0 | 3439500.0 | 10.31 |
| 7 | Team Lead | 3694 | 1589619.0 | 540804.0 | 194681.0 | 2325104.0 | 1114700.0 | 3869800.0 | 12.09 |
| 8 | Senior Analyst | 4443 | 857364.0 | 291225.0 | 109593.0 | 1258182.0 | 671800.0 | 2172300.0 | 12.5 |

_Showing first 8 of 10 rows._

### Q12 — dept_designation_compa_ratio (`Compensation Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `25` | **Export:** `reports/sql_results/Q12_dept_designation_compa_ratio.csv`
- **Business Question:** Which department-designation cells pay above or below the company-wide designation average?
- **Interpretation:** Computes internal compa-ratio (dept cell avg / company designation avg) using window partitions.

| department_name | designation | headcount | dept_desig_avg_comp_inr | company_desig_avg_inr | compa_ratio_pct |
| --- | --- | --- | --- | --- | --- |
| Engineering | Team Lead | 941 | 2670473.0 | 2316325.0 | 115.3 |
| Data & Analytics | Director | 34 | 8763529.0 | 7644961.0 | 114.6 |
| Data & Analytics | Senior Analyst | 447 | 1475078.0 | 1289763.0 | 114.4 |
| Product | Senior Analyst | 291 | 1476011.0 | 1289763.0 | 114.4 |
| Engineering | Senior Manager | 339 | 5223426.0 | 4574791.0 | 114.2 |
| Engineering | Director | 161 | 8684952.0 | 7644961.0 | 113.6 |
| Data & Analytics | Analyst | 441 | 748219.0 | 658983.0 | 113.5 |
| Engineering | Manager | 594 | 3435457.0 | 3032009.0 | 113.3 |

_Showing first 8 of 25 rows._

### Q13 — top_earners_ranked_per_department (`Compensation Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `40` | **Export:** `reports/sql_results/Q13_top_earners_ranked_per_department.csv`
- **Business Question:** Who are the top 5 highest-compensated employees in each department and what quartile do they represent?
- **Interpretation:** Demonstrates DENSE_RANK() and NTILE(4) partitioned by department for executive compensation review.

| department_name | dept_rank | employee_id | designation | location | tenure_years | total_compensation_inr | net_salary_inr | comp_quartile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Customer Success | 1 | EMP20718 | Director | Mumbai | 1.45 | 8607700.0 | 6850300.0 | 1 |
| Customer Success | 2 | EMP03031 | Director | Hyderabad | 5.92 | 7834300.0 | 6420300.0 | 1 |
| Customer Success | 3 | EMP12345 | Director | Hyderabad | 1.12 | 7615000.0 | 6240500.0 | 1 |
| Customer Success | 4 | EMP08735 | Director | Bengaluru | 1.36 | 7566200.0 | 6105700.0 | 1 |
| Customer Success | 5 | EMP21046 | Director | Mumbai | 4.51 | 7420900.0 | 5983700.0 | 1 |
| Data & Analytics | 1 | EMP19627 | VP | Bengaluru | 2.33 | 15869400.0 | 11346200.0 | 1 |
| Data & Analytics | 2 | EMP01316 | VP | Gurugram | 4.26 | 15224400.0 | 11124500.0 | 1 |
| Data & Analytics | 3 | EMP09454 | VP | Bengaluru | 8.51 | 14379700.0 | 10401900.0 | 1 |

_Showing first 8 of 40 rows._

### Q14 — below_average_increment_analysis (`Salary Increment Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q14_below_average_increment_analysis.csv`
- **Business Question:** Which departments have the highest share of eligible staff receiving below-peer-average salary increments?
- **Interpretation:** Compares each employee's salary_growth_pct against their Department + Designation peer average via window AVG().

| department_name | eligible_employees | below_peer_avg_count | below_peer_avg_pct | below_avg_attrition_pct | at_or_above_attrition_pct | dept_avg_growth_pct |
| --- | --- | --- | --- | --- | --- | --- |
| Customer Success | 2015 | 1021 | 50.67 | 13.6 | 6.36 | 8.79 |
| Finance | 1297 | 657 | 50.66 | 8.08 | 4.87 | 8.79 |
| Product | 1299 | 657 | 50.58 | 10.5 | 6.57 | 8.76 |
| Engineering | 6159 | 3112 | 50.53 | 25.0 | 13.05 | 6.56 |
| Human Resources | 857 | 431 | 50.29 | 6.29 | 5.42 | 8.7 |
| Operations | 4755 | 2375 | 49.95 | 26.65 | 13.4 | 6.5 |
| Data & Analytics | 1952 | 974 | 49.9 | 12.59 | 6.3 | 8.82 |
| Sales | 3573 | 1779 | 49.79 | 15.13 | 7.12 | 8.79 |

### Q15 — salary_increment_buckets_vs_attrition (`Salary Increment Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q15_salary_increment_buckets_vs_attrition.csv`
- **Business Question:** How do salary growth brackets relate to retention among eligible full-time/contract employees?
- **Interpretation:** Segments salary_growth_pct using CASE brackets to quantify low-increment flight sensitivity.

| increment_bucket | employee_count | avg_growth_pct | avg_total_comp_inr | attrition_rate_pct |
| --- | --- | --- | --- | --- |
| 1. Low (<4%) | 3040 | 2.41 | 2076222.0 | 31.24 |
| 2. Moderate (4-8%) | 8819 | 6.19 | 2203437.0 | 15.12 |
| 3. Competitive (8-12%) | 7852 | 9.74 | 2356864.0 | 9.28 |
| 4. High (12%+) | 2156 | 13.56 | 2410422.0 | 6.55 |

### Q16 — location_cost_of_living_pay_differential (`Compensation Analysis`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `7` | **Export:** `reports/sql_results/Q16_location_cost_of_living_pay_differential.csv`
- **Business Question:** How does average pay vary across office cities and cost-of-living tiers?
- **Interpretation:** Compares city pay averages vs overall enterprise average using a scalar subquery benchmark.

| cost_of_living_tier | city | headcount | avg_total_comp_inr | pct_vs_company_avg | total_payroll_cr |
| --- | --- | --- | --- | --- | --- |
| Tier-1 | Mumbai | 3275 | 2326168.0 | 5.99 | 761.82 |
| Tier-1 | Bengaluru | 7196 | 2294217.0 | 4.53 | 1650.92 |
| Tier-1 | Gurugram | 3015 | 2217545.0 | 1.04 | 668.59 |
| Tier-1 | Hyderabad | 4387 | 2159352.0 | -1.61 | 947.31 |
| Tier-1 | Pune | 3542 | 2126326.0 | -3.12 | 753.14 |
| Tier-1 | Chennai | 1981 | 1978570.0 | -9.85 | 391.95 |
| Tier-2 | Noida | 1510 | 1936291.0 | -11.77 | 292.38 |

### Q17 — compensation_anomalies_audit (`Compensation Anomalies`)
- **Source:** `02_compensation_and_payroll.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q17_compensation_anomalies_audit.csv`
- **Business Question:** How many records were flagged as out-of-band salary anomalies during ETL, and where are they concentrated?
- **Interpretation:** Audits normalized extreme salary anomalies by department and designation alongside bonus-outlier counts.

| department_name | total_payroll_records | flagged_salary_anomalies | anomaly_rate_pct | high_bonus_ratio_cases | max_clean_total_comp_inr |
| --- | --- | --- | --- | --- | --- |
| Engineering | 7019 | 29 | 0.413 | 0 | 17237800.0 |
| Operations | 5377 | 18 | 0.335 | 1 | 13173300.0 |
| Sales | 4048 | 14 | 0.346 | 113 | 17177600.0 |
| Customer Success | 2288 | 11 | 0.481 | 0 | 8607700.0 |
| Data & Analytics | 2232 | 8 | 0.358 | 0 | 15869400.0 |
| Product | 1479 | 5 | 0.338 | 0 | 15845400.0 |
| Human Resources | 984 | 3 | 0.305 | 0 | 12776100.0 |
| Finance | 1479 | 1 | 0.068 | 0 | 13605200.0 |

### Q18 — department_attrition_vs_target (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q18_department_attrition_vs_target.csv`
- **Business Question:** Which departments have the highest attrition rates relative to their target attrition benchmarks?
- **Interpretation:** Ranks departments by actual attrition excess above target_attrition_pct to prioritize intervention.

| attrition_rank | department_name | total_employees | exited_employees | attrition_rate_pct | target_attrition_pct | excess_vs_target_pct | attrition_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Operations | 5390 | 1017 | 18.91 | 13.5 | 5.41 | High Risk Hotspot |
| 2 | Engineering | 7027 | 1270 | 18.12 | 13.0 | 5.12 | High Risk Hotspot |
| 3 | Sales | 4055 | 419 | 10.35 | 13.0 | -2.65 | On / Below Target |
| 4 | Customer Success | 2291 | 221 | 9.68 | 12.0 | -2.32 | On / Below Target |
| 5 | Data & Analytics | 2241 | 194 | 8.68 | 11.5 | -2.82 | On / Below Target |
| 6 | Product | 1481 | 125 | 8.45 | 11.0 | -2.55 | On / Below Target |
| 7 | Finance | 1481 | 93 | 6.3 | 8.5 | -2.2 | On / Below Target |
| 8 | Human Resources | 987 | 52 | 5.28 | 9.0 | -3.72 | On / Below Target |

### Q19 — monthly_attrition_trend_rolling (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `45` | **Export:** `reports/sql_results/Q19_monthly_attrition_trend_rolling.csv`
- **Business Question:** What is the monthly exit volume and 3-month rolling average across 2023-2026?
- **Interpretation:** Uses LAG() and sliding window AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) to smooth exit seasonality.

| year_month | exits_count | prev_month_exits | rolling_3m_avg_exits | hires_count |
| --- | --- | --- | --- | --- |
| 2023-01 | 1 |  | 1.0 | 309 |
| 2023-02 | 0 | 1.0 | 0.5 | 276 |
| 2023-03 | 1 | 0.0 | 0.7 | 351 |
| 2023-04 | 1 | 1.0 | 0.7 | 330 |
| 2023-05 | 1 | 1.0 | 1.0 | 387 |
| 2023-06 | 0 | 1.0 | 0.7 | 359 |
| 2023-07 | 2 | 0.0 | 1.0 | 374 |
| 2023-08 | 2 | 2.0 | 1.3 | 437 |

_Showing first 8 of 45 rows._

### Q20 — exited_vs_active_tenure_and_comp (`Employee Tenure`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q20_exited_vs_active_tenure_and_comp.csv`
- **Business Question:** What is the average tenure and compensation of exited employees compared to active staff across departments?
- **Interpretation:** Uses conditional aggregation across attrition_flag=1 vs attrition_flag=0 cohorts.

| department_name | avg_exited_tenure_yrs | avg_active_tenure_yrs | avg_exited_comp_inr | avg_active_comp_inr | avg_exited_promo_gap_yrs | avg_active_promo_gap_yrs |
| --- | --- | --- | --- | --- | --- | --- |
| Engineering | 3.26 | 2.94 | 2616093.0 | 2590072.0 | 2.29 | 1.78 |
| Operations | 3.28 | 3.0 | 1659828.0 | 1526146.0 | 2.24 | 1.79 |
| Finance | 3.42 | 2.96 | 2367768.0 | 2162512.0 | 2.43 | 1.87 |
| Product | 3.43 | 3.12 | 3353653.0 | 3418972.0 | 2.31 | 1.89 |
| Customer Success | 3.48 | 2.98 | 1474747.0 | 1469582.0 | 2.34 | 1.8 |
| Sales | 3.52 | 3.02 | 2283703.0 | 2433164.0 | 2.56 | 1.84 |
| Data & Analytics | 3.55 | 3.06 | 2112397.0 | 2085146.0 | 2.57 | 1.89 |
| Human Resources | 3.75 | 2.94 | 2170135.0 | 2047508.0 | 2.72 | 1.85 |

### Q21 — attrition_by_tenure_band (`Employee Tenure`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `5` | **Export:** `reports/sql_results/Q21_attrition_by_tenure_band.csv`
- **Business Question:** Which tenure bands exhibit the sharpest attrition concentration?
- **Interpretation:** Evaluates retention curves across <1 yr, 1-3 yrs, 3-5 yrs, 5-10 yrs, and 10+ yrs cohorts.

| tenure_band | total_employees | exited_employees | attrition_rate_pct | share_of_total_exits_pct | avg_tenure_years |
| --- | --- | --- | --- | --- | --- |
| <1 yr | 3097 | 249 | 8.04 | 7.34 | 0.64 |
| 1-3 yrs | 11219 | 1504 | 13.41 | 44.35 | 1.99 |
| 3-5 yrs | 6803 | 1012 | 14.88 | 29.84 | 3.87 |
| 5-10 yrs | 3611 | 598 | 16.56 | 17.63 | 6.42 |
| 10+ yrs | 163 | 28 | 17.18 | 0.83 | 11.42 |

### Q22 — attrition_by_salary_band_and_quintile (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `5` | **Export:** `reports/sql_results/Q22_attrition_by_salary_band_and_quintile.csv`
- **Business Question:** How does attrition vary across salary bands and within-company compensation quintiles?
- **Interpretation:** Uses NTILE(5) compensation quintiles to assess retention sensitivity across pay levels.

| pay_quintile | employee_count | min_comp_inr | max_comp_inr | avg_comp_inr | avg_salary_growth_pct | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 4970.0 | 276200.0 | 759600.0 | 557557.0 | 6.25 | 12.03 |
| 2.0 | 4969.0 | 759800.0 | 1309900.0 | 1071145.0 | 7.01 | 14.53 |
| 3.0 | 4969.0 | 1310400.0 | 2127700.0 | 1661502.0 | 7.31 | 14.07 |
| 4.0 | 4969.0 | 2127800.0 | 3005000.0 | 2521431.0 | 7.3 | 14.53 |
| 5.0 | 4969.0 | 3005200.0 | 17237800.0 | 5160705.0 | 7.81 | 12.98 |

### Q23 — exit_reasons_ranked_by_department (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `25` | **Export:** `reports/sql_results/Q23_exit_reasons_ranked_by_department.csv`
- **Business Question:** What are the top exit reasons overall and within each department?
- **Interpretation:** Uses DENSE_RANK() partitioned by department to identify whether Compensation, Career Growth, or Work-Life Balance dominates.

| department_name | reason_rank | exit_reason | exit_count | dept_exit_share_pct |
| --- | --- | --- | --- | --- |
| Customer Success | 1 | Compensation | 56 | 25.3 |
| Customer Success | 2 | Career Growth | 53 | 24.0 |
| Customer Success | 3 | Manager / Culture | 45 | 20.4 |
| Data & Analytics | 1 | Career Growth | 48 | 24.7 |
| Data & Analytics | 1 | Compensation | 48 | 24.7 |
| Data & Analytics | 2 | Manager / Culture | 37 | 19.1 |
| Data & Analytics | 3 | Work-Life Balance | 31 | 16.0 |
| Engineering | 1 | Compensation | 310 | 24.4 |

_Showing first 8 of 25 rows._

### Q24 — location_designation_attrition_hotspots (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `15` | **Export:** `reports/sql_results/Q24_location_designation_attrition_hotspots.csv`
- **Business Question:** Which department-designation combinations experience the highest attrition rates (min 50 headcount)?
- **Interpretation:** Pinpoints specific organizational roles driving elevated turnover.

| hotspot_rank | department_name | designation | headcount | exited_count | attrition_rate_pct | avg_promo_gap_yrs | avg_overtime_hrs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Operations | VP | 55 | 16 | 29.09 | 2.1 | 234.9 |
| 2 | Operations | Director | 143 | 33 | 23.08 | 1.96 | 223.0 |
| 3 | Operations | Senior Manager | 312 | 67 | 21.47 | 1.92 | 227.4 |
| 4 | Engineering | Team Lead | 942 | 198 | 21.02 | 1.96 | 136.6 |
| 5 | Operations | Manager | 600 | 124 | 20.67 | 1.97 | 214.9 |
| 6 | Engineering | Senior Manager | 338 | 68 | 20.12 | 1.91 | 133.8 |
| 7 | Engineering | Principal | 344 | 69 | 20.06 | 1.92 | 140.6 |
| 8 | Operations | Senior Analyst | 1281 | 245 | 19.13 | 1.89 | 216.2 |

_Showing first 8 of 15 rows._

### Q25 — attrition_payroll_exposure_by_department (`Attrition Analysis`)
- **Source:** `03_attrition_and_retention.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q25_attrition_payroll_exposure_by_department.csv`
- **Business Question:** What is the cumulative annual compensation base associated with exited employees by department?
- **Interpretation:** Quantifies total compensation turnover exposure (INR Cr) across departments.

| department_name | exited_headcount | exited_comp_base_cr | pct_of_dept_comp_turned_over | avg_exited_comp_inr |
| --- | --- | --- | --- | --- |
| Engineering | 1270 | 331.98 | 18.28 | 2616093.0 |
| Operations | 1017 | 168.47 | 20.24 | 1659828.0 |
| Sales | 419 | 95.46 | 9.77 | 2283703.0 |
| Product | 125 | 41.92 | 8.31 | 3353653.0 |
| Data & Analytics | 194 | 40.77 | 8.77 | 2112397.0 |
| Customer Success | 221 | 32.59 | 9.72 | 1474747.0 |
| Finance | 93 | 22.02 | 6.86 | 2367768.0 |
| Human Resources | 52 | 11.28 | 5.6 | 2170135.0 |

### Q26 — performance_rating_vs_comp_and_attrition (`Performance Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `5` | **Export:** `reports/sql_results/Q26_performance_rating_vs_comp_and_attrition.csv`
- **Business Question:** Does performance rating correlate with compensation growth, bonus ratio, and attrition?
- **Interpretation:** Tests pay-for-performance alignment across ratings 1 through 5.

| performance_rating | employee_count | workforce_share_pct | avg_total_comp_inr | avg_salary_growth_pct | avg_bonus_to_basic_pct | avg_promotions | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 1257.0 | 5.05 | 1852687.0 | 2.48 | 4.15 | 0.74 | 31.5 |
| 2.0 | 3313.0 | 13.31 | 2027482.0 | 4.49 | 7.71 | 0.97 | 25.69 |
| 3.0 | 11602.0 | 46.61 | 2171982.0 | 6.7 | 11.3 | 1.05 | 11.78 |
| 4.0 | 6478.0 | 26.02 | 2314043.0 | 8.79 | 15.07 | 1.18 | 9.09 |
| 5.0 | 2243.0 | 9.01 | 2402940.0 | 11.11 | 18.67 | 1.28 | 8.38 |

### Q27 — manager_vs_performance_alignment_matrix (`Performance Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `3` | **Export:** `reports/sql_results/Q27_manager_vs_performance_alignment_matrix.csv`
- **Business Question:** How does alignment (or gap) between manager rating and performance rating impact attrition?
- **Interpretation:** Uses CASE classification to detect manager-employee appraisal friction.

| rating_segment | employee_count | avg_salary_growth_pct | avg_promo_gap_yrs | attrition_rate_pct |
| --- | --- | --- | --- | --- |
| Low Manager Rating (<=2) | 5762 | 4.68 | 1.91 | 24.44 |
| Standard Alignment | 11350 | 6.79 | 1.92 | 11.27 |
| Aligned Top Talent (4-5) | 7781 | 9.45 | 1.83 | 9.05 |

### Q28 — promotion_gap_vs_attrition (`Promotion Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q28_promotion_gap_vs_attrition.csv`
- **Business Question:** How strongly does promotion gap affect attrition overall and within Engineering?
- **Interpretation:** Quantifies attrition escalation when promotion_gap exceeds 2.5 and 4.0 years.

| promotion_gap_bucket | total_employees | overall_attrition_pct | engineering_attrition_pct | operations_attrition_pct | avg_salary_growth_pct |
| --- | --- | --- | --- | --- | --- |
| 1. <= 1.5 yrs | 12153 | 11.15 | 14.78 | 16.14 | 6.63 |
| 2. 1.5 - 2.5 yrs | 6157 | 11.94 | 16.7 | 16.67 | 7.59 |
| 3. 2.5 - 4.0 yrs | 4437 | 16.95 | 22.2 | 22.79 | 7.6 |
| 4. > 4.0 yrs | 2146 | 25.58 | 33.86 | 32.98 | 7.75 |

### Q29 — tenured_never_promoted_employees (`Promotion Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q29_tenured_never_promoted_employees.csv`
- **Business Question:** How many tenured employees (3+ years) have zero promotions across departments, and what is their attrition rate?
- **Interpretation:** Identifies career-progression bottlenecks using conditional aggregation.

| department_name | tenured_3plus_count | zero_promotion_count | pct_never_promoted | never_promoted_attrition_pct | promoted_attrition_pct |
| --- | --- | --- | --- | --- | --- |
| Engineering | 2901 | 513 | 17.68 | 30.21 | 18.22 |
| Operations | 2351 | 411 | 17.48 | 29.93 | 18.87 |
| Sales | 1744 | 277 | 15.88 | 17.69 | 11.25 |
| Customer Success | 959 | 139 | 14.49 | 17.27 | 11.34 |
| Data & Analytics | 983 | 154 | 15.67 | 14.29 | 9.29 |
| Product | 668 | 106 | 15.87 | 11.32 | 8.9 |
| Human Resources | 406 | 72 | 17.73 | 11.11 | 5.99 |
| Finance | 615 | 112 | 18.21 | 8.04 | 6.56 |

### Q30 — training_effectiveness_analysis (`Training Effectiveness`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q30_training_effectiveness_analysis.csv`
- **Business Question:** Are higher annual training hours associated with stronger performance ratings, more promotions, and lower attrition?
- **Interpretation:** Segments training_hours into 4 investment tiers to inspect retention and career outcomes.

| training_tier | employee_count | avg_training_hrs | avg_perf_rating | avg_promotions | avg_salary_growth_pct | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Low (<20 hrs) | 1313 | 14.8 | 2.53 | 0.94 | 5.73 | 20.03 |
| 2. Moderate (20-35 hrs) | 6946 | 28.8 | 2.9 | 1.03 | 6.47 | 16.71 |
| 3. High (35-50 hrs) | 10975 | 42.3 | 3.27 | 1.11 | 7.27 | 12.8 |
| 4. Intensive (50+ hrs) | 5659 | 57.3 | 3.62 | 1.1 | 8.01 | 9.93 |

### Q31 — high_performer_flight_risk_pockets (`Performance Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q31_high_performer_flight_risk_pockets.csv`
- **Business Question:** Which departments hold the largest pockets of high-performing employees facing promotion stagnation or below-peer raises?
- **Interpretation:** Queries reusable view vw_high_risk_compensation_pockets to quantify critical talent at risk.

| department_name | high_perf_at_risk_count | avg_promo_gap_yrs | avg_growth_vs_peer_pct | avg_total_comp_inr | observed_attrition_pct |
| --- | --- | --- | --- | --- | --- |
| Engineering | 848 | 3.07 | 1.39 | 2860130.0 | 17.81 |
| Operations | 668 | 3.06 | 1.48 | 1746453.0 | 16.32 |
| Sales | 528 | 3.08 | 1.58 | 2624115.0 | 10.04 |
| Data & Analytics | 286 | 3.33 | 1.59 | 2326813.0 | 9.79 |
| Customer Success | 254 | 2.83 | 1.3 | 1671066.0 | 9.06 |
| Finance | 189 | 3.03 | 1.58 | 2264595.0 | 5.82 |
| Product | 184 | 3.17 | 1.38 | 4033632.0 | 4.89 |
| Human Resources | 107 | 2.92 | 1.47 | 2205057.0 | 4.67 |

### Q32 — department_promotion_and_training_benchmarks (`Promotion Analysis`)
- **Source:** `04_performance_promotion_training.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q32_department_promotion_and_training_benchmarks.csv`
- **Business Question:** How do departments compare on average promotion counts, promotion gaps, and training hours per employee?
- **Interpretation:** Benchmarks career mobility and L&D investment across departments with RANK().

| stagnation_rank | department_name | avg_promotions | avg_promotion_gap_yrs | avg_training_hours | avg_perf_rating | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Data & Analytics | 1.12 | 1.95 | 40.8 | 3.23 | 8.68 |
| 2 | Product | 1.15 | 1.93 | 40.6 | 3.23 | 8.45 |
| 3 | Sales | 1.06 | 1.92 | 40.6 | 3.21 | 10.35 |
| 4 | Finance | 1.04 | 1.9 | 40.6 | 3.2 | 6.3 |
| 5 | Human Resources | 1.04 | 1.89 | 39.7 | 3.2 | 5.28 |
| 6 | Operations | 1.1 | 1.87 | 40.5 | 3.18 | 18.91 |
| 7 | Engineering | 1.05 | 1.87 | 40.3 | 3.21 | 18.12 |
| 8 | Customer Success | 1.09 | 1.85 | 40.6 | 3.22 | 9.68 |

### Q33 — leave_utilization_by_department_and_year (`Leave Utilization`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `24` | **Export:** `reports/sql_results/Q33_leave_utilization_by_department_and_year.csv`
- **Business Question:** How do leave types (sick, casual, unpaid) and annualized leave utilization vary by department?
- **Interpretation:** Aggregates multi-year fact_leave normalized for 2026 YTD (9-month) scaling.

| department_name | year | employee_count | avg_sick_leave | avg_casual_leave | avg_unpaid_leave | avg_total_leave_days | avg_annualized_leave_util_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Customer Success | 2024 | 1640 | 3.6 | 9.5 | 1.1 | 14.2 | 50.7 |
| Customer Success | 2025 | 2106 | 3.6 | 9.4 | 1.0 | 14.1 | 50.4 |
| Customer Success | 2026 | 2227 | 2.7 | 7.1 | 0.9 | 10.7 | 51.1 |
| Data & Analytics | 2024 | 1568 | 3.7 | 9.4 | 1.0 | 14.1 | 50.4 |
| Data & Analytics | 2025 | 2041 | 3.7 | 9.5 | 1.0 | 14.2 | 50.6 |
| Data & Analytics | 2026 | 2177 | 2.7 | 7.2 | 0.9 | 10.8 | 51.3 |
| Engineering | 2024 | 5013 | 3.9 | 9.5 | 1.1 | 14.5 | 51.7 |
| Engineering | 2025 | 6432 | 3.9 | 9.5 | 1.1 | 14.4 | 51.5 |

_Showing first 8 of 24 rows._

### Q34 — leave_and_unpaid_leave_vs_attrition (`Leave Utilization`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q34_leave_and_unpaid_leave_vs_attrition.csv`
- **Business Question:** Do high-leave and high-unpaid-leave employees exhibit significantly higher attrition?
- **Interpretation:** Segments annualized leave utilization and unpaid leave flags against attrition rates.

| leave_tier | employee_count | avg_annual_leave_days | avg_unpaid_days | avg_annual_overtime_hrs | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- |
| 1. Low (<12 days/yr) | 6006 | 8.9 | 0.58 | 99.5 | 11.21 |
| 2. Normal (12-20 days/yr) | 15122 | 15.1 | 0.96 | 111.9 | 13.27 |
| 3. Elevated (20-28 days/yr) | 3624 | 21.8 | 1.38 | 137.8 | 18.43 |
| 4. High (28+ days/yr) | 126 | 29.1 | 1.79 | 182.0 | 23.02 |

### Q35 — overtime_concentration_and_burnout_by_dept (`Overtime Analysis`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `8` | **Export:** `reports/sql_results/Q35_overtime_concentration_and_burnout_by_dept.csv`
- **Business Question:** Which departments carry the heaviest overtime burden and how does high overtime (>200 hrs/yr) relate to attrition?
- **Interpretation:** Uses conditional aggregation to contrast burnout-threshold (>200 hrs) vs normal-overtime attrition.

| department_name | employee_count | avg_annual_overtime_hrs | pct_over_200_hrs | high_ot_attrition_pct | normal_ot_attrition_pct |
| --- | --- | --- | --- | --- | --- |
| Operations | 5376 | 216.1 | 48.9 | 25.19 | 12.81 |
| Engineering | 7002 | 135.3 | 20.2 | 25.32 | 16.21 |
| Product | 1478 | 57.9 | 1.2 | 11.11 | 8.36 |
| Finance | 1477 | 56.8 | 1.2 | 5.56 | 6.31 |
| Customer Success | 2280 | 56.3 | 1.1 | 33.33 | 9.31 |
| Sales | 4046 | 56.2 | 1.5 | 11.86 | 10.31 |
| Data & Analytics | 2235 | 56.0 | 1.1 | 24.0 | 8.46 |
| Human Resources | 984 | 52.6 | 1.3 | 0.0 | 5.36 |

### Q36 — yoy_overtime_surge_and_attrition (`Overtime Analysis`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q36_yoy_overtime_surge_and_attrition.csv`
- **Business Question:** Does a sharp year-over-year surge in annualized overtime (+40 hrs or more) correlate with higher attrition?
- **Interpretation:** Uses LAG() over fact_leave partitioned by employee_key across 2024-2026 to detect workload escalation.

| ot_trend_segment | employee_count | avg_current_ot_hrs | avg_yoy_ot_delta_hrs | attrition_rate_pct |
| --- | --- | --- | --- | --- |
| 4. Stable Overtime | 21058 | 112.0 | -0.0 | 14.09 |
| 3. Overtime Relief (-40h) | 839 | 93.9 | -49.3 | 13.59 |
| 2. Sharp Overtime Surge (+40h) | 937 | 149.5 | 48.9 | 12.91 |
| 1. First Observation Year | 2044 | 114.7 |  | 8.51 |

### Q37 — sick_leave_vs_overtime_tiers (`Leave Utilization`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `4` | **Export:** `reports/sql_results/Q37_sick_leave_vs_overtime_tiers.csv`
- **Business Question:** Do employees working heavy overtime take higher sick leave, compounding exit risk?
- **Interpretation:** Tests the relationship between overtime workload bands, sick days, and attrition.

| overtime_tier | employee_count | avg_overtime_hrs | avg_sick_leave_days | avg_unpaid_leave_days | attrition_rate_pct |
| --- | --- | --- | --- | --- | --- |
| 1. Low (<80 hrs) | 11999 | 38.4 | 2.72 | 0.93 | 10.18 |
| 2. Moderate (80-160 hrs) | 6783 | 114.6 | 2.72 | 0.95 | 11.96 |
| 3. High (160-250 hrs) | 3532 | 199.4 | 2.92 | 0.92 | 17.64 |
| 4. Severe (250+ hrs) | 2564 | 338.9 | 4.71 | 0.94 | 28.08 |

### Q38 — data_quality_warehouse_audit (`Compensation Anomalies`)
- **Source:** `05_leave_overtime_and_dq.sql` | **Rows Returned:** `24` | **Export:** `reports/sql_results/Q38_data_quality_warehouse_audit.csv`
- **Business Question:** What were the pre-ETL data quality dimension scores and defect volumes persisted in the warehouse?
- **Interpretation:** Surfaces Data Quality audit metrics directly from vw_data_quality_audit for governance reporting.

| metric_category | metric_name | metric_value | assessed_at_utc |
| --- | --- | --- | --- |
| quality_score_pct | completeness | 99.95 | 2026-11-10T11:34:49+00:00 |
| quality_score_pct | uniqueness | 99.87 | 2026-11-10T11:34:49+00:00 |
| quality_score_pct | validity | 99.88 | 2026-11-10T11:34:49+00:00 |
| quality_score_pct | consistency | 98.61 | 2026-11-10T11:34:49+00:00 |
| quality_score_pct | integrity | 99.91 | 2026-11-10T11:34:49+00:00 |
| quality_score_pct | overall_data_quality_score | 99.71 | 2026-11-10T11:34:49+00:00 |
| defect_count | total_employee_records | 25137.0 | 2026-11-10T11:34:49+00:00 |
| defect_count | unique_valid_employees | 24987.0 | 2026-11-10T11:34:49+00:00 |

_Showing first 8 of 24 rows._
