"""
MuleGuard PDF Report Generator Module
=========================================

Purpose:
    Responsible for generating professional, structured PDF investigation
    reports summarizing flagged mule accounts, their risk scores,
    detection reasoning, and dataset-level statistics for compliance
    and law-enforcement handoff.

Future Role:
    - Consumes the output of TransactionParser (dataset summary) and
      MuleDetector (detection results) to assemble a complete
      multi-section PDF report using reportlab.
    - Will be extended with embedded graph visualization images and
      configurable report branding/templates as the platform matures.
    - Writes generated reports to the /reports directory with
      timestamped filenames for traceability.

Author: MuleGuard Engineering Team
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

logger = logging.getLogger("muleguard.report_generator")


class ReportGenerationError(Exception):
    """
    Raised when the PDF investigation report cannot be generated.
    """
    pass


class PDFReportGenerator:
    """
    Generates formal PDF investigation reports summarizing MuleGuard's
    analysis results for a given transaction dataset.

    Responsibilities:
        - Assemble report content (cover page, dataset summary,
          flagged accounts, investigation summary) into a structured
          PDF document via reportlab.
        - Manage report output paths and timestamped file naming.
        - Provide a consistent, professional report template.
    """

    def __init__(self, output_dir: str = "reports") -> None:
        """
        Initialize the PDFReportGenerator.

        Args:
            output_dir (str): Directory where generated PDF reports
                will be saved. Defaults to the project's `reports/` folder.
        """
        try:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)

            self.styles = getSampleStyleSheet()
            self._register_custom_styles()

            logger.debug(
                "PDFReportGenerator initialized with output_dir='%s'.",
                str(self.output_dir),
            )

        except Exception as exc:
            logger.exception("Unexpected error while initializing PDFReportGenerator: %s", exc)
            raise

    def _register_custom_styles(self) -> None:
        """
        Register custom paragraph styles used throughout the report,
        skipping registration if a style name already exists.
        """
        custom_styles = [
            ParagraphStyle(
                name="MuleGuardTitle",
                fontSize=24,
                leading=28,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1a1a2e"),
                spaceAfter=12,
            ),
            ParagraphStyle(
                name="MuleGuardSubtitle",
                fontSize=13,
                leading=16,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#555555"),
                spaceAfter=20,
            ),
            ParagraphStyle(
                name="MuleGuardSectionHeading",
                fontSize=15,
                leading=18,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#0f3460"),
                spaceBefore=16,
                spaceAfter=8,
            ),
            ParagraphStyle(
                name="MuleGuardBodyText",
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#222222"),
                spaceAfter=6,
            ),
            ParagraphStyle(
                name="MuleGuardCaption",
                fontSize=9,
                leading=12,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#777777"),
                spaceAfter=6,
            ),
        ]

        for style in custom_styles:
            if style.name not in self.styles:
                self.styles.add(style)

    def build_cover_page(self, metadata: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Build the report's cover page section (title, case reference,
        generation timestamp, analyst name).

        Args:
            metadata (Optional[Dict[str, Any]]): Report metadata such as
                case ID, dataset name, and analyst identifier.

        Returns:
            List[Any]: A list of reportlab flowables representing the
                cover page.
        """
        try:
            metadata = metadata or {}

            case_id = metadata.get("case_id", "N/A")
            dataset_name = metadata.get("dataset_name", "N/A")
            analyst_name = metadata.get("analyst_name", "N/A")
            generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            story: List[Any] = [
                Spacer(1, 3 * cm),
                Paragraph("MuleGuard Investigation Report", self.styles["MuleGuardTitle"]),
                Paragraph(
                    "Real-Time Transaction Graph Analysis for UPI Mule Account Identification",
                    self.styles["MuleGuardSubtitle"],
                ),
                Spacer(1, 1 * cm),
            ]

            metadata_table_data = [
                ["Report Generated On:", generated_at],
                ["Case Reference ID:", str(case_id)],
                ["Dataset Analyzed:", str(dataset_name)],
                ["Analyst:", str(analyst_name)],
            ]

            metadata_table = Table(metadata_table_data, colWidths=[5 * cm, 9 * cm])
            metadata_table.setStyle(
                TableStyle([
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0f3460")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ])
            )

            story.append(metadata_table)
            story.append(PageBreak())

            return story

        except Exception as exc:
            logger.exception("Unexpected error while building cover page: %s", exc)
            raise ReportGenerationError(f"Failed to build cover page: {exc}") from exc

    def build_dataset_summary_section(
        self, summary_data: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Build the dataset summary section describing the analyzed
        transaction dataset.

        Args:
            summary_data (Optional[Dict[str, Any]]): Dataset summary
                statistics (total_rows, unique_senders, unique_receivers,
                total_missing_values, duplicate_records, date_range).

        Returns:
            List[Any]: A list of reportlab flowables for this section.
        """
        try:
            summary_data = summary_data or {}

            story: List[Any] = [
                Paragraph("1. Dataset Summary", self.styles["MuleGuardSectionHeading"]),
            ]

            if not summary_data:
                story.append(
                    Paragraph(
                        "No dataset summary information is available for this report.",
                        self.styles["MuleGuardBodyText"],
                    )
                )
                return story

            date_range = summary_data.get("date_range")
            date_range_text = (
                f"{date_range.get('start')} to {date_range.get('end')}"
                if date_range else "N/A"
            )

            table_data = [
                ["Metric", "Value"],
                ["Total Transactions", str(summary_data.get("total_rows", "N/A"))],
                ["Total Columns", str(summary_data.get("total_columns", "N/A"))],
                ["Unique Senders", str(summary_data.get("unique_senders", "N/A"))],
                ["Unique Receivers", str(summary_data.get("unique_receivers", "N/A"))],
                ["Missing Values", str(summary_data.get("total_missing_values", "N/A"))],
                ["Duplicate Records", str(summary_data.get("duplicate_records", "N/A"))],
                ["Date Range", date_range_text],
            ]

            table = Table(table_data, colWidths=[7 * cm, 7 * cm])
            table.setStyle(self._default_table_style())

            story.append(table)
            story.append(Spacer(1, 0.5 * cm))

            return story

        except Exception as exc:
            logger.exception("Unexpected error while building dataset summary section: %s", exc)
            raise ReportGenerationError(f"Failed to build dataset summary section: {exc}") from exc

    def build_flagged_accounts_section(
        self, flagged_accounts: Optional[List[Dict[str, Any]]] = None
    ) -> List[Any]:
        """
        Build the detailed section listing each flagged account, its
        risk score, category, and detection reasoning.

        Args:
            flagged_accounts (Optional[List[Dict[str, Any]]]): Scored,
                flagged account records produced by MuleDetector.

        Returns:
            List[Any]: A list of reportlab flowables for this section.
        """
        try:
            flagged_accounts = flagged_accounts or []

            story: List[Any] = [
                Paragraph("2. Suspicious Mule Accounts", self.styles["MuleGuardSectionHeading"]),
            ]

            if not flagged_accounts:
                story.append(
                    Paragraph(
                        "No suspicious mule accounts were identified in this dataset.",
                        self.styles["MuleGuardBodyText"],
                    )
                )
                return story

            summary_table_data = [["Account", "Risk Score", "Category"]]
            for record in flagged_accounts:
                summary_table_data.append([
                    str(record.get("account", "N/A")),
                    f"{record.get('score', 0.0):.2f}",
                    str(record.get("category", "N/A")),
                ])

            summary_table = Table(summary_table_data, colWidths=[6 * cm, 4 * cm, 4 * cm])
            summary_table.setStyle(self._default_table_style())
            story.append(summary_table)
            story.append(Spacer(1, 0.5 * cm))

            story.append(Paragraph("2.1 Detection Reasoning", self.styles["MuleGuardSectionHeading"]))

            for record in flagged_accounts:
                account = record.get("account", "N/A")
                category = record.get("category", "N/A")
                score = record.get("score", 0.0)
                explanation = record.get(
                    "explanation",
                    "No detailed explanation available for this account.",
                )

                story.append(
                    Paragraph(
                        f"<b>Account:</b> {account} &nbsp;&nbsp; "
                        f"<b>Score:</b> {score:.2f} &nbsp;&nbsp; "
                        f"<b>Category:</b> {category}",
                        self.styles["MuleGuardBodyText"],
                    )
                )
                story.append(Paragraph(explanation, self.styles["MuleGuardCaption"]))
                story.append(Spacer(1, 0.3 * cm))

            return story

        except Exception as exc:
            logger.exception("Unexpected error while building flagged accounts section: %s", exc)
            raise ReportGenerationError(f"Failed to build flagged accounts section: {exc}") from exc

    def build_investigation_summary_section(
        self, investigation_summary: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Build the investigation summary section highlighting aggregate
        detection statistics and overall risk posture.

        Args:
            investigation_summary (Optional[Dict[str, Any]]): Summary
                statistics produced by MuleDetector.get_summary_statistics().

        Returns:
            List[Any]: A list of reportlab flowables for this section.
        """
        try:
            investigation_summary = investigation_summary or {}

            story: List[Any] = [
                Paragraph("3. Investigation Summary", self.styles["MuleGuardSectionHeading"]),
            ]

            if not investigation_summary or not investigation_summary.get("total_accounts_analyzed"):
                story.append(
                    Paragraph(
                        "No investigation summary statistics are available for this report.",
                        self.styles["MuleGuardBodyText"],
                    )
                )
                return story

            category_counts = investigation_summary.get("category_counts", {})
            total_accounts = investigation_summary.get("total_accounts_analyzed", 0)
            average_score = investigation_summary.get("average_score", 0.0)
            highest_risk_account = investigation_summary.get("highest_risk_account")

            table_data = [
                ["Metric", "Value"],
                ["Total Accounts Analyzed", str(total_accounts)],
                ["High Risk Accounts", str(category_counts.get("High Risk", 0))],
                ["Medium Risk Accounts", str(category_counts.get("Medium Risk", 0))],
                ["Low Risk Accounts", str(category_counts.get("Low Risk", 0))],
                ["Average Risk Score", f"{average_score:.2f}"],
            ]

            table = Table(table_data, colWidths=[7 * cm, 7 * cm])
            table.setStyle(self._default_table_style())
            story.append(table)
            story.append(Spacer(1, 0.5 * cm))

            if highest_risk_account:
                story.append(
                    Paragraph(
                        f"<b>Highest Risk Account:</b> "
                        f"{highest_risk_account.get('account', 'N/A')} "
                        f"(Score: {highest_risk_account.get('score', 0.0):.2f}, "
                        f"Category: {highest_risk_account.get('category', 'N/A')})",
                        self.styles["MuleGuardBodyText"],
                    )
                )

            high_risk_count = category_counts.get("High Risk", 0)
            if high_risk_count > 0:
                conclusion = (
                    f"This investigation identified {high_risk_count} account(s) "
                    f"exhibiting high-risk mule account behavior. Immediate "
                    f"further investigation and potential account restriction "
                    f"is recommended for these accounts."
                )
            elif category_counts.get("Medium Risk", 0) > 0:
                conclusion = (
                    f"This investigation identified "
                    f"{category_counts.get('Medium Risk', 0)} account(s) with "
                    f"moderate risk indicators. Continued monitoring is recommended."
                )
            else:
                conclusion = (
                    "No accounts exhibiting significant mule account behavior "
                    "were identified in this dataset."
                )

            story.append(Spacer(1, 0.3 * cm))
            story.append(Paragraph(conclusion, self.styles["MuleGuardBodyText"]))

            return story

        except Exception as exc:
            logger.exception(
                "Unexpected error while building investigation summary section: %s", exc
            )
            raise ReportGenerationError(
                f"Failed to build investigation summary section: {exc}"
            ) from exc

    def _default_table_style(self) -> TableStyle:
        """
        Provide a consistent default TableStyle used across report tables.

        Returns:
            TableStyle: A reportlab TableStyle instance.
        """
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])

    def generate_report(
        self,
        metadata: Optional[Dict[str, Any]] = None,
        summary_data: Optional[Dict[str, Any]] = None,
        flagged_accounts: Optional[List[Dict[str, Any]]] = None,
        investigation_summary: Optional[Dict[str, Any]] = None,
        output_filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate the complete PDF investigation report and write it to disk.

        Args:
            metadata (Optional[Dict[str, Any]]): Report metadata for the
                cover page (case_id, dataset_name, analyst_name).
            summary_data (Optional[Dict[str, Any]]): Dataset summary
                statistics from TransactionParser.get_summary_report().
            flagged_accounts (Optional[List[Dict[str, Any]]]): Flagged
                account records from MuleDetector.detect().
            investigation_summary (Optional[Dict[str, Any]]): Summary
                statistics from MuleDetector.get_summary_statistics().
            output_filename (Optional[str]): Desired output filename;
                defaults to an auto-generated timestamped name.

        Returns:
            Optional[str]: Path to the generated PDF file, or None on failure.
        """
        try:
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"muleguard_report_{timestamp}.pdf"

            if not output_filename.lower().endswith(".pdf"):
                output_filename += ".pdf"

            output_path = self.output_dir / output_filename

            document = SimpleDocTemplate(
                str(output_path),
                pagesize=A4,
                leftMargin=2 * cm,
                rightMargin=2 * cm,
                topMargin=2 * cm,
                bottomMargin=2 * cm,
                title="MuleGuard Investigation Report",
                author="MuleGuard",
            )

            story: List[Any] = []
            story.extend(self.build_cover_page(metadata))
            story.extend(self.build_dataset_summary_section(summary_data))
            story.extend(self.build_flagged_accounts_section(flagged_accounts))
            story.extend(self.build_investigation_summary_section(investigation_summary))

            document.build(story)

            logger.info("PDF investigation report generated successfully at '%s'.", str(output_path))

            return str(output_path)

        except ReportGenerationError as exc:
            logger.error("Report generation failed: %s", exc)
            return None
        except Exception as exc:
            logger.exception("Unexpected error while generating PDF report: %s", exc)
            return None