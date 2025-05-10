"""AWS Lambda function for service history handling.

This module provides a Lambda handler for processing service history events
through API Gateway and AppSync. It supports storing service events in CloudWatch Logs
and retrieving historical data.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

import boto3
from dateutil import parser

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
appconfig_client = boto3.client("appconfig")
logs_client = boto3.client("logs")

# Constants
APP_ID = os.environ.get("APPCONFIG_APP_ID", "ServiceHistoryApp")
ENV_ID = os.environ.get("APPCONFIG_ENV_ID", "Production")
CONFIG_PROFILE_ID = os.environ.get("APPCONFIG_CONFIG_PROFILE_ID", "ServiceHistoryConfig")
LOG_GROUP_CONFIG_KEY = "logGroup"


class ValidationError(Exception):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        """Initialize ValidationError.

        Args:
            message: Error description
            status_code: HTTP status code
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def get_log_group_name() -> str:
    """Retrieve log group name from AWS AppConfig.

    Returns:
        The configured log group name.

    Raises:
        ValidationError: If configuration is missing or invalid
        Exception: If unable to retrieve configuration due to AWS service issues
    """
    try:
        response = appconfig_client.get_configuration(
            Application=APP_ID,
            Environment=ENV_ID,
            Configuration=CONFIG_PROFILE_ID,
            ClientId="ServiceHistoryLambda",
        )

        try:
            config_data = json.loads(response["Content"].read())
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Invalid AppConfig configuration format: {e!s}")
            raise ValidationError(f"Invalid configuration format: {e!s}") from e

        log_group_name = config_data.get(LOG_GROUP_CONFIG_KEY)

        if not log_group_name:
            raise ValidationError(f"Configuration missing '{LOG_GROUP_CONFIG_KEY}' key")

        if not isinstance(log_group_name, str):
            raise ValidationError(
                f"Invalid log group name type: expected string, got {type(log_group_name).__name__}"
            )

        return log_group_name
    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve AppConfig configuration: {e!s}")
        raise ValidationError(f"Could not retrieve log group configuration: {e!s}") from e


def extract_id_from_path(path: str) -> str:
    """Extract ID from the request path.

    Args:
        path: The API path

    Returns:
        The extracted ID

    Raises:
        ValidationError: If ID cannot be extracted or path is invalid
    """
    try:
        if not isinstance(path, str):
            raise ValidationError(
                f"Invalid path format: expected string, got {type(path).__name__}"
            )

        if not path:
            raise ValidationError("Empty path provided")

        match = re.search(r"/([^/]+)$", path)
        if not match:
            raise ValidationError("ID not found in request path")

        id_value = match.group(1)
        if not id_value:
            raise ValidationError("Extracted ID is empty")

        return id_value
    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error extracting ID from path '{path}': {e!s}")
        raise ValidationError(f"Failed to extract ID from path: {e!s}") from e


def validate_create_input(body: Dict[str, Any]) -> None:
    """Validate the input data for create operation.

    Args:
        body: The request body

    Raises:
        ValidationError: If validation fails
    """
    try:
        if body is None:
            raise ValidationError("Request body cannot be None")

        if not isinstance(body, dict):
            raise ValidationError(f"Request body must be a JSON object, got {type(body).__name__}")

        if not body:
            raise ValidationError("Request body cannot be empty")

    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error validating create input: {e!s}")
        raise ValidationError(f"Input validation failed: {e!s}") from e


def validate_read_input(query_params: Dict[str, str], id_value: str) -> Tuple[datetime, datetime]:
    """Validate the input data for read operation.

    Args:
        query_params: Query parameters
        id_value: The ID value

    Returns:
        Tuple of start and end datetimes

    Raises:
        ValidationError: If validation fails
    """
    if not id_value:
        raise ValidationError("ID is required")

    start_time = None
    end_time = None

    if "start" in query_params:
        try:
            start_time = parser.parse(query_params["start"])
        except ValueError as e:
            raise ValidationError("Invalid start time format. Expected ISO 8601 format.") from e

    if "end" in query_params:
        try:
            end_time = parser.parse(query_params["end"])
        except ValueError as e:
            raise ValidationError("Invalid end time format. Expected ISO 8601 format.") from e

    # Default to last hour if not specified
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=1)

    if end_time is None:
        end_time = datetime.now()

    # Validate time range
    if start_time >= end_time:
        raise ValidationError("Start time must be before end time")

    return start_time, end_time


