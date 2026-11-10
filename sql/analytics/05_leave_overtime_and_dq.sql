-- =============================================================================
-- Phase 2 SQL Analytics (05): Leave Utilization, Overtime & Data Quality Audit
-- Compatible with SQLite 3.45+ and PostgreSQL 16 (search_path = dw)
-- =============================================================================

-- QUERY_ID: Q33
-- QUERY_NAME: leave_utilization_by_department_and_year
-- TOPIC: Leave Utilization
-- BUSINESS_QUESTION: How do leave types (sick, casual, unpaid) and annualized leave utilization vary by department?
-- INTERPRETATION: Aggregates multi-year fact_leave normalized for 2026 YTD (9-month) scaling.
SELECT
    d.department_name,
    fl.year,
    COUNT(DISTINCT fl.employee_key) AS employee_count,
    ROUND(AVG(fl.sick_leave), 1) AS avg_sick_leave,
    ROUND(AVG(fl.casual_leave), 1) AS avg_casual_leave,
    ROUND(AVG(fl.unpaid_leave), 1) AS avg_unpaid_leave,
    ROUND(AVG(fl.leave_days), 1) AS avg_total_leave_days,
    ROUND(100.0 * AVG(CASE WHEN fl.year = 2026 THEN fl.leave_utilization / 0.75 ELSE fl.leave_utilization END), 1) AS avg_annualized_leave_util_pct
FROM fact_leave fl
JOIN dim_department d ON fl.department_key = d.department_key
GROUP BY d.department_name, fl.year
ORDER BY d.department_name, fl.year;

-- QUERY_ID: Q34
-- QUERY_NAME: leave_and_unpaid_leave_vs_attrition
-- TOPIC: Leave Utilization
-- BUSINESS_QUESTION: Do high-leave and high-unpaid-leave employees exhibit significantly higher attrition?
-- INTERPRETATION: Segments annualized leave utilization and unpaid leave flags against attrition rates.
WITH leave_cohorts AS (
    SELECT
        CASE
            WHEN annualized_leave_days < 12 THEN '1. Low (<12 days/yr)'
            WHEN annualized_leave_days < 20 THEN '2. Normal (12-20 days/yr)'
            WHEN annualized_leave_days < 28 THEN '3. Elevated (20-28 days/yr)'
            ELSE '4. High (28+ days/yr)'
        END AS leave_tier,
        annualized_leave_days,
        unpaid_leave,
        annualized_overtime_hours,
        attrition_flag
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL AND annualized_leave_days IS NOT NULL
)
SELECT
    leave_tier,
    COUNT(*) AS employee_count,
    ROUND(AVG(annualized_leave_days), 1) AS avg_annual_leave_days,
    ROUND(AVG(unpaid_leave), 2) AS avg_unpaid_days,
    ROUND(AVG(annualized_overtime_hours), 1) AS avg_annual_overtime_hrs,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM leave_cohorts
GROUP BY leave_tier
ORDER BY leave_tier;

-- QUERY_ID: Q35
-- QUERY_NAME: overtime_concentration_and_burnout_by_dept
-- TOPIC: Overtime Analysis
-- BUSINESS_QUESTION: Which departments carry the heaviest overtime burden and how does high overtime (>200 hrs/yr) relate to attrition?
-- INTERPRETATION: Uses conditional aggregation to contrast burnout-threshold (>200 hrs) vs normal-overtime attrition.
SELECT
    department_name,
    COUNT(*) AS employee_count,
    ROUND(AVG(annualized_overtime_hours), 1) AS avg_annual_overtime_hrs,
    ROUND(100.0 * AVG(CASE WHEN annualized_overtime_hours >= 200 THEN 1.0 ELSE 0.0 END), 1) AS pct_over_200_hrs,
    ROUND(100.0 * AVG(CASE WHEN annualized_overtime_hours >= 200 THEN attrition_flag END), 2) AS high_ot_attrition_pct,
    ROUND(100.0 * AVG(CASE WHEN annualized_overtime_hours < 200 THEN attrition_flag END), 2) AS normal_ot_attrition_pct
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL AND annualized_overtime_hours IS NOT NULL
GROUP BY department_name
ORDER BY avg_annual_overtime_hrs DESC;

