"""Unit & end-to-end integration tests for Phase 1 pipeline."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from config.settings import CANONICAL_DEPARTMENTS, CANONICAL_LOCATIONS
from src.data_generation.generate_hr_data import generate_raw_datasets
from src.etl.etl_pipeline import run_etl_pipeline
from src.quality.dq_assessor import assess_data_quality
from src.warehouse.load_warehouse import load_sqlite_warehouse


class TestPhase1Pipeline(unittest.TestCase):
    """End-to-end verification on an isolated temporary directory."""

    def test_end_to_end_phase1_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            raw_dir = base / "raw"
            quarantine_dir = base / "quarantine"
            processed_dir = base / "processed"
            reports_dir = base / "reports"
            db_path = base / "warehouse" / "test_dw.db"

            # 1. Generate 2,500 synthetic employees for fast test execution
            gen = generate_raw_datasets(num_employees=2500, seed=123, output_dir=raw_dir)
            self.assertGreater(gen["raw_rows"]["employees"], 2500)
            for fname in ("employees.csv", "compensation.csv", "attendance_leave.csv", "career.csv", "exit.csv"):
                self.assertTrue((raw_dir / fname).exists(), f"Missing {fname}")

            # 2. Data Quality Assessment catches injected defects
            dq = assess_data_quality(raw_dir=raw_dir, reports_dir=reports_dir)
            hs = dq["headline_summary"]
            self.assertGreater(hs["duplicate_employee_records"], 0)
            self.assertGreater(hs["duplicate_payroll_records"], 0)
            self.assertGreater(hs["missing_or_invalid_salaries"], 0)
            self.assertGreater(hs["salary_anomalies"], 0)
            self.assertGreater(hs["invalid_dates"], 0)
            self.assertGreater(hs["department_inconsistencies"], 0)
            self.assertGreater(hs["missing_attrition_labels"], 0)
            self.assertTrue((reports_dir / "data_quality_report.json").exists())
            self.assertTrue((reports_dir / "data_quality_report.md").exists())

            # 3. ETL Pipeline cleans, standardizes, quarantines, and engineers all derived features
            etl = run_etl_pipeline(
                raw_dir=raw_dir,
                quarantine_dir=quarantine_dir,
                processed_dir=processed_dir,
                reports_dir=reports_dir,
            )
            self.assertGreater(etl["quarantined_counts"]["employees"], 0)
            self.assertGreater(etl["quarantined_counts"]["compensation"], 0)

            master = pd.read_parquet(processed_dir / "master_workforce.parquet")
            self.assertEqual(master["employee_id"].nunique(), len(master))
            self.assertTrue(set(master["department"].unique()).issubset(set(CANONICAL_DEPARTMENTS.keys())))
            self.assertTrue(set(master["location"].unique()).issubset(set(CANONICAL_LOCATIONS.keys())))

            required_derived = [
                "tenure_years",
                "salary_growth_pct",
                "leave_utilization",
                "overtime_ratio",
                "promotion_gap",
                "bonus_to_salary_ratio",
                "total_compensation",
            ]
            for col in required_derived:
                self.assertIn(col, master.columns)

            # Verify net_salary reconciliation on valid compensation rows
            comp_valid = master.dropna(subset=["basic_salary"])
            reconciled = comp_valid["basic_salary"] + comp_valid["allowances"] + comp_valid["bonus"] - comp_valid["deductions"]
            self.assertTrue(((comp_valid["net_salary"] - reconciled).abs() <= 0.05).all())
            self.assertTrue((comp_valid["promotion_gap"] >= 0).all())
            self.assertTrue((comp_valid["tenure_years"] >= 0).all())

            # 4. Load Warehouse & verify FK integrity + analytical signals
            wh = load_sqlite_warehouse(
                warehouse_export_dir=processed_dir / "warehouse",
                sqlite_path=db_path,
                reports_dir=reports_dir,
            )
            self.assertEqual(wh["table_row_counts"]["dim_department"], len(CANONICAL_DEPARTMENTS))
            self.assertEqual(wh["table_row_counts"]["dim_location"], len(CANONICAL_LOCATIONS))
            self.assertGreater(wh["kpi_sanity_check"]["attrition_rate_pct"], 5.0)
            self.assertLess(wh["kpi_sanity_check"]["attrition_rate_pct"], 25.0)

            conn = sqlite3.connect(db_path)
            try:
                fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
                self.assertEqual(fk_violations, [])
                net_diff = conn.execute(
                    "SELECT COUNT(*) FROM fact_compensation WHERE ABS(net_salary - (basic_salary + allowances + bonus - deductions)) > 1.0"
                ).fetchone()[0]
                self.assertEqual(net_diff, 0)
                dq_metric_count = conn.execute("SELECT COUNT(*) FROM meta_data_quality_metrics").fetchone()[0]
                self.assertGreater(dq_metric_count, 10)
            finally:
                conn.close()

            # Verify realistic attrition signal: promotion_gap > 2.5 yrs has higher attrition than <= 1.5 yrs
            valid_attr = master.dropna(subset=["attrition_flag", "promotion_gap"])
            high_gap_attr = valid_attr.loc[valid_attr["promotion_gap"] > 2.5, "attrition_flag"].mean()
            low_gap_attr = valid_attr.loc[valid_attr["promotion_gap"] <= 1.5, "attrition_flag"].mean()
            self.assertGreater(high_gap_attr, low_gap_attr)


if __name__ == "__main__":
    unittest.main()