def _validate_cloudwatch_inputs(log_group_name: str, id_value: str, data: Dict[str, Any]) -> None:
    """Validate inputs for CloudWatch logging.

    Args:
        log_group_name: The CloudWatch log group name
        id_value: The ID value
        data: The data to write

    Raises:
        ValidationError: If validation fails
    """
    if not log_group_name:
        raise ValidationError("Log group name cannot be empty")

    if not id_value:
        raise ValidationError("ID value cannot be empty")

    if data is None:
        raise ValidationError("Data cannot be None")


def _ensure_log_group_exists(log_group_name: str) -> None:
    """Ensure CloudWatch log group exists, creating it if needed.

    Args:
        log_group_name: The CloudWatch log group name

    Raises:
        ValidationError: If log group creation fails
    """
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
        logger.info(f"Created log group: {log_group_name}")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass
    except Exception as e:
        logger.error(f"Error creating log group '{log_group_name}': {e!s}")
        raise ValidationError(f"Failed to create log group: {e!s}") from e


def _create_log_stream(log_group_name: str, log_stream_name: str) -> None:
    """Create a CloudWatch log stream.

    Args:
        log_group_name: The CloudWatch log group name
        log_stream_name: The log stream name

    Raises:
        ValidationError: If log stream creation fails
    """
    try:
        logs_client.create_log_stream(logGroupName=log_group_name, logStreamName=log_stream_name)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass
    except Exception as e:
        logger.error(f"Error creating log stream '{log_stream_name}': {e!s}")
        raise ValidationError(f"Failed to create log stream: {e!s}") from e


def _put_log_event(
    log_group_name: str, log_stream_name: str, timestamp: int, event_data: Dict[str, Any]
) -> None:
    """Write log event to CloudWatch.

    Args:
        log_group_name: The CloudWatch log group name
        log_stream_name: The log stream name
        timestamp: Event timestamp in milliseconds
        event_data: Event data to log

    Raises:
        ValidationError: If putting log event fails
    """
    try:
        response = logs_client.put_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            logEvents=[{"timestamp": timestamp, "message": json.dumps(event_data)}],
        )
        if "rejectedLogEventsInfo" in response:
            logger.warning(f"Some log events were rejected: {response['rejectedLogEventsInfo']}")

    except json.JSONDecodeError as e:
        logger.error(f"Error serializing event data: {e!s}")
        raise ValidationError(f"Failed to serialize data to JSON: {e!s}") from e
    except Exception as e:
        logger.error(f"Error putting log events: {e!s}")
        raise ValidationError(f"Failed to write log events: {e!s}") from e


def write_to_cloudwatch(log_group_name: str, id_value: str, data: Dict[str, Any]) -> None:
    """Write data to CloudWatch Logs.

    Args:
        log_group_name: The CloudWatch log group name
        id_value: The ID value
        data: The data to write

    Raises:
        ValidationError: If input validation fails
        Exception: If write fails due to AWS service issues
    """
    try:
        # Validate inputs
        _validate_cloudwatch_inputs(log_group_name, id_value, data)

        # Ensure log group exists
        _ensure_log_group_exists(log_group_name)

        # Create a log stream with the ID and timestamp
        timestamp = int(time.time() * 1000)
        log_stream_name = f"{id_value}/{timestamp}"
        _create_log_stream(log_group_name, log_stream_name)

        # Create a structured log event with searchable fields
        event_data = {"id": id_value, "timestamp": timestamp, **data}

        # Write the log event
        _put_log_event(log_group_name, log_stream_name, timestamp, event_data)

    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Failed to write to CloudWatch Logs: {e!s}")
        raise ValidationError(f"Failed to write to CloudWatch: {e!s}") from e


def query_cloudwatch_logs(
    log_group_name: str, id_value: str, start_time: datetime, end_time: datetime
) -> List[Dict[str, Any]]:
    """Query CloudWatch Logs for historical data.

    Args:
        log_group_name: The CloudWatch log group name
        id_value: The ID to filter by
        start_time: Start time for query
        end_time: End time for query

    Returns:
        List of log events

    Raises:
        Exception: If query fails
    """
    try:
        # Convert datetime to milliseconds since epoch
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)

        # Create a query that filters by the ID
        query = (
            f'fields @timestamp, @message | filter @message like "{id_value}" | '
            f"sort @timestamp desc"
        )

        # Start query
        start_query_response = logs_client.start_query(
            logGroupName=log_group_name,
            startTime=start_time_ms,
            endTime=end_time_ms,
            queryString=query,
        )

        query_id = start_query_response["queryId"]

        # Poll for query results
        response = None
        while response is None or response["status"] == "Running":
            time.sleep(0.5)  # Wait before checking again
            response = logs_client.get_query_results(queryId=query_id)

        results = []
        for result in response.get("results", []):
            message = None
            timestamp = None

            for field in result:
                if field["field"] == "@message":
                    try:
                        message = json.loads(field["value"])
                    except json.JSONDecodeError:
                        message = field["value"]
                elif field["field"] == "@timestamp":
                    timestamp = field["value"]

            if message:
                # Add timestamp if available
                if timestamp and isinstance(message, dict):
                    message["@timestamp"] = timestamp
                results.append(message)

        return results

    except Exception as e:
        logger.error(f"Failed to query CloudWatch Logs: {e!s}")
        raise


