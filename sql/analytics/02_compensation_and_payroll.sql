-- =============================================================================
-- Phase 2 SQL Analytics (02): Compensation, Increments, Budget & Anomalies
-- Compatible with SQLite 3.45+ and PostgreSQL 16 (search_path = dw)
-- =============================================================================

-- QUERY_ID: Q09
-- QUERY_NAME: department_payroll_and_budget_utilization
-- TOPIC: Department Budget Utilization
-- BUSINESS_QUESTION: Which departments have the highest payroll expenditure and which exceed annual budget allocations?
-- INTERPRETATION: Compares actual total compensation against dim_department budgets with RANK() and variance status.
WITH dept_budget AS (
    SELECT
        department_name,
        total_employees AS headcount,
        total_payroll_cr,
        annual_budget_cr,
        budget_utilization_pct,
        ROUND(total_payroll_cr - annual_budget_cr, 2) AS variance_cr,
        avg_total_comp_inr
    FROM vw_department_kpi_summary
)
SELECT
    RANK() OVER (ORDER BY total_payroll_cr DESC) AS payroll_rank,
    department_name,
    headcount,
    total_payroll_cr,
    annual_budget_cr,
    variance_cr,
    budget_utilization_pct,
    CASE
        WHEN budget_utilization_pct > 105.0 THEN 'Critical Overrun (>105%)'
        WHEN budget_utilization_pct > 100.0 THEN 'Over Budget (100-105%)'
        ELSE 'Within Budget'
    END AS budget_status,
    avg_total_comp_inr
FROM dept_budget
ORDER BY payroll_rank;

-- QUERY_ID: Q10
-- QUERY_NAME: compensation_component_decomposition
-- TOPIC: Payroll Expenditure
-- BUSINESS_QUESTION: How does total payroll decompose into Basic Salary, Allowances, Bonus, Deductions, and Net Salary per department?
-- INTERPRETATION: Reconciles gross-to-net payroll waterfall across all departments in INR Crores.
SELECT
    d.department_name,
    ROUND(SUM(c.basic_salary) / 10000000.0, 2) AS basic_cr,
    ROUND(SUM(c.allowances) / 10000000.0, 2) AS allowances_cr,
    ROUND(SUM(c.bonus) / 10000000.0, 2) AS bonus_cr,
    ROUND(SUM(c.total_compensation) / 10000000.0, 2) AS gross_total_comp_cr,
    ROUND(SUM(c.deductions) / 10000000.0, 2) AS deductions_cr,
    ROUND(SUM(c.net_salary) / 10000000.0, 2) AS net_salary_cr,
    ROUND(100.0 * SUM(c.bonus) / NULLIF(SUM(c.total_compensation), 0), 2) AS bonus_share_pct,
    ROUND(100.0 * SUM(c.deductions) / NULLIF(SUM(c.total_compensation), 0), 2) AS effective_deduction_pct
FROM dim_department d
JOIN fact_compensation c ON d.department_key = c.department_key
GROUP BY d.department_name
ORDER BY gross_total_comp_cr DESC;

-- QUERY_ID: Q11
-- QUERY_NAME: compensation_by_designation
-- TOPIC: Compensation Analysis
-- BUSINESS_QUESTION: What are the average, minimum, maximum, and variable bonus shares across designations?
-- INTERPRETATION: Benchmarks career-ladder pay progression from Analyst/Software Engineer to VP.
SELECT
    DENSE_RANK() OVER (ORDER BY AVG(c.total_compensation) DESC) AS pay_tier_rank,
    e.designation,
    COUNT(*) AS headcount,
    ROUND(AVG(c.basic_salary), 0) AS avg_basic_inr,
    ROUND(AVG(c.allowances), 0) AS avg_allowances_inr,
    ROUND(AVG(c.bonus), 0) AS avg_bonus_inr,
    ROUND(AVG(c.total_compensation), 0) AS avg_total_comp_inr,
    ROUND(MIN(c.total_compensation), 0) AS min_total_comp_inr,
    ROUND(MAX(c.total_compensation), 0) AS max_total_comp_inr,
    ROUND(100.0 * AVG(c.bonus_to_salary_ratio), 2) AS avg_bonus_to_basic_pct
