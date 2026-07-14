"""
MuleGuard Constants Module
==============================

Purpose:
    Centralized definition of shared constants, configuration defaults,
    and fixed values used across the MuleGuard platform (schema
    definitions, risk thresholds, file paths, UI labels).

Future Role:
    - Will serve as the single source of truth for tunable parameters
      (rule weights, risk level thresholds, required dataset columns)
      so they are not hardcoded/duplicated across modules.
    - Will be extended as new heuristic rules and configuration needs
      are introduced.

Author: MuleGuard Engineering Team
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Project Directory Paths
# ---------------------------------------------------------------------------

# TODO: Validate these resolve correctly relative to project root at runtime
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_INPUT_DIR: Path = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT_DIR: Path = PROJECT_ROOT / "data" / "output"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"


# ---------------------------------------------------------------------------
# Transaction Schema Constants
# ---------------------------------------------------------------------------

# TODO: Finalize required column names against actual dataset schema
REQUIRED_TRANSACTION_COLUMNS = [
    # "transaction_id",
    # "sender_vpa",
    # "receiver_vpa",
    # "amount",
    # "timestamp",
]


# ---------------------------------------------------------------------------
# Risk Engine Constants
# ---------------------------------------------------------------------------

# TODO: Define default weight per heuristic rule (must sum meaningfully
#       within the scoring model's normalization scheme)
DEFAULT_RULE_WEIGHTS = {
    # "FanInFanOutRule": 0.0,
    # "CircularFlowRule": 0.0,
    # "RapidPassThroughRule": 0.0,
}

# TODO: Define score thresholds mapping to RiskLevel categories
RISK_LEVEL_THRESHOLDS = {
    # "LOW": (0, 25),
    # "MEDIUM": (25, 50),
    # "HIGH": (50, 75),
    # "CRITICAL": (75, 100),
}


# ---------------------------------------------------------------------------
# Logging Constants
# ---------------------------------------------------------------------------

# TODO: Finalize logging format/level defaults
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


# ---------------------------------------------------------------------------
# Dashboard / UI Constants
# ---------------------------------------------------------------------------

# TODO: Define app title, theme colors, and other UI-facing constants
APP_TITLE = "MuleGuard - UPI Mule Account Investigation Platform"