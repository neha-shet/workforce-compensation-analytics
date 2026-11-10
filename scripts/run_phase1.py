"""End-to-end Phase 1 Orchestrator: Dataset -> Data Quality -> ETL -> Warehouse."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DB_BACKEND, NUM_EMPLOYEES, RANDOM_SEED
from src.data_generation.generate_hr_data import generate_raw_datasets
from src.etl.etl_pipeline import run_etl_pipeline
from src.quality.dq_assessor import assess_data_quality
from src.warehouse.load_warehouse import load_warehouse


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 1: Dataset, DQ Report, ETL, Warehouse Load")
    parser.add_argument("--employees", type=int, default=NUM_EMPLOYEES, help="Target number of unique employees")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Random seed for reproducibility")
    parser.add_argument("--backend", type=str, default=DB_BACKEND, choices=["sqlite", "postgres", "both"], help="Warehouse backend")
    args = parser.parse_args()

    print("\n[1/4] Generating realistic Enterprise HR & Payroll datasets...")
    gen_summary = generate_raw_datasets(num_employees=args.employees, seed=args.seed)
    for t_name, cnt in gen_summary["raw_rows"].items():
        print(f"  - {t_name}.csv: {cnt:,} raw rows")

    print("\n[2/4] Running Pre-ETL Data Quality Assessment...")
    dq = assess_data_quality()
    hs = dq["headline_summary"]
    qs = dq["quality_scores_pct"]
    print(f"  - Overall Data Quality Score : {qs['overall_data_quality_score']:.2f}%")
    print(f"  - Duplicate Employee Records : {hs['duplicate_employee_records']:,}")
    print(f"  - Duplicate Payroll Records  : {hs['duplicate_payroll_records']:,}")
    print(f"  - Missing/Invalid Salaries   : {hs['missing_or_invalid_salaries']:,}")
    print(f"  - Salary Anomalies           : {hs['salary_anomalies']:,}")
    print(f"  - Invalid Dates              : {hs['invalid_dates']:,}")
    print(f"  - Impossible Tenure          : {hs['impossible_tenure_records']:,}")
    print(f"  - Department Inconsistencies : {hs['department_inconsistencies']:,}")
    print(f"  - Missing Attrition Labels   : {hs['missing_attrition_labels']:,}")

    print("\n[3/4] Running Python ETL, Quarantine & Feature Engineering...")
    etl_summary = run_etl_pipeline()
    print(f"  - Quarantined rows : {etl_summary['quarantined_counts']}")
    print(f"  - Repaired counts  : {etl_summary['repaired_counts']}")
    print(f"  - Clean master rows: {etl_summary['output_counts']['master_workforce']:,}")

    print(f"\n[4/4] Loading Star Schema Data Warehouse (backend={args.backend})...")
    wh_results = load_warehouse(backend=args.backend)
    for res in wh_results:
        print(f"  - Backend: {res.get('backend')}")
        if "kpi_sanity_check" in res:
            kpi = res["kpi_sanity_check"]
            print(
                f"    Employees={kpi['total_employees']:,} | "
                f"Payroll=INR {kpi['total_payroll_inr_cr']:,.2f} Cr | "
                f"Avg Comp=INR {kpi['avg_total_comp_inr']:,.0f} | "
                f"Attrition={kpi['attrition_rate_pct']:.2f}% | "
                f"Avg Tenure={kpi['avg_tenure_years']:.2f} yrs"
            )
        if res.get("status") == "skipped":
            print(f"    Skipped: {res.get('reason')}")

    print("\nPhase 1 complete. Reports saved to `reports/data_quality_report.md` and `reports/etl_run_summary.json`.")


if __name__ == "__main__":
    main()

