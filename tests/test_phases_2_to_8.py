"""Comprehensive automated test suite covering Phases 2 through 8."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from app.data_loader import (
    fetch_data_quality_artifacts,
    fetch_department_kpi,
    fetch_leave_history,
    fetch_ml_and_shap_artifacts,
    fetch_monthly_trends,
    fetch_recommendations,
    fetch_workforce_360,
    format_inr,
    format_inr_crore,
)
from config.settings import PATHS
from src.analytics.eda_analysis import run_eda_pipeline
from src.analytics.sql_runner import apply_sqlite_views, parse_sql_queries, run_all_sql_queries
from src.ml.shap_explainer import explain_single_employee_row, run_shap_explainability
from src.ml.train_models import FEATURE_COLUMNS, FORBIDDEN_LEAKAGE_COLUMNS, load_ml_dataset, train_and_evaluate_models
from src.recommendations.engine import generate_business_recommendations
from src.simulator.scenario_engine import ScenarioParams, simulate_workforce_scenario


class TestSQLAnalyticsLayer(unittest.TestCase):
    def test_all_views_and_35_plus_queries_execute(self) -> None:
        views = apply_sqlite_views(PATHS.sqlite_db)
        self.assertGreaterEqual(len(views), 5)
        for expected in (
            "vw_employee_workforce_360",
            "vw_department_kpi_summary",
            "vw_monthly_hiring_and_attrition",
            "vw_high_risk_compensation_pockets",
            "vw_data_quality_audit",
        ):
            self.assertIn(expected, views)

        queries = parse_sql_queries()
        self.assertGreaterEqual(len(queries), 35)

        conn = sqlite3.connect(PATHS.sqlite_db)
        try:
            for q in queries:
                df = pd.read_sql_query(q.sql, conn)
                self.assertGreater(len(df), 0, f"Query {q.query_id} ({q.query_name}) returned 0 rows")
        finally:
            conn.close()

    def test_sql_runner_report_artifacts_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = run_all_sql_queries(db_path=PATHS.sqlite_db, reports_dir=Path(tmp))
            self.assertGreaterEqual(res["total_queries_executed"], 35)
            self.assertTrue((Path(tmp) / "sql_analytical_findings.md").exists())
            self.assertTrue((Path(tmp) / "sql_execution_summary.json").exists())


class TestEDAPipeline(unittest.TestCase):
    def test_eda_generates_charts_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rep_dir = Path(tmp)
            out = run_eda_pipeline(db_path=PATHS.sqlite_db, reports_dir=rep_dir)
            self.assertGreaterEqual(len(out["figures_created"]), 10)
            self.assertGreaterEqual(len(out["findings"]), 6)
            self.assertTrue((rep_dir / "eda_report.md").exists())
            for fig in out["figures_created"]:
                fig_path = rep_dir / "figures" / fig
                self.assertTrue(fig_path.exists() and fig_path.stat().st_size > 10_000)


class TestMLAndSHAP(unittest.TestCase):
    def test_no_leakage_in_features(self) -> None:
        self.assertEqual(set(FEATURE_COLUMNS).intersection(FORBIDDEN_LEAKAGE_COLUMNS), set())
        df = load_ml_dataset(PATHS.sqlite_db)
        self.assertGreater(len(df), 24_000)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)

    def test_saved_model_prediction_and_shap_explanation(self) -> None:
        ml = fetch_ml_and_shap_artifacts()
        bundle = ml["bundle"]
        self.assertIsNotNone(bundle)
        comp = ml["comparison"]
        self.assertIn("Logistic Regression", comp["models"])
        self.assertIn("Random Forest", comp["models"])
        self.assertIn("XGBoost", comp["models"])

        best_name = comp["best_model_name"]
        best_metrics = comp["models"][best_name]["test_recall_optimized"]
        self.assertGreater(best_metrics["roc_auc"], 0.70)
        self.assertGreater(best_metrics["recall"], 0.55)

        df = load_ml_dataset(PATHS.sqlite_db)
        sample_row = df.iloc[[0]]
        prob = float(bundle["pipeline"].predict_proba(sample_row[FEATURE_COLUMNS])[0, 1])
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

        exp = explain_single_employee_row(bundle, sample_row)
        self.assertIn(exp["risk_tier"], ("HIGH", "MEDIUM", "LOW"))
        self.assertGreaterEqual(len(exp["top_factors"]), 5)
        self.assertTrue((PATHS.reports / "figures" / "13_shap_summary_beeswarm.png").exists())

    def test_model_training_and_shap_pipeline_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            tmp_db = base / "subset_dw.db"
            m_dir = base / "models"
            r_dir = base / "reports"
            p_dir = base / "processed"

            # Build an isolated 2,500-employee SQLite star-schema subset so production artifacts are untouched
            conn = sqlite3.connect(tmp_db)
            try:
                conn.execute("ATTACH DATABASE ? AS src_dw", (str(PATHS.sqlite_db),))
                for t in ("dim_department", "dim_location", "dim_date", "meta_data_quality_metrics"):
                    conn.execute(f"CREATE TABLE {t} AS SELECT * FROM src_dw.{t}")
                conn.execute("CREATE TABLE dim_employee AS SELECT * FROM src_dw.dim_employee WHERE employee_key % 10 = 0")
                for ft in ("fact_compensation", "fact_performance", "fact_leave", "fact_attrition"):
                    conn.execute(
                        f"CREATE TABLE {ft} AS SELECT f.* FROM src_dw.{ft} f "
                        "JOIN dim_employee e ON f.employee_key = e.employee_key"
                    )
                conn.commit()
            finally:
                conn.close()

            train_res = train_and_evaluate_models(
                db_path=tmp_db,
                models_dir=m_dir,
                reports_dir=r_dir,
                processed_dir=p_dir,
            )
            self.assertIn(train_res["best_model_name"], ("Logistic Regression", "Random Forest", "XGBoost"))
            self.assertTrue((m_dir / "best_attrition_model.joblib").exists())
            self.assertTrue((m_dir / "model_comparison.json").exists())
            self.assertTrue((r_dir / "model_evaluation.md").exists())
            self.assertTrue((p_dir / "employee_risk_scores.parquet").exists())
            self.assertTrue((r_dir / "figures" / "11_model_roc_and_pr_curves.png").exists())
            self.assertTrue((r_dir / "figures" / "12_confusion_matrices.png").exists())

            shap_res = run_shap_explainability(
                db_path=tmp_db,
                models_dir=m_dir,
                reports_dir=r_dir,
                sample_size=150,
            )
            self.assertGreaterEqual(len(shap_res["domain_feature_importance"]), 10)
            self.assertTrue((m_dir / "shap_global_importance.json").exists())
            self.assertTrue((r_dir / "shap_explainability_report.md").exists())
            self.assertTrue((r_dir / "figures" / "13_shap_summary_beeswarm.png").exists())
            self.assertTrue((r_dir / "figures" / "14_shap_feature_importance_bar.png").exists())
            self.assertTrue((r_dir / "figures" / "15_shap_dependence_top_drivers.png").exists())


class TestScenarioAndRecommendations(unittest.TestCase):
    def test_scenario_payroll_calculations(self) -> None:
        df = fetch_workforce_360(PATHS.sqlite_db)
        active = df[df["is_active"] == 1].copy()

        # Baseline 0% changes must yield exact 0 net delta
        res0 = simulate_workforce_scenario(active, ScenarioParams())
        self.assertAlmostEqual(res0["net_financial_impact_cr"], 0.0, places=2)
        self.assertEqual(res0["employees_affected"], 0)

        # Pure 5% budget increase must yield exact +5.0% payroll increase
        res5 = simulate_workforce_scenario(active, ScenarioParams(budget_increase_pct=5.0))
        self.assertAlmostEqual(res5["net_impact_pct"], 5.0, places=1)
        self.assertEqual(res5["employees_affected"], res5["active_headcount"])

        # Combined scenario with ML sensitivity
        ml = fetch_ml_and_shap_artifacts()
        res_combo = simulate_workforce_scenario(
            active,
            ScenarioParams(
                department_filter="Engineering",
                budget_increase_pct=3.0,
                overtime_reduction_pct=15.0,
                promotion_rate_boost_pct=10.0,
                retention_intervention_pct=25.0,
            ),
            model_bundle=ml["bundle"],
            include_ml_sensitivity=True,
        )
        self.assertGreater(res_combo["promoted_employees_count"], 0)
        self.assertGreater(res_combo["cost_breakdown_cr"]["overtime_savings_cr"], 0.0)
        self.assertIsNotNone(res_combo["ml_risk_sensitivity"])

    def test_recommendations_engine_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rec_out = generate_business_recommendations(db_path=PATHS.sqlite_db, reports_dir=Path(tmp))
            self.assertGreaterEqual(len(rec_out["recommendations"]), 5)
            for r in rec_out["recommendations"]:
                for key in ("finding", "supporting_metric", "business_implication", "recommended_action"):
                    self.assertTrue(bool(r[key].strip()), f"Missing {key} in {r['id']}")


class TestDashboardLoadingAndApp(unittest.TestCase):
    def test_dashboard_data_loaders_and_formatting(self) -> None:
        self.assertEqual(format_inr(2194698), "₹21,94,698")
        self.assertEqual(format_inr_crore(5466.12, already_in_crores=True), "₹5,466.12 Cr")

        wf = fetch_workforce_360()
        self.assertEqual(len(wf), 24_953)
        self.assertEqual(len(fetch_department_kpi()), 8)
        self.assertGreater(len(fetch_monthly_trends()), 40)
        self.assertGreater(len(fetch_leave_history()), 15)
        dq = fetch_data_quality_artifacts()
        self.assertIn("headline_summary", dq["dq_report"])
        self.assertGreater(len(fetch_recommendations()["recommendations"]), 5)

    def test_all_7_page_functions_render_in_bare_mode(self) -> None:
        import app.streamlit_app as st_app

        df = fetch_workforce_360(PATHS.sqlite_db)
        dept_kpi = fetch_department_kpi(PATHS.sqlite_db)
        monthly = fetch_monthly_trends(PATHS.sqlite_db)
        leave_hist = fetch_leave_history(PATHS.sqlite_db)
        dq = fetch_data_quality_artifacts()
        recs = fetch_recommendations()
        ml = fetch_ml_and_shap_artifacts()

        st_app.page_executive_overview(df, monthly, recs)
        st_app.page_compensation_analytics(df, dept_kpi)
        st_app.page_workforce_analytics(df, leave_hist)
        st_app.page_attrition_analytics(df)
        st_app.page_data_quality(dq)
        st_app.page_predictive_analytics(df, ml)
        st_app.page_scenario_simulator(df, ml)

    def test_streamlit_all_7_pages_render_without_exception(self) -> None:
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(str(PATHS.root / "app" / "streamlit_app.py"), default_timeout=60)
        at.run()
        self.assertFalse(at.exception, f"Page 1 raised exception: {at.exception}")
        self.assertIn("24,953", "\n".join(m.value for m in at.markdown))

        # Verify compact searchable sidebar filters update scope cleanly & reset button restores full cohort
        at.sidebar.multiselect(key="flt_dept").select("Engineering").run()
        self.assertFalse(at.exception, f"Sidebar filter selection raised exception: {at.exception}")
        self.assertTrue(any("1 filter group" in m.value for m in at.sidebar.markdown))
        at.sidebar.button[0].click().run()
        self.assertFalse(at.exception, f"Reset All Filters button raised exception: {at.exception}")
        self.assertTrue(any("Enterprise-Wide" in m.value for m in at.sidebar.markdown))

        pages = [
            "2. Compensation Analytics",
            "3. Workforce Analytics",
            "4. Attrition Analytics",
            "5. Data Quality",
            "6. Predictive Analytics & SHAP",
            "7. Workforce Scenario Simulator",
        ]
        for page_name in pages:
            at.sidebar.radio[0].set_value(page_name).run()
            self.assertFalse(at.exception, f"{page_name} raised exception: {at.exception}")

        # Verify filtered view also works cleanly on Scenario Simulator / Predictive page without error
        at.sidebar.multiselect(key="flt_dept").select("Sales").run()
        self.assertFalse(at.exception, f"Filtered Page 7 raised exception: {at.exception}")


if __name__ == "__main__":
    unittest.main()
