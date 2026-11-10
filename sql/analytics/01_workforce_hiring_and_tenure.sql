-- =============================================================================
-- Phase 2 SQL Analytics (01): Workforce Distribution, Hiring Trends & Tenure
-- Compatible with SQLite 3.45+ and PostgreSQL 16 (search_path = dw)
-- =============================================================================

-- QUERY_ID: Q01
-- QUERY_NAME: enterprise_workforce_overview
-- TOPIC: Workforce Distribution
-- BUSINESS_QUESTION: What are the top-level synthetic enterprise workforce, payroll, attrition, and tenure KPIs?
-- INTERPRETATION: Establishes baseline executive metrics across the 24,953 clean employee records in the warehouse.
SELECT
    COUNT(*) AS total_employees,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_employees,
    SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_employees,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct,
    ROUND(SUM(total_compensation) / 10000000.0, 2) AS total_payroll_cr,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(AVG(tenure_years), 2) AS avg_tenure_years,
    ROUND(AVG(age_years), 1) AS avg_age_years
FROM vw_employee_workforce_360;

-- QUERY_ID: Q02
-- QUERY_NAME: department_headcount_and_share
-- TOPIC: Department-wise Headcount
-- BUSINESS_QUESTION: How is headcount distributed across departments and what percentage share does each represent?
-- INTERPRETATION: Uses window SUM() OVER() to compute exact workforce share alongside active vs exited breakdown.
WITH dept_counts AS (
    SELECT
        department_name,
        department_head_function,
        COUNT(*) AS total_headcount,
        SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_headcount,
        SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_headcount
    FROM vw_employee_workforce_360
    GROUP BY department_name, department_head_function
)
SELECT
    DENSE_RANK() OVER (ORDER BY total_headcount DESC) AS size_rank,
    department_name,
    department_head_function,
    total_headcount,
    active_headcount,
    exited_headcount,
    ROUND(100.0 * total_headcount / SUM(total_headcount) OVER (), 2) AS workforce_share_pct
FROM dept_counts
ORDER BY size_rank;

-- QUERY_ID: Q03
-- QUERY_NAME: location_workforce_distribution
-- TOPIC: Workforce Distribution
-- BUSINESS_QUESTION: Which office locations concentrate the workforce and how do they rank by active headcount and pay?
-- INTERPRETATION: Evaluates geographic footprint across Indian hubs and regional tiers.
SELECT
    RANK() OVER (ORDER BY COUNT(*) DESC) AS location_rank,
    location,
    region,
    cost_of_living_tier,
    COUNT(*) AS total_employees,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_employees,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS headcount_share_pct,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM vw_employee_workforce_360
GROUP BY location, region, cost_of_living_tier
ORDER BY location_rank;

