"""
MuleGuard Test Suite Package
================================

Purpose:
    Root package for all automated tests covering MuleGuard's parser,
    graph, risk_engine, dashboard, and report_generator modules.

Future Role:
    - Will house unit tests (per module) and integration tests
      (end-to-end pipeline tests) using pytest.
    - Will include fixtures providing controlled sample datasets
      for deterministic testing (kept separate from production data).
"""

# TODO: Add shared pytest fixtures in a conftest.py within this package
# TODO: Add test modules mirroring app/ structure:
#       test_transaction_parser.py, test_graph_builder.py,
#       test_mule_detector.py, test_risk_score.py, test_pdf_report.py