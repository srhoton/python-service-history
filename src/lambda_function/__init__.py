"""AWS Lambda function package for service history.

This package provides functionality for storing and retrieving service history
data via AWS Lambda, supporting both API Gateway and AppSync events.
"""

__version__ = "0.1.0"

from lambda_function.lambda_handler import (
    lambda_handler,
    ValidationError,
    handle_create_event,
    handle_read_event,
)

__all__ = ["lambda_handler", "ValidationError", "handle_create_event", "handle_read_event"]