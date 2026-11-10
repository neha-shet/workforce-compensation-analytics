# Workforce & Compensation Business Recommendation Report

**Generated (UTC):** `2026-11-10T11:56:14+00:00` | **Total Actionable Recommendations:** `7`

> **Synthetic Data Note:** All supporting metrics are derived from the Phase 1 synthetic enterprise dataset (`24,953` clean employees) and validated warehouse/ML outputs.

## [Critical] REC-01: Departmental Attrition Hotspots
- **Owner:** VP Engineering, VP Operations & HRBP Leads
- **Finding:** Operations, Engineering exhibit severe excess attrition above departmental targets.
- **Supporting Metric:** Operations: 18.91% vs 13.5% target (1,017 exits); Engineering: 18.12% vs 13.0% target (1,270 exits). Together they drive 67.4% (2,287) of all synthetic exits.
- **Business Implication:** Sustained turnover in core delivery and operational units elevates hiring/onboarding costs, slows product throughput, and destabilizes team capacity.
- **Recommended Action:** Initiate quarterly retention sprint reviews in Operations and Engineering focusing on manager coaching, workload rebalancing, and targeted career progression tracks.

## [Critical] REC-02: Career Progression & Promotion Gaps
- **Owner:** Talent Management & Department Heads
- **Finding:** Employees with promotion gaps exceeding 2.5 years leave at substantially higher rates than recently promoted peers.
- **Supporting Metric:** Attrition is 19.76% for >2.5 yr promotion gaps (and 25.58% at 4+ yrs) vs 11.15% at <=1.5 yrs. 1,359 active Engineering staff currently exceed 2.5 yrs without promotion.
- **Business Implication:** Experienced mid-level contributors hit perceived career ceilings and exit to external competitors right as their domain productivity peaks.
- **Recommended Action:** Institute mandatory bi-annual promotion/role-expansion reviews for all active staff with >=2.5 years since last promotion, starting with Engineering high performers.

## [High] REC-03: Workload & Overtime Burnout
- **Owner:** Operations Leadership & Workforce Planning
- **Finding:** Severe overtime concentration (>=250 annualized hours) strongly corresponds with elevated burnout exits, led by Operations.
- **Supporting Metric:** 250+ hr overtime staff record 28.08% attrition vs 10.18% for <80 hrs. Operations averages 216.2 hrs/yr with 1,974 active staff currently logging >=200 annualized overtime hrs.
- **Business Implication:** Chronic overtime inflates fatigue-driven sick leave, degrades operational SLA quality, and accelerates Work-Life Balance exits.
- **Recommended Action:** Cap sustained overtime via shift-capacity reallocation and targeted hiring/cross-training in high-load Operations hubs (utilizing existing Operations budget headroom at 89.2% utilization).

## [High] REC-04: Pay-for-Performance & Raise Equity
- **Owner:** Total Rewards & Compensation Committee
- **Finding:** A measurable pocket of active high performers (rating 4-5) received below-peer-average annual increments.
- **Supporting Metric:** 1,055 active high performers trail their Department-Designation peer raise average (avg gap -1.22 pp). Overall, <4% raise cohorts show 31.24% attrition.
- **Business Implication:** Under-rewarding top contributors undermines meritocracy and raises regretful attrition risk among mission-critical talent.
- **Recommended Action:** Reallocate merit increment budgets toward high-performing, under-indexed cohorts rather than uniform across-the-board raises.

## [High] REC-05: Payroll Budget Governance
- **Owner:** CFO / FP&A & Department Heads
- **Finding:** Multiple departments exceed allocated annual compensation budgets by more than 5%.
- **Supporting Metric:** Critical budget overruns detected in Sales (111.8% | +₹103.43 Cr), Product (111.1% | +₹50.53 Cr), Finance (109.2% | +₹27.20 Cr), Human Resources (107.4% | +₹13.89 Cr).
- **Business Implication:** Unchecked variable bonus inflation and off-cycle adjustments compress operating margins and constrain discretionary retention funding where needed most (e.g., Operations).
- **Recommended Action:** Enforce quarterly headcount-and-bonus variance gates in Sales, Product, Finance, and HR while rebalancing unfilled requisition budgets toward high-attrition operational gaps.

## [Medium] REC-06: Payroll Data Quality & Controls
- **Owner:** HRIS Engineering & Payroll Operations
- **Finding:** Pre-ETL payroll exports contained duplicate records, out-of-band salary anomalies, and inconsistent master taxonomies.
- **Supporting Metric:** Baseline DQ score 99.71% flagged 90 out-of-band salary anomalies, 85 duplicate payroll rows, 137 duplicate employee rows, and 420 non-canonical department strings.
- **Business Implication:** Without automated ETL validation and quarantine rules, extreme payroll data-entry errors distort executive compensation budgets and corrupt predictive risk scoring.
- **Recommended Action:** Embed the Phase 1 automated schema validation, designation salary-band guardrails, and canonical master-data dropdowns directly at HRIS entry and payroll export stages.

## [High] REC-07: Predictive Retention Targeting
- **Owner:** People Analytics & HRBPs
- **Finding:** Predictive risk screening identifies 1,697 active employees in the High Risk tier (predicted prob >= 65%).
- **Supporting Metric:** High-risk active cohort is concentrated in Engineering (762), Operations (693), with mean predicted risk 73.9%.
- **Business Implication:** Blanket retention bonuses waste budget on low-risk staff while missing silent flight risks.
- **Recommended Action:** Deploy monthly People Analytics review lists pairing top SHAP risk indicators (promotion gap, raise velocity, overtime) with HRBP stay interviews; track retention lift via pilot control groups.
