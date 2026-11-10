# SQL Data Warehouse & Analytical Layer Documentation

> **Synthetic Data Note:** All row counts and executed outputs reflect the Phase 1 synthetic enterprise dataset (`24,953` clean employees) loaded into `data/warehouse/workforce_dw.db` and structured identically for PostgreSQL 16 (`dw` schema).

## 1. Dimensional Star Schema

### Dimension Tables
- **`dim_department`** (`department_key` PK, `department_name`, `department_head_function`, `annual_budget_inr`, `target_attrition_pct`)
- **`dim_location`** (`location_key` PK, `city`, `region`, `country`, `cost_of_living_tier`)
- **`dim_date`** (`date_key` PK `YYYYMMDD`, `full_date`, `year`, `quarter`, `month`, `month_name`, `day_of_week`, `fiscal_year`, `is_weekend`)
- **`dim_employee`** (`employee_key` PK, `employee_id`, `department_key` FK, `location_key` FK, `designation`, `employment_type`, `education`, `date_of_birth`, `age_years`, `joining_date`, `experience_years`, `tenure_years`, `tenure_band`, `is_active`)

### Fact & Audit Tables
- **`fact_compensation`** (`compensation_key` PK, `employee_key` FK, `department_key` FK, `location_key` FK, `increment_date_key` FK, `basic_salary`, `allowances`, `bonus`, `deductions`, `net_salary`, `total_compensation`, `salary_increment`, `salary_growth_pct`, `bonus_to_salary_ratio`, `salary_band`, `is_salary_anomaly`)
- **`fact_leave`** (`leave_key` PK, `employee_key` FK, `department_key` FK, `date_key` FK, `year`, `leave_days`, `sick_leave`, `casual_leave`, `unpaid_leave`, `overtime_hours`, `leave_utilization`, `overtime_ratio`)
- **`fact_performance`** (`performance_key` PK, `employee_key` FK, `department_key` FK, `last_promotion_date_key` FK, `performance_rating`, `manager_rating`, `promotion_count`, `training_hours`, `promotion_gap`)
- **`fact_attrition`** (`attrition_key` PK, `employee_key` FK, `department_key` FK, `location_key` FK, `exit_date_key` FK, `attrition_flag`, `exit_reason`, `tenure_at_exit_years`, `last_total_compensation`)
- **`meta_data_quality_metrics`** (`metric_id` PK, `metric_category`, `metric_name`, `metric_value`, `assessed_at_utc`)

## 2. Reusable Analytical SQL Views

- SQLite views: `sql/analytics/00_views_sqlite.sql`
- PostgreSQL 16 (`dw` schema) views: `sql/analytics/00_views_postgres.sql`

| View Name | Purpose |
|---|---|
| `vw_employee_workforce_360` | Unified 360-degree employee table joining all 4 dimensions, 4 facts, and annualized 2026 YTD leave/overtime |
| `vw_department_kpi_summary` | Department headcount, active vs exited, attrition vs target, payroll (INR Cr), budget utilization %, mean tenure, promo gap, overtime |
| `vw_monthly_hiring_and_attrition` | Monthly cohorts (2022–2026) tracking hires, exits, and net headcount delta |
| `vw_high_risk_compensation_pockets` | High performers (`performance_rating >= 4`) facing promotion stagnation (`>= 2.5 yrs`) or below-peer-average raises |
| `vw_data_quality_audit` | Pre-ETL data quality scores and defect counts from `meta_data_quality_metrics` |

## 3. Analytical Query Catalog (38 Queries across 5 Modules)

All analytical queries use portable ANSI SQL (`CTEs`, `RANK()`, `DENSE_RANK()`, `NTILE()`, `LAG()`, `LEAD()`, `SUM() OVER`, `AVG() OVER`, `CASE`, subqueries, conditional aggregation) and run identically on SQLite 3.45+ and PostgreSQL 16 (with `SET search_path TO dw, public;`).

