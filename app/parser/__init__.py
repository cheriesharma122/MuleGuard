"""
MuleGuard Parser Subpackage
=============================

Purpose:
    Groups all modules responsible for ingesting, validating, and
    normalizing raw UPI transaction data before it enters the graph
    construction stage.

Future Role:
    - Will expose TransactionParser and any related validation/schema
      utilities as the public interface of this subpackage.
"""

# TODO: Expose TransactionParser at subpackage level once stable
# from app.parser.transaction_parser import TransactionParser