def handle_create_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle create events from API Gateway or AppSync.

    Args:
        event: The Lambda event

    Returns:
        Response object

    Raises:
        ValidationError: If validation fails
    """
    # Extract path and body based on event source
    path = ""
    body = {}

    # Handle API Gateway event
    if "path" in event:
        path = event["path"]
        if "body" in event:
            try:
                body = (
                    json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                )
            except json.JSONDecodeError as e:
                raise ValidationError("Invalid JSON in request body") from e
    # Handle AppSync event
    elif "info" in event and "fieldName" in event["info"]:
        path = event["info"].get("fieldName", "")
        body = event.get("arguments", {})
    else:
        raise ValidationError("Unsupported event format")

    # Extract and validate ID
    id_value = extract_id_from_path(path)
    validate_create_input(body)

    # Get log group name from AppConfig
    log_group_name = get_log_group_name()

    # Write to CloudWatch
    write_to_cloudwatch(log_group_name, id_value, body)

    # Return success response
    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": "Data successfully recorded", "id": id_value, "success": True}
        ),
        "headers": {"Content-Type": "application/json"},
    }


def handle_read_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle read events from API Gateway or AppSync.

    Args:
        event: The Lambda event

    Returns:
        Response object with history data

    Raises:
        ValidationError: If validation fails
    """
    # Extract path and query parameters based on event source
    path = ""
    query_params = {}

    # Handle API Gateway event
    if "path" in event:
        path = event["path"]
        query_params = event.get("queryStringParameters", {}) or {}
    # Handle AppSync event
    elif "info" in event and "fieldName" in event["info"]:
        path = event["info"].get("fieldName", "")
        query_params = event.get("arguments", {})
    else:
        raise ValidationError("Unsupported event format")

    # Extract and validate ID
    id_value = extract_id_from_path(path)
    start_time, end_time = validate_read_input(query_params, id_value)

    # Get log group name from AppConfig
    log_group_name = get_log_group_name()

    # Query CloudWatch
    results = query_cloudwatch_logs(log_group_name, id_value, start_time, end_time)

    # Return response with results
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "id": id_value,
                "startTime": start_time.isoformat(),
                "endTime": end_time.isoformat(),
                "count": len(results),
                "records": results,
            }
        ),
        "headers": {"Content-Type": "application/json"},
    }


def lambda_handler(event: Dict[str, Any], context: object) -> Dict[str, Any]:
    """AWS Lambda handler function.

    Args:
        event: The Lambda event
        context: The Lambda context

    Returns:
        Response object

    Raises:
        Exception: If processing fails
    """
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Determine HTTP method or GraphQL operation type
        method = ""

        # Handle API Gateway event
        if "httpMethod" in event:
            method = event["httpMethod"]
        # Handle AppSync event
        elif "info" in event and "fieldName" in event["info"]:
            operation_type = event["info"].get("parentTypeName", "").upper()
            if operation_type == "MUTATION":
                method = "POST"  # Treat mutations as POST
            elif operation_type == "QUERY":
                method = "GET"  # Treat queries as GET

        # Process based on method
        if method == "POST" or method == "PUT":
            return handle_create_event(event)
        elif method == "GET":
            return handle_read_event(event)
        elif method == "DELETE" or method == "PATCH":
            return {
                "statusCode": 405,
                "body": json.dumps(
                    {
                        "message": "Method not allowed. Update and Delete operations are not "
                        "supported.",
                        "success": False,
                    }
                ),
                "headers": {"Content-Type": "application/json"},
            }
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"message": f"Unsupported method: {method}", "success": False}),
                "headers": {"Content-Type": "application/json"},
            }

    except ValidationError as e:
        return {
            "statusCode": e.status_code,
            "body": json.dumps({"message": e.message, "success": False}),
            "headers": {"Content-Type": "application/json"},
        }
    except Exception as e:
        logger.error(f"Unhandled exception: {e!s}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal server error", "success": False}),
            "headers": {"Content-Type": "application/json"},
        }
