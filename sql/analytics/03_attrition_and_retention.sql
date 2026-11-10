-- =============================================================================
-- Phase 2 SQL Analytics (03): Attrition, Tenure & Retention Risk Analysis
-- Compatible with SQLite 3.45+ and PostgreSQL 16 (search_path = dw)
-- =============================================================================

-- QUERY_ID: Q18
-- QUERY_NAME: department_attrition_vs_target
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: Which departments have the highest attrition rates relative to their target attrition benchmarks?
-- INTERPRETATION: Ranks departments by actual attrition excess above target_attrition_pct to prioritize intervention.
SELECT
    RANK() OVER (ORDER BY attrition_rate_pct DESC) AS attrition_rank,
    department_name,
    total_employees,
    exited_employees,
    attrition_rate_pct,
    target_attrition_pct,
    ROUND(attrition_rate_pct - target_attrition_pct, 2) AS excess_vs_target_pct,
    CASE
        WHEN attrition_rate_pct - target_attrition_pct >= 3.0 THEN 'High Risk Hotspot'
        WHEN attrition_rate_pct > target_attrition_pct THEN 'Above Target'
        ELSE 'On / Below Target'
    END AS attrition_status
FROM vw_department_kpi_summary
ORDER BY attrition_rank;

-- QUERY_ID: Q19
-- QUERY_NAME: monthly_attrition_trend_rolling
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: What is the monthly exit volume and 3-month rolling average across 2023-2026?
-- INTERPRETATION: Uses LAG() and sliding window AVG() OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) to smooth exit seasonality.
WITH m_exits AS (
    SELECT
        year_month,
        exits_count,
        hires_count
    FROM vw_monthly_hiring_and_attrition
    WHERE year_month >= '2023-01'
)
SELECT
    year_month,
    exits_count,
    LAG(exits_count, 1) OVER (ORDER BY year_month) AS prev_month_exits,
    ROUND(
        AVG(exits_count) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW),
        1
    ) AS rolling_3m_avg_exits,
    hires_count
FROM m_exits
ORDER BY year_month;

-- QUERY_ID: Q20
-- QUERY_NAME: exited_vs_active_tenure_and_comp
-- TOPIC: Employee Tenure
-- BUSINESS_QUESTION: What is the average tenure and compensation of exited employees compared to active staff across departments?
-- INTERPRETATION: Uses conditional aggregation across attrition_flag=1 vs attrition_flag=0 cohorts.
SELECT
    department_name,
    ROUND(AVG(CASE WHEN attrition_flag = 1 THEN tenure_years END), 2) AS avg_exited_tenure_yrs,
    ROUND(AVG(CASE WHEN attrition_flag = 0 THEN tenure_years END), 2) AS avg_active_tenure_yrs,
    ROUND(AVG(CASE WHEN attrition_flag = 1 THEN total_compensation END), 0) AS avg_exited_comp_inr,
    ROUND(AVG(CASE WHEN attrition_flag = 0 THEN total_compensation END), 0) AS avg_active_comp_inr,
    ROUND(AVG(CASE WHEN attrition_flag = 1 THEN promotion_gap END), 2) AS avg_exited_promo_gap_yrs,
    ROUND(AVG(CASE WHEN attrition_flag = 0 THEN promotion_gap END), 2) AS avg_active_promo_gap_yrs
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL
GROUP BY department_name
ORDER BY avg_exited_tenure_yrs;

-- QUERY_ID: Q21
-- QUERY_NAME: attrition_by_tenure_band
-- TOPIC: Employee Tenure
-- BUSINESS_QUESTION: Which tenure bands exhibit the sharpest attrition concentration?
-- INTERPRETATION: Evaluates retention curves across <1 yr, 1-3 yrs, 3-5 yrs, 5-10 yrs, and 10+ yrs cohorts.
SELECT
    tenure_band,
    COUNT(*) AS total_employees,
    SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_employees,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) / SUM(SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END)) OVER (), 2) AS share_of_total_exits_pct,
    ROUND(AVG(tenure_years), 2) AS avg_tenure_years
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL
GROUP BY tenure_band
ORDER BY avg_tenure_years;

