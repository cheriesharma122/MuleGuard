"""
MuleGuard - Application Entry Point
=====================================

Purpose:
    This is the main orchestration script for the MuleGuard platform.
    It initializes the application, wires together the parser, graph,
    risk engine, dashboard, and report generator modules, and provides
    the primary execution entry point (CLI batch mode or dashboard
    launcher).

Future Role:
    - Acts as the composition root for the entire MuleGuard pipeline,
      coordinating data ingestion through to report generation.
    - Supports headless batch analysis mode for CI/automation use cases,
      in addition to the interactive Streamlit dashboard.
    - Provides centralized logging configuration for the whole application.

Author: MuleGuard Engineering Team
"""

import argparse
import logging
import logging.handlers
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from app.parser.transaction_parser import TransactionParser, TransactionSchemaError
from app.graph.graph_builder import GraphBuilder
from app.risk_engine.risk_score import RiskScore
from app.risk_engine.mule_detector import MuleDetector
from app.report_generator.pdf_report import PDFReportGenerator
from app.utils import constants

logger = logging.getLogger("muleguard.main")


class MuleGuardApplication:
    """
    Top-level orchestrator class for the MuleGuard investigation platform.

    Responsibilities:
        - Initialize and hold references to core subsystem components.
        - Coordinate the end-to-end pipeline: ingest -> build graph ->
          detect mules -> score risk -> report.
        - Provide a single controlled entry point for both CLI batch
          mode and Streamlit-based execution contexts.
    """

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        Initialize the MuleGuard application.

        Args:
            config_path (Optional[str]): Path to a configuration file.
                Reserved for future use (currently unused).
        """
        self.config_path = config_path

        self.parser = TransactionParser(
            required_columns=["sender_vpa", "receiver_vpa", "amount", "timestamp"]
        )
        self.graph_builder = GraphBuilder(directed=True)
        self.risk_score_engine = RiskScore()
        self.mule_detector = MuleDetector(risk_score_engine=self.risk_score_engine)
        self.report_generator = PDFReportGenerator(output_dir=str(constants.REPORTS_DIR))

        logger.debug("MuleGuardApplication initialized.")

    def setup_logging(self, log_level: str = "INFO") -> None:
        """
        Configure application-wide logging (console + rotating file handlers).

        Args:
            log_level (str): Logging level as a string (e.g., "DEBUG", "INFO").
        """
        try:
            constants.LOGS_DIR.mkdir(parents=True, exist_ok=True)
            log_file_path = constants.LOGS_DIR / "muleguard.log"

            root_logger = logging.getLogger("muleguard")
            root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
            root_logger.handlers.clear()

            formatter = logging.Formatter(constants.DEFAULT_LOG_FORMAT)

            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            file_handler = logging.handlers.RotatingFileHandler(
                filename=str(log_file_path),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            logger.info("Logging initialized. Log file: %s", str(log_file_path))

        except Exception as exc:
            logging.basicConfig(level=logging.INFO)
            logger.exception("Failed to configure advanced logging, falling back to basic config: %s", exc)

    def run_pipeline(self, input_file: str) -> Optional[Dict[str, Any]]:
        """
        Execute the full MuleGuard analysis pipeline on a given dataset.

        Args:
            input_file (str): Path to the raw UPI transaction dataset.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing pipeline
                results (raw_dataframe, cleaned_dataframe, graph,
                detection_results, summary_stats), or None on failure.
        """
        try:
            logger.info("Starting MuleGuard pipeline for input file: %s", input_file)

            raw_dataframe = self.parser.load_file(input_file)
            if raw_dataframe is None or raw_dataframe.empty:
                logger.error("Failed to load input file or file is empty: %s", input_file)
                return None

            try:
                self.parser.validate_schema(raw_dataframe)
            except TransactionSchemaError as exc:
                logger.error("Schema validation failed: %s", exc)
                return None

            cleaned_dataframe = self.parser.clean_data(raw_dataframe)
            dataset_summary = self.parser.get_summary_report(cleaned_dataframe)

            graph = self.graph_builder.build_graph(cleaned_dataframe)
            if graph is None or graph.number_of_nodes() == 0:
                logger.error("Failed to build transaction graph from cleaned data.")
                return None

            detection_results = self.mule_detector.detect(graph)
            summary_stats = self.mule_detector.get_summary_statistics(graph)

            logger.info(
                "Pipeline completed successfully. Accounts analyzed: %d, "
                "High risk: %d, Medium risk: %d, Low risk: %d.",
                summary_stats.get("total_accounts_analyzed", 0),
                summary_stats.get("category_counts", {}).get("High Risk", 0),
                summary_stats.get("category_counts", {}).get("Medium Risk", 0),
                summary_stats.get("category_counts", {}).get("Low Risk", 0),
            )

            return {
                "raw_dataframe": raw_dataframe,
                "cleaned_dataframe": cleaned_dataframe,
                "dataset_summary": dataset_summary,
                "graph": graph,
                "detection_results": detection_results,
                "summary_stats": summary_stats,
            }

        except FileNotFoundError as exc:
            logger.error("Input file not found: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Unexpected error occurred in MuleGuard pipeline: %s", exc)
            return None

    def generate_report(
        self,
        pipeline_results: Dict[str, Any],
        case_id: Optional[str] = None,
        analyst_name: Optional[str] = None,
        dataset_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a PDF investigation report from completed pipeline results.

        Args:
            pipeline_results (Dict[str, Any]): Results dictionary returned
                by run_pipeline().
            case_id (Optional[str]): Case reference identifier.
            analyst_name (Optional[str]): Name of the analyst running the report.
            dataset_name (Optional[str]): Name of the dataset analyzed.

        Returns:
            Optional[str]: Path to the generated PDF report, or None on failure.
        """
        try:
            metadata = {
                "case_id": case_id or "N/A",
                "analyst_name": analyst_name or "N/A",
                "dataset_name": dataset_name or "N/A",
            }

            report_path = self.report_generator.generate_report(
                metadata=metadata,
                summary_data=pipeline_results.get("dataset_summary"),
                flagged_accounts=pipeline_results.get("detection_results"),
                investigation_summary=pipeline_results.get("summary_stats"),
            )

            if report_path:
                logger.info("Investigation report generated at: %s", report_path)
            else:
                logger.warning("Report generation returned no output path.")

            return report_path

        except Exception as exc:
            logger.exception("Unexpected error while generating investigation report: %s", exc)
            return None

    def launch_dashboard(self) -> None:
        """
        Launch the Streamlit-based investigation dashboard as a subprocess.
        """
        try:
            dashboard_path = Path(__file__).resolve().parent / "app" / "dashboard" / "dashboard.py"

            if not dashboard_path.exists():
                logger.error("Dashboard entry point not found at: %s", str(dashboard_path))
                return

            logger.info("Launching MuleGuard dashboard: streamlit run %s", str(dashboard_path))

            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", str(dashboard_path)],
                check=True,
            )

        except subprocess.CalledProcessError as exc:
            logger.error("Streamlit dashboard process exited with an error: %s", exc)
        except FileNotFoundError as exc:
            logger.error("Streamlit executable not found. Is streamlit installed? %s", exc)
        except Exception as exc:
            logger.exception("Unexpected error while launching dashboard: %s", exc)