FROM dim_employee e
JOIN fact_compensation c ON e.employee_key = c.employee_key
GROUP BY e.designation
ORDER BY pay_tier_rank;

-- QUERY_ID: Q12
-- QUERY_NAME: dept_designation_compa_ratio
-- TOPIC: Compensation Analysis
-- BUSINESS_QUESTION: Which department-designation cells pay above or below the company-wide designation average?
-- INTERPRETATION: Computes internal compa-ratio (dept cell avg / company designation avg) using window partitions.
WITH cell_stats AS (
    SELECT
        d.department_name,
        e.designation,
        COUNT(*) AS headcount,
        AVG(c.total_compensation) AS cell_avg_comp
    FROM dim_employee e
    JOIN dim_department d ON e.department_key = d.department_key
    JOIN fact_compensation c ON e.employee_key = c.employee_key
    WHERE e.employment_type <> 'Intern'
    GROUP BY d.department_name, e.designation
    HAVING COUNT(*) >= 15
),
with_benchmark AS (
    SELECT
        department_name,
        designation,
        headcount,
        cell_avg_comp,
        AVG(cell_avg_comp) OVER (PARTITION BY designation) AS designation_mean_comp
    FROM cell_stats
)
SELECT
    department_name,
    designation,
    headcount,
    ROUND(cell_avg_comp, 0) AS dept_desig_avg_comp_inr,
    ROUND(designation_mean_comp, 0) AS company_desig_avg_inr,
    ROUND(100.0 * cell_avg_comp / NULLIF(designation_mean_comp, 0), 1) AS compa_ratio_pct
FROM with_benchmark
ORDER BY compa_ratio_pct DESC
LIMIT 25;

-- QUERY_ID: Q13
-- QUERY_NAME: top_earners_ranked_per_department
-- TOPIC: Compensation Analysis
-- BUSINESS_QUESTION: Who are the top 5 highest-compensated employees in each department and what quartile do they represent?
-- INTERPRETATION: Demonstrates DENSE_RANK() and NTILE(4) partitioned by department for executive compensation review.
WITH ranked AS (
    SELECT
        d.department_name,
        e.employee_id,
        e.designation,
        l.city AS location,
        e.tenure_years,
        c.total_compensation,
        c.net_salary,
        DENSE_RANK() OVER (PARTITION BY d.department_name ORDER BY c.total_compensation DESC) AS dept_rank,
        NTILE(4) OVER (PARTITION BY d.department_name ORDER BY c.total_compensation DESC) AS comp_quartile
    FROM dim_employee e
    JOIN dim_department d ON e.department_key = d.department_key
    JOIN dim_location l ON e.location_key = l.location_key
    JOIN fact_compensation c ON e.employee_key = c.employee_key
)
SELECT
    department_name,
    dept_rank,
    employee_id,
    designation,
    location,
    tenure_years,
    ROUND(total_compensation, 0) AS total_compensation_inr,
    ROUND(net_salary, 0) AS net_salary_inr,
    comp_quartile
FROM ranked
WHERE dept_rank <= 5
ORDER BY department_name, dept_rank, employee_id;

-- QUERY_ID: Q14
-- QUERY_NAME: below_average_increment_analysis
-- TOPIC: Salary Increment Analysis
-- BUSINESS_QUESTION: Which departments have the highest share of eligible staff receiving below-peer-average salary increments?
-- INTERPRETATION: Compares each employee's salary_growth_pct against their Department + Designation peer average via window AVG().
WITH peer_inc AS (
    SELECT
        department_name,
        designation,
        employee_id,
        performance_rating,
        salary_increment,
        salary_growth_pct,
        attrition_flag,
        AVG(salary_growth_pct) OVER (PARTITION BY department_name, designation) AS peer_avg_growth_pct
    FROM vw_employee_workforce_360
    WHERE employment_type <> 'Intern' AND tenure_years >= 1.0
)
SELECT
    department_name,
    COUNT(*) AS eligible_employees,
    SUM(CASE WHEN salary_growth_pct < peer_avg_growth_pct THEN 1 ELSE 0 END) AS below_peer_avg_count,
    ROUND(100.0 * AVG(CASE WHEN salary_growth_pct < peer_avg_growth_pct THEN 1.0 ELSE 0.0 END), 2) AS below_peer_avg_pct,
    ROUND(AVG(CASE WHEN salary_growth_pct < peer_avg_growth_pct THEN attrition_flag END) * 100.0, 2) AS below_avg_attrition_pct,
    ROUND(AVG(CASE WHEN salary_growth_pct >= peer_avg_growth_pct THEN attrition_flag END) * 100.0, 2) AS at_or_above_attrition_pct,
    ROUND(AVG(salary_growth_pct), 2) AS dept_avg_growth_pct
