-- =============================================================================
-- Reusable Analytical SQL Views (PostgreSQL 16 Warehouse - dw schema)
-- =============================================================================

SET search_path TO dw, public;

DROP VIEW IF EXISTS dw.vw_data_quality_audit CASCADE;
DROP VIEW IF EXISTS dw.vw_high_risk_compensation_pockets CASCADE;
DROP VIEW IF EXISTS dw.vw_monthly_hiring_and_attrition CASCADE;
DROP VIEW IF EXISTS dw.vw_department_kpi_summary CASCADE;
DROP VIEW IF EXISTS dw.vw_employee_workforce_360 CASCADE;

CREATE OR REPLACE VIEW dw.vw_employee_workforce_360 AS
WITH latest_leave AS (
    SELECT
        fl.*,
        CASE WHEN fl.year = 2026 THEN ROUND((fl.leave_days / 0.75)::numeric, 1) ELSE fl.leave_days END AS annualized_leave_days,
        CASE WHEN fl.year = 2026 THEN ROUND((fl.overtime_hours / 0.75)::numeric, 1) ELSE fl.overtime_hours END AS annualized_overtime_hours,
        ROW_NUMBER() OVER (PARTITION BY fl.employee_key ORDER BY fl.year DESC) AS rn
    FROM dw.fact_leave fl
)
SELECT
    e.employee_key,
    e.employee_id,
    d.department_name,
    d.department_head_function,
    d.annual_budget_inr,
    d.target_attrition_pct,
    l.city AS location,
    l.region,
    l.cost_of_living_tier,
    e.designation,
    e.employment_type,
    e.education,
    e.age_years,
    e.joining_date,
    e.experience_years,
    e.tenure_years,
    e.tenure_band,
    e.is_active,
    c.basic_salary,
    c.allowances,
    c.bonus,
    c.deductions,
    c.net_salary,
    c.total_compensation,
    c.salary_increment,
    c.salary_growth_pct,
    c.bonus_to_salary_ratio,
    c.salary_band,
    c.is_salary_anomaly,
    p.performance_rating,
    p.manager_rating,
    p.promotion_count,
    p.training_hours,
    p.promotion_gap,
    ll.year AS latest_leave_year,
    ll.leave_days,
    ll.sick_leave,
    ll.casual_leave,
    ll.unpaid_leave,
    ll.overtime_hours,
    ll.annualized_leave_days,
    ll.annualized_overtime_hours,
    ll.leave_utilization,
    ll.overtime_ratio,
    a.attrition_flag,
    a.exit_reason,
    ed.full_date AS exit_date
FROM dw.dim_employee e
JOIN dw.dim_department d ON e.department_key = d.department_key
JOIN dw.dim_location l ON e.location_key = l.location_key
LEFT JOIN dw.fact_compensation c ON e.employee_key = c.employee_key
LEFT JOIN dw.fact_performance p ON e.employee_key = p.employee_key
LEFT JOIN latest_leave ll ON e.employee_key = ll.employee_key AND ll.rn = 1
LEFT JOIN dw.fact_attrition a ON e.employee_key = a.employee_key
LEFT JOIN dw.dim_date ed ON a.exit_date_key = ed.date_key;

CREATE OR REPLACE VIEW dw.vw_department_kpi_summary AS
SELECT
    department_name,
    department_head_function,
    COUNT(*) AS total_employees,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_employees,
    SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_employees,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct,
    MAX(target_attrition_pct) AS target_attrition_pct,
    ROUND(SUM(total_compensation) / 10000000.0, 2) AS total_payroll_cr,
    ROUND(MAX(annual_budget_inr) / 10000000.0, 2) AS annual_budget_cr,
    ROUND(100.0 * SUM(total_compensation) / NULLIF(MAX(annual_budget_inr), 0), 2) AS budget_utilization_pct,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct,
    ROUND(AVG(tenure_years), 2) AS avg_tenure_years,
    ROUND(AVG(promotion_gap), 2) AS avg_promotion_gap_years,
    ROUND(AVG(annualized_overtime_hours), 1) AS avg_annualized_overtime_hrs
FROM dw.vw_employee_workforce_360
GROUP BY department_name, department_head_function;

CREATE OR REPLACE VIEW dw.vw_monthly_hiring_and_attrition AS
WITH hires AS (
    SELECT TO_CHAR(joining_date, 'YYYY-MM') AS year_month, COUNT(*) AS hires_count
    FROM dw.dim_employee
    WHERE joining_date >= DATE '2022-01-01'
    GROUP BY TO_CHAR(joining_date, 'YYYY-MM')
),
exits AS (
    SELECT TO_CHAR(dt.full_date, 'YYYY-MM') AS year_month, COUNT(*) AS exits_count
    FROM dw.fact_attrition a
    JOIN dw.dim_date dt ON a.exit_date_key = dt.date_key
    WHERE a.attrition_flag = 1
    GROUP BY TO_CHAR(dt.full_date, 'YYYY-MM')
),
months AS (
    SELECT DISTINCT TO_CHAR(full_date, 'YYYY-MM') AS year_month
    FROM dw.dim_date
    WHERE full_date BETWEEN DATE '2022-01-01' AND DATE '2026-09-30'
)
SELECT
    m.year_month,
    COALESCE(h.hires_count, 0) AS hires_count,
    COALESCE(ex.exits_count, 0) AS exits_count,
    COALESCE(h.hires_count, 0) - COALESCE(ex.exits_count, 0) AS net_headcount_change
FROM months m
LEFT JOIN hires h ON m.year_month = h.year_month
LEFT JOIN exits ex ON m.year_month = ex.year_month
ORDER BY m.year_month;

CREATE OR REPLACE VIEW dw.vw_high_risk_compensation_pockets AS
WITH peer AS (
    SELECT
        employee_id, department_name, designation, location, tenure_years,
        performance_rating, manager_rating, promotion_gap, total_compensation,
        salary_growth_pct, annualized_overtime_hours, attrition_flag,
        AVG(salary_growth_pct) OVER (PARTITION BY department_name, designation) AS peer_avg_growth_pct
    FROM dw.vw_employee_workforce_360
    WHERE employment_type <> 'Intern' AND tenure_years >= 1.0
)
SELECT *, ROUND((salary_growth_pct - peer_avg_growth_pct)::numeric, 2) AS growth_vs_peer_pct
FROM peer
WHERE performance_rating >= 4
  AND (promotion_gap >= 2.5 OR salary_growth_pct < peer_avg_growth_pct);

CREATE OR REPLACE VIEW dw.vw_data_quality_audit AS
SELECT metric_id, metric_category, metric_name, metric_value, assessed_at_utc
FROM dw.meta_data_quality_metrics;