def parse_cli_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments for headless/batch execution mode or
    dashboard launch mode.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="muleguard",
        description="MuleGuard - Real-Time Transaction Graph Analysis for UPI Mule Account Identification",
    )

    parser.add_argument(
        "--mode",
        choices=["dashboard", "batch"],
        default="dashboard",
        help="Execution mode: 'dashboard' launches the Streamlit UI, "
             "'batch' runs the pipeline headlessly. Defaults to 'dashboard'.",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to the input transaction dataset (required for batch mode).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate a PDF investigation report after batch analysis.",
    )
    parser.add_argument(
        "--case-id",
        type=str,
        default=None,
        help="Case reference ID to include in the generated report.",
    )
    parser.add_argument(
        "--analyst",
        type=str,
        default=None,
        help="Analyst name to include in the generated report.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG level) logging.",
    )

    return parser.parse_args()


def main() -> None:
    """
    Application entry point.

    Parses CLI arguments, initializes the MuleGuardApplication, and
    dispatches to either dashboard mode or headless batch pipeline mode.
    """
    args = parse_cli_arguments()

    app = MuleGuardApplication()
    app.setup_logging(log_level="DEBUG" if args.verbose else "INFO")

    logger.info("MuleGuard starting up in '%s' mode.", args.mode)

    try:
        if args.mode == "dashboard":
            app.launch_dashboard()

        elif args.mode == "batch":
            if not args.input:
                logger.error("Batch mode requires --input <path_to_dataset>.")
                sys.exit(1)

            pipeline_results = app.run_pipeline(args.input)

            if pipeline_results is None:
                logger.error("Pipeline execution failed. See logs above for details.")
                sys.exit(1)

            if args.report:
                app.generate_report(
                    pipeline_results,
                    case_id=args.case_id,
                    analyst_name=args.analyst,
                    dataset_name=Path(args.input).name,
                )

            logger.info("Batch analysis completed successfully.")

    except KeyboardInterrupt:
        logger.warning("MuleGuard execution interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        logger.exception("Unhandled exception in MuleGuard main(): %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()