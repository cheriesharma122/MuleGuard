"""
MuleGuard Graph Builder Module
==================================

Purpose:
    Responsible for constructing a directed transaction graph from
    cleaned UPI transaction data, where nodes represent accounts (VPAs)
    and edges represent transactions between them.

Future Role:
    - Will build and maintain a networkx.DiGraph representing the
      transaction network.
    - Will compute graph-level structural metrics (in-degree, out-degree,
      betweenness centrality, connected components) used later by the
      risk engine to identify mule account patterns (fan-in/fan-out,
      layering, circular flows).
    - Will support incremental graph updates as new transaction batches
      arrive.
    - Will provide graph export utilities for the dashboard's pyvis
      visualization layer and for offline investigation/reporting.

Author: MuleGuard Engineering Team
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
import networkx as nx

logger = logging.getLogger("muleguard.graph")


class GraphConstructionError(Exception):
    """
    Raised when the transaction graph cannot be constructed from the
    provided dataset.
    """
    pass


class GraphBuilder:
    """
    Constructs and manages the transaction network graph used for
    mule account pattern analysis.

    Responsibilities:
        - Build a directed graph from transaction records.
        - Attach relevant metadata to nodes (accounts) and edges
          (transactions) for downstream risk analysis.
        - Provide access to basic graph statistics.
        - Export the graph to standard formats (GraphML/GEXF) for
          use in external tools or the dashboard's visualization layer.
    """

    def __init__(self, directed: bool = True) -> None:
        """
        Initialize the GraphBuilder.

        Args:
            directed (bool): Whether to construct a directed graph
                (True) representing money flow direction, or an
                undirected graph (False). Defaults to True.
        """
        self.directed = directed
        self.graph: nx.DiGraph = nx.DiGraph() if directed else nx.Graph()

        logger.debug(
            "GraphBuilder initialized (directed=%s).", self.directed
        )

    def build_graph(self, transactions: pd.DataFrame) -> Optional[nx.DiGraph]:
        """
        Build the transaction graph from a cleaned transactions DataFrame.

        Args:
            transactions (pd.DataFrame): Cleaned transaction records,
                expected to contain sender_vpa, receiver_vpa, and
                optionally amount, timestamp, transaction_id, and
                bank_ref columns.

        Returns:
            Optional[nx.DiGraph]: The constructed transaction graph,
                or None if construction failed.
        """
        try:
            if transactions is None or transactions.empty:
                logger.warning("No transactions provided; cannot build graph.")
                return None

            sender_columns = [
                column for column in transactions.columns
                if "sender" in column.lower()
            ]
            receiver_columns = [
                column for column in transactions.columns
                if "receiver" in column.lower()
            ]
            amount_columns = [
                column for column in transactions.columns
                if "amount" in column.lower()
            ]
            timestamp_columns = [
                column for column in transactions.columns
                if "timestamp" in column.lower() or "date" in column.lower()
            ]
            id_columns = [
                column for column in transactions.columns
                if "transaction_id" in column.lower() or column.lower() == "txn_id"
            ]
            bank_ref_columns = [
                column for column in transactions.columns
                if "bank_ref" in column.lower() or "bank_reference" in column.lower()
            ]

            if not sender_columns or not receiver_columns:
                raise GraphConstructionError(
                    "Transactions DataFrame is missing required sender_vpa/"
                    "receiver_vpa columns needed for graph construction."
                )

            sender_column = sender_columns[0]
            receiver_column = receiver_columns[0]
            amount_column = amount_columns[0] if amount_columns else None
            timestamp_column = timestamp_columns[0] if timestamp_columns else None
            id_column = id_columns[0] if id_columns else None
            bank_ref_column = bank_ref_columns[0] if bank_ref_columns else None

            self.graph = nx.DiGraph() if self.directed else nx.Graph()

            skipped_rows = 0

            for row in transactions.itertuples(index=False):
                sender = getattr(row, sender_column, None)
                receiver = getattr(row, receiver_column, None)

                if pd.isna(sender) or pd.isna(receiver):
                    skipped_rows += 1
                    continue

                if sender not in self.graph:
                    self.graph.add_node(sender, account_type="unknown")
                if receiver not in self.graph:
                    self.graph.add_node(receiver, account_type="unknown")

                edge_attributes: Dict[str, Any] = {}

                if amount_column:
                    amount_value = getattr(row, amount_column, None)
                    edge_attributes["amount"] = (
                        None if pd.isna(amount_value) else amount_value
                    )

                if timestamp_column:
                    timestamp_value = getattr(row, timestamp_column, None)
                    edge_attributes["timestamp"] = (
                        None if pd.isna(timestamp_value) else str(timestamp_value)
                    )

                if id_column:
                    id_value = getattr(row, id_column, None)
                    edge_attributes["transaction_id"] = (
                        None if pd.isna(id_value) else id_value
                    )

                if bank_ref_column:
                    bank_ref_value = getattr(row, bank_ref_column, None)
                    edge_attributes["bank_ref"] = (
                        None if pd.isna(bank_ref_value) else bank_ref_value
                    )

                self.graph.add_edge(sender, receiver, **edge_attributes)

            if skipped_rows > 0:
                logger.warning(
                    "Skipped %d transaction row(s) due to missing sender/"
                    "receiver values.",
                    skipped_rows,
                )

            logger.info(
                "Transaction graph built successfully with %d nodes and %d edges.",
                self.graph.number_of_nodes(),
                self.graph.number_of_edges(),
            )

            return self.graph

        except GraphConstructionError as exc:
            logger.error("Graph construction failed: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Unexpected error while building transaction graph: %s", exc)
            return None

    def get_graph(self) -> Optional[nx.DiGraph]:
        """
        Retrieve the currently constructed transaction graph.

        Returns:
            Optional[nx.DiGraph]: The current graph instance, or None
                if no graph has been built yet.
        """
        try:
            if self.graph is None:
                logger.warning("get_graph() called but no graph has been built.")
                return None
            return self.graph
        except Exception as exc:
            logger.exception("Unexpected error while retrieving graph: %s", exc)
            return None

    def get_node_count(self) -> int:
        """
        Get the total number of nodes (accounts) in the current graph.

        Returns:
            int: Number of nodes in the graph. Returns 0 if no graph exists.
        """
        try:
            if self.graph is None:
                logger.warning("get_node_count() called but no graph has been built.")
                return 0
            return self.graph.number_of_nodes()
        except Exception as exc:
            logger.exception("Unexpected error while counting nodes: %s", exc)
            return 0

    def get_edge_count(self) -> int:
        """
        Get the total number of edges (transactions) in the current graph.

        Returns:
            int: Number of edges in the graph. Returns 0 if no graph exists.
        """
        try:
            if self.graph is None:
                logger.warning("get_edge_count() called but no graph has been built.")
                return 0
            return self.graph.number_of_edges()
        except Exception as exc:
            logger.exception("Unexpected error while counting edges: %s", exc)
            return 0

    def clear_graph(self) -> None:
        """
        Reset the current graph to an empty graph, preserving the
        configured directedness.
        """
        try:
            self.graph = nx.DiGraph() if self.directed else nx.Graph()
            logger.info("Graph has been cleared and reset to an empty graph.")
        except Exception as exc:
            logger.exception("Unexpected error while clearing graph: %s", exc)

    def export_graph(
        self,
        output_path: str,
        file_format: str = "graphml",
    ) -> Optional[str]:
        """
        Export the current graph to disk in a standard graph file format.

        Args:
            output_path (str): Destination file path for the exported graph.
            file_format (str): Export format, either "graphml" or "gexf".
                Defaults to "graphml".

        Returns:
            Optional[str]: The output path if export succeeded, or None
                if export failed.
        """
        try:
            if self.graph is None or self.graph.number_of_nodes() == 0:
                logger.warning("export_graph() called but graph is empty or unbuilt.")
                return None

            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            normalized_format = file_format.lower().strip()

            if normalized_format == "graphml":
                nx.write_graphml(self.graph, path)
            elif normalized_format == "gexf":
                nx.write_gexf(self.graph, path)
            else:
                logger.error(
                    "Unsupported export format '%s'. Supported formats: "
                    "'graphml', 'gexf'.",
                    file_format,
                )
                return None

            logger.info(
                "Graph exported successfully to '%s' in '%s' format.",
                str(path),
                normalized_format,
            )

            return str(path)

        except Exception as exc:
            logger.exception("Unexpected error while exporting graph: %s", exc)
            return None