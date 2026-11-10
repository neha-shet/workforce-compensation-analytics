# Workforce & Compensation Data Quality Assessment Report

**Generated (UTC):** `2026-11-10T11:34:49+00:00` | **Reference As-Of Date:** `2026-09-30`

## Overall Data Quality Score: **99.71%**

### Quality Dimension Scores

| Dimension | Score (%) | Description |
|---|---:|---|
| Completeness | 99.95% | Presence of required IDs, salaries, and attrition labels |
| Uniqueness | 99.87% | Absence of duplicate employee, payroll, and attendance keys |
| Validity | 99.88% | Conformance to ID regex, positive money/dates, and expected salary bands |
| Consistency | 98.61% | Canonical departments, locations, labels, and net-pay reconciliation |
| Temporal Integrity | 99.91% | Valid age at hire, promotions & exits occurring after joining date |

### Executive Defect Summary

```text
Total Employee Rows (Raw)    : 25,137
Unique Valid Employee IDs    : 24,987
Total Records (All 5 Tables) : 165,163
Duplicate Employee Records   : 137
Duplicate Payroll Records    : 85
Missing Employee IDs         : 11
Invalid Employee IDs         : 7
Missing / Invalid Salaries   : 42
Negative Deductions          : 24
Net Salary Mismatches        : 62
Salary Anomalies (Out-of-Band): 90
Invalid Dates                : 18
Impossible Tenure / Dates    : 43
Department Inconsistencies   : 420
Location Inconsistencies     : 360
Missing Attrition Labels     : 54
Leave & Overtime Anomalies   : 32
```

### Raw Table Volumes

| Table | Raw Row Count |
|---|---:|
| `employees.csv` | 25,137 |
| `compensation.csv` | 25,085 |
| `attendance_leave.csv` | 64,941 |
| `career.csv` | 25,000 |
| `exit.csv` | 25,000 |

### Detected Non-Canonical Categories (Standardized in ETL)
- **Departments:** `Analytics`, `Business Development`, `CS`, `Cust Success`, `Data Science`, `ENG`, `Engg`, `Fin`, `Finance & Accounts`, `HR`, `OPS`, `Operation`, `People Ops`, `Product Mgmt`, `R&D Engineering`, `Sales & BD`, `data & analytics `, `engineering `, `finance `, `hr `, `ops `, `product `, `sales `
- **Locations:** `BLR`, `Bangalore`, `Bombay`, `Gurgaon`, `Hyderabad `, `Madras`, `bengaluru `, `chennai `, `gurugram `, `hyd`, `mumbai `, `noida `, `pune `
