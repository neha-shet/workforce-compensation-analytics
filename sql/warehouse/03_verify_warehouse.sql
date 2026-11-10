-- =============================================================================
-- Warehouse Integrity & Sanity Verification Queries
-- =============================================================================

-- 1. Row counts per star schema table
SELECT 'dim_department' AS table_name, COUNT(*) AS row_count FROM dim_department
UNION ALL
SELECT 'dim_location', COUNT(*) FROM dim_location
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date
UNION ALL
SELECT 'dim_employee', COUNT(*) FROM dim_employee
UNION ALL
SELECT 'fact_compensation', COUNT(*) FROM fact_compensation
UNION ALL
SELECT 'fact_leave', COUNT(*) FROM fact_leave
UNION ALL
SELECT 'fact_performance', COUNT(*) FROM fact_performance
UNION ALL
SELECT 'fact_attrition', COUNT(*) FROM fact_attrition
UNION ALL
SELECT 'meta_data_quality_metrics', COUNT(*) FROM meta_data_quality_metrics;

-- 2. Executive KPI Sanity Check
SELECT
    COUNT(DISTINCT e.employee_key) AS total_employees,
    ROUND(SUM(c.total_compensation) / 10000000.0, 2) AS total_payroll_inr_cr,
    ROUND(AVG(c.total_compensation), 0) AS avg_total_comp_inr,
    ROUND(100.0 * AVG(a.attrition_flag), 2) AS attrition_rate_pct,
    ROUND(AVG(e.tenure_years), 2) AS avg_tenure_years
FROM dim_employee e
LEFT JOIN fact_compensation c ON e.employee_key = c.employee_key
LEFT JOIN fact_attrition a ON e.employee_key = a.employee_key;

-- 3. Net Salary Reconciliation Check (should return 0 rows)
SELECT COUNT(*) AS net_salary_discrepancy_count
FROM fact_compensation
WHERE ABS(net_salary - (basic_salary + allowances + bonus - deductions)) > 1.0;

