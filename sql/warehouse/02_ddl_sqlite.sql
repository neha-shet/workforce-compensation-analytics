-- =============================================================================
-- Workforce & Compensation Analytics Engine
-- SQLite Dimensional Star Schema DDL (Local Analytical Mirror)
-- =============================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS meta_data_quality_metrics;
DROP TABLE IF EXISTS fact_attrition;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_leave;
DROP TABLE IF EXISTS fact_compensation;
DROP TABLE IF EXISTS dim_employee;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_location;
DROP TABLE IF EXISTS dim_department;

CREATE TABLE dim_department (
    department_key           INTEGER PRIMARY KEY,
    department_name          TEXT NOT NULL UNIQUE,
    department_head_function TEXT NOT NULL,
    annual_budget_inr        REAL NOT NULL CHECK (annual_budget_inr >= 0),
    target_attrition_pct     REAL NOT NULL CHECK (target_attrition_pct >= 0)
);

CREATE TABLE dim_location (
    location_key             INTEGER PRIMARY KEY,
    city                     TEXT NOT NULL UNIQUE,
    region                   TEXT NOT NULL,
    country                  TEXT NOT NULL,
    cost_of_living_tier      TEXT NOT NULL
);

CREATE TABLE dim_date (
    date_key                 INTEGER PRIMARY KEY,
    full_date                TEXT NOT NULL UNIQUE,
    year                     INTEGER NOT NULL,
    quarter                  INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month                    INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name               TEXT NOT NULL,
    day_of_week              TEXT NOT NULL,
    fiscal_year              TEXT NOT NULL,
    is_weekend               INTEGER NOT NULL CHECK (is_weekend IN (0, 1))
);

CREATE TABLE dim_employee (
    employee_key             INTEGER PRIMARY KEY,
    employee_id              TEXT NOT NULL UNIQUE,
    department_key           INTEGER NOT NULL REFERENCES dim_department(department_key),
    location_key             INTEGER NOT NULL REFERENCES dim_location(location_key),
    designation              TEXT NOT NULL,
    employment_type          TEXT NOT NULL,
    education                TEXT NOT NULL,
    date_of_birth            TEXT NOT NULL,
    age_years                REAL NOT NULL,
    joining_date             TEXT NOT NULL,
    experience_years         REAL NOT NULL CHECK (experience_years >= 0),
    tenure_years             REAL NOT NULL CHECK (tenure_years >= 0),
    tenure_band              TEXT NOT NULL,
    is_active                INTEGER NOT NULL CHECK (is_active IN (0, 1))
);

CREATE TABLE fact_compensation (
    compensation_key         INTEGER PRIMARY KEY,
    employee_key             INTEGER NOT NULL REFERENCES dim_employee(employee_key),
    department_key           INTEGER NOT NULL REFERENCES dim_department(department_key),
    location_key             INTEGER NOT NULL REFERENCES dim_location(location_key),
    increment_date_key       INTEGER REFERENCES dim_date(date_key),
    basic_salary             REAL NOT NULL CHECK (basic_salary > 0),
    allowances               REAL NOT NULL CHECK (allowances >= 0),
    bonus                    REAL NOT NULL CHECK (bonus >= 0),
    deductions               REAL NOT NULL CHECK (deductions >= 0),
    net_salary               REAL NOT NULL,
    total_compensation       REAL NOT NULL CHECK (total_compensation > 0),
    salary_increment         REAL NOT NULL CHECK (salary_increment >= 0),
    salary_growth_pct        REAL NOT NULL,
    bonus_to_salary_ratio    REAL NOT NULL,
    salary_band              TEXT NOT NULL,
    is_salary_anomaly        INTEGER NOT NULL CHECK (is_salary_anomaly IN (0, 1))
);

CREATE TABLE fact_leave (
    leave_key                INTEGER PRIMARY KEY,
    employee_key             INTEGER NOT NULL REFERENCES dim_employee(employee_key),
    department_key           INTEGER NOT NULL REFERENCES dim_department(department_key),
    date_key                 INTEGER NOT NULL REFERENCES dim_date(date_key),
    year                     INTEGER NOT NULL,
    leave_days               INTEGER NOT NULL CHECK (leave_days >= 0),
    sick_leave               INTEGER NOT NULL CHECK (sick_leave >= 0),
    casual_leave             INTEGER NOT NULL CHECK (casual_leave >= 0),
    unpaid_leave             INTEGER NOT NULL CHECK (unpaid_leave >= 0),
    overtime_hours           REAL NOT NULL CHECK (overtime_hours >= 0),
    leave_utilization        REAL NOT NULL,
    overtime_ratio           REAL NOT NULL
);

CREATE TABLE fact_performance (
    performance_key          INTEGER PRIMARY KEY,
    employee_key             INTEGER NOT NULL REFERENCES dim_employee(employee_key),
    department_key           INTEGER NOT NULL REFERENCES dim_department(department_key),
    last_promotion_date_key  INTEGER REFERENCES dim_date(date_key),
    performance_rating       INTEGER NOT NULL CHECK (performance_rating BETWEEN 1 AND 5),
    manager_rating           INTEGER NOT NULL CHECK (manager_rating BETWEEN 1 AND 5),
    promotion_count          INTEGER NOT NULL CHECK (promotion_count >= 0),
    training_hours           REAL NOT NULL CHECK (training_hours >= 0),
    promotion_gap            REAL NOT NULL CHECK (promotion_gap >= 0)
);

CREATE TABLE fact_attrition (
    attrition_key            INTEGER PRIMARY KEY,
    employee_key             INTEGER NOT NULL REFERENCES dim_employee(employee_key),
    department_key           INTEGER NOT NULL REFERENCES dim_department(department_key),
    location_key             INTEGER NOT NULL REFERENCES dim_location(location_key),
    exit_date_key            INTEGER REFERENCES dim_date(date_key),
    attrition_flag           INTEGER NOT NULL CHECK (attrition_flag IN (0, 1)),
    exit_reason              TEXT,
    tenure_at_exit_years     REAL,
    last_total_compensation  REAL
);

CREATE TABLE meta_data_quality_metrics (
    metric_id                INTEGER PRIMARY KEY,
    metric_category          TEXT NOT NULL,
    metric_name              TEXT NOT NULL,
    metric_value             REAL NOT NULL,
    assessed_at_utc          TEXT NOT NULL
);

CREATE INDEX idx_emp_dept ON dim_employee(department_key);
CREATE INDEX idx_emp_loc ON dim_employee(location_key);
CREATE INDEX idx_emp_desig ON dim_employee(designation);

CREATE INDEX idx_comp_emp ON fact_compensation(employee_key);
CREATE INDEX idx_comp_dept ON fact_compensation(department_key);
CREATE INDEX idx_comp_band ON fact_compensation(salary_band);

CREATE INDEX idx_leave_emp ON fact_leave(employee_key);
CREATE INDEX idx_leave_yr ON fact_leave(year);

CREATE INDEX idx_perf_emp ON fact_performance(employee_key);
CREATE INDEX idx_perf_dept ON fact_performance(department_key);

CREATE INDEX idx_attr_emp ON fact_attrition(employee_key);
CREATE INDEX idx_attr_dept ON fact_attrition(department_key);
CREATE INDEX idx_attr_flag ON fact_attrition(attrition_flag);

