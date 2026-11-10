-- =============================================================================
-- Workforce & Compensation Analytics Engine
-- PostgreSQL 16 Dimensional Star Schema DDL
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS dw;

-- Drop facts before dimensions for idempotent rebuilds
DROP TABLE IF EXISTS dw.meta_data_quality_metrics CASCADE;
DROP TABLE IF EXISTS dw.fact_attrition CASCADE;
DROP TABLE IF EXISTS dw.fact_performance CASCADE;
DROP TABLE IF EXISTS dw.fact_leave CASCADE;
DROP TABLE IF EXISTS dw.fact_compensation CASCADE;
DROP TABLE IF EXISTS dw.dim_employee CASCADE;
DROP TABLE IF EXISTS dw.dim_date CASCADE;
DROP TABLE IF EXISTS dw.dim_location CASCADE;
DROP TABLE IF EXISTS dw.dim_department CASCADE;

-- =============================================================================
-- DIMENSION TABLES
-- =============================================================================

CREATE TABLE dw.dim_department (
    department_key          INTEGER PRIMARY KEY,
    department_name         VARCHAR(80) NOT NULL UNIQUE,
    department_head_function VARCHAR(80) NOT NULL,
    annual_budget_inr       NUMERIC(16, 2) NOT NULL CHECK (annual_budget_inr >= 0),
    target_attrition_pct    NUMERIC(5, 2) NOT NULL CHECK (target_attrition_pct >= 0)
);

CREATE TABLE dw.dim_location (
    location_key            INTEGER PRIMARY KEY,
    city                    VARCHAR(80) NOT NULL UNIQUE,
    region                  VARCHAR(40) NOT NULL,
    country                 VARCHAR(60) NOT NULL,
    cost_of_living_tier     VARCHAR(20) NOT NULL
);

CREATE TABLE dw.dim_date (
    date_key                INTEGER PRIMARY KEY,  -- YYYYMMDD
    full_date               DATE NOT NULL UNIQUE,
    year                    INTEGER NOT NULL,
    quarter                 INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month                   INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name              VARCHAR(10) NOT NULL,
    day_of_week             VARCHAR(10) NOT NULL,
    fiscal_year             VARCHAR(16) NOT NULL,
    is_weekend              SMALLINT NOT NULL CHECK (is_weekend IN (0, 1))
);

CREATE TABLE dw.dim_employee (
    employee_key            INTEGER PRIMARY KEY,
    employee_id             VARCHAR(20) NOT NULL UNIQUE,
    department_key          INTEGER NOT NULL REFERENCES dw.dim_department(department_key),
    location_key            INTEGER NOT NULL REFERENCES dw.dim_location(location_key),
    designation             VARCHAR(80) NOT NULL,
    employment_type         VARCHAR(30) NOT NULL,
    education               VARCHAR(40) NOT NULL,
    date_of_birth           DATE NOT NULL,
    age_years               NUMERIC(5, 1) NOT NULL,
    joining_date            DATE NOT NULL,
    experience_years        NUMERIC(5, 1) NOT NULL CHECK (experience_years >= 0),
    tenure_years            NUMERIC(6, 2) NOT NULL CHECK (tenure_years >= 0),
    tenure_band             VARCHAR(20) NOT NULL,
    is_active               SMALLINT NOT NULL CHECK (is_active IN (0, 1))
);

-- =============================================================================
-- FACT TABLES
-- =============================================================================

CREATE TABLE dw.fact_compensation (
    compensation_key        INTEGER PRIMARY KEY,
    employee_key            INTEGER NOT NULL REFERENCES dw.dim_employee(employee_key),
    department_key          INTEGER NOT NULL REFERENCES dw.dim_department(department_key),
    location_key            INTEGER NOT NULL REFERENCES dw.dim_location(location_key),
    increment_date_key      INTEGER REFERENCES dw.dim_date(date_key),
    basic_salary            NUMERIC(14, 2) NOT NULL CHECK (basic_salary > 0),
    allowances              NUMERIC(14, 2) NOT NULL CHECK (allowances >= 0),
    bonus                   NUMERIC(14, 2) NOT NULL CHECK (bonus >= 0),
    deductions              NUMERIC(14, 2) NOT NULL CHECK (deductions >= 0),
    net_salary              NUMERIC(14, 2) NOT NULL,
    total_compensation      NUMERIC(14, 2) NOT NULL CHECK (total_compensation > 0),
    salary_increment        NUMERIC(14, 2) NOT NULL CHECK (salary_increment >= 0),
    salary_growth_pct       NUMERIC(6, 2) NOT NULL,
    bonus_to_salary_ratio   NUMERIC(8, 4) NOT NULL,
    salary_band             VARCHAR(20) NOT NULL,
    is_salary_anomaly       SMALLINT NOT NULL CHECK (is_salary_anomaly IN (0, 1))
);

