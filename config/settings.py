"""Centralized configuration, paths, and enterprise HR domain rules."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv_if_present(env_path: Path) -> None:
    """Load simple KEY=VALUE lines from .env without requiring python-dotenv."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv_if_present(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Paths:
    root: Path = PROJECT_ROOT
    data_raw: Path = PROJECT_ROOT / "data" / "raw"
    data_quarantine: Path = PROJECT_ROOT / "data" / "quarantine"
    data_processed: Path = PROJECT_ROOT / "data" / "processed"
    data_warehouse_exports: Path = PROJECT_ROOT / "data" / "processed" / "warehouse"
    sqlite_db: Path = PROJECT_ROOT / os.getenv("SQLITE_DB_PATH", "data/warehouse/workforce_dw.db")
    reports: Path = PROJECT_ROOT / "reports"
    sql_warehouse: Path = PROJECT_ROOT / "sql" / "warehouse"


PATHS = Paths()

# Runtime Parameters
NUM_EMPLOYEES: int = int(os.getenv("NUM_EMPLOYEES", "25000"))
RANDOM_SEED: int = int(os.getenv("RANDOM_SEED", "42"))
AS_OF_DATE: date = date.fromisoformat(os.getenv("AS_OF_DATE", "2026-09-30"))
CURRENCY: str = os.getenv("CURRENCY", "INR")
ANNUAL_LEAVE_ENTITLEMENT: float = 28.0
STANDARD_ANNUAL_WORK_HOURS: float = 2080.0
LEAVE_YEARS: tuple[int, ...] = (2024, 2025, 2026)

# Database Settings
DB_BACKEND: str = os.getenv("DB_BACKEND", "sqlite").lower()
PG_HOST: str = os.getenv("PG_HOST", "localhost")
PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
PG_DB: str = os.getenv("PG_DB", "workforce_dw")
PG_USER: str = os.getenv("PG_USER", "analytics_user")
PG_PASSWORD: str = os.getenv("PG_PASSWORD", "")
PG_SCHEMA: str = os.getenv("PG_SCHEMA", "dw")

# Canonical Department Taxonomy & Raw Messy Mapping
CANONICAL_DEPARTMENTS: dict[str, dict[str, object]] = {
    "Engineering": {"head_function": "Technology & R&D", "budget_inr": 17_800_000_000.0, "target_attrition": 13.0},
    "Operations": {"head_function": "Business Operations", "budget_inr": 9_350_000_000.0, "target_attrition": 13.5},
    "Sales": {"head_function": "Revenue & Growth", "budget_inr": 8_750_000_000.0, "target_attrition": 13.0},
    "Data & Analytics": {"head_function": "Technology & R&D", "budget_inr": 4_650_000_000.0, "target_attrition": 11.5},
    "Product": {"head_function": "Technology & R&D", "budget_inr": 4_550_000_000.0, "target_attrition": 11.0},
    "Customer Success": {"head_function": "Revenue & Growth", "budget_inr": 3_450_000_000.0, "target_attrition": 12.0},
    "Finance": {"head_function": "Corporate Functions", "budget_inr": 2_950_000_000.0, "target_attrition": 8.5},
    "Human Resources": {"head_function": "Corporate Functions", "budget_inr": 1_880_000_000.0, "target_attrition": 9.0},
}

DEPARTMENT_ALIASES: dict[str, str] = {
    "engineering": "Engineering",
    "engg": "Engineering",
    "eng": "Engineering",
    "r&d engineering": "Engineering",
    "operations": "Operations",
    "ops": "Operations",
    "operation": "Operations",
    "sales": "Sales",
    "sales & bd": "Sales",
    "business development": "Sales",
    "data & analytics": "Data & Analytics",
    "data science": "Data & Analytics",
    "analytics": "Data & Analytics",
    "product": "Product",
    "product mgmt": "Product",
    "customer success": "Customer Success",
    "cust success": "Customer Success",
    "cs": "Customer Success",
    "finance": "Finance",
    "fin": "Finance",
    "finance & accounts": "Finance",
    "human resources": "Human Resources",
    "hr": "Human Resources",
    "people ops": "Human Resources",
}

# Canonical Locations
CANONICAL_LOCATIONS: dict[str, dict[str, str]] = {
    "Bengaluru": {"region": "South", "country": "India", "tier": "Tier-1"},
    "Hyderabad": {"region": "South", "country": "India", "tier": "Tier-1"},
    "Pune": {"region": "West", "country": "India", "tier": "Tier-1"},
    "Mumbai": {"region": "West", "country": "India", "tier": "Tier-1"},
    "Gurugram": {"region": "North", "country": "India", "tier": "Tier-1"},
    "Chennai": {"region": "South", "country": "India", "tier": "Tier-1"},
    "Noida": {"region": "North", "country": "India", "tier": "Tier-2"},
}

LOCATION_ALIASES: dict[str, str] = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
    "hyderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "pune": "Pune",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "chennai": "Chennai",
    "madras": "Chennai",
    "noida": "Noida",
}

# Employment type normalization
EMPLOYMENT_TYPE_ALIASES: dict[str, str] = {
    "full-time": "Full-Time",
    "full time": "Full-Time",
    "ft": "Full-Time",
    "permanent": "Full-Time",
    "contract": "Contract",
    "contractor": "Contract",
    "intern": "Intern",
    "internship": "Intern",
}

# Expected Annual Basic Salary Ranges (INR) by Designation for Generation & DQ Checks
DESIGNATION_SALARY_BANDS_INR: dict[str, tuple[float, float]] = {
    "Analyst": (280_000.0, 680_000.0),
    "Software Engineer": (450_000.0, 1_150_000.0),
    "Senior Analyst": (550_000.0, 1_250_000.0),
    "Senior Engineer": (850_000.0, 1_950_000.0),
    "Team Lead": (950_000.0, 2_150_000.0),
    "Manager": (1_200_000.0, 2_750_000.0),
    "Senior Manager": (1_750_000.0, 3_800_000.0),
    "Principal": (2_100_000.0, 4_500_000.0),
    "Director": (2_800_000.0, 6_200_000.0),
    "VP": (4_200_000.0, 9_500_000.0),
}

# DQ validation ceiling multiplier above band max before flagging as extreme anomaly
SALARY_ANOMALY_UPPER_MULTIPLIER: float = 1.65
SALARY_ANOMALY_LOWER_MULTIPLIER: float = 0.50


def ensure_directories() -> None:
    """Create required project data and report directories if absent."""
    for folder in (
        PATHS.data_raw,
        PATHS.data_quarantine,
        PATHS.data_processed,
        PATHS.data_warehouse_exports,
        PATHS.sqlite_db.parent,
        PATHS.reports,
    ):
        folder.mkdir(parents=True, exist_ok=True)