FROM peer_inc
GROUP BY department_name
ORDER BY below_peer_avg_pct DESC;

-- QUERY_ID: Q15
-- QUERY_NAME: salary_increment_buckets_vs_attrition
-- TOPIC: Salary Increment Analysis
-- BUSINESS_QUESTION: How do salary growth brackets relate to retention among eligible full-time/contract employees?
-- INTERPRETATION: Segments salary_growth_pct using CASE brackets to quantify low-increment flight sensitivity.
WITH bucketed AS (
    SELECT
        CASE
            WHEN salary_growth_pct < 4.0 THEN '1. Low (<4%)'
            WHEN salary_growth_pct < 8.0 THEN '2. Moderate (4-8%)'
            WHEN salary_growth_pct < 12.0 THEN '3. Competitive (8-12%)'
            ELSE '4. High (12%+)'
        END AS increment_bucket,
        salary_growth_pct,
        total_compensation,
        attrition_flag
    FROM vw_employee_workforce_360
    WHERE employment_type <> 'Intern' AND tenure_years >= 1.0 AND salary_growth_pct IS NOT NULL
)
SELECT
    increment_bucket,
    COUNT(*) AS employee_count,
    ROUND(AVG(salary_growth_pct), 2) AS avg_growth_pct,
    ROUND(AVG(total_compensation), 0) AS avg_total_comp_inr,
    ROUND(100.0 * AVG(attrition_flag), 2) AS attrition_rate_pct
FROM bucketed
GROUP BY increment_bucket
ORDER BY increment_bucket;

-- QUERY_ID: Q16
-- QUERY_NAME: location_cost_of_living_pay_differential
-- TOPIC: Compensation Analysis
-- BUSINESS_QUESTION: How does average pay vary across office cities and cost-of-living tiers?
-- INTERPRETATION: Compares city pay averages vs overall enterprise average using a scalar subquery benchmark.
SELECT
    l.cost_of_living_tier,
    l.city,
    COUNT(*) AS headcount,
    ROUND(AVG(c.total_compensation), 0) AS avg_total_comp_inr,
    ROUND(
        100.0 * (AVG(c.total_compensation) - (SELECT AVG(total_compensation) FROM fact_compensation))
        / (SELECT AVG(total_compensation) FROM fact_compensation),
        2
    ) AS pct_vs_company_avg,
    ROUND(SUM(c.total_compensation) / 10000000.0, 2) AS total_payroll_cr
FROM dim_employee e
JOIN dim_location l ON e.location_key = l.location_key
JOIN fact_compensation c ON e.employee_key = c.employee_key
GROUP BY l.cost_of_living_tier, l.city
ORDER BY avg_total_comp_inr DESC;

-- QUERY_ID: Q17
-- QUERY_NAME: compensation_anomalies_audit
-- TOPIC: Compensation Anomalies
-- BUSINESS_QUESTION: How many records were flagged as out-of-band salary anomalies during ETL, and where are they concentrated?
-- INTERPRETATION: Audits normalized extreme salary anomalies by department and designation alongside bonus-outlier counts.
SELECT
    d.department_name,
    COUNT(*) AS total_payroll_records,
    SUM(CASE WHEN c.is_salary_anomaly = 1 THEN 1 ELSE 0 END) AS flagged_salary_anomalies,
    ROUND(100.0 * AVG(c.is_salary_anomaly), 3) AS anomaly_rate_pct,
    SUM(CASE WHEN c.bonus_to_salary_ratio > 0.30 THEN 1 ELSE 0 END) AS high_bonus_ratio_cases,
    ROUND(MAX(c.total_compensation), 0) AS max_clean_total_comp_inr
FROM fact_compensation c
JOIN dim_department d ON c.department_key = d.department_key
GROUP BY d.department_name
ORDER BY flagged_salary_anomalies DESC;