CREATE TABLE dw.fact_leave (
    leave_key               INTEGER PRIMARY KEY,
    employee_key            INTEGER NOT NULL REFERENCES dw.dim_employee(employee_key),
    department_key          INTEGER NOT NULL REFERENCES dw.dim_department(department_key),
    date_key                INTEGER NOT NULL REFERENCES dw.dim_date(date_key),
    year                    INTEGER NOT NULL,
    leave_days              INTEGER NOT NULL CHECK (leave_days >= 0),
    sick_leave              INTEGER NOT NULL CHECK (sick_leave >= 0),
    casual_leave            INTEGER NOT NULL CHECK (casual_leave >= 0),
    unpaid_leave            INTEGER NOT NULL CHECK (unpaid_leave >= 0),
    overtime_hours          NUMERIC(7, 1) NOT NULL CHECK (overtime_hours >= 0),
    leave_utilization       NUMERIC(8, 4) NOT NULL,
    overtime_ratio          NUMERIC(8, 4) NOT NULL
);

CREATE TABLE dw.fact_performance (
    performance_key         INTEGER PRIMARY KEY,
    employee_key            INTEGER NOT NULL REFERENCES dw.dim_employee(employee_key),
    department_key          INTEGER NOT NULL REFERENCES dw.dim_department(department_key),
    last_promotion_date_key INTEGER REFERENCES dw.dim_date(date_key),
    performance_rating      SMALLINT NOT NULL CHECK (performance_rating BETWEEN 1 AND 5),
    manager_rating          SMALLINT NOT NULL CHECK (manager_rating BETWEEN 1 AND 5),
    promotion_count         INTEGER NOT NULL CHECK (promotion_count >= 0),
    training_hours          NUMERIC(6, 1) NOT NULL CHECK (training_hours >= 0),
    promotion_gap           NUMERIC(6, 2) NOT NULL CHECK (promotion_gap >= 0)
);

CREATE TABLE dw.fact_attrition (
    attrition_key           INTEGER PRIMARY KEY,
    employee_key            INTEGER NOT NULL REFERENCES dw.dim_employee(employee_key),
    department_key          INTEGER NOT NULL REFERENCES dw.dim_department(department_key),
    location_key            INTEGER NOT NULL REFERENCES dw.dim_location(location_key),
    exit_date_key           INTEGER REFERENCES dw.dim_date(date_key),
    attrition_flag          SMALLINT NOT NULL CHECK (attrition_flag IN (0, 1)),
    exit_reason             VARCHAR(80),
    tenure_at_exit_years    NUMERIC(6, 2),
    last_total_compensation NUMERIC(14, 2)
);

CREATE TABLE dw.meta_data_quality_metrics (
    metric_id               INTEGER PRIMARY KEY,
    metric_category         VARCHAR(50) NOT NULL,
    metric_name             VARCHAR(100) NOT NULL,
    metric_value            NUMERIC(14, 2) NOT NULL,
    assessed_at_utc         VARCHAR(40) NOT NULL
);

-- =============================================================================
-- ANALYTICAL INDEXES
-- =============================================================================

CREATE INDEX idx_emp_dept ON dw.dim_employee(department_key);
CREATE INDEX idx_emp_loc ON dw.dim_employee(location_key);
CREATE INDEX idx_emp_desig ON dw.dim_employee(designation);

CREATE INDEX idx_comp_emp ON dw.fact_compensation(employee_key);
CREATE INDEX idx_comp_dept ON dw.fact_compensation(department_key);
CREATE INDEX idx_comp_band ON dw.fact_compensation(salary_band);

CREATE INDEX idx_leave_emp ON dw.fact_leave(employee_key);
CREATE INDEX idx_leave_yr ON dw.fact_leave(year);

CREATE INDEX idx_perf_emp ON dw.fact_performance(employee_key);
CREATE INDEX idx_perf_dept ON dw.fact_performance(department_key);

CREATE INDEX idx_attr_emp ON dw.fact_attrition(employee_key);
CREATE INDEX idx_attr_dept ON dw.fact_attrition(department_key);
CREATE INDEX idx_attr_flag ON dw.fact_attrition(attrition_flag);

