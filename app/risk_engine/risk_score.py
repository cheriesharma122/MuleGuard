"""
MuleGuard Risk Score Module
===============================

Purpose:
    Responsible for converting per-account transaction behavior derived
    from the transaction graph into quantitative, explainable risk
    scores, which investigators can use to prioritize review.

Future Role:
    - Implements a weighted scoring model combining multiple behavioral
      signals (incoming/outgoing transaction volume, total amount,
      transaction frequency, and counterparty diversity) into a single
      normalized risk score (0-100).
    - Supports configurable signal weights to allow tuning of relative
      factor importance as detection heuristics evolve.
    - Produces a risk classification (LOW/MEDIUM/HIGH/CRITICAL)
      alongside the numeric score for dashboard display.
    - Provides human-readable score explanations for investigator
      transparency and inclusion in generated reports.

Author: MuleGuard Engineering Team
"""

import logging
from typing import Optional, Dict, Any, List

import networkx as nx

logger = logging.getLogger("muleguard.risk_engine.risk_score")


class RiskLevel:
    """
    Standardized risk classification labels used across the
    MuleGuard platform.
    """

    LOW: str = "LOW"
    MEDIUM: str = "MEDIUM"
    HIGH: str = "HIGH"
    CRITICAL: str = "CRITICAL"


