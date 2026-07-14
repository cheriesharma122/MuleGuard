"""
MuleGuard Investigation Dashboard Module
============================================

Purpose:
    Implements the interactive Streamlit-based user interface that
    allows investigators to upload UPI transaction datasets, review
    dataset statistics, explore the constructed transaction graph
    visually, and review flagged mule accounts with their risk scores.

Future Role:
    - Acts as the primary user-facing entry point into the MuleGuard
      analysis pipeline (parser -> graph -> risk engine -> dashboard).
    - Will be extended with report generation triggers, saved-session
      support, and richer graph filtering/drill-down controls as the
      report_generator module matures.

Author: MuleGuard Engineering Team
"""

import logging
import tempfile
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import networkx as nx
import plotly.express as px
from pyvis.network import Network

from app.parser.transaction_parser import TransactionParser, TransactionSchemaError
from app.graph.graph_builder import GraphBuilder
from app.risk_engine.risk_score import RiskScore, RiskLevel
from app.risk_engine.mule_detector import MuleDetector

logger = logging.getLogger("muleguard.dashboard")


class Dashboard:
    """
    Encapsulates the Streamlit dashboard UI and its interaction with
    the underlying MuleGuard analysis pipeline.

    Responsibilities:
        - Render dashboard layout (sidebar, tabs, widgets).
        - Manage Streamlit session state for uploaded data and
          analysis results.
        - Orchestrate calls into the parser, graph, and risk_engine
          modules based on user interaction.
        - Render graph visualizations and summary metrics/alerts.
    """

    def __init__(self) -> None:
        """
        Initialize the Dashboard controller and its underlying
        pipeline components.
        """
        self.parser = TransactionParser(
            required_columns=["sender_vpa", "receiver_vpa", "amount", "timestamp"]
        )
        self.graph_builder = GraphBuilder(directed=True)
        self.risk_score_engine = RiskScore()
        self.mule_detector = MuleDetector(risk_score_engine=self.risk_score_engine)

        self._init_session_state()

        logger.debug("Dashboard initialized.")

    def _init_session_state(self) -> None:
        """
        Initialize Streamlit session_state keys used across reruns,
        if they do not already exist.
        """
        defaults: Dict[str, Any] = {
            "raw_dataframe": None,
            "cleaned_dataframe": None,
            "graph": None,
            "detection_results": None,
            "summary_stats": None,
            "upload_error": None,
        }
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    def _save_uploaded_file(self, uploaded_file: Any) -> Optional[str]:
        """
        Persist a Streamlit UploadedFile object to a temporary file on
        disk so it can be consumed by TransactionParser.load_file().

        Args:
            uploaded_file: The Streamlit UploadedFile object.

        Returns:
            Optional[str]: Path to the temporary file, or None on failure.
        """
        try:
            suffix = Path(uploaded_file.name).suffix or ".csv"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                temp_path = tmp_file.name

            logger.info("Uploaded file saved temporarily at '%s'.", temp_path)
            return temp_path

        except Exception as exc:
            logger.exception("Unexpected error while saving uploaded file: %s", exc)
            return None

    def process_uploaded_file(self, uploaded_file: Any) -> None:
        """
        Run the full ingestion pipeline (load -> validate -> clean ->
        build graph -> detect mules) on an uploaded transaction file,
        storing results in Streamlit session state.

        Args:
            uploaded_file: The Streamlit UploadedFile object.
        """
        st.session_state["upload_error"] = None

        try:
            if uploaded_file is None:
                st.session_state["upload_error"] = "No file was uploaded."
                return

            temp_path = self._save_uploaded_file(uploaded_file)
            if temp_path is None:
                st.session_state["upload_error"] = "Failed to save the uploaded file."
                return

            raw_dataframe = self.parser.load_file(temp_path)
            if raw_dataframe is None or raw_dataframe.empty:
                st.session_state["upload_error"] = (
                    "The uploaded file could not be read or is empty. "
                    "Please upload a valid CSV, Excel, or JSON file."
                )
                return

            try:
                self.parser.validate_schema(raw_dataframe)
            except TransactionSchemaError as exc:
                st.session_state["upload_error"] = f"Schema validation failed: {exc}"
                return

            cleaned_dataframe = self.parser.clean_data(raw_dataframe)

            graph = self.graph_builder.build_graph(cleaned_dataframe)
            if graph is None or graph.number_of_nodes() == 0:
                st.session_state["upload_error"] = (
                    "Unable to construct a transaction graph from the "
                    "uploaded dataset."
                )
                return

            detection_results = self.mule_detector.detect(graph)
            summary_stats = self.mule_detector.get_summary_statistics(graph)

            st.session_state["raw_dataframe"] = raw_dataframe
            st.session_state["cleaned_dataframe"] = cleaned_dataframe
            st.session_state["graph"] = graph
            st.session_state["detection_results"] = detection_results
            st.session_state["summary_stats"] = summary_stats

            logger.info(
                "File processed successfully. Rows=%d, Nodes=%d, Edges=%d, Flagged=%d.",
                len(cleaned_dataframe),
                graph.number_of_nodes(),
                graph.number_of_edges(),
                len(detection_results),
            )

        except Exception as exc:
            logger.exception("Unexpected error while processing uploaded file: %s", exc)
            st.session_state["upload_error"] = (
                f"An unexpected error occurred while processing the file: {exc}"
            )

    def render_sidebar(self) -> None:
        """
        Render the sidebar containing file upload controls and
        pipeline trigger actions.
        """
        try:
            st.sidebar.title("MuleGuard")
            st.sidebar.caption("UPI Mule Account Investigation Platform")

            uploaded_file = st.sidebar.file_uploader(
                "Upload UPI transaction dataset",
                type=["csv", "xlsx", "xls", "json"],
                help="Supported formats: CSV, Excel (.xlsx/.xls), JSON.",
            )

            if st.sidebar.button("Run Analysis", use_container_width=True):
                if uploaded_file is None:
                    st.sidebar.warning("Please upload a file before running analysis.")
                else:
                    with st.spinner("Processing transaction data..."):
                        self.process_uploaded_file(uploaded_file)

            if st.sidebar.button("Clear Session", use_container_width=True):
                for key in [
                    "raw_dataframe", "cleaned_dataframe", "graph",
                    "detection_results", "summary_stats", "upload_error",
                ]:
                    st.session_state[key] = None
                st.sidebar.info("Session cleared.")

            if st.session_state.get("upload_error"):
                st.sidebar.error(st.session_state["upload_error"])

        except Exception as exc:
            logger.exception("Unexpected error while rendering sidebar: %s", exc)
            st.sidebar.error("An error occurred while rendering the sidebar.")

    def render_overview_tab(self) -> None:
        """
        Render the dataset overview tab, including summary statistics
        and a preview of the cleaned transaction data.
        """
        try:
            dataframe: Optional[pd.DataFrame] = st.session_state.get("cleaned_dataframe")

            if dataframe is None or dataframe.empty:
                st.info("Upload a transaction dataset and click 'Run Analysis' to begin.")
                return

            summary = self.parser.get_summary_report(dataframe)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Transactions", summary.get("total_rows", 0))
            col2.metric("Unique Senders", summary.get("unique_senders") or "N/A")
            col3.metric("Unique Receivers", summary.get("unique_receivers") or "N/A")
            col4.metric("Duplicate Records", summary.get("duplicate_records", 0))

            date_range = summary.get("date_range")
            if date_range:
                st.caption(f"Date range: {date_range['start']} to {date_range['end']}")

            st.subheader("Dataset Preview")
            st.dataframe(dataframe.head(100), use_container_width=True)

        except Exception as exc:
            logger.exception("Unexpected error while rendering overview tab: %s", exc)
            st.error("An error occurred while rendering the dataset overview.")

    def render_graph_view_tab(self) -> None:
        """
        Render the interactive transaction graph visualization tab
        using pyvis, embedded within the Streamlit page.
        """
        try:
            graph: Optional[nx.DiGraph] = st.session_state.get("graph")
            detection_results: Optional[List[Dict[str, Any]]] = st.session_state.get(
                "detection_results"
            )

            if graph is None or graph.number_of_nodes() == 0:
                st.info("No transaction graph available yet. Run an analysis first.")
                return

            st.subheader("Transaction Network Graph")
            st.caption(
                f"{graph.number_of_nodes()} accounts, {graph.number_of_edges()} transactions."
            )

            risk_by_account: Dict[str, Dict[str, Any]] = {}
            if detection_results:
                risk_by_account = {
                    record["account"]: record for record in detection_results
                }

            category_colors = {
                "Low Risk": "#2ecc71",
                "Medium Risk": "#f39c12",
                "High Risk": "#e74c3c",
            }

            max_nodes_to_render = 300
            if graph.number_of_nodes() > max_nodes_to_render:
                st.warning(
                    f"Graph has {graph.number_of_nodes()} nodes; rendering only the "
                    f"top {max_nodes_to_render} highest-risk accounts for performance."
                )
                if detection_results:
                    top_accounts = {
                        record["account"]
                        for record in detection_results[:max_nodes_to_render]
                    }
                else:
                    top_accounts = set(list(graph.nodes())[:max_nodes_to_render])
                render_graph = graph.subgraph(top_accounts).copy()
            else:
                render_graph = graph

            net = Network(
                height="600px",
                width="100%",
                directed=True,
                bgcolor="#0e1117",
                font_color="white",
            )

            for node in render_graph.nodes():
                record = risk_by_account.get(node)
                category = record.get("category") if record else "Unknown"
                score = record.get("score") if record else 0.0
                color = category_colors.get(category, "#95a5a6")

                net.add_node(
                    node,
                    label=str(node),
                    title=f"Account: {node}\nCategory: {category}\nScore: {score}",
                    color=color,
                )

            for source, target, data in render_graph.edges(data=True):
                amount = data.get("amount")
                timestamp = data.get("timestamp")
                edge_title = f"Amount: {amount}\nTimestamp: {timestamp}"
                net.add_edge(source, target, title=edge_title)

            net.set_options("""
            var options = {
              "physics": {
                "stabilization": true,
                "barnesHut": {
                  "gravitationalConstant": -8000,
                  "springLength": 150
                }
              }
            }
            """)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_html:
                net.save_graph(tmp_html.name)
                html_path = tmp_html.name

            with open(html_path, "r", encoding="utf-8") as html_file:
                html_content = html_file.read()

            st.components.v1.html(html_content, height=620, scrolling=True)

        except Exception as exc:
            logger.exception("Unexpected error while rendering graph view tab: %s", exc)
            st.error("An error occurred while rendering the transaction graph.")

    def render_flagged_accounts_tab(self) -> None:
        """
        Render the tab listing flagged mule accounts with their risk
        scores, categories, and explanations.
        """
        try:
            detection_results: Optional[List[Dict[str, Any]]] = st.session_state.get(
                "detection_results"
            )

            if not detection_results:
                st.info("No flagged accounts available yet. Run an analysis first.")
                return

            st.subheader("Flagged Accounts")

            category_filter = st.multiselect(
                "Filter by risk category",
                options=["Low Risk", "Medium Risk", "High Risk"],
                default=["Medium Risk", "High Risk"],
            )

            filtered_results = [
                record for record in detection_results
                if record.get("category") in category_filter
            ] if category_filter else detection_results

            if not filtered_results:
                st.warning("No accounts match the selected filter.")
                return

            table_data = [
                {
                    "Account": record.get("account"),
                    "Risk Score": record.get("score"),
                    "Category": record.get("category"),
                    "Incoming Txns": int(record.get("raw_metrics", {}).get("incoming_volume", 0)),
                    "Outgoing Txns": int(record.get("raw_metrics", {}).get("outgoing_volume", 0)),
                    "Total Amount": record.get("raw_metrics", {}).get("total_amount", 0.0),
                    "Unique Counterparties": int(
                        record.get("raw_metrics", {}).get("unique_counterparties", 0)
                    ),
                }
                for record in filtered_results
            ]

            results_df = pd.DataFrame(table_data)
            st.dataframe(results_df, use_container_width=True)

            fig = px.histogram(
                results_df,
                x="Risk Score",
                color="Category",
                nbins=20,
                title="Risk Score Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Account Drill-Down")
            selected_account = st.selectbox(
                "Select an account to view details",
                options=[record.get("account") for record in filtered_results],
            )

            if selected_account:
                selected_record = next(
                    (r for r in filtered_results if r.get("account") == selected_account),
                    None,
                )
                if selected_record:
                    st.write(selected_record.get("explanation", "No explanation available."))
                    st.json(selected_record.get("raw_metrics", {}))

        except Exception as exc:
            logger.exception("Unexpected error while rendering flagged accounts tab: %s", exc)
            st.error("An error occurred while rendering flagged accounts.")

    def render_alerts_and_summary(self) -> None:
        """
        Render top-level summary metrics and alert banners based on
        the mule detection summary statistics.
        """
        try:
            summary_stats: Optional[Dict[str, Any]] = st.session_state.get("summary_stats")

            if not summary_stats or not summary_stats.get("total_accounts_analyzed"):
                return

            st.subheader("Investigation Summary")

            category_counts = summary_stats.get("category_counts", {})
            total_accounts = summary_stats.get("total_accounts_analyzed", 0)
            average_score = summary_stats.get("average_score", 0.0)
            highest_risk_account = summary_stats.get("highest_risk_account")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Accounts", total_accounts)
            col2.metric("High Risk", category_counts.get("High Risk", 0))
            col3.metric("Medium Risk", category_counts.get("Medium Risk", 0))
            col4.metric("Average Risk Score", f"{average_score:.2f}")

            high_risk_count = category_counts.get("High Risk", 0)
            if high_risk_count > 0:
                st.error(
                    f"⚠️ {high_risk_count} account(s) flagged as HIGH RISK. "
                    f"Immediate investigation recommended."
                )
            elif category_counts.get("Medium Risk", 0) > 0:
                st.warning(
                    f"{category_counts.get('Medium Risk', 0)} account(s) flagged as "
                    f"MEDIUM RISK. Review recommended."
                )
            else:
                st.success("No high or medium risk accounts detected.")

            if highest_risk_account:
                st.caption(
                    f"Highest risk account: {highest_risk_account.get('account')} "
                    f"(Score: {highest_risk_account.get('score')}, "
                    f"Category: {highest_risk_account.get('category')})"
                )

        except Exception as exc:
            logger.exception("Unexpected error while rendering alerts/summary: %s", exc)
            st.error("An error occurred while rendering the investigation summary.")

    def run(self) -> None:
        """
        Main entry point that renders the full dashboard layout,
        including sidebar, summary/alerts, and tabbed content.
        """
        try:
            st.set_page_config(
                page_title="MuleGuard - UPI Mule Account Investigation",
                layout="wide",
            )

            st.title("MuleGuard")
            st.caption("Real-Time Transaction Graph Analysis for UPI Mule Account Identification")

            self.render_sidebar()
            self.render_alerts_and_summary()

            tab_overview, tab_graph, tab_flagged = st.tabs(
                ["Overview", "Graph View", "Flagged Accounts"]
            )

            with tab_overview:
                self.render_overview_tab()

            with tab_graph:
                self.render_graph_view_tab()

            with tab_flagged:
                self.render_flagged_accounts_tab()

        except Exception as exc:
            logger.exception("Unexpected error while rendering dashboard: %s", exc)
            st.error("A critical error occurred while rendering the MuleGuard dashboard.")


def main() -> None:
    """
    Streamlit script entry point (invoked via `streamlit run dashboard.py`).
    """
    dashboard = Dashboard()
    dashboard.run()
    st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 14px;'>"
    "Developed by <b>Cherie</b>"
    "</div>",
    unsafe_allow_html=True,
)


if __name__ == "__main__":
    main()