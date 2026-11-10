"""Workforce Intelligence — Workforce & Compensation Analytics Engine (Streamlit App).

Connects directly to the verified SQLite Star Schema Data Warehouse
(`data/warehouse/workforce_dw.db`), ML Attrition Champion Pipeline, SHAP
Explainability, Workforce Scenario Simulator, and Business Recommendation Engine.
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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
    format_inr_lakhs,
)
from config.settings import PATHS

# =============================================================================
# PAGE CONFIGURATION & ENTERPRISE DESIGN SYSTEM
# =============================================================================
st.set_page_config(
    page_title="Workforce Intelligence | Compensation & Attrition Engine",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Restrained enterprise navy, white & neutral slate palette
NAVY_PRIMARY = "#0F2942"
NAVY_MID = "#1E3A5F"
COBALT = "#2B6CB0"
SLATE_TEXT = "#0F172A"
SLATE_SUB = "#475569"
SLATE_MUTED = "#64748B"
BORDER_COLOR = "#E2E8F0"
GRID_COLOR = "#E2E8F0"
TEAL_ACCENT = "#0D9488"
AMBER_WARN = "#D97706"
CRIMSON_RISK = "#B91C1C"

COLOR_SEQ = [
    "#0F2942",
    "#2B6CB0",
    "#0D9488",
    "#64748B",
    "#475569",
    "#94A3B8",
    "#D97706",
    "#B91C1C",
]
NAVY_CONTINUOUS = ["#DBEAFE", "#93C5FD", "#3B82F6", "#1E3A5F", "#0F2942"]
RISK_CONTINUOUS = ["#0D9488", "#94A3B8", "#D97706", "#B91C1C"]

st.markdown(
    """
    <style>
    /* Global canvas & typography */
    html, body, [class*="css"] {
        font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #0F172A;
    }
    .stApp {
        background-color: #F8FAFC;
    }
    .block-container {
        max-width: 1520px;
        padding-top: 3.15rem;
        padding-bottom: 2.5rem;
        padding-left: 1.75rem;
        padding-right: 1.75rem;
        overflow-x: hidden;
    }
    @media (max-width: 1100px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }

    /* Sidebar polish */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.15rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .sidebar-brand {
        background: #0F2942;
        color: #FFFFFF;
        border-radius: 8px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.9rem;
    }
    .sidebar-brand-title {
        font-size: 1.02rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #FFFFFF;
        margin: 0;
    }
    .sidebar-brand-sub {
        font-size: 0.72rem;
        color: #CBD5E1;
        margin-top: 0.25rem;
        line-height: 1.35;
    }
    .sidebar-section-label {
        font-size: 0.7rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin: 0.75rem 0 0.35rem 0;
    }
    .filter-summary-pill {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 0.45rem 0.65rem;
        font-size: 0.75rem;
        color: #334155;
        margin-top: 0.35rem;
        margin-bottom: 0.55rem;
    }

    /* Consistent page headers */
    .page-header {
        margin-bottom: 0.9rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #E2E8F0;
    }
    .page-eyebrow {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: #2B6CB0;
        margin-bottom: 0.2rem;
    }
    .page-title {
        font-size: clamp(1.35rem, 1.85vw, 1.75rem);
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.015em;
        line-height: 1.2;
        margin: 0;
    }
    .page-subtitle {
        font-size: 0.88rem;
        color: #475569;
        margin-top: 0.3rem;
        line-height: 1.45;
    }

    /* Section headers */
    .section-heading {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin: 1.15rem 0 0.2rem 0;
        letter-spacing: -0.01em;
    }
    .section-caption {
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 0.7rem;
    }

    /* Responsive equal-height KPI grid */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.85rem;
        align-items: stretch;
        margin-bottom: 1rem;
        width: 100%;
    }
    .kpi-grid-6 {
        display: grid;
        grid-template-columns: repeat(6, minmax(0, 1fr));
        gap: 0.8rem;
        align-items: stretch;
        margin-bottom: 1rem;
        width: 100%;
    }
    .kpi-grid-3 {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.85rem;
        align-items: stretch;
        margin-bottom: 0.9rem;
        width: 100%;
    }
    @media (max-width: 1380px) {
        .kpi-grid-6 {
            grid-template-columns: repeat(3, minmax(0, 1fr));
        }
    }
    @media (max-width: 1180px) {
        .kpi-grid {
            grid-template-columns: repeat(auto-fit, minmax(185px, 1fr));
        }
    }
    @media (max-width: 780px) {
        .kpi-grid-6, .kpi-grid-3, .kpi-grid {
            grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
        }
    }
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-top: 3px solid #0F2942;
        border-radius: 8px;
        padding: 0.85rem 0.9rem 0.8rem 0.9rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 108px;
        height: 100%;
        min-width: 0;
        box-sizing: border-box;
    }
    .kpi-label {
        font-size: 0.71rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        line-height: 1.3;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: clamp(0.98rem, 1.15vw, 1.36rem);
        font-weight: 700;
        color: #0F172A;
        line-height: 1.24;
        font-variant-numeric: tabular-nums;
        white-space: nowrap;
    }
    .kpi-value.wrap-text {
        font-size: clamp(0.92rem, 1.05vw, 1.14rem);
        white-space: normal;
        overflow-wrap: break-word;
        line-height: 1.25;
    }
    .kpi-sub {
        font-size: 0.76rem;
        color: #475569;
        margin-top: 0.35rem;
        line-height: 1.35;
    }

    /* Notice banners */
    .disclaimer-banner {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2B6CB0;
        padding: 0.7rem 0.95rem;
        border-radius: 6px;
        font-size: 0.83rem;
        color: #334155;
        margin-bottom: 1rem;
        line-height: 1.45;
    }

    /* Business recommendation cards */
    .rec-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #B91C1C;
        border-radius: 8px;
        padding: 0.95rem 1.1rem;
        margin-bottom: 0.85rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        height: 100%;
        box-sizing: border-box;
    }
    .rec-card.high { border-left-color: #D97706; }
    .rec-card.medium { border-left-color: #2B6CB0; }
    .rec-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.5rem;
        margin-bottom: 0.45rem;
        flex-wrap: wrap;
    }
    .rec-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #0F172A;
    }
    .rec-badge {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 0.15rem 0.48rem;
        border-radius: 4px;
        background: #FEE2E2;
        color: #991B1B;
    }
    .rec-badge.high { background: #FEF3C7; color: #92400E; }
    .rec-badge.medium { background: #DBEAFE; color: #1E40AF; }
    .rec-owner {
        font-size: 0.76rem;
        color: #64748B;
        margin-bottom: 0.5rem;
    }
    .rec-row {
        font-size: 0.82rem;
        color: #334155;
        line-height: 1.45;
        margin-bottom: 0.28rem;
    }
    .rec-row strong {
        color: #0F172A;
    }

    /* Streamlit bordered container card polish */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-color: #E2E8F0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    /* Tighter tabs / buttons / download buttons */
    .stDownloadButton button, .stButton button {
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
        border-color: #CBD5E1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-eyebrow">{html.escape(eyebrow)}</div>
            <h1 class="page-title">{html.escape(title)}</h1>
            <div class="page-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card_html(label: str, value: str, sub: str = "", wrap_text: bool = False) -> str:
    val_cls = "kpi-value wrap-text" if wrap_text else "kpi-value"
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_sub = html.escape(str(sub)) if sub else "&nbsp;"
    return (
        f'<div class="kpi-card">'
        f'<div><div class="kpi-label">{safe_label}</div>'
        f'<div class="{val_cls}" title="{safe_value}">{safe_value}</div></div>'
        f'<div class="kpi-sub">{safe_sub}</div>'
        f"</div>"
    )


def render_kpi_card(label: str, value: str, sub: str = "", wrap_text: bool = False) -> None:
    st.markdown(_kpi_card_html(label, value, sub, wrap_text=wrap_text), unsafe_allow_html=True)


def render_kpi_grid(items: list[dict[str, Any]], columns_class: str = "kpi-grid") -> None:
    cards_html = "".join(
        _kpi_card_html(
            item["label"],
            item["value"],
            item.get("sub", ""),
            wrap_text=bool(item.get("wrap_text", False)),
        )
        for item in items
    )
    st.markdown(f'<div class="{columns_class}">{cards_html}</div>', unsafe_allow_html=True)


def style_plotly(
    fig: go.Figure,
    height: int = 390,
    legend_pos: str = "top",
    show_legend: bool = True,
    b_margin: int | None = None,
) -> go.Figure:
    """Apply clean, consistent enterprise layout without title-legend or tick collisions."""
    if not show_legend:
        top_m, bot_m = 54, b_margin or 32
        legend_cfg: dict[str, Any] = {}
    elif legend_pos == "bottom":
        top_m, bot_m = 56, b_margin or 100
        legend_cfg = dict(
            orientation="h",
            yanchor="top",
            y=-0.26,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=SLATE_SUB),
            bgcolor="rgba(255,255,255,0)",
        )
    elif legend_pos == "right":
        top_m, bot_m = 54, b_margin or 28
        legend_cfg = dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color=SLATE_SUB),
            bgcolor="rgba(255,255,255,0)",
        )
    else:  # clean top legend positioned below title
        top_m, bot_m = 80, b_margin or 34
        legend_cfg = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.0,
            font=dict(size=11, color=SLATE_SUB),
            bgcolor="rgba(255,255,255,0)",
        )

    fig.update_layout(
        height=height,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        showlegend=show_legend,
        margin=dict(l=16, r=24, t=top_m, b=bot_m),
        title=dict(
            font=dict(size=14, color=SLATE_TEXT, family="Inter, Segoe UI, sans-serif"),
            x=0.0,
            xanchor="left",
            y=0.96,
            yanchor="top",
        ),
        font=dict(size=12, color=SLATE_SUB, family="Inter, Segoe UI, sans-serif"),
        hoverlabel=dict(bgcolor="#0F172A", bordercolor="#0F172A", font=dict(size=12, color="#FFFFFF")),
        coloraxis_colorbar=dict(
            thickness=11,
            len=0.78,
            outlinewidth=0,
            tickfont=dict(size=10, color=SLATE_MUTED),
            title_font=dict(size=11, color=SLATE_SUB),
        ),
    )
    if show_legend:
        fig.update_layout(legend=legend_cfg, legend_title_text="")

    fig.update_xaxes(
        automargin=True,
        showgrid=False,
        showline=True,
        linecolor="#CBD5E1",
        tickfont=dict(size=11, color=SLATE_SUB),
        title_font=dict(size=12, color=SLATE_SUB),
    )
    fig.update_yaxes(
        automargin=True,
        gridcolor=GRID_COLOR,
        gridwidth=1,
        zerolinecolor="#CBD5E1",
        tickfont=dict(size=11, color=SLATE_SUB),
        title_font=dict(size=12, color=SLATE_SUB),
    )
    return fig


