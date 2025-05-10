"""AWS Lambda function package for service history.

This package provides functionality for storing and retrieving service history
data via AWS Lambda, supporting both API Gateway and AppSync events.
"""

__version__ = "0.1.0"

from .lambda_handler import (
    ValidationError,
    handle_create_event,
    handle_read_event,
    lambda_handler,
)

__all__ = ["ValidationError", "handle_create_event", "handle_read_event", "lambda_handler"]
