"""Pipeline Orchestrator for Phases 2-7 (SQL -> EDA -> ML -> SHAP -> Recommendations).

Reuses verified Phase 1 outputs in `data/warehouse/workforce_dw.db` without
regenerating synthetic data.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.eda_analysis import run_eda_pipeline
from src.analytics.sql_runner import run_all_sql_queries
from src.ml.shap_explainer import run_shap_explainability
from src.ml.train_models import train_and_evaluate_models
from src.recommendations.engine import generate_business_recommendations


def main() -> None:
    print("\n[Phase 2] Deploying SQL views & executing 38 analytical queries...")
    sql_out = run_all_sql_queries()
    print(f"  - Views created: {len(sql_out['views_created'])}")
    print(f"  - Queries executed: {sql_out['total_queries_executed']}")

    print("\n[Phase 3] Running Exploratory Data Analysis & Matplotlib plotting...")
    eda_out = run_eda_pipeline()
    print(f"  - Charts generated: {len(eda_out['figures_created'])}")
    print(f"  - Findings documented: {len(eda_out['findings'])}")

    print("\n[Phase 4] Training & comparing attrition prediction models...")
    ml_out = train_and_evaluate_models()
    best = ml_out["best_model_name"]
    m = ml_out["models"][best]["test_recall_optimized"]
    print(f"  - Champion: {best} | Test ROC-AUC={m['roc_auc']:.4f} | Recall={m['recall']:.4f} | F1={m['f1_score']:.4f}")

    print("\n[Phase 5] Generating global & local SHAP explainability...")
    shap_out = run_shap_explainability()
    print(f"  - Explainer: {shap_out['explainer_type']} | Top driver: {shap_out['domain_feature_importance'][0]['feature']}")

    print("\n[Phase 7] Generating prioritized business recommendations...")
    rec_out = generate_business_recommendations()
    print(f"  - Recommendations generated: {rec_out['total_recommendations']}")

    print("\nPhases 2-7 complete. Launch Streamlit dashboard with:\n  streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()