-- QUERY_ID: Q36
-- QUERY_NAME: yoy_overtime_surge_and_attrition
-- TOPIC: Overtime Analysis
-- BUSINESS_QUESTION: Does a sharp year-over-year surge in annualized overtime (+40 hrs or more) correlate with higher attrition?
-- INTERPRETATION: Uses LAG() over fact_leave partitioned by employee_key across 2024-2026 to detect workload escalation.
WITH annual_ot AS (
    SELECT
        fl.employee_key,
        fl.department_key,
        fl.year,
        CASE WHEN fl.year = 2026 THEN ROUND(fl.overtime_hours / 0.75, 1) ELSE fl.overtime_hours END AS ann_ot_hrs
    FROM fact_leave fl
),
ot_with_lag AS (
    SELECT
        employee_key,
        department_key,
        year,
        ann_ot_hrs,
        LAG(ann_ot_hrs, 1) OVER (PARTITION BY employee_key ORDER BY year) AS prev_yr_ot_hrs
    FROM annual_ot
),
latest_surge AS (
    SELECT
        o.employee_key,
        d.department_name,
        o.ann_ot_hrs,
        o.prev_yr_ot_hrs,
        o.ann_ot_hrs - o.prev_yr_ot_hrs AS yoy_ot_delta,
        CASE
            WHEN o.prev_yr_ot_hrs IS NULL THEN '1. First Observation Year'
            WHEN (o.ann_ot_hrs - o.prev_yr_ot_hrs) >= 40.0 THEN '2. Sharp Overtime Surge (+40h)'
            WHEN (o.ann_ot_hrs - o.prev_yr_ot_hrs) <= -40.0 THEN '3. Overtime Relief (-40h)'
            ELSE '4. Stable Overtime'
        END AS ot_trend_segment,
        ROW_NUMBER() OVER (PARTITION BY o.employee_key ORDER BY o.year DESC) AS rn
    FROM ot_with_lag o
    JOIN dim_department d ON o.department_key = d.department_key
)
SELECT
    ls.ot_trend_segment,
    COUNT(*) AS employee_count,
    ROUND(AVG(ls.ann_ot_hrs), 1) AS avg_current_ot_hrs,
    ROUND(AVG(ls.yoy_ot_delta), 1) AS avg_yoy_ot_delta_hrs,
    ROUND(100.0 * AVG(a.attrition_flag), 2) AS attrition_rate_pct
FROM latest_surge ls
JOIN fact_attrition a ON ls.employee_key = a.employee_key
WHERE ls.rn = 1
GROUP BY ls.ot_trend_segment
ORDER BY attrition_rate_pct DESC;

-- QUERY_ID: Q37
-- QUERY_NAME: sick_leave_vs_overtime_tiers
-- TOPIC: Leave Utilization
-- BUSINESS_QUESTION: Do employees working heavy overtime take higher sick leave, compounding exit risk?
-- INTERPRETATION: Tests the relationship between overtime workload bands, sick days, and attrition.
WITH ot_tiers AS (
    SELECT
        CASE
            WHEN annualized_overtime_hours < 80 THEN '1. Low (<80 hrs)'
            WHEN annualized_overtime_hours < 160 THEN '2. Moderate (80-160 hrs)'
            WHEN annualized_overtime_hours < 250 THEN '3. High (160-250 hrs)'
            ELSE '4. Severe (250+ hrs)'
        END AS overtime_tier,
        annualized_overtime_hours,
        sick_leave,
        unpaid_leave,
        attrition_flag
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL AND annualized_overtime_hours IS NOT NULL
)
SELECT
    overtime_tier,
    COUNT(*) AS employee_count,
    ROUND(AVG(annualized_overtime_hours), 1) AS avg_overtime_hrs,
    ROUND(AVG(sick_leave), 2) AS avg_sick_leave_days,
    ROUND(AVG(unpaid_leave), 2) AS avg_unpaid_leave_days,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM ot_tiers
GROUP BY overtime_tier
ORDER BY overtime_tier;

-- QUERY_ID: Q38
-- QUERY_NAME: data_quality_warehouse_audit
-- TOPIC: Compensation Anomalies
-- BUSINESS_QUESTION: What were the pre-ETL data quality dimension scores and defect volumes persisted in the warehouse?
-- INTERPRETATION: Surfaces Data Quality audit metrics directly from vw_data_quality_audit for governance reporting.
SELECT
    metric_category,
    metric_name,
    metric_value,
    assessed_at_utc
FROM vw_data_quality_audit
ORDER BY metric_category DESC, metric_id;