class RiskScore:
    """
    Computes quantitative risk scores for accounts within a transaction
    graph, based on a configurable weighted behavioral scoring model.

    Responsibilities:
        - Extract per-account behavioral metrics from the transaction graph
          (incoming/outgoing transaction counts, total amount, frequency,
          unique counterparties).
        - Normalize and aggregate these metrics into a single risk score
          on a 0-100 scale.
        - Classify accounts into risk levels based on score thresholds.
        - Provide human-readable score explanations for reporting.
    """

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "incoming_volume": 0.20,
        "outgoing_volume": 0.20,
        "total_amount": 0.25,
        "transaction_frequency": 0.15,
        "unique_counterparties": 0.20,
    }

    DEFAULT_RISK_THRESHOLDS: Dict[str, tuple] = {
        RiskLevel.LOW: (0, 25),
        RiskLevel.MEDIUM: (25, 50),
        RiskLevel.HIGH: (50, 75),
        RiskLevel.CRITICAL: (75, 100),
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        risk_thresholds: Optional[Dict[str, tuple]] = None,
    ) -> None:
        """
        Initialize the RiskScore engine.

        Args:
            weights (Optional[Dict[str, float]]): Mapping of behavioral
                signal name to its relative weight in the scoring
                formula. Defaults to RiskScore.DEFAULT_WEIGHTS.
            risk_thresholds (Optional[Dict[str, tuple]]): Mapping of
                RiskLevel label to a (min, max) score range. Defaults
                to RiskScore.DEFAULT_RISK_THRESHOLDS.
        """
        self.weights = weights if weights is not None else dict(self.DEFAULT_WEIGHTS)
        self.risk_thresholds = (
            risk_thresholds if risk_thresholds is not None
            else dict(self.DEFAULT_RISK_THRESHOLDS)
        )

        logger.debug(
            "RiskScore initialized with weights=%s, thresholds=%s.",
            self.weights,
            self.risk_thresholds,
        )

    def _extract_account_metrics(
        self, graph: nx.DiGraph, account: str
    ) -> Dict[str, float]:
        """
        Extract raw behavioral metrics for a single account from the
        transaction graph.

        Args:
            graph (nx.DiGraph): The transaction graph.
            account (str): The account (node) identifier.

        Returns:
            Dict[str, float]: Raw metrics for the account, including
                incoming/outgoing counts, total amount, transaction
                frequency proxy, and unique counterparty count.
        """
        try:
            in_edges = list(graph.in_edges(account, data=True))
            out_edges = list(graph.out_edges(account, data=True))

            incoming_count = len(in_edges)
            outgoing_count = len(out_edges)

            incoming_amount = sum(
                (data.get("amount") or 0) for _, _, data in in_edges
                if isinstance(data.get("amount"), (int, float))
            )
            outgoing_amount = sum(
                (data.get("amount") or 0) for _, _, data in out_edges
                if isinstance(data.get("amount"), (int, float))
            )
            total_amount = incoming_amount + outgoing_amount

            unique_senders = {u for u, _, _ in in_edges}
            unique_receivers = {v for _, v, _ in out_edges}
            unique_counterparties = len(unique_senders | unique_receivers)

            transaction_frequency = incoming_count + outgoing_count

            return {
                "incoming_volume": float(incoming_count),
                "outgoing_volume": float(outgoing_count),
                "total_amount": float(total_amount),
                "transaction_frequency": float(transaction_frequency),
                "unique_counterparties": float(unique_counterparties),
            }

        except Exception as exc:
            logger.exception(
                "Unexpected error extracting metrics for account '%s': %s",
                account,
                exc,
            )
            return {
                "incoming_volume": 0.0,
                "outgoing_volume": 0.0,
                "total_amount": 0.0,
                "transaction_frequency": 0.0,
                "unique_counterparties": 0.0,
            }

    def _normalize_metrics(
        self, all_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Normalize raw metrics across all accounts to a 0-1 scale using
        min-max normalization per metric.

        Args:
            all_metrics (Dict[str, Dict[str, float]]): Mapping of
                account -> raw metric dict.

        Returns:
            Dict[str, Dict[str, float]]: Mapping of account -> normalized
                metric dict (values in range [0, 1]).
        """
        try:
            if not all_metrics:
                return {}

            metric_names = self.weights.keys()
            min_max: Dict[str, tuple] = {}

            for metric_name in metric_names:
                values = [
                    metrics.get(metric_name, 0.0)
                    for metrics in all_metrics.values()
                ]
                min_value = min(values) if values else 0.0
                max_value = max(values) if values else 0.0
                min_max[metric_name] = (min_value, max_value)

            normalized: Dict[str, Dict[str, float]] = {}

            for account, metrics in all_metrics.items():
                normalized[account] = {}
                for metric_name in metric_names:
                    raw_value = metrics.get(metric_name, 0.0)
                    min_value, max_value = min_max[metric_name]

                    if max_value == min_value:
                        normalized_value = 0.0
                    else:
                        normalized_value = (
                            (raw_value - min_value) / (max_value - min_value)
                        )

                    normalized[account][metric_name] = normalized_value

            return normalized

        except Exception as exc:
            logger.exception("Unexpected error during metric normalization: %s", exc)
            return {account: {name: 0.0 for name in self.weights} for account in all_metrics}

    def calculate_score(self, normalized_metrics: Dict[str, float]) -> float:
        """
        Calculate a normalized risk score (0-100) from an account's
        normalized behavioral metrics.

        Args:
            normalized_metrics (Dict[str, float]): Normalized metric
                values (0-1 scale) for a single account.

        Returns:
            float: Risk score in the range [0, 100].
        """
        try:
            weighted_sum = 0.0
            total_weight = 0.0

            for metric_name, weight in self.weights.items():
                metric_value = normalized_metrics.get(metric_name, 0.0)
                weighted_sum += metric_value * weight
                total_weight += weight

            if total_weight == 0:
                logger.warning("Total weight is zero; returning score of 0.0.")
                return 0.0

            score = (weighted_sum / total_weight) * 100.0
            score = max(0.0, min(100.0, score))

            return round(score, 2)

        except Exception as exc:
            logger.exception("Unexpected error while calculating risk score: %s", exc)
            return 0.0

    def classify_risk_level(self, score: float) -> str:
        """
        Map a numeric risk score to a categorical risk level.

        Args:
            score (float): Numeric risk score (0-100).

        Returns:
            str: One of RiskLevel.LOW / MEDIUM / HIGH / CRITICAL.
        """
        try:
            for level, (min_score, max_score) in self.risk_thresholds.items():
                if min_score <= score < max_score:
                    return level

            if score >= self.risk_thresholds.get(RiskLevel.CRITICAL, (75, 100))[0]:
                return RiskLevel.CRITICAL

            return RiskLevel.LOW

        except Exception as exc:
            logger.exception("Unexpected error while classifying risk level: %s", exc)
            return RiskLevel.LOW

    def generate_score_explanation(
        self,
        account: str,
        raw_metrics: Dict[str, float],
        score: float,
        risk_level: str,
    ) -> str:
        """
        Generate a human-readable explanation of the contributing
        factors behind an account's risk score.

        Args:
            account (str): The account identifier.
            raw_metrics (Dict[str, float]): Raw (non-normalized) metrics
                for the account.
            score (float): The computed risk score.
            risk_level (str): The classified risk level.

        Returns:
            str: Human-readable explanation string.
        """
        try:
            explanation = (
                f"Account '{account}' received a risk score of {score:.2f} "
                f"({risk_level}). "
                f"Incoming transactions: {int(raw_metrics.get('incoming_volume', 0))}, "
                f"Outgoing transactions: {int(raw_metrics.get('outgoing_volume', 0))}, "
                f"Total transaction amount: {raw_metrics.get('total_amount', 0):.2f}, "
                f"Transaction frequency: {int(raw_metrics.get('transaction_frequency', 0))}, "
                f"Unique counterparties: {int(raw_metrics.get('unique_counterparties', 0))}."
            )
            return explanation

        except Exception as exc:
            logger.exception(
                "Unexpected error generating explanation for account '%s': %s",
                account,
                exc,
            )
            return f"Account '{account}' risk explanation unavailable due to an internal error."

    def score_accounts(self, graph: Optional[nx.DiGraph]) -> List[Dict[str, Any]]:
        """
        Compute risk scores for every account (node) in the given
        transaction graph.

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to score.

        Returns:
            List[Dict[str, Any]]: List of per-account records containing
                account identifier, raw metrics, normalized metrics,
                score, risk level, and explanation. Returns an empty
                list if the graph is empty or invalid.
        """
        try:
            if graph is None or graph.number_of_nodes() == 0:
                logger.warning("score_accounts() called with an empty or None graph.")
                return []

            raw_metrics_by_account: Dict[str, Dict[str, float]] = {
                account: self._extract_account_metrics(graph, account)
                for account in graph.nodes()
            }

            normalized_metrics_by_account = self._normalize_metrics(raw_metrics_by_account)

            results: List[Dict[str, Any]] = []

            for account in graph.nodes():
                raw_metrics = raw_metrics_by_account.get(account, {})
                normalized_metrics = normalized_metrics_by_account.get(account, {})

                score = self.calculate_score(normalized_metrics)
                risk_level = self.classify_risk_level(score)
                explanation = self.generate_score_explanation(
                    account, raw_metrics, score, risk_level
                )

                results.append({
                    "account": account,
                    "raw_metrics": raw_metrics,
                    "normalized_metrics": normalized_metrics,
                    "score": score,
                    "risk_level": risk_level,
                    "explanation": explanation,
                })

            results.sort(key=lambda record: record["score"], reverse=True)

            logger.info(
                "Risk scoring complete for %d account(s). "
                "Highest score: %.2f, Lowest score: %.2f.",
                len(results),
                results[0]["score"] if results else 0.0,
                results[-1]["score"] if results else 0.0,
            )

            return results

        except Exception as exc:
            logger.exception("Unexpected error while scoring accounts: %s", exc)
            return []

    def get_top_risky_accounts(
        self,
        graph: Optional[nx.DiGraph],
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the top N highest-risk accounts from the transaction graph.

        Args:
            graph (Optional[nx.DiGraph]): The transaction graph to score.
            top_n (int): Number of top-risk accounts to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: The top N scored account records,
                sorted by descending risk score.
        """
        try:
            all_scores = self.score_accounts(graph)

            if not all_scores:
                logger.warning("get_top_risky_accounts() found no scored accounts.")
                return []

            top_n = max(0, top_n)
            top_accounts = all_scores[:top_n]

            logger.info(
                "Retrieved top %d risky account(s) out of %d scored.",
                len(top_accounts),
                len(all_scores),
            )

            return top_accounts

        except Exception as exc:
            logger.exception("Unexpected error while retrieving top risky accounts: %s", exc)
            return []