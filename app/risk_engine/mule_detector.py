"""
MuleGuard Mule Detector Module
==================================

Purpose:
    Responsible for consuming risk scores produced by the RiskScore
    engine and applying configurable thresholds to identify and
    categorize suspicious mule accounts within the transaction graph.

Future Role:
    - Serves as the orchestration layer between raw graph-derived risk
      scores and the dashboard/report_generator modules, producing a
      structured, investigator-friendly detection result set.
    - Supports configurable risk thresholds so analysts can tune
      detection sensitivity without modifying scoring logic.
    - Provides categorized (Low/Medium/High Risk) account groupings
      and summary statistics for dashboard visualization and PDF
      report generation.

Author: MuleGuard Engineering Team
"""

import logging
from typing import Optional, Dict, Any, List

import networkx as nx

from app.risk_engine.risk_score import RiskScore, RiskLevel

logger = logging.getLogger("muleguard.risk_engine.mule_detector")


class MuleDetector:
    """
    Identifies and categorizes suspicious mule accounts based on risk
    scores computed by the RiskScore engine.

    Responsibilities:
        - Delegate account-level risk scoring to a RiskScore instance.
        - Apply configurable thresholds to categorize accounts into
          Low/Medium/High Risk buckets.
        - Produce structured detection results consumable by the
          dashboard and report_generator modules.
        - Provide summary statistics of the detection run.
    """

    DEFAULT_CATEGORY_THRESHOLDS: Dict[str, tuple] = {
        "Low Risk": (0, 40),
        "Medium Risk": (40, 70),
        "High Risk": (70, 100),
    }

    def __init__(
        self,
        risk_score_engine: Optional[RiskScore] = None,
        category_thresholds: Optional[Dict[str, tuple]] = None,
    ) -> None:
        """
        Initialize the MuleDetector.

        Args:
            risk_score_engine (Optional[RiskScore]): A configured
                RiskScore instance used to compute account risk scores.
                If not provided, a default RiskScore instance is created.
            category_thresholds (Optional[Dict[str, tuple]]): Mapping of
                category label to a (min, max) score range used to
                classify accounts. Defaults to
                MuleDetector.DEFAULT_CATEGORY_THRESHOLDS.
        """
        self.risk_score_engine = risk_score_engine if risk_score_engine is not None else RiskScore()
        self.category_thresholds = (
            category_thresholds if category_thresholds is not None
            else dict(self.DEFAULT_CATEGORY_THRESHOLDS)
        )

        logger.debug(
            "MuleDetector initialized with category_thresholds=%s.",
            self.category_thresholds,
        )

    def _categorize_score(self, score: float) -> str:
        """
        Map a numeric risk score to a detection category label based
        on the configured category_thresholds.

        Args:
            score (float): Numeric risk score (0-100).

        Returns:
            str: One of the configured category labels
                (e.g. "Low Risk", "Medium Risk", "High Risk").
        """
        try:
            for category, (min_score, max_score) in self.category_thresholds.items():
                if min_score <= score < max_score:
                    return category

            highest_category = max(
                self.category_thresholds.items(),
                key=lambda item: item[1][0],
            )[0]

            if score >= self.category_thresholds.get(highest_category, (70, 100))[0]:
                return highest_category

            lowest_category = min(
                self.category_thresholds.items(),
                key=lambda item: item[1][0],
            )[0]
            return lowest_category

        except Exception as exc:
            logger.exception("Unexpected error while categorizing score %.2f: %s", score, exc)
            return "Low Risk"

    def detect(self, graph: Optional[nx.DiGraph]) -> List[Dict[str, Any]]:
        """
        Run mule account detection over the given transaction graph.

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to analyze.

        Returns:
            List[Dict[str, Any]]: List of per-account detection records,
                each containing account identifier, raw metrics, score,
                risk_level (from RiskScore), category (from MuleDetector
                thresholds), and explanation. Returns an empty list if
                the graph is empty or invalid.
        """
        try:
            if graph is None or graph.number_of_nodes() == 0:
                logger.warning("detect() called with an empty or None graph.")
                return []

            scored_accounts = self.risk_score_engine.score_accounts(graph)

            if not scored_accounts:
                logger.warning("No scored accounts returned from RiskScore engine.")
                return []

            detection_results: List[Dict[str, Any]] = []

            for record in scored_accounts:
                score = record.get("score", 0.0)
                category = self._categorize_score(score)

                detection_record = dict(record)
                detection_record["category"] = category

                detection_results.append(detection_record)

            detection_results.sort(key=lambda record: record["score"], reverse=True)

            logger.info(
                "Mule detection complete. %d account(s) analyzed.",
                len(detection_results),
            )

            return detection_results

        except Exception as exc:
            logger.exception("Unexpected error during mule detection: %s", exc)
            return []

    def get_accounts_by_category(
        self,
        graph: Optional[nx.DiGraph],
        category: str,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts belonging to a specific risk category.

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to analyze.
            category (str): The category label to filter by
                (e.g. "Low Risk", "Medium Risk", "High Risk").

        Returns:
            List[Dict[str, Any]]: Filtered list of detection records
                matching the given category.
        """
        try:
            all_results = self.detect(graph)

            if not all_results:
                logger.warning("get_accounts_by_category() found no detection results.")
                return []

            filtered_results = [
                record for record in all_results
                if record.get("category") == category
            ]

            logger.info(
                "Found %d account(s) in category '%s'.",
                len(filtered_results),
                category,
            )

            return filtered_results

        except Exception as exc:
            logger.exception(
                "Unexpected error while filtering accounts by category '%s': %s",
                category,
                exc,
            )
            return []

    def get_high_risk_accounts(
        self,
        graph: Optional[nx.DiGraph],
    ) -> List[Dict[str, Any]]:
        """
        Convenience method to retrieve all accounts categorized as
        "High Risk".

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to analyze.

        Returns:
            List[Dict[str, Any]]: Detection records for High Risk accounts.
        """
        return self.get_accounts_by_category(graph, "High Risk")

    def get_summary_statistics(
        self,
        graph: Optional[nx.DiGraph],
    ) -> Dict[str, Any]:
        """
        Generate summary statistics for a mule detection run, suitable
        for dashboard display or inclusion in a PDF report.

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to analyze.

        Returns:
            Dict[str, Any]: Summary statistics including total accounts
                analyzed, counts per category, average score, and the
                highest-risk account.
        """
        try:
            all_results = self.detect(graph)

            if not all_results:
                logger.warning("get_summary_statistics() found no detection results.")
                return {
                    "total_accounts_analyzed": 0,
                    "category_counts": {
                        category: 0 for category in self.category_thresholds
                    },
                    "average_score": 0.0,
                    "highest_risk_account": None,
                }

            category_counts: Dict[str, int] = {
                category: 0 for category in self.category_thresholds
            }
            for record in all_results:
                category = record.get("category")
                if category in category_counts:
                    category_counts[category] += 1
                else:
                    category_counts[category] = category_counts.get(category, 0) + 1

            total_score = sum(record.get("score", 0.0) for record in all_results)
            average_score = round(total_score / len(all_results), 2) if all_results else 0.0

            highest_risk_account = all_results[0] if all_results else None

            summary = {
                "total_accounts_analyzed": len(all_results),
                "category_counts": category_counts,
                "average_score": average_score,
                "highest_risk_account": highest_risk_account,
            }

            logger.info("Generated mule detection summary statistics: %s", summary)

            return summary

        except Exception as exc:
            logger.exception("Unexpected error while generating summary statistics: %s", exc)
            return {
                "total_accounts_analyzed": 0,
                "category_counts": {},
                "average_score": 0.0,
                "highest_risk_account": None,
            }