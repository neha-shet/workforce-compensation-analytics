-- =============================================================================
-- Phase 2 SQL Analytics (04): Performance, Promotion & Training Effectiveness
-- Compatible with SQLite 3.45+ and PostgreSQL 16 (search_path = dw)
-- =============================================================================

-- QUERY_ID: Q26
-- QUERY_NAME: performance_rating_vs_comp_and_attrition
-- TOPIC: Performance Analysis
-- BUSINESS_QUESTION: Does performance rating correlate with compensation growth, bonus ratio, and attrition?
-- INTERPRETATION: Tests pay-for-performance alignment across ratings 1 through 5.
SELECT
    performance_rating,
    COUNT(*) AS employee_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS workforce_share_pct,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct,
    ROUND(100.0 * AVG(bonus_to_salary_ratio), 2) AS avg_bonus_to_basic_pct,
    ROUND(AVG(promotion_count), 2) AS avg_promotions,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL
GROUP BY performance_rating
ORDER BY performance_rating;

-- QUERY_ID: Q27
-- QUERY_NAME: manager_vs_performance_alignment_matrix
-- TOPIC: Performance Analysis
-- BUSINESS_QUESTION: How does alignment (or gap) between manager rating and performance rating impact attrition?
-- INTERPRETATION: Uses CASE classification to detect manager-employee appraisal friction.
WITH alignment AS (
    SELECT
        CASE
            WHEN manager_rating <= 2 AND performance_rating >= 4 THEN 'High Performer / Low Manager Score'
            WHEN manager_rating <= 2 THEN 'Low Manager Rating (<=2)'
            WHEN performance_rating >= 4 AND manager_rating >= 4 THEN 'Aligned Top Talent (4-5)'
            ELSE 'Standard Alignment'
        END AS rating_segment,
        attrition_flag,
        salary_growth_pct,
        promotion_gap
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL
)
SELECT
    rating_segment,
    COUNT(*) AS employee_count,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct,
    ROUND(AVG(promotion_gap), 2) AS avg_promo_gap_yrs,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM alignment
GROUP BY rating_segment
ORDER BY attrition_rate_pct DESC;

-- QUERY_ID: Q28
-- QUERY_NAME: promotion_gap_vs_attrition
-- TOPIC: Promotion Analysis
-- BUSINESS_QUESTION: How strongly does promotion gap affect attrition overall and within Engineering?
-- INTERPRETATION: Quantifies attrition escalation when promotion_gap exceeds 2.5 and 4.0 years.
WITH pg_buckets AS (
    SELECT
        CASE
            WHEN promotion_gap <= 1.5 THEN '1. <= 1.5 yrs'
            WHEN promotion_gap <= 2.5 THEN '2. 1.5 - 2.5 yrs'
            WHEN promotion_gap <= 4.0 THEN '3. 2.5 - 4.0 yrs'
            ELSE '4. > 4.0 yrs'
        END AS promotion_gap_bucket,
        department_name,
        attrition_flag,
        salary_growth_pct
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL
)
SELECT
    promotion_gap_bucket,
    COUNT(*) AS total_employees,
    ROUND(100.0 * AVG(attrition_flag), 2) AS overall_attrition_pct,
    ROUND(100.0 * AVG(CASE WHEN department_name = 'Engineering' THEN attrition_flag END), 2) AS engineering_attrition_pct,
    ROUND(100.0 * AVG(CASE WHEN department_name = 'Operations' THEN attrition_flag END), 2) AS operations_attrition_pct,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct
FROM pg_buckets
GROUP BY promotion_gap_bucket
ORDER BY promotion_gap_bucket;