-- QUERY_ID: Q04
-- QUERY_NAME: monthly_hiring_trends_with_lag
-- TOPIC: Monthly Hiring Trends
-- BUSINESS_QUESTION: How have monthly hiring volumes evolved since 2022 and what is the month-over-month momentum?
-- INTERPRETATION: Uses LAG() and cumulative window SUM() to track hiring velocity and net headcount expansion.
WITH monthly AS (
    SELECT
        year_month,
        hires_count,
        exits_count,
        net_headcount_change
    FROM vw_monthly_hiring_and_attrition
)
SELECT
    year_month,
    hires_count,
    LAG(hires_count, 1) OVER (ORDER BY year_month) AS prev_month_hires,
    hires_count - COALESCE(LAG(hires_count, 1) OVER (ORDER BY year_month), hires_count) AS mom_hire_delta,
    exits_count,
    net_headcount_change,
    SUM(hires_count) OVER (ORDER BY year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_hires
FROM monthly
ORDER BY year_month DESC
LIMIT 24;

-- QUERY_ID: Q05
-- QUERY_NAME: quarterly_hiring_vs_exits
-- TOPIC: Monthly Hiring Trends
-- BUSINESS_QUESTION: What is the quarterly hiring, attrition, and net growth trajectory across 2023-2026?
-- INTERPRETATION: Joins dim_date directly for fiscal/calendar quarter aggregation with LEAD() next-quarter comparison.
WITH hired_q AS (
    SELECT
        dt.year,
        dt.quarter,
        COUNT(*) AS hires
    FROM dim_employee e
    JOIN dim_date dt ON e.joining_date = dt.full_date
    WHERE dt.year >= 2023
    GROUP BY dt.year, dt.quarter
),
exited_q AS (
    SELECT
        dt.year,
        dt.quarter,
        COUNT(*) AS exits
    FROM fact_attrition a
    JOIN dim_date dt ON a.exit_date_key = dt.date_key
    WHERE a.attrition_flag = 1 AND dt.year >= 2023
    GROUP BY dt.year, dt.quarter
)
SELECT
    h.year,
    h.quarter,
    h.hires,
    COALESCE(ex.exits, 0) AS exits,
    h.hires - COALESCE(ex.exits, 0) AS net_change,
    LEAD(h.hires, 1) OVER (ORDER BY h.year, h.quarter) AS next_quarter_hires
FROM hired_q h
LEFT JOIN exited_q ex ON h.year = ex.year AND h.quarter = ex.quarter
ORDER BY h.year, h.quarter;

-- QUERY_ID: Q06
-- QUERY_NAME: designation_and_employment_type_mix
-- TOPIC: Workforce Distribution
-- BUSINESS_QUESTION: What is the workforce pyramid by designation and employment type?
-- INTERPRETATION: Uses conditional aggregation across Full-Time, Contract, and Intern cohorts per seniority level.
SELECT
    designation,
    COUNT(*) AS total_employees,
    SUM(CASE WHEN employment_type = 'Full-Time' THEN 1 ELSE 0 END) AS full_time_count,
    SUM(CASE WHEN employment_type = 'Contract' THEN 1 ELSE 0 END) AS contract_count,
    SUM(CASE WHEN employment_type = 'Intern' THEN 1 ELSE 0 END) AS intern_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct,
    ROUND(AVG(experience_years), 1) AS avg_experience_years
FROM vw_employee_workforce_360
GROUP BY designation
ORDER BY AVG(total_compensation) DESC;

-- QUERY_ID: Q07
-- QUERY_NAME: tenure_distribution_and_experience_gap
-- TOPIC: Employee Tenure
-- BUSINESS_QUESTION: How is the workforce distributed across tenure bands and how does internal tenure compare to total experience?
-- INTERPRETATION: Distinguishes early-tenure employees from veteran staff and quantifies prior external experience.
SELECT
    tenure_band,
    COUNT(*) AS employee_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS share_pct,
    ROUND(AVG(tenure_years), 2) AS avg_tenure_years,
    ROUND(AVG(experience_years), 2) AS avg_total_experience_years,
    ROUND(AVG(experience_years - tenure_years), 2) AS avg_prior_experience_years,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr
FROM vw_employee_workforce_360
GROUP BY tenure_band
ORDER BY avg_tenure_years;

-- QUERY_ID: Q08
-- QUERY_NAME: age_demographics_by_department
-- TOPIC: Workforce Distribution
-- BUSINESS_QUESTION: What are the age demographics and education mix across departments?
-- INTERPRETATION: Uses CASE age cohorts and conditional aggregation to inspect talent maturity across functions.
SELECT
    department_name,
    COUNT(*) AS headcount,
    ROUND(AVG(age_years), 1) AS avg_age,
    ROUND(100.0 * AVG(CASE WHEN age_years < 28 THEN 1.0 ELSE 0.0 END), 1) AS pct_under_28,
    ROUND(100.0 * AVG(CASE WHEN age_years BETWEEN 28 AND 38 THEN 1.0 ELSE 0.0 END), 1) AS pct_28_to_38,
    ROUND(100.0 * AVG(CASE WHEN age_years > 38 THEN 1.0 ELSE 0.0 END), 1) AS pct_over_38,
    ROUND(100.0 * AVG(CASE WHEN education IN ('MBA', 'M.Tech', 'M.Sc', 'PhD') THEN 1.0 ELSE 0.0 END), 1) AS pct_postgrad
FROM vw_employee_workforce_360
GROUP BY department_name
ORDER BY avg_age DESC;

