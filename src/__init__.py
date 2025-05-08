"""Service History Lambda package.

This package provides AWS Lambda functions for service history
logging and retrieval via API Gateway and AppSync.
"""

__version__ = "0.1.0"

from src.lambda_function import lambda_handler, ValidationError

__all__ = ["lambda_handler", "ValidationError"]