-- QUERY_ID: Q29
-- QUERY_NAME: tenured_never_promoted_employees
-- TOPIC: Promotion Analysis
-- BUSINESS_QUESTION: How many tenured employees (3+ years) have zero promotions across departments, and what is their attrition rate?
-- INTERPRETATION: Identifies career-progression bottlenecks using conditional aggregation.
SELECT
    department_name,
    COUNT(*) AS tenured_3plus_count,
    SUM(CASE WHEN promotion_count = 0 THEN 1 ELSE 0 END) AS zero_promotion_count,
    ROUND(100.0 * AVG(CASE WHEN promotion_count = 0 THEN 1.0 ELSE 0.0 END), 2) AS pct_never_promoted,
    ROUND(100.0 * AVG(CASE WHEN promotion_count = 0 THEN attrition_flag END), 2) AS never_promoted_attrition_pct,
    ROUND(100.0 * AVG(CASE WHEN promotion_count > 0 THEN attrition_flag END), 2) AS promoted_attrition_pct
FROM vw_employee_workforce_360
WHERE tenure_years >= 3.0 AND attrition_flag IS NOT NULL
GROUP BY department_name
ORDER BY never_promoted_attrition_pct DESC;

-- QUERY_ID: Q30
-- QUERY_NAME: training_effectiveness_analysis
-- TOPIC: Training Effectiveness
-- BUSINESS_QUESTION: Are higher annual training hours associated with stronger performance ratings, more promotions, and lower attrition?
-- INTERPRETATION: Segments training_hours into 4 investment tiers to inspect retention and career outcomes.
WITH training_tiers AS (
    SELECT
        CASE
            WHEN training_hours < 20 THEN '1. Low (<20 hrs)'
            WHEN training_hours < 35 THEN '2. Moderate (20-35 hrs)'
            WHEN training_hours < 50 THEN '3. High (35-50 hrs)'
            ELSE '4. Intensive (50+ hrs)'
        END AS training_tier,
        training_hours,
        performance_rating,
        promotion_count,
        salary_growth_pct,
        attrition_flag
    FROM vw_employee_workforce_360
    WHERE attrition_flag IS NOT NULL
)
SELECT
    training_tier,
    COUNT(*) AS employee_count,
    ROUND(AVG(training_hours), 1) AS avg_training_hrs,
    ROUND(AVG(performance_rating), 2) AS avg_perf_rating,
    ROUND(AVG(promotion_count), 2) AS avg_promotions,
    ROUND(AVG(salary_growth_pct), 2) AS avg_salary_growth_pct,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM training_tiers
GROUP BY training_tier
ORDER BY training_tier;

-- QUERY_ID: Q31
-- QUERY_NAME: high_performer_flight_risk_pockets
-- TOPIC: Performance Analysis
-- BUSINESS_QUESTION: Which departments hold the largest pockets of high-performing employees facing promotion stagnation or below-peer raises?
-- INTERPRETATION: Queries reusable view vw_high_risk_compensation_pockets to quantify critical talent at risk.
SELECT
    department_name,
    COUNT(*) AS high_perf_at_risk_count,
    ROUND(AVG(promotion_gap), 2) AS avg_promo_gap_yrs,
    ROUND(AVG(growth_vs_peer_pct), 2) AS avg_growth_vs_peer_pct,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(100.0 * AVG(attrition_flag), 2) AS observed_attrition_pct
FROM vw_high_risk_compensation_pockets
WHERE attrition_flag IS NOT NULL
GROUP BY department_name
ORDER BY high_perf_at_risk_count DESC;

-- QUERY_ID: Q32
-- QUERY_NAME: department_promotion_and_training_benchmarks
-- TOPIC: Promotion Analysis
-- BUSINESS_QUESTION: How do departments compare on average promotion counts, promotion gaps, and training hours per employee?
-- INTERPRETATION: Benchmarks career mobility and L&D investment across departments with RANK().
SELECT
    RANK() OVER (ORDER BY AVG(promotion_gap) DESC) AS stagnation_rank,
    department_name,
    ROUND(AVG(promotion_count), 2) AS avg_promotions,
    ROUND(AVG(promotion_gap), 2) AS avg_promotion_gap_yrs,
    ROUND(AVG(training_hours), 1) AS avg_training_hours,
    ROUND(AVG(performance_rating), 2) AS avg_perf_rating,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM vw_employee_workforce_360
WHERE attrition_flag IS NOT NULL
GROUP BY department_name
ORDER BY stagnation_rank;