| ID | Query Name | Topic | Source File | Rows |
|---|---|---|---|---:|
| Q01 | `enterprise_workforce_overview` | Workforce Distribution | `01_workforce_hiring_and_tenure.sql` | 1 |
| Q02 | `department_headcount_and_share` | Department-wise Headcount | `01_workforce_hiring_and_tenure.sql` | 8 |
| Q03 | `location_workforce_distribution` | Workforce Distribution | `01_workforce_hiring_and_tenure.sql` | 7 |
| Q04 | `monthly_hiring_trends_with_lag` | Monthly Hiring Trends | `01_workforce_hiring_and_tenure.sql` | 24 |
| Q05 | `quarterly_hiring_vs_exits` | Monthly Hiring Trends | `01_workforce_hiring_and_tenure.sql` | 15 |
| Q06 | `designation_and_employment_type_mix` | Workforce Distribution | `01_workforce_hiring_and_tenure.sql` | 10 |
| Q07 | `tenure_distribution_and_experience_gap` | Employee Tenure | `01_workforce_hiring_and_tenure.sql` | 5 |
| Q08 | `age_demographics_by_department` | Workforce Distribution | `01_workforce_hiring_and_tenure.sql` | 8 |
| Q09 | `department_payroll_and_budget_utilization` | Department Budget Utilization | `02_compensation_and_payroll.sql` | 8 |
| Q10 | `compensation_component_decomposition` | Payroll Expenditure | `02_compensation_and_payroll.sql` | 8 |
| Q11 | `compensation_by_designation` | Compensation Analysis | `02_compensation_and_payroll.sql` | 10 |
| Q12 | `dept_designation_compa_ratio` | Compensation Analysis | `02_compensation_and_payroll.sql` | 25 |
| Q13 | `top_earners_ranked_per_department` | Compensation Analysis | `02_compensation_and_payroll.sql` | 40 |
| Q14 | `below_average_increment_analysis` | Salary Increment Analysis | `02_compensation_and_payroll.sql` | 8 |
| Q15 | `salary_increment_buckets_vs_attrition` | Salary Increment Analysis | `02_compensation_and_payroll.sql` | 4 |
| Q16 | `location_cost_of_living_pay_differential` | Compensation Analysis | `02_compensation_and_payroll.sql` | 7 |
| Q17 | `compensation_anomalies_audit` | Compensation Anomalies | `02_compensation_and_payroll.sql` | 8 |
| Q18 | `department_attrition_vs_target` | Attrition Analysis | `03_attrition_and_retention.sql` | 8 |
| Q19 | `monthly_attrition_trend_rolling` | Attrition Analysis | `03_attrition_and_retention.sql` | 45 |
| Q20 | `exited_vs_active_tenure_and_comp` | Employee Tenure | `03_attrition_and_retention.sql` | 8 |
| Q21 | `attrition_by_tenure_band` | Employee Tenure | `03_attrition_and_retention.sql` | 5 |
| Q22 | `attrition_by_salary_band_and_quintile` | Attrition Analysis | `03_attrition_and_retention.sql` | 5 |
| Q23 | `exit_reasons_ranked_by_department` | Attrition Analysis | `03_attrition_and_retention.sql` | 25 |
| Q24 | `location_designation_attrition_hotspots` | Attrition Analysis | `03_attrition_and_retention.sql` | 15 |
| Q25 | `attrition_payroll_exposure_by_department` | Attrition Analysis | `03_attrition_and_retention.sql` | 8 |
| Q26 | `performance_rating_vs_comp_and_attrition` | Performance Analysis | `04_performance_promotion_training.sql` | 5 |
| Q27 | `manager_vs_performance_alignment_matrix` | Performance Analysis | `04_performance_promotion_training.sql` | 3 |
| Q28 | `promotion_gap_vs_attrition` | Promotion Analysis | `04_performance_promotion_training.sql` | 4 |
| Q29 | `tenured_never_promoted_employees` | Promotion Analysis | `04_performance_promotion_training.sql` | 8 |
| Q30 | `training_effectiveness_analysis` | Training Effectiveness | `04_performance_promotion_training.sql` | 4 |
| Q31 | `high_performer_flight_risk_pockets` | Performance Analysis | `04_performance_promotion_training.sql` | 8 |
| Q32 | `department_promotion_and_training_benchmarks` | Promotion Analysis | `04_performance_promotion_training.sql` | 8 |
| Q33 | `leave_utilization_by_department_and_year` | Leave Utilization | `05_leave_overtime_and_dq.sql` | 24 |
| Q34 | `leave_and_unpaid_leave_vs_attrition` | Leave Utilization | `05_leave_overtime_and_dq.sql` | 4 |
| Q35 | `overtime_concentration_and_burnout_by_dept` | Overtime Analysis | `05_leave_overtime_and_dq.sql` | 8 |
| Q36 | `yoy_overtime_surge_and_attrition` | Overtime Analysis | `05_leave_overtime_and_dq.sql` | 4 |
| Q37 | `sick_leave_vs_overtime_tiers` | Leave Utilization | `05_leave_overtime_and_dq.sql` | 4 |
| Q38 | `data_quality_warehouse_audit` | Compensation Anomalies | `05_leave_overtime_and_dq.sql` | 24 |

## 4. Execution Commands

Execute all 5 SQL views and 38 queries against the SQLite warehouse and regenerate `reports/sql_analytical_findings.md`:

```bash
python -m src.analytics.sql_runner
```

For PostgreSQL 16 (after starting `docker compose up -d` and running Phase 1 with `--backend postgres`):

```bash
psql -h localhost -U analytics_user -d workforce_dw -f sql/analytics/00_views_postgres.sql
```