# =============================================================================
# CACHED DATA & MODEL LOADERS
# =============================================================================
@st.cache_data(ttl=600)
def load_all_workforce_data() -> dict[str, Any]:
    return {
        "workforce": fetch_workforce_360(),
        "dept_kpi": fetch_department_kpi(),
        "monthly_trends": fetch_monthly_trends(),
        "leave_history": fetch_leave_history(),
        "dq": fetch_data_quality_artifacts(),
        "recommendations": fetch_recommendations(),
    }


@st.cache_resource
def load_ml_bundle() -> dict[str, Any]:
    return fetch_ml_and_shap_artifacts()


@st.cache_resource
def load_shap_explainer(_bundle: dict[str, Any], _bg_rows: pd.DataFrame) -> tuple[Any, str]:
    from src.ml.shap_explainer import _create_explainer
    from src.ml.train_models import FEATURE_COLUMNS

    pipe = _bundle["pipeline"]
    prep = pipe.named_steps["prep"]
    clf = pipe.named_steps["clf"]
    X_bg = prep.transform(_bg_rows[FEATURE_COLUMNS].head(50))
    return _create_explainer(clf, X_bg)


def _reset_sidebar_filters() -> None:
    for key in ("flt_dept", "flt_loc", "flt_desig", "flt_type", "flt_tenure"):
        if key in st.session_state:
            st.session_state[key] = []


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.markdown('<div class="sidebar-section-label">Cohort Filters</div>', unsafe_allow_html=True)
    depts = sorted(df["department_name"].dropna().unique().tolist())
    locs = sorted(df["location"].dropna().unique().tolist())
    desigs = sorted(df["designation"].dropna().unique().tolist())
    emp_types = sorted(df["employment_type"].dropna().unique().tolist())
    tenure_order = ["<1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
    tenures = [t for t in tenure_order if t in df["tenure_band"].dropna().unique()]

    sel_depts_raw = st.sidebar.multiselect(
        "Department",
        options=depts,
        default=[],
        key="flt_dept",
        placeholder="All Departments (type to search)",
    )
    sel_locs_raw = st.sidebar.multiselect(
        "Location",
        options=locs,
        default=[],
        key="flt_loc",
        placeholder="All Locations (type to search)",
    )

    with st.sidebar.expander("Role, Type & Tenure Filters", expanded=False):
        sel_desigs_raw = st.multiselect(
            "Designation",
            options=desigs,
            default=[],
            key="flt_desig",
            placeholder="All Designations (search)",
        )
        sel_types_raw = st.multiselect(
            "Employment Type",
            options=emp_types,
            default=[],
            key="flt_type",
            placeholder="All Employment Types",
        )
        sel_tenures_raw = st.multiselect(
            "Tenure Band",
            options=tenures,
            default=[],
            key="flt_tenure",
            placeholder="All Tenure Bands",
        )

    sel_depts = sel_depts_raw or depts
    sel_locs = sel_locs_raw or locs
    sel_desigs = sel_desigs_raw or desigs
    sel_types = sel_types_raw or emp_types
    sel_tenures = sel_tenures_raw or tenures

    filtered = df[
        df["department_name"].isin(sel_depts)
        & df["location"].isin(sel_locs)
        & df["designation"].isin(sel_desigs)
        & df["employment_type"].isin(sel_types)
        & df["tenure_band"].isin(sel_tenures)
    ].copy()

    active_filter_count = sum(
        1 for s in (sel_depts_raw, sel_locs_raw, sel_desigs_raw, sel_types_raw, sel_tenures_raw) if len(s) > 0
    )
    st.sidebar.markdown(
        f'<div class="filter-summary-pill"><b>Active Scope:</b> {len(filtered):,} of {len(df):,} records'
        + (f" ({active_filter_count} filter group{'s' if active_filter_count > 1 else ''})" if active_filter_count else " (Enterprise-Wide)")
        + "</div>",
        unsafe_allow_html=True,
    )
    if active_filter_count > 0:
        st.sidebar.button("Reset All Filters", on_click=_reset_sidebar_filters, width="stretch")

    return filtered


# =============================================================================
# PAGE 1: EXECUTIVE OVERVIEW
# =============================================================================
def page_executive_overview(df: pd.DataFrame, monthly_trends: pd.DataFrame, rec_data: dict[str, Any]) -> None:
    render_page_header(
        "Workforce Intelligence · Executive Summary",
        "Executive Workforce Overview",
        "Enterprise headcount, gross payroll expenditure, attrition rates, and prioritized retention recommendations.",
    )
    st.markdown(
        '<div class="disclaimer-banner">'
        "<strong>Synthetic Enterprise Dataset Notice:</strong> Metrics below reflect 24,953 cleaned synthetic HR/payroll records "
        "in the local SQLite Star Schema warehouse (not real-world company benchmarks)."
        "</div>",
        unsafe_allow_html=True,
    )

    total_emp = len(df)
    active_emp = int((df["is_active"] == 1).sum())
    total_payroll_inr = float(df["total_compensation"].sum())
    avg_comp_inr = float(df["total_compensation"].mean()) if df["total_compensation"].notna().any() else 0.0
    labeled = df.dropna(subset=["attrition_flag"])
    attr_rate = float(labeled["attrition_flag"].mean() * 100.0) if not labeled.empty else 0.0
    avg_tenure = float(df["tenure_years"].mean()) if not df.empty else 0.0
    risk_series = df["risk_tier"] if "risk_tier" in df.columns else pd.Series("Low", index=df.index)
    high_risk_cnt = int(((df["is_active"] == 1) & (risk_series == "High")).sum())

    render_kpi_grid(
        [
            {"label": "Total Employees", "value": f"{total_emp:,}", "sub": f"{active_emp:,} Active Staff"},
            {"label": "Total Payroll", "value": format_inr_crore(total_payroll_inr), "sub": "Annual Gross CTC"},
            {"label": "Avg Compensation", "value": format_inr(avg_comp_inr), "sub": format_inr_lakhs(avg_comp_inr)},
            {"label": "Attrition Rate", "value": f"{attr_rate:.2f}%", "sub": f"{int((labeled['attrition_flag']==1).sum()):,} Exited"},
            {"label": "Average Tenure", "value": f"{avg_tenure:.2f} yrs", "sub": "Filtered Cohort"},
            {"label": "Active High Risk", "value": f"{high_risk_cnt:,}", "sub": "ML Prob >= 65%"},
        ],
        columns_class="kpi-grid-6",
    )

    col_l, col_r = st.columns([1.1, 1.0], gap="medium")

    with col_l:
        with st.container(border=True):
            dept_agg = (
                df.groupby("department_name", as_index=False)
                .agg(
                    headcount=("employee_id", "count"),
                    payroll_cr=("total_compensation", lambda s: round(float(s.sum()) / 1e7, 2)),
                    attr_pct=("attrition_flag", lambda s: round(float(s.dropna().mean() * 100.0), 2) if s.notna().any() else 0.0),
                )
                .sort_values("payroll_cr", ascending=True)
            )
            fig_dept = px.bar(
                dept_agg,
                y="department_name",
                x="payroll_cr",
                color="attr_pct",
                color_continuous_scale=RISK_CONTINUOUS,
                orientation="h",
                text="headcount",
                title="Department Payroll (INR Cr) & Attrition Rate (%)",
                labels={"payroll_cr": "Annual Payroll (INR Cr)", "department_name": "", "attr_pct": "Attrition %"},
                custom_data=["headcount", "attr_pct"],
            )
            fig_dept.update_traces(
                texttemplate="HC: %{text:,}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Annual Payroll: ₹%{x:,.2f} Cr<br>Headcount: %{customdata[0]:,}<br>Attrition Rate: %{customdata[1]:.2f}%<extra></extra>",
            )
            max_pay = float(dept_agg["payroll_cr"].max()) if not dept_agg.empty else 100.0
            fig_dept.update_xaxes(range=[0, max_pay * 1.24])
            st.plotly_chart(style_plotly(fig_dept, 410, show_legend=False), width="stretch")

    with col_r:
        with st.container(border=True):
            mt = monthly_trends[monthly_trends["year_month"] >= "2023-01"].copy()
            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=mt["year_month"],
                    y=mt["hires_count"],
                    mode="lines",
                    name="Monthly Hires",
                    line=dict(color=COBALT, width=2.5),
                    hovertemplate="%{x}: <b>%{y:,}</b> hires<extra></extra>",
                )
            )
            fig_trend.add_trace(
                go.Scatter(
                    x=mt["year_month"],
                    y=mt["exits_count"],
                    mode="lines",
                    name="Monthly Exits",
                    line=dict(color=CRIMSON_RISK, width=2.5),
                    hovertemplate="%{x}: <b>%{y:,}</b> exits<extra></extra>",
                )
            )
            fig_trend.update_layout(
                title="Workforce Hiring vs. Attrition Trend (2023–2026)",
                xaxis_title="Month",
                yaxis_title="Employees",
                hovermode="x unified",
            )
            fig_trend.update_xaxes(nticks=10)
            st.plotly_chart(style_plotly(fig_trend, 410, legend_pos="top"), width="stretch")

    st.markdown('<div class="section-heading">Actionable Business Recommendations (Data-Driven)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Prioritized intervention roadmap derived directly from warehouse KPIs, EDA tests, and attrition driver attribution.</div>',
        unsafe_allow_html=True,
    )

    recs = rec_data.get("recommendations", [])
    if recs:
        prio_options = ["All Priorities", "Critical", "High", "Medium"]
        sel_prio = st.radio("Filter Priority", prio_options, horizontal=True, label_visibility="collapsed")
        shown_recs = recs if sel_prio == "All Priorities" else [r for r in recs if r["priority"] == sel_prio]

        for i in range(0, len(shown_recs), 2):
            rec_cols = st.columns(2, gap="medium")
            for col_slot, rec in zip(rec_cols, shown_recs[i : i + 2]):
                prio_cls = "high" if rec["priority"] == "High" else ("medium" if rec["priority"] == "Medium" else "")
                with col_slot:
                    st.markdown(
                        f"""
                        <div class="rec-card {prio_cls}">
                            <div class="rec-header">
                                <span class="rec-title">{html.escape(rec['id'])} · {html.escape(rec['category'])}</span>
                                <span class="rec-badge {prio_cls}">{html.escape(rec['priority'])}</span>
                            </div>
                            <div class="rec-owner">Owner: {html.escape(rec['owner'])}</div>
                            <div class="rec-row"><strong>Finding:</strong> {html.escape(rec['finding'])}</div>
                            <div class="rec-row"><strong>Metric:</strong> {html.escape(rec['supporting_metric'])}</div>
                            <div class="rec-row"><strong>Implication:</strong> {html.escape(rec['business_implication'])}</div>
                            <div class="rec-row"><strong>Action:</strong> {html.escape(rec['recommended_action'])}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        exp_c1, exp_c2, _ = st.columns([1.2, 1.2, 2.6])
        rec_df = pd.DataFrame(recs)
        with exp_c1:
            st.download_button(
                "Download Recommendations (CSV)",
                rec_df.to_csv(index=False).encode("utf-8"),
                file_name="business_recommendations.csv",
                mime="text/csv",
                width="stretch",
            )
        with exp_c2:
            st.download_button(
                "Download Filtered Workforce (CSV)",
                df.to_csv(index=False).encode("utf-8"),
                file_name="filtered_workforce_snapshot.csv",
                mime="text/csv",
                width="stretch",
            )


# =============================================================================
# PAGE 2: COMPENSATION ANALYTICS
# =============================================================================
def page_compensation_analytics(df: pd.DataFrame, dept_kpi: pd.DataFrame) -> None:
    render_page_header(
        "Total Rewards & Payroll Governance",
        "Compensation & Payroll Analytics",
        "Compensation distribution, salary structure across career bands, annual increment equity, and departmental budget utilization.",
    )
    comp = df.dropna(subset=["total_compensation", "basic_salary"]).copy()

    render_kpi_grid(
        [
            {"label": "Total Payroll", "value": format_inr_crore(comp["total_compensation"].sum()), "sub": f"{len(comp):,} Paid Staff"},
            {"label": "Avg Basic Salary", "value": format_inr(comp["basic_salary"].mean()), "sub": format_inr_lakhs(comp["basic_salary"].mean())},
            {"label": "Median Total Comp", "value": format_inr(comp["total_compensation"].median()), "sub": format_inr_lakhs(comp["total_compensation"].median())},
            {"label": "Avg Bonus", "value": format_inr(comp["bonus"].mean()), "sub": f"{comp['bonus_to_salary_ratio'].mean()*100:.1f}% of Basic"},
            {"label": "Avg Increment %", "value": f"{comp['salary_growth_pct'].mean():.2f}%", "sub": "Annual Raise Velocity"},
        ]
    )

    r1_l, r1_r = st.columns(2, gap="medium")
    with r1_l:
        with st.container(border=True):
            comp_hist = comp.assign(total_comp_lakhs=comp["total_compensation"] / 1e5)
            fig_hist = px.histogram(
                comp_hist[comp_hist["total_comp_lakhs"] <= 100],
                x="total_comp_lakhs",
                nbins=45,
                color_discrete_sequence=[COBALT],
                title="Total Compensation Distribution (INR Lakhs, <= ₹100L)",
                labels={"total_comp_lakhs": "Total Compensation (₹ Lakhs)", "count": "Employees"},
            )
            fig_hist.update_traces(hovertemplate="Band: ₹%{x:.1f}L<br>Employees: %{y:,}<extra></extra>")
            fig_hist.update_yaxes(title_text="Employees")
            st.plotly_chart(style_plotly(fig_hist, 385, show_legend=False), width="stretch")

    with r1_r:
        with st.container(border=True):
            dept_sal = (
                comp.groupby("department_name", as_index=False)
                .agg(
                    avg_comp=("total_compensation", "mean"),
                    med_comp=("total_compensation", "median"),
                    payroll_cr=("total_compensation", lambda s: s.sum() / 1e7),
                )
                .sort_values("avg_comp", ascending=True)
            )
            dept_sal["avg_comp_lakhs"] = dept_sal["avg_comp"] / 1e5
            fig_ds = px.bar(
                dept_sal,
                y="department_name",
                x="avg_comp_lakhs",
                orientation="h",
                color_discrete_sequence=[NAVY_PRIMARY],
                text="avg_comp_lakhs",
                title="Average Total Compensation by Department (₹ Lakhs)",
                labels={"avg_comp_lakhs": "Avg Total Comp (₹ Lakhs)", "department_name": ""},
                custom_data=["med_comp", "payroll_cr"],
            )
            fig_ds.update_traces(
                texttemplate="₹%{text:.1f}L",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Mean Comp: ₹%{x:.2f}L<br>Median Comp: ₹%{customdata[0]:,.0f}<br>Payroll: ₹%{customdata[1]:,.2f} Cr<extra></extra>",
            )
            max_l = float(dept_sal["avg_comp_lakhs"].max()) if not dept_sal.empty else 30.0
            fig_ds.update_xaxes(range=[0, max_l * 1.22])
            st.plotly_chart(style_plotly(fig_ds, 385, show_legend=False), width="stretch")

    r2_l, r2_r = st.columns(2, gap="medium")
    with r2_l:
        with st.container(border=True):
            desig_agg = (
                comp.groupby("designation", as_index=False)
                .agg(
                    avg_basic=("basic_salary", "mean"),
                    avg_allow=("allowances", "mean"),
                    avg_bonus=("bonus", "mean"),
                    avg_tot=("total_compensation", "mean"),
                )
                .sort_values("avg_tot", ascending=True)
            )
            fig_desig = go.Figure()
            fig_desig.add_trace(go.Bar(y=desig_agg["designation"], x=desig_agg["avg_basic"] / 1e5, name="Basic", orientation="h", marker_color=NAVY_PRIMARY, hovertemplate="%{y} · Basic: ₹%{x:.2f}L<extra></extra>"))
            fig_desig.add_trace(go.Bar(y=desig_agg["designation"], x=desig_agg["avg_allow"] / 1e5, name="Allowances", orientation="h", marker_color=COBALT, hovertemplate="%{y} · Allowances: ₹%{x:.2f}L<extra></extra>"))
            fig_desig.add_trace(go.Bar(y=desig_agg["designation"], x=desig_agg["avg_bonus"] / 1e5, name="Bonus", orientation="h", marker_color=TEAL_ACCENT, hovertemplate="%{y} · Bonus: ₹%{x:.2f}L<extra></extra>"))
            fig_desig.update_layout(barmode="stack", title="Average Compensation Mix by Designation (₹ Lakhs)", xaxis_title="INR Lakhs", hovermode="y unified")
            st.plotly_chart(style_plotly(fig_desig, 405, legend_pos="top"), width="stretch")

    with r2_r:
        with st.container(border=True):
            bu = (
                comp.groupby("department_name", as_index=False)
                .agg(actual_cr=("total_compensation", lambda s: round(s.sum() / 1e7, 2)))
                .merge(dept_kpi[["department_name", "annual_budget_cr"]], on="department_name", how="left")
            )
            bu["utilization_pct"] = np.round(100.0 * bu["actual_cr"] / bu["annual_budget_cr"].replace(0, np.nan), 1)
            bu = bu.sort_values("utilization_pct", ascending=False)
            fig_bu = go.Figure()
            fig_bu.add_trace(
                go.Bar(
                    x=bu["department_name"],
                    y=bu["actual_cr"],
                    name="Actual Payroll (Cr)",
                    marker_color=COBALT,
                    customdata=bu["utilization_pct"],
                    hovertemplate="<b>%{x}</b><br>Payroll: ₹%{y:,.2f} Cr<br>Utilization: %{customdata:.1f}%<extra></extra>",
                )
            )
            fig_bu.add_trace(
                go.Bar(
                    x=bu["department_name"],
                    y=bu["annual_budget_cr"],
                    name="Allocated Budget (Cr)",
                    marker_color="#94A3B8",
                    hovertemplate="<b>%{x}</b><br>Budget: ₹%{y:,.2f} Cr<extra></extra>",
                )
            )
            fig_bu.update_layout(barmode="group", title="Department Payroll vs. Budget Utilization (INR Cr)", yaxis_title="INR Crores", hovermode="x unified")
            fig_bu.update_xaxes(tickangle=-25)
            st.plotly_chart(style_plotly(fig_bu, 405, legend_pos="top"), width="stretch")

    r3_l, r3_r = st.columns(2, gap="medium")
    with r3_l:
        with st.container(border=True):
            perf_bonus = comp.groupby("performance_rating", as_index=False).agg(
                avg_bonus_inr=("bonus", "mean"),
                avg_growth_pct=("salary_growth_pct", "mean"),
            )
            fig_pb = px.bar(
                perf_bonus,
                x="performance_rating",
                y="avg_bonus_inr",
                color="avg_growth_pct",
                color_continuous_scale=NAVY_CONTINUOUS,
                title="Bonus & Increment Growth by Performance Rating",
                labels={"performance_rating": "Performance Rating", "avg_bonus_inr": "Avg Bonus (INR)", "avg_growth_pct": "Avg Raise %"},
                custom_data=["avg_growth_pct"],
            )
            fig_pb.update_traces(hovertemplate="Rating %{x}<br>Avg Bonus: ₹%{y:,.0f}<br>Avg Salary Growth: %{customdata[0]:.2f}%<extra></extra>")
            fig_pb.update_xaxes(dtick=1)
            st.plotly_chart(style_plotly(fig_pb, 365, show_legend=False), width="stretch")

    with r3_r:
        with st.container(border=True):
            elig = comp[(comp["employment_type"] != "Intern") & (comp["tenure_years"] >= 1.0)]
            fig_inc = px.box(
                elig,
                x="department_name",
                y="salary_growth_pct",
                color="department_name",
                color_discrete_sequence=COLOR_SEQ,
                title="Annual Salary Increment % Spread Across Departments",
                labels={"department_name": "", "salary_growth_pct": "Salary Growth (%)"},
            )
            fig_inc.update_xaxes(tickangle=-25)
            st.plotly_chart(style_plotly(fig_inc, 365, show_legend=False), width="stretch")

    st.download_button(
        "Download Compensation Summary by Department (CSV)",
        bu.to_csv(index=False).encode("utf-8"),
        file_name="department_budget_utilization.csv",
        mime="text/csv",
    )


# =============================================================================
# PAGE 3: WORKFORCE ANALYTICS
# =============================================================================
def page_workforce_analytics(df: pd.DataFrame, leave_history: pd.DataFrame) -> None:
    render_page_header(
        "Demographics, Mobility & Capacity",
        "Workforce Demographics, Tenure, Leave & Performance",
        "Geographic footprint, qualification mix, hiring cohorts, tenure maturity, overtime trends, and appraisal calibration.",
    )

    render_kpi_grid(
        [
            {"label": "Filtered Workforce", "value": f"{len(df):,}", "sub": f"{int((df['is_active']==1).sum()):,} Active"},
            {"label": "Avg Age", "value": f"{df['age_years'].mean():.1f} yrs", "sub": "Enterprise Talent Age"},
            {"label": "Avg Experience", "value": f"{df['experience_years'].mean():.1f} yrs", "sub": f"Tenure: {df['tenure_years'].mean():.2f} yrs"},
            {"label": "Avg Ann. Leave", "value": f"{df['annualized_leave_days'].mean():.1f} days", "sub": "Per Year (Normalized)"},
            {"label": "Avg Perf Rating", "value": f"{df['performance_rating'].mean():.2f} / 5", "sub": f"Manager: {df['manager_rating'].mean():.2f} / 5"},
        ]
    )

    r1_l, r1_r = st.columns(2, gap="medium")
    with r1_l:
        with st.container(border=True):
            loc_df = df.groupby(["location", "region"], as_index=False).agg(headcount=("employee_id", "count"), avg_comp=("total_compensation", "mean")).sort_values("headcount", ascending=False)
            fig_loc = px.bar(
                loc_df,
                x="location",
                y="headcount",
                color="region",
                text="headcount",
                color_discrete_sequence=[NAVY_PRIMARY, COBALT, TEAL_ACCENT],
                title="Location-Wise Headcount Distribution",
                labels={"location": "City", "headcount": "Employees", "region": "Region"},
                custom_data=["avg_comp"],
            )
            fig_loc.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Employees: %{y:,}<br>Avg Total Comp: ₹%{customdata[0]:,.0f}<extra></extra>",
            )
            max_hc = float(loc_df["headcount"].max()) if not loc_df.empty else 100.0
            fig_loc.update_yaxes(range=[0, max_hc * 1.18])
            st.plotly_chart(style_plotly(fig_loc, 390, legend_pos="top"), width="stretch")

    with r1_r:
        with st.container(border=True):
            edu_df = df.groupby("education", as_index=False).size().sort_values("size", ascending=True)
            fig_et = px.bar(
                edu_df,
                y="education",
                x="size",
                text="size",
                orientation="h",
                color_discrete_sequence=[TEAL_ACCENT],
                title="Education Qualification Distribution",
                labels={"size": "Employees", "education": ""},
            )
            fig_et.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b>: %{x:,} employees<extra></extra>",
            )
            max_edu = float(edu_df["size"].max()) if not edu_df.empty else 100.0
            fig_et.update_xaxes(range=[0, max_edu * 1.18])
            st.plotly_chart(style_plotly(fig_et, 390, show_legend=False), width="stretch")

    r2_l, r2_r = st.columns(2, gap="medium")
    with r2_l:
        with st.container(border=True):
            hire_df = df.assign(join_year=pd.to_datetime(df["joining_date"]).dt.year)
            hire_yr = hire_df.groupby(["join_year", "department_name"], as_index=False).size()
            fig_hire = px.area(
                hire_yr[hire_yr["join_year"] >= 2018],
                x="join_year",
                y="size",
                color="department_name",
                color_discrete_sequence=COLOR_SEQ,
                title="Annual Hiring Cohort Mix (2018–2026)",
                labels={"join_year": "Joining Year", "size": "Hires", "department_name": ""},
            )
            fig_hire.update_layout(hovermode="x unified")
            fig_hire.update_xaxes(dtick=1)
            st.plotly_chart(style_plotly(fig_hire, 425, legend_pos="bottom", b_margin=105), width="stretch")

    with r2_r:
        with st.container(border=True):
            ten_order = ["<1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
            ten_dist = df.groupby("tenure_band", as_index=False).size()
            ten_dist["tenure_band"] = pd.Categorical(ten_dist["tenure_band"], categories=ten_order, ordered=True)
            ten_dist = ten_dist.sort_values("tenure_band")
            fig_ten = px.bar(
                ten_dist,
                x="tenure_band",
                y="size",
                text="size",
                color_discrete_sequence=[NAVY_PRIMARY],
                title="Workforce Distribution by Tenure Band",
                labels={"tenure_band": "Tenure Band", "size": "Employees"},
            )
            fig_ten.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Tenure %{x}: <b>%{y:,}</b> employees<extra></extra>",
            )
            max_td = float(ten_dist["size"].max()) if not ten_dist.empty else 100.0
            fig_ten.update_yaxes(range=[0, max_td * 1.18])
            st.plotly_chart(style_plotly(fig_ten, 425, show_legend=False), width="stretch")

    r3_l, r3_r = st.columns(2, gap="medium")
    with r3_l:
        with st.container(border=True):
            sel_depts = df["department_name"].unique().tolist()
            lh = leave_history[leave_history["department_name"].isin(sel_depts)]
            fig_lv = px.line(
                lh,
                x="year",
                y="avg_ann_overtime_hrs",
                color="department_name",
                markers=True,
                color_discrete_sequence=COLOR_SEQ,
                title="Multi-Year Annualized Overtime Trend (2024–2026)",
                labels={"year": "Year", "avg_ann_overtime_hrs": "Avg Annualized Overtime (hrs)", "department_name": ""},
            )
            fig_lv.update_layout(hovermode="x unified")
            fig_lv.update_xaxes(dtick=1)
            st.plotly_chart(style_plotly(fig_lv, 420, legend_pos="bottom", b_margin=105), width="stretch")

    with r3_r:
        with st.container(border=True):
            fig_pm = px.density_heatmap(
                df,
                x="manager_rating",
                y="performance_rating",
                color_continuous_scale=NAVY_CONTINUOUS,
                text_auto=True,
                title="Performance Rating vs. Manager Rating Matrix",
                labels={"manager_rating": "Manager Rating", "performance_rating": "Performance Rating"},
            )
            fig_pm.update_xaxes(dtick=1)
            fig_pm.update_yaxes(dtick=1)
            st.plotly_chart(style_plotly(fig_pm, 420, show_legend=False), width="stretch")


# =============================================================================
# PAGE 4: ATTRITION ANALYTICS
# =============================================================================
def page_attrition_analytics(df: pd.DataFrame) -> None:
    render_page_header(
        "Retention Risk & Turnover Drivers",
        "Attrition & Retention Driver Analytics",
        "Departmental turnover targets, promotion stagnation impacts, tenure vulnerability curves, and cited exit drivers.",
    )
    labeled = df.dropna(subset=["attrition_flag"]).copy()
    labeled["attrition_flag"] = labeled["attrition_flag"].astype(int)
    exited = labeled[labeled["attrition_flag"] == 1]

    top_reason = exited["exit_reason"].mode()[0] if not exited.empty and exited["exit_reason"].notna().any() else "N/A"
    active_pg = labeled.loc[labeled["attrition_flag"] == 0, "promotion_gap"].mean()
    active_pg_str = f"Active Mean: {active_pg:.2f} yrs" if pd.notna(active_pg) else "Active Mean: N/A"
    render_kpi_grid(
        [
            {"label": "Overall Attrition", "value": f"{labeled['attrition_flag'].mean()*100:.2f}%" if not labeled.empty else "0.00%", "sub": f"{len(exited):,} Exited Staff"},
            {"label": "Avg Exited Tenure", "value": f"{exited['tenure_years'].mean():.2f} yrs" if not exited.empty else "N/A", "sub": "At Time of Exit"},
            {"label": "Exited Promo Gap", "value": f"{exited['promotion_gap'].mean():.2f} yrs" if not exited.empty else "N/A", "sub": active_pg_str},
            {"label": "Exited Comp Base", "value": format_inr_crore(exited["total_compensation"].sum()), "sub": "Turnover Payroll Exposure"},
            {"label": "Top Exit Reason", "value": str(top_reason), "sub": "Most Cited Driver", "wrap_text": True},
        ]
    )

    r1_l, r1_r = st.columns(2, gap="medium")
    with r1_l:
        with st.container(border=True):
            dept_a = (
                labeled.groupby("department_name", as_index=False)
                .agg(attr_pct=("attrition_flag", lambda s: round(s.mean() * 100.0, 2)), target=("target_attrition_pct", "max"), exits=("attrition_flag", "sum"))
                .sort_values("attr_pct", ascending=True)
            )
            fig_da = go.Figure()
            fig_da.add_trace(
                go.Bar(
                    y=dept_a["department_name"],
                    x=dept_a["attr_pct"],
                    orientation="h",
                    name="Actual Attrition %",
                    marker_color=NAVY_PRIMARY,
                    customdata=dept_a["exits"],
                    text=dept_a["attr_pct"],
                    texttemplate="%{text:.1f}%",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Attrition: %{x:.2f}%<br>Exits: %{customdata:,}<extra></extra>",
                )
            )
            fig_da.add_trace(
                go.Scatter(
                    y=dept_a["department_name"],
                    x=dept_a["target"],
                    mode="markers",
                    name="Target Threshold %",
                    marker=dict(color=CRIMSON_RISK, size=10, symbol="diamond"),
                    hovertemplate="<b>%{y}</b> Target: %{x:.1f}%<extra></extra>",
                )
            )
            fig_da.update_layout(title="Department Attrition Rate vs. Target Threshold", xaxis_title="Attrition Rate (%)")
            max_attr = float(max(dept_a["attr_pct"].max(), dept_a["target"].max())) if not dept_a.empty else 25.0
            fig_da.update_xaxes(range=[0, max_attr * 1.22])
            st.plotly_chart(style_plotly(fig_da, 395, legend_pos="top"), width="stretch")

    with r1_r:
        with st.container(border=True):
            pg = labeled.assign(
                pg_bucket=pd.cut(labeled["promotion_gap"], bins=[-0.1, 1.5, 2.5, 4.0, 30.0], labels=["<=1.5 yrs", "1.5-2.5 yrs", "2.5-4.0 yrs", "4.0+ yrs"])
            )
            pg_agg = pg.groupby("pg_bucket", observed=False, as_index=False).agg(attr_pct=("attrition_flag", lambda s: round(s.mean() * 100.0, 2)), n=("employee_id", "count"))
            fig_pg = px.bar(
                pg_agg,
                x="pg_bucket",
                y="attr_pct",
                text="attr_pct",
                color="attr_pct",
                color_continuous_scale=RISK_CONTINUOUS,
                title="Promotion Gap vs. Attrition Rate (%)",
                labels={"pg_bucket": "Years Since Last Promotion", "attr_pct": "Attrition Rate (%)"},
                custom_data=["n"],
            )
            fig_pg.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Attrition Rate: %{y:.2f}%<br>Cohort Size: %{customdata[0]:,}<extra></extra>",
            )
            max_pg = float(pg_agg["attr_pct"].max()) if not pg_agg.empty else 30.0
            fig_pg.update_yaxes(range=[0, max_pg * 1.22])
            st.plotly_chart(style_plotly(fig_pg, 395, show_legend=False), width="stretch")

    r2_l, r2_r = st.columns(2, gap="medium")
    with r2_l:
        with st.container(border=True):
            ten_order = ["<1 yr", "1-3 yrs", "3-5 yrs", "5-10 yrs", "10+ yrs"]
            ta = labeled.groupby("tenure_band", as_index=False).agg(attr_pct=("attrition_flag", lambda s: round(s.mean() * 100.0, 2)), n=("employee_id", "count"))
            ta["tenure_band"] = pd.Categorical(ta["tenure_band"], categories=ten_order, ordered=True)
            ta = ta.sort_values("tenure_band")
            fig_ta = px.line(
                ta,
                x="tenure_band",
                y="attr_pct",
                markers=True,
                text="attr_pct",
                title="Attrition Curve Across Tenure Bands",
                labels={"tenure_band": "Tenure Band", "attr_pct": "Attrition Rate (%)"},
                custom_data=["n"],
            )
            fig_ta.update_traces(
                line_color=COBALT,
                line_width=3,
                marker_size=9,
                texttemplate="%{text:.1f}%",
                textposition="top center",
                hovertemplate="<b>%{x}</b><br>Attrition Rate: %{y:.2f}%<br>Cohort: %{customdata[0]:,}<extra></extra>",
            )
            max_ta = float(ta["attr_pct"].max()) if not ta.empty else 20.0
            fig_ta.update_yaxes(range=[0, max_ta * 1.24])
            st.plotly_chart(style_plotly(fig_ta, 370, show_legend=False), width="stretch")

    with r2_r:
        with st.container(border=True):
            sal_order = ["<8L", "8L-15L", "15L-25L", "25L-40L", "40L+"]
            sa = labeled.dropna(subset=["salary_band"]).groupby("salary_band", as_index=False).agg(attr_pct=("attrition_flag", lambda s: round(s.mean() * 100.0, 2)), n=("employee_id", "count"))
            sa["salary_band"] = pd.Categorical(sa["salary_band"], categories=sal_order, ordered=True)
            sa = sa.sort_values("salary_band")
            fig_sa = px.bar(
                sa,
                x="salary_band",
                y="attr_pct",
                text="attr_pct",
                color_discrete_sequence=[NAVY_MID],
                title="Attrition Rate by Total Compensation Band (INR)",
                labels={"salary_band": "Total Comp Band", "attr_pct": "Attrition Rate (%)"},
                custom_data=["n"],
            )
            fig_sa.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Attrition: %{y:.2f}%<br>Employees: %{customdata[0]:,}<extra></extra>",
            )
            max_sa = float(sa["attr_pct"].max()) if not sa.empty else 20.0
            fig_sa.update_yaxes(range=[0, max_sa * 1.22])
            st.plotly_chart(style_plotly(fig_sa, 370, show_legend=False), width="stretch")

    r3_l, r3_r = st.columns(2, gap="medium")
    with r3_l:
        with st.container(border=True):
            pa = labeled.groupby("performance_rating", as_index=False).agg(attr_pct=("attrition_flag", lambda s: round(s.mean() * 100.0, 2)), n=("employee_id", "count"))
            fig_pa = px.bar(
                pa,
                x="performance_rating",
                y="attr_pct",
                text="attr_pct",
                color="attr_pct",
                color_continuous_scale=RISK_CONTINUOUS,
                title="Attrition Rate by Performance Rating (1–5)",
                labels={"performance_rating": "Performance Rating", "attr_pct": "Attrition Rate (%)"},
                custom_data=["n"],
            )
            fig_pa.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="Rating %{x}<br>Attrition: %{y:.2f}%<br>Employees: %{customdata[0]:,}<extra></extra>",
            )
            fig_pa.update_xaxes(dtick=1)
            max_pa = float(pa["attr_pct"].max()) if not pa.empty else 30.0
            fig_pa.update_yaxes(range=[0, max_pa * 1.22])
            st.plotly_chart(style_plotly(fig_pa, 370, show_legend=False), width="stretch")

    with r3_r:
        with st.container(border=True):
            er = exited["exit_reason"].value_counts().reset_index()
            er.columns = ["exit_reason", "count"]
            if er.empty:
                st.info("No exited employees in the selected cohort.")
            else:
                fig_er = px.pie(
                    er,
                    names="exit_reason",
                    values="count",
                    hole=0.48,
                    color_discrete_sequence=COLOR_SEQ,
                    title="Primary Exit Reasons Breakdown",
                )
                fig_er.update_traces(
                    textposition="inside",
                    textinfo="percent",
                    hovertemplate="<b>%{label}</b><br>Exits: %{value:,} (%{percent})<extra></extra>",
                )
                st.plotly_chart(style_plotly(fig_er, 370, legend_pos="right"), width="stretch")


# =============================================================================
# PAGE 5: DATA QUALITY
# =============================================================================
def page_data_quality(dq_artifacts: dict[str, Any]) -> None:
    render_page_header(
        "ETL Governance & Schema Auditing",
        "Data Quality & Pipeline Governance",
        "Pre-ETL validation dimension scores, detected payroll anomalies, deduplication logs, and quarantined record inspection.",
    )
    dq = dq_artifacts.get("dq_report", {})
    etl = dq_artifacts.get("etl_summary", {})
    hs = dq.get("headline_summary", {})
    qs = dq.get("quality_scores_pct", {})

    total_dups = hs.get("duplicate_employee_records", 0) + hs.get("duplicate_payroll_records", 0)
    total_q = sum(etl.get("quarantined_counts", {}).values())
    render_kpi_grid(
        [
            {"label": "Overall DQ Score", "value": f"{qs.get('overall_data_quality_score', 0):.2f}%", "sub": "Weighted Pre-ETL Score"},
            {"label": "Raw Records", "value": f"{dq.get('total_raw_records_all_tables', 0):,}", "sub": "Across 5 HR/Payroll Files"},
            {"label": "Duplicate Records", "value": f"{total_dups:,}", "sub": "Emp + Payroll Duplicates"},
            {"label": "Salary Anomalies", "value": f"{hs.get('salary_anomalies', 0):,}", "sub": "Out-of-Band Flagged"},
            {"label": "Quarantined Rows", "value": f"{total_q:,}", "sub": "Isolated in Audit CSVs"},
        ]
    )

    col_l, col_r = st.columns(2, gap="medium")
    with col_l:
        with st.container(border=True):
            dim_df = pd.DataFrame(
                [
                    {"Dimension": k.replace("_", " ").title(), "Score (%)": v}
                    for k, v in qs.items()
                    if k != "overall_data_quality_score"
                ]
            )
            fig_dq = px.bar(
                dim_df,
                x="Dimension",
                y="Score (%)",
                text="Score (%)",
                color="Score (%)",
                color_continuous_scale=[COBALT, TEAL_ACCENT],
                range_y=[90, 102.5],
                title="Data Quality Dimension Scores (%)",
            )
            fig_dq.update_traces(
                texttemplate="%{text:.2f}%",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Quality Score: %{y:.2f}%<extra></extra>",
            )
            fig_dq.update_xaxes(tickangle=-18)
            st.plotly_chart(style_plotly(fig_dq, 385, show_legend=False), width="stretch")

    with col_r:
        with st.container(border=True):
            defect_df = pd.DataFrame(
                [
                    {"Check": k.replace("_", " ").title(), "Count": v}
                    for k, v in hs.items()
                    if k not in ("total_employee_records", "unique_valid_employees")
                ]
            ).sort_values("Count", ascending=True)
            fig_def = px.bar(
                defect_df,
                y="Check",
                x="Count",
                text="Count",
                orientation="h",
                color_discrete_sequence=[AMBER_WARN],
                title="Detected Pre-ETL Defects & Standardization Counts",
            )
            fig_def.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b>: %{x:,} records<extra></extra>",
            )
            max_def = float(defect_df["Count"].max()) if not defect_df.empty else 100.0
            fig_def.update_xaxes(range=[0, max_def * 1.18])
            st.plotly_chart(style_plotly(fig_def, 385, show_legend=False), width="stretch")

    with st.container(border=True):
        st.markdown('<div class="section-heading" style="margin-top:0;">Quarantine & Anomaly Inspection</div>', unsafe_allow_html=True)
        q_files = dq_artifacts.get("quarantine_files", {})
        if q_files:
            sel_q = st.selectbox("Select Quarantine / Anomaly Audit File", list(q_files.keys()))
            q_df = q_files[sel_q]
            st.caption(f"Showing `{len(q_df):,}` quarantined/flagged rows from `data/quarantine/{sel_q}`")
            st.dataframe(q_df.head(100), width="stretch")
            st.download_button(
                f"Download {sel_q}",
                q_df.to_csv(index=False).encode("utf-8"),
                file_name=sel_q,
                mime="text/csv",
            )


# =============================================================================
# PAGE 6: PREDICTIVE ANALYTICS & SHAP EXPLAINABILITY
# =============================================================================
def page_predictive_analytics(df: pd.DataFrame, ml_artifacts: dict[str, Any]) -> None:
    render_page_header(
        "Machine Learning & Explainability",
        "Predictive Attrition Risk & SHAP Explainability",
        "Leakage-controlled model comparison (LogReg vs. Random Forest vs. XGBoost), global feature attribution, and live individual scoring.",
    )
    comp_meta = ml_artifacts.get("comparison", {})
    bundle = ml_artifacts.get("bundle")
    shap_summary = ml_artifacts.get("shap_summary", {})

    if not comp_meta or bundle is None:
        st.error("Trained ML model artifacts not found. Run `python -m src.ml.train_models` and `python -m src.ml.shap_explainer`.")
        return

    best_name = comp_meta["best_model_name"]
    best_m = comp_meta["models"][best_name]["test_recall_optimized"]

    render_kpi_grid(
        [
            {"label": "Champion Model", "value": best_name, "sub": f"Decision Threshold: {best_m['threshold']:.2f}", "wrap_text": True},
            {"label": "Test ROC-AUC", "value": f"{best_m['roc_auc']:.4f}", "sub": f"5-Fold CV: {comp_meta['models'][best_name]['cv_roc_auc']:.4f}"},
            {"label": "Test Recall", "value": f"{best_m['recall']*100:.1f}%", "sub": "Prioritized Retention Metric"},
            {"label": "Test F1 / PR-AUC", "value": f"{best_m['f1_score']:.3f}", "sub": f"PR-AUC: {best_m['pr_auc']:.3f}"},
            {"label": "Active High Risk", "value": f"{comp_meta['active_high_risk_count']:,}", "sub": "Predicted Prob >= 65%"},
        ]
    )

    comp_rows = []
    for name, res in comp_meta["models"].items():
        m = res["test_recall_optimized"]
        comp_rows.append(
            {
                "Model": name,
                "Threshold": m["threshold"],
                "Accuracy": m["accuracy"],
                "Precision": m["precision"],
                "Recall": m["recall"],
                "F1-Score": m["f1_score"],
                "ROC-AUC": m["roc_auc"],
                "PR-AUC": m["pr_auc"],
            }
        )
    comp_df = pd.DataFrame(comp_rows)

    with st.container(border=True):
        st.markdown("**Model Comparison (Held-Out Test Set)**")
        st.dataframe(
            comp_df,
            hide_index=True,
            width="stretch",
            column_config={
                "Model": st.column_config.TextColumn("Model"),
                "Threshold": st.column_config.NumberColumn("Threshold", format="%.2f"),
                "Accuracy": st.column_config.NumberColumn("Accuracy", format="%.4f"),
                "Precision": st.column_config.NumberColumn("Precision", format="%.4f"),
                "Recall": st.column_config.NumberColumn("Recall", format="%.4f"),
                "F1-Score": st.column_config.NumberColumn("F1-Score", format="%.4f"),
                "ROC-AUC": st.column_config.NumberColumn("ROC-AUC", format="%.4f"),
                "PR-AUC": st.column_config.NumberColumn("PR-AUC", format="%.4f"),
            },
        )

    col_m1, col_m2 = st.columns(2, gap="medium")
    with col_m1:
        with st.container(border=True):
            melt_df = comp_df.melt(id_vars="Model", value_vars=["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"], var_name="Metric", value_name="Score")
            fig_mc = px.bar(
                melt_df,
                x="Metric",
                y="Score",
                color="Model",
                barmode="group",
                color_discrete_sequence=[SLATE_MUTED, COBALT, NAVY_PRIMARY],
                title="Performance Comparison Across Candidate Models",
                labels={"Model": ""},
            )
            fig_mc.update_traces(hovertemplate="<b>%{fullData.name}</b><br>%{x}: %{y:.4f}<extra></extra>")
            fig_mc.update_yaxes(range=[0, 1.05])
            st.plotly_chart(style_plotly(fig_mc, 400, legend_pos="top"), width="stretch")

    with col_m2:
        with st.container(border=True):
            active_df = df[df["is_active"] == 1].dropna(subset=["attrition_probability"]).copy()
            fig_rd = px.histogram(
                active_df,
                x="attrition_probability",
                color="risk_tier",
                nbins=40,
                color_discrete_map={"High": CRIMSON_RISK, "Medium": AMBER_WARN, "Low": TEAL_ACCENT},
                category_orders={"risk_tier": ["Low", "Medium", "High"]},
                title="Active Workforce Risk Distribution (Predicted Prob.)",
                labels={"attrition_probability": "Predicted Attrition Probability", "risk_tier": ""},
            )
            fig_rd.add_vline(
                x=float(best_m["threshold"]),
                line_dash="dash",
                line_color=NAVY_PRIMARY,
                annotation_text=f"Threshold {best_m['threshold']:.2f}",
                annotation_position="top right",
            )
            fig_rd.update_yaxes(title_text="Active Employees")
            st.plotly_chart(style_plotly(fig_rd, 400, legend_pos="top"), width="stretch")

    st.markdown('<div class="section-heading">Global SHAP Explainability (Non-Causal Predictive Drivers)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">SHAP values quantify feature contributions to the model prediction; they do not establish real-world causation.</div>',
        unsafe_allow_html=True,
    )
    dom_imp = pd.DataFrame(shap_summary.get("domain_feature_importance", []))
    sh_l, sh_r = st.columns(2, gap="medium")
    with sh_l:
        with st.container(border=True):
            if not dom_imp.empty:
                top12 = dom_imp.head(12).iloc[::-1]
                fig_sh = px.bar(
                    top12,
                    x="mean_abs_shap",
                    y="feature",
                    orientation="h",
                    text="mean_abs_shap",
                    color_discrete_sequence=[NAVY_PRIMARY],
                    title="Top 12 Global Risk Drivers (Mean |SHAP|)",
                    labels={"mean_abs_shap": "Mean |SHAP Contribution|", "feature": ""},
                )
                fig_sh.update_traces(
                    texttemplate="%{text:.3f}",
                    textposition="outside",
                    cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>Mean |SHAP|: %{x:.4f}<extra></extra>",
                )
                max_shap = float(top12["mean_abs_shap"].max())
                fig_sh.update_xaxes(range=[0, max_shap * 1.2])
                st.plotly_chart(style_plotly(fig_sh, 420, show_legend=False), width="stretch")
    with sh_r:
        with st.container(border=True):
            beeswarm_path = PATHS.reports / "figures" / "13_shap_summary_beeswarm.png"
            if beeswarm_path.exists():
                st.image(str(beeswarm_path), caption="SHAP Summary Beeswarm Plot (Encoded Features)", width="stretch")

    with st.container(border=True):
        st.markdown('<div class="section-heading" style="margin-top:0;">Individual Employee Risk Scoring & Live SHAP Explanation</div>', unsafe_allow_html=True)
        mode_choice = st.radio("Inspection Mode", ["Select Existing Active Employee", "Custom What-If Employee Profile"], horizontal=True)

        active_list = df[df["is_active"] == 1].sort_values("attrition_probability", ascending=False)
        emp_row: pd.DataFrame | None = None
        if mode_choice == "Select Existing Active Employee":
            if active_list.empty:
                st.warning("No active employees match the current filters. Switch to Custom What-If Employee Profile or widen filters.")
            else:
                top_sample = active_list.head(250)
                labels = [
                    f"{r['employee_id']} | {r['department_name']} - {r['designation']} (Risk: {r['attrition_probability']*100:.1f}%)"
                    for _, r in top_sample.iterrows()
                ]
                sel_idx = st.selectbox("Select Employee (Sorted by Highest Risk)", range(len(labels)), format_func=lambda i: labels[i])
                emp_row = top_sample.iloc[[sel_idx]]
        else:
            w1, w2, w3, w4 = st.columns(4)
            with w1:
                w_dept = st.selectbox("Department", sorted(df["department_name"].unique()))
                w_loc = st.selectbox("Location", sorted(df["location"].unique()))
                w_desig = st.selectbox("Designation", sorted(df["designation"].unique()))
            with w2:
                w_age = st.slider("Age (Years)", 21, 60, 30)
                w_ten = st.slider("Tenure (Years)", 0.2, 15.0, 3.2, 0.2)
                w_pgap = st.slider("Promotion Gap (Years)", 0.0, 10.0, 3.5, 0.2)
            with w3:
                w_comp = st.number_input("Total Compensation (INR)", 300_000, 15_000_000, 1_800_000, 100_000)
                w_growth = st.slider("Salary Growth (%)", 0.0, 22.0, 3.5, 0.5)
                w_perf = st.slider("Performance Rating", 1, 5, 4)
            with w4:
                w_mgr = st.slider("Manager Rating", 1, 5, 3)
                w_ot = st.slider("Annualized Overtime (hrs)", 0, 500, 220, 10)
                w_leave = st.slider("Annualized Leave Days", 0, 45, 22, 1)

            emp_row = pd.DataFrame(
                [
                    {
                        "employee_id": "CUSTOM_SIM",
                        "department_name": w_dept,
                        "location": w_loc,
                        "designation": w_desig,
                        "employment_type": "Full-Time",
                        "education": "B.Tech",
                        "age_years": float(w_age),
                        "experience_years": float(max(w_ten, w_ten + 2.0)),
                        "tenure_years": float(w_ten),
                        "basic_salary": float(w_comp * 0.65),
                        "allowances": float(w_comp * 0.23),
                        "bonus": float(w_comp * 0.12),
                        "total_compensation": float(w_comp),
                        "salary_increment": float(w_comp * (w_growth / 100.0)),
                        "salary_growth_pct": float(w_growth),
                        "bonus_to_salary_ratio": 0.18,
                        "performance_rating": int(w_perf),
                        "manager_rating": int(w_mgr),
                        "promotion_count": 1 if w_ten > 2.5 and w_pgap < w_ten else 0,
                        "promotion_gap": float(w_pgap),
                        "training_hours": 28.0,
                        "annualized_leave_days": float(w_leave),
                        "annualized_sick_leave": float(round(w_leave * 0.3)),
                        "annualized_unpaid_leave": 2.0 if w_leave > 24 else 0.0,
                        "annualized_overtime_hours": float(w_ot),
                    }
                ]
            )

        if emp_row is not None:
            from src.ml.shap_explainer import explain_single_employee_row

            explainer, exp_mode = load_shap_explainer(bundle, df)
            explanation = explain_single_employee_row(bundle, emp_row, explainer=explainer, mode=exp_mode)
            top_driver = explanation["top_factors"][0]

            render_kpi_grid(
                [
                    {"label": "Predicted Risk Score", "value": f"{explanation['attrition_probability']*100:.1f}%", "sub": f"Decision Threshold: {explanation['decision_threshold']:.2f}"},
                    {"label": "Risk Tier", "value": explanation["risk_tier"], "sub": f"Explainer: {explanation['explainer_type']}"},
                    {"label": "Strongest Contributor", "value": top_driver["feature"], "sub": f"{top_driver['direction']} ({top_driver['shap_contribution']:+.3f})", "wrap_text": True},
                ],
                columns_class="kpi-grid-3",
            )

            fac_df = pd.DataFrame(explanation["top_factors"]).iloc[::-1]
            fac_df["label"] = fac_df["feature"] + " = " + fac_df["value"]
            fig_local = px.bar(
                fac_df,
                x="shap_contribution",
                y="label",
                orientation="h",
                color="direction",
                color_discrete_map={"Increases Risk": CRIMSON_RISK, "Reduces Risk": TEAL_ACCENT},
                title="Top Feature Contributions to Individual Prediction (SHAP)",
                labels={"shap_contribution": "SHAP Log-Odds Contribution", "label": "", "direction": "Direction"},
            )
            fig_local.add_vline(x=0, line_color="#64748B", line_width=1)
            fig_local.update_traces(hovertemplate="<b>%{y}</b><br>SHAP Contribution: %{x:+.4f}<extra></extra>")
            st.plotly_chart(style_plotly(fig_local, 370, legend_pos="top"), width="stretch")

        st.download_button(
            "Download Active High-Risk Employee Watchlist (CSV)",
            active_list[active_list["risk_tier"] == "High"][
                ["employee_id", "department_name", "designation", "location", "tenure_years", "promotion_gap", "salary_growth_pct", "annualized_overtime_hours", "total_compensation", "attrition_probability"]
            ]
            .to_csv(index=False)
            .encode("utf-8"),
            file_name="active_high_risk_watchlist.csv",
            mime="text/csv",
        )


# =============================================================================
# PAGE 7: WORKFORCE SCENARIO SIMULATOR
# =============================================================================
def page_scenario_simulator(df: pd.DataFrame, ml_artifacts: dict[str, Any]) -> None:
    render_page_header(
        "Strategic Workforce Planning",
        "Workforce Scenario Simulator",
        "Interactive budget, merit increment, overtime reduction, promotion velocity, and targeted retention cost simulator.",
    )
    st.markdown(
        '<div class="disclaimer-banner">'
        "<strong>Decision-Support Guardrail:</strong> Financial payroll projections are deterministic calculations based on explicit HR assumptions. "
        "Changing compensation alone is <b>not</b> claimed to automatically reduce real-world attrition; optional ML risk shifts reflect non-causal sensitivity estimates only."
        "</div>",
        unsafe_allow_html=True,
    )

    active_df = df[df["is_active"] == 1].copy()
    depts = ["All"] + sorted(active_df["department_name"].dropna().unique().tolist())

    with st.container(border=True):
        st.markdown("**Scenario Levers & Policy Parameters**")
        c_ctrl1, c_ctrl2, c_ctrl3 = st.columns(3, gap="medium")
        with c_ctrl1:
            sim_dept = st.selectbox("Target Department Scope", depts)
            budget_inc = st.slider("Compensation Budget Increase (%)", 0.0, 15.0, 5.0, 0.5)
        with c_ctrl2:
            sal_inc = st.slider("Additional Merit Increment (%)", 0.0, 10.0, 2.0, 0.5)
            ot_red = st.slider("Excess Overtime Reduction (%)", 0.0, 40.0, 15.0, 5.0)
        with c_ctrl3:
            promo_boost = st.slider("Promotion Boost (% of >=2.5y Stagnant Staff)", 0.0, 30.0, 10.0, 2.5)
            ret_cov = st.slider("Targeted Retention Coverage (% High-Risk Staff)", 0.0, 100.0, 25.0, 5.0)

        include_ml = st.checkbox("Include Exploratory ML Risk Sensitivity Estimate (Non-Causal)", value=True)

    from src.simulator.scenario_engine import ScenarioParams, simulate_workforce_scenario

    params = ScenarioParams(
        department_filter=sim_dept,
        budget_increase_pct=float(budget_inc),
        salary_increment_pct=float(sal_inc),
        overtime_reduction_pct=float(ot_red),
        promotion_rate_boost_pct=float(promo_boost),
        retention_intervention_pct=float(ret_cov),
    )

    bundle = ml_artifacts.get("bundle")
    sim_res = simulate_workforce_scenario(
        active_df,
        params=params,
        model_bundle=bundle,
        include_ml_sensitivity=include_ml and bundle is not None,
    )

    sign = "+" if sim_res["net_financial_impact_cr"] >= 0 else ""
    if sim_res["ml_risk_sensitivity"] is not None:
        sens = sim_res["ml_risk_sensitivity"]
        ml_kpi = {
            "label": "ML Risk Score Shift*",
            "value": f"{sens['risk_score_shift_pp']:+.2f} pp",
            "sub": f"Flagged: {sens['baseline_flagged_high_risk']:,} -> {sens['simulated_flagged_high_risk']:,}",
        }
    else:
        ml_kpi = {"label": "ML Risk Sensitivity", "value": "Disabled", "sub": "Toggle checkbox above to estimate"}

    render_kpi_grid(
        [
            {"label": "Current Active Payroll", "value": format_inr_crore(sim_res["baseline_payroll_cr"], already_in_crores=True), "sub": f"{sim_res['active_headcount']:,} Active Staff"},
            {"label": "Projected Payroll", "value": format_inr_crore(sim_res["projected_payroll_cr"], already_in_crores=True), "sub": f"Budget Util: {sim_res['projected_budget_utilization_pct']:.1f}%"},
            {"label": "Net Financial Impact", "value": f"{sign}₹{sim_res['net_financial_impact_cr']:,.2f} Cr", "sub": f"{sign}{sim_res['net_impact_pct']:.2f}% vs Baseline"},
            {"label": "Employees Affected", "value": f"{sim_res['employees_affected']:,}", "sub": f"Promo: {sim_res['promoted_employees_count']:,} · Ret: {sim_res['retention_covered_count']:,}"},
            ml_kpi,
        ]
    )

    s_l, s_r = st.columns(2, gap="medium")
    with s_l:
        with st.container(border=True):
            cb = sim_res["cost_breakdown_cr"]
            cb_df = pd.DataFrame(
                [
                    {"Component": "Budget Uplift", "INR Cr": cb["budget_uplift_cr"]},
                    {"Component": "Merit Increment", "INR Cr": cb["salary_increment_cr"]},
                    {"Component": "Promotion Lift", "INR Cr": cb["promotion_cost_cr"]},
                    {"Component": "Retention Grants", "INR Cr": cb["retention_grant_cr"]},
                    {"Component": "Overtime Savings", "INR Cr": -cb["overtime_savings_cr"]},
                ]
            )
            cb_df["Color"] = np.where(cb_df["INR Cr"] >= 0, "Cost Increase", "Savings")
            fig_cb = px.bar(
                cb_df,
                x="Component",
                y="INR Cr",
                color="Color",
                text="INR Cr",
                color_discrete_map={"Cost Increase": COBALT, "Savings": TEAL_ACCENT},
                title="Projected Annual Expenditure Delta by Lever (INR Cr)",
            )
            fig_cb.update_traces(
                texttemplate="₹%{text:.2f} Cr",
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Impact: ₹%{y:,.2f} Cr<extra></extra>",
            )
            min_v = float(min(0.0, cb_df["INR Cr"].min()))
            max_v = float(max(0.0, cb_df["INR Cr"].max()))
            pad_top = max(10.0, max_v * 0.24)
            pad_bot = max(5.0, abs(min_v) * 0.30) if min_v < 0 else 0.0
            fig_cb.update_yaxes(range=[min_v - pad_bot, max_v + pad_top], zeroline=True, zerolinewidth=1.2)
            fig_cb.update_xaxes(tickangle=-18)
            st.plotly_chart(style_plotly(fig_cb, 395, legend_pos="top"), width="stretch")

    with s_r:
        with st.container(border=True):
            dept_bd = sim_res["department_breakdown"]
            fig_sb = go.Figure()
            fig_sb.add_trace(
                go.Bar(
                    x=dept_bd["department_name"],
                    y=dept_bd["baseline_payroll_cr"],
                    name="Baseline Payroll (Cr)",
                    marker_color="#94A3B8",
                    hovertemplate="<b>%{x}</b><br>Baseline: ₹%{y:,.2f} Cr<extra></extra>",
                )
            )
            fig_sb.add_trace(
                go.Bar(
                    x=dept_bd["department_name"],
                    y=dept_bd["projected_payroll_cr"],
                    name="Projected Payroll (Cr)",
                    marker_color=NAVY_PRIMARY,
                    hovertemplate="<b>%{x}</b><br>Projected: ₹%{y:,.2f} Cr<extra></extra>",
                )
            )
            fig_sb.update_layout(barmode="group", title="Baseline vs. Projected Active Payroll by Department", yaxis_title="INR Crores", hovermode="x unified")
            fig_sb.update_xaxes(tickangle=-25)
            st.plotly_chart(style_plotly(fig_sb, 395, legend_pos="top"), width="stretch")

    if sim_res["ml_risk_sensitivity"] is not None:
        st.info(f"*Exploratory Model Sensitivity Note:* {sim_res['ml_risk_sensitivity']['disclaimer']}")

    with st.expander("Explicit Scenario Modeling Assumptions", expanded=True):
        for a in sim_res["assumptions"]:
            st.markdown(f"- {a}")

    with st.container(border=True):
        st.markdown("**Departmental Scenario Impact Breakdown**")
        st.dataframe(
            dept_bd,
            hide_index=True,
            width="stretch",
            column_config={
                "department_name": "Department",
                "active_employees": st.column_config.NumberColumn("Active Staff", format="%d"),
                "baseline_payroll_cr": st.column_config.NumberColumn("Baseline (₹ Cr)", format="₹%.2f"),
                "projected_payroll_cr": st.column_config.NumberColumn("Projected (₹ Cr)", format="₹%.2f"),
                "net_delta_cr": st.column_config.NumberColumn("Net Delta (₹ Cr)", format="₹%.2f"),
                "annual_budget_cr": st.column_config.NumberColumn("Budget (₹ Cr)", format="₹%.2f"),
                "projected_budget_util_pct": st.column_config.NumberColumn("Projected Util (%)", format="%.1f%%"),
            },
        )
        st.download_button(
            "Download Scenario Impact Table (CSV)",
            dept_bd.to_csv(index=False).encode("utf-8"),
            file_name="workforce_scenario_projection.csv",
            mime="text/csv",
        )


# =============================================================================
# MAIN APPLICATION ROUTER
# =============================================================================
def main() -> None:
    try:
        data = load_all_workforce_data()
    except Exception as exc:
        st.error(f"Application initialization failed: {exc}")
        st.stop()

    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">Workforce Intelligence</div>
            <div class="sidebar-brand-sub">Compensation & Attrition Engine · 24,953 Synthetic Records</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="sidebar-section-label">Analytics Modules</div>', unsafe_allow_html=True)

    pages = [
        "1. Executive Overview",
        "2. Compensation Analytics",
        "3. Workforce Analytics",
        "4. Attrition Analytics",
        "5. Data Quality",
        "6. Predictive Analytics & SHAP",
        "7. Workforce Scenario Simulator",
    ]
    selected_page = st.sidebar.radio("Navigation", pages, label_visibility="collapsed")

    raw_df = data["workforce"]
    filtered_df = apply_sidebar_filters(raw_df)
    if filtered_df.empty:
        st.warning("No records match the current sidebar filters. Please widen your selection.")
        st.stop()

    if selected_page == "1. Executive Overview":
        page_executive_overview(filtered_df, data["monthly_trends"], data["recommendations"])
    elif selected_page == "2. Compensation Analytics":
        page_compensation_analytics(filtered_df, data["dept_kpi"])
    elif selected_page == "3. Workforce Analytics":
        page_workforce_analytics(filtered_df, data["leave_history"])
    elif selected_page == "4. Attrition Analytics":
        page_attrition_analytics(filtered_df)
    elif selected_page == "5. Data Quality":
        page_data_quality(data["dq"])
    elif selected_page == "6. Predictive Analytics & SHAP":
        ml_artifacts = load_ml_bundle()
        page_predictive_analytics(filtered_df, ml_artifacts)
    elif selected_page == "7. Workforce Scenario Simulator":
        ml_artifacts = load_ml_bundle()
        page_scenario_simulator(raw_df, ml_artifacts)


if __name__ == "__main__":
    main()