-- QUERY_ID: Q22
-- QUERY_NAME: attrition_by_salary_band_and_quintile
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: How does attrition vary across salary bands and within-company compensation quintiles?
-- INTERPRETATION: Uses NTILE(5) compensation quintiles to assess retention sensitivity across pay levels.
WITH comp_quintiles AS (
    SELECT
        employee_id,
        salary_band,
        total_compensation,
        salary_growth_pct,
        attrition_flag,
        NTILE(5) OVER (ORDER BY total_compensation) AS pay_quintile
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL AND total_compensation IS NOT NULL
)
SELECT
    pay_quintile,
    COUNT(*) AS employee_count,
    ROUND(MIN(total_compensation), 0) AS min_comp_inr,
    ROUND(MAX(total_compensation), 0) AS max_comp_inr,
    ROUND(AVG(total_compensation), 0) AS avg_comp_inr,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM comp_quintiles
GROUP BY pay_quintile
ORDER BY pay_quintile;

-- QUERY_ID: Q23
-- QUERY_NAME: exit_reasons_ranked_by_department
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: What are the top exit reasons overall and within each department?
-- INTERPRETATION: Uses DENSE_RANK() partitioned by department to identify whether Compensation, Career Growth, or Work-Life Balance dominates.
WITH reason_counts AS (
    SELECT
        department_name,
        exit_reason,
        COUNT(*) AS exit_count
    FROM vw_employee_workforce_360
    WHERE attrition_flag = 1 AND exit_reason IS NOT NULL
    GROUP BY department_name, exit_reason
),
ranked_reasons AS (
    SELECT
        department_name,
        exit_reason,
        exit_count,
        ROUND(100.0 * exit_count / SUM(exit_count) OVER (PARTITION BY department_name), 1) AS dept_exit_share_pct,
        DENSE_RANK() OVER (PARTITION BY department_name ORDER BY exit_count DESC) AS reason_rank
    FROM reason_counts
)
SELECT
    department_name,
    reason_rank,
    exit_reason,
    exit_count,
    dept_exit_share_pct
FROM ranked_reasons
WHERE reason_rank <= 3
ORDER BY department_name, reason_rank;

-- QUERY_ID: Q24
-- QUERY_NAME: location_designation_attrition_hotspots
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: Which department-designation combinations experience the highest attrition rates (min 50 headcount)?
-- INTERPRETATION: Pinpoints specific organizational roles driving elevated turnover.
SELECT
    RANK() OVER (ORDER BY AVG(attrition_flag) DESC) AS hotspot_rank,
    department_name,
    designation,
    COUNT(*) AS headcount,
    SUM(CASE WHEN attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_count,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct,
    ROUND(AVG(promotion_gap), 2) AS avg_promo_gap_yrs,
    ROUND(AVG(annualized_overtime_hours), 1) AS avg_overtime_hrs
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL
GROUP BY department_name, designation
HAVING COUNT(*) >= 50
ORDER BY hotspot_rank
LIMIT 15;

-- QUERY_ID: Q25
-- QUERY_NAME: attrition_payroll_exposure_by_department
-- TOPIC: Attrition Analysis
-- BUSINESS_QUESTION: What is the cumulative annual compensation base associated with exited employees by department?
-- INTERPRETATION: Quantifies total compensation turnover exposure (INR Cr) across departments.
SELECT
    d.department_name,
    SUM(CASE WHEN a.attrition_flag = 1 THEN 1 ELSE 0 END) AS exited_headcount,
    ROUND(SUM(CASE WHEN a.attrition_flag = 1 THEN a.last_total_compensation ELSE 0 END) / 10000000.0, 2) AS exited_comp_base_cr,
    ROUND(
        100.0 * SUM(CASE WHEN a.attrition_flag = 1 THEN a.last_total_compensation ELSE 0 END)
        / NULLIF(SUM(a.last_total_compensation), 0),
        2
    ) AS pct_of_dept_comp_turned_over,
    ROUND(AVG(CASE WHEN a.attrition_flag = 1 THEN a.last_total_compensation END), 0) AS avg_exited_comp_inr
FROM fact_attrition a
JOIN dim_department d ON a.department_key = d.department_key
GROUP BY d.department_name
ORDER BY exited_comp_base_cr DESC;

