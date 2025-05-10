"""Tests for the lambda_handler module."""

import json
import os
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from dateutil import parser

from src.lambda_function.lambda_handler import (
    ValidationError,
    extract_id_from_path,
    get_log_group_name,
    handle_create_event,
    handle_read_event,
    lambda_handler,
    query_cloudwatch_logs,
    validate_create_input,
    validate_read_input,
    write_to_cloudwatch,
)


@pytest.fixture
def mock_appconfig() -> MagicMock:
    """Set up mock AppConfig client for testing.

    Returns:
        Mock AppConfig client.
    """
    with patch("src.lambda_function.lambda_handler.appconfig_client") as mock_client:
        mock_response = {
            "Content": MagicMock(
                read=MagicMock(return_value=json.dumps({"logGroup": "test-log-group"}).encode())
            )
        }
        mock_client.get_configuration.return_value = mock_response
        yield mock_client


@pytest.fixture
def set_environment_variables() -> None:
    """Set up environment variables for testing.

    Sets required environment variables and cleans them up after test.
    """
    os.environ["APPCONFIG_APP_ID"] = "TestApp"
    os.environ["APPCONFIG_ENV_ID"] = "TestEnv"
    os.environ["APPCONFIG_CONFIG_PROFILE_ID"] = "TestConfig"
    yield
    os.environ.pop("APPCONFIG_APP_ID", None)
    os.environ.pop("APPCONFIG_ENV_ID", None)
    os.environ.pop("APPCONFIG_CONFIG_PROFILE_ID", None)


class TestHelperFunctions:
    """Tests for helper functions in lambda_handler.py."""

    def test_extract_id_from_path(self) -> None:
        """Test extracting ID from path."""
        # Valid paths
        assert extract_id_from_path("/service/123") == "123"
        assert extract_id_from_path("/api/v1/history/abc-def") == "abc-def"

        # Invalid paths
        with pytest.raises(ValidationError):
            extract_id_from_path("/service/")
        with pytest.raises(ValidationError):
            extract_id_from_path("/")
        with pytest.raises(ValidationError):
            extract_id_from_path("")

    def test_get_log_group_name(
        self, mock_appconfig: MagicMock, set_environment_variables: None
    ) -> None:
        """Test retrieval of log group name from AppConfig."""
        # Test successful retrieval
        assert get_log_group_name() == "test-log-group"

        # Test with missing key
        mock_appconfig.get_configuration.return_value = {
            "Content": MagicMock(read=MagicMock(return_value=json.dumps({}).encode()))
        }
        with pytest.raises(ValidationError):
            get_log_group_name()

        # Test with exception
        mock_appconfig.get_configuration.side_effect = Exception("Test exception")
        with pytest.raises(Exception):
            get_log_group_name()

    def test_validate_create_input(self) -> None:
        """Test validation of create input data."""
        # Valid inputs
        validate_create_input({"key": "value"})
        validate_create_input({"multiple": "values", "number": 123})

        # Empty dict is valid
        validate_create_input({})

        # Invalid inputs
        with pytest.raises(ValidationError):
            validate_create_input("not a dict")  # type: ignore
        with pytest.raises(ValidationError):
            validate_create_input(None)  # type: ignore

    def test_validate_read_input(self) -> None:
        """Test validation of read input parameters."""
        # Test with valid times
        start, end = validate_read_input(
            {"start": "2023-01-01T00:00:00Z", "end": "2023-01-02T00:00:00Z"}, "test-id"
        )
        assert start == parser.parse("2023-01-01T00:00:00Z")
        assert end == parser.parse("2023-01-02T00:00:00Z")

        # Test with default times
        start, end = validate_read_input({}, "test-id")
        assert (datetime.now() - start).total_seconds() <= 3605  # About an hour
        assert (datetime.now() - end).total_seconds() <= 5  # Just now

        # Test with invalid times
        with pytest.raises(ValidationError):
            validate_read_input({"start": "invalid"}, "test-id")
        with pytest.raises(ValidationError):
            validate_read_input({"end": "invalid"}, "test-id")


class TestCloudWatchOperations:
    """Tests for CloudWatch Logs operations."""

    def setup_method(self, method: object) -> None:
        """Set up test environment."""
        self.log_group_name = "test-log-group"
        self.id_value = "test-id"

    def test_write_to_cloudwatch(self) -> None:
        """Test writing data to CloudWatch Logs."""
        test_data = {"message": "Test message", "value": 123}

        # Mock the CloudWatch Logs client
        mock_logs_client = MagicMock()

        # Set up the mock to return a sequence number for put_log_events
        mock_logs_client.put_log_events.return_value = {"nextSequenceToken": "next-token"}

        # Set up a timestamp for consistent testing
        timestamp = int(time.time() * 1000)

        # Test the write function
        with patch("src.lambda_function.lambda_handler.logs_client", mock_logs_client):
            with patch("src.lambda_function.lambda_handler.int") as mock_int:
                mock_int.return_value = timestamp
                write_to_cloudwatch(self.log_group_name, self.id_value, test_data)

        # Verify create_log_stream was called with correct arguments
        mock_logs_client.create_log_stream.assert_called_once()
        call_args = mock_logs_client.create_log_stream.call_args[1]
        assert call_args["logGroupName"] == self.log_group_name
        assert self.id_value in call_args["logStreamName"]

        # Verify that put_log_events was called with correct arguments
        mock_logs_client.put_log_events.assert_called_once()
        call_args = mock_logs_client.put_log_events.call_args[1]
        assert call_args["logGroupName"] == self.log_group_name
        assert self.id_value in call_args["logStreamName"]

        # Check the log event content
        log_events = call_args["logEvents"]
        assert len(log_events) == 1
        assert log_events[0]["timestamp"] == timestamp

        # Verify the message content
        event_data = json.loads(log_events[0]["message"])
        assert event_data["id"] == self.id_value
        assert event_data["message"] == test_data["message"]
        assert event_data["value"] == test_data["value"]

    def test_query_cloudwatch_logs(self) -> None:
        """Test querying CloudWatch Logs."""
        # Mock the CloudWatch Logs client
        mock_logs_client = MagicMock()

        # Set up the mock to return a query ID and then results
        mock_logs_client.start_query.return_value = {"queryId": "test-query-id"}

        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2023-01-01T12:00:00Z"},
                    {"field": "id", "value": self.id_value},
                    {"field": "message", "value": "Query test"},
                ]
            ],
        }

        # Test the query function
        with patch("src.lambda_function.lambda_handler.logs_client", mock_logs_client):
            start_time = datetime.now() - timedelta(hours=1)
            end_time = datetime.now()
            results = query_cloudwatch_logs(
                self.log_group_name, self.id_value, start_time, end_time
            )

        # Verify start_query was called with correct arguments
        mock_logs_client.start_query.assert_called_once()
        call_args = mock_logs_client.start_query.call_args[1]
        assert call_args["logGroupName"] == self.log_group_name
        assert "startTime" in call_args
        assert "endTime" in call_args
        assert "queryString" in call_args
        assert self.id_value in call_args["queryString"]

        # Verify get_query_results was called
        mock_logs_client.get_query_results.assert_called_once_with(queryId="test-query-id")

        # Verify results were correctly processed
        assert len(results) == 1
        assert results[0]["id"] == self.id_value
        assert results[0]["message"] == "Query test"
        assert "@timestamp" in results[0]


class TestEventHandlers:
    """Tests for event handling functions."""

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.write_to_cloudwatch")
    def test_handle_create_event_api_gateway(
        self, mock_write: MagicMock, mock_get_log_group: MagicMock
    ) -> None:
        """Test handling create event from API Gateway."""
        mock_get_log_group.return_value = "test-log-group"

        # Test with API Gateway event
        api_event = {"path": "/service/test-id", "body": json.dumps({"message": "Test message"})}

        response = handle_create_event(api_event)

        assert response["statusCode"] == 200
        assert "success" in json.loads(response["body"])
        assert json.loads(response["body"])["success"] is True
        assert json.loads(response["body"])["id"] == "test-id"

        mock_write.assert_called_once_with("test-log-group", "test-id", {"message": "Test message"})

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.write_to_cloudwatch")
    def test_handle_create_event_appsync(
        self, mock_write: MagicMock, mock_get_log_group: MagicMock
    ) -> None:
        """Test handling create event from AppSync."""
        mock_get_log_group.return_value = "test-log-group"

        # Test with AppSync event
        appsync_event = {
            "info": {"fieldName": "createServiceEvent", "parentTypeName": "Mutation"},
            "arguments": {"id": "test-id", "data": {"message": "Test AppSync message"}},
        }

        response = handle_create_event(appsync_event)

        assert response["statusCode"] == 200
        assert "success" in json.loads(response["body"])
        assert json.loads(response["body"])["success"] is True

        mock_write.assert_called_once_with(
            "test-log-group", "test-id", {"message": "Test AppSync message"}
        )

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.query_cloudwatch_logs")
    def test_handle_read_event_api_gateway(
        self, mock_query: MagicMock, mock_get_log_group: MagicMock
    ) -> None:
        """Test handling read event from API Gateway."""
        mock_get_log_group.return_value = "test-log-group"
        mock_query.return_value = [
            {"id": "test-id", "message": "Test record 1"},
            {"id": "test-id", "message": "Test record 2"},
        ]

        # Test with API Gateway event
        api_event = {
            "path": "/service/test-id",
            "queryStringParameters": {
                "start": "2023-01-01T00:00:00Z",
                "end": "2023-01-02T00:00:00Z",
            },
        }

        response = handle_read_event(api_event)

        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["id"] == "test-id"
        assert response_body["count"] == 2
        assert len(response_body["records"]) == 2
        assert response_body["startTime"] == "2023-01-01T00:00:00+00:00"
        assert response_body["endTime"] == "2023-01-02T00:00:00+00:00"

        mock_query.assert_called_once()

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.query_cloudwatch_logs")
    def test_handle_read_event_appsync(
        self, mock_query: MagicMock, mock_get_log_group: MagicMock
    ) -> None:
        """Test handling read event from AppSync."""
        mock_get_log_group.return_value = "test-log-group"
        mock_query.return_value = [{"id": "test-id", "message": "Test AppSync record"}]

        # Test with AppSync event
        appsync_event = {
            "info": {"fieldName": "getServiceEvents", "parentTypeName": "Query"},
            "arguments": {
                "id": "test-id",
                "start": "2023-01-01T00:00:00Z",
                "end": "2023-01-02T00:00:00Z",
            },
        }

        response = handle_read_event(appsync_event)

        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["id"] == "test-id"
        assert response_body["count"] == 1

        mock_query.assert_called_once()


class TestLambdaHandler:
    """Tests for the main Lambda handler function."""

    @patch("src.lambda_function.lambda_handler.handle_create_event")
    @patch("src.lambda_function.lambda_handler.handle_read_event")
    def test_lambda_handler_api_gateway(self, mock_read: MagicMock, mock_create: MagicMock) -> None:
        """Test lambda_handler with API Gateway events."""
        # Setup mock return values
        mock_create.return_value = {"statusCode": 200, "body": json.dumps({"success": True})}
        mock_read.return_value = {"statusCode": 200, "body": json.dumps({"records": []})}

        # Test POST request
        post_event = {"httpMethod": "POST", "path": "/service/test-id"}
        response = lambda_handler(post_event, {})
        assert response["statusCode"] == 200
        mock_create.assert_called_once_with(post_event)

        mock_create.reset_mock()
        mock_read.reset_mock()

        # Test GET request
        get_event = {"httpMethod": "GET", "path": "/service/test-id"}
        response = lambda_handler(get_event, {})
        assert response["statusCode"] == 200
        mock_read.assert_called_once_with(get_event)

        # Test unsupported methods
        delete_event = {"httpMethod": "DELETE", "path": "/service/test-id"}
        response = lambda_handler(delete_event, {})
        assert response["statusCode"] == 405

        patch_event = {"httpMethod": "PATCH", "path": "/service/test-id"}
        response = lambda_handler(patch_event, {})
        assert response["statusCode"] == 405

    @patch("src.lambda_function.lambda_handler.handle_create_event")
    @patch("src.lambda_function.lambda_handler.handle_read_event")
    def test_lambda_handler_appsync(self, mock_read: MagicMock, mock_create: MagicMock) -> None:
        """Test lambda_handler with AppSync events."""
        # Setup mock return values
        mock_create.return_value = {"statusCode": 200, "body": json.dumps({"success": True})}
        mock_read.return_value = {"statusCode": 200, "body": json.dumps({"records": []})}

        # Test mutation (POST)
        mutation_event = {"info": {"fieldName": "createServiceEvent", "parentTypeName": "Mutation"}}
        response = lambda_handler(mutation_event, {})
        assert response["statusCode"] == 200
        mock_create.assert_called_once_with(mutation_event)

        mock_create.reset_mock()
        mock_read.reset_mock()

        # Test query (GET)
        query_event = {"info": {"fieldName": "getServiceEvents", "parentTypeName": "Query"}}
        response = lambda_handler(query_event, {})
        assert response["statusCode"] == 200
        mock_read.assert_called_once_with(query_event)

    def test_lambda_handler_error_handling(self) -> None:
        """Test lambda_handler error handling."""
        # Test with ValidationError
        with patch("src.lambda_function.lambda_handler.handle_create_event") as mock_create:
            mock_create.side_effect = ValidationError("Test validation error", 400)

            event = {"httpMethod": "POST", "path": "/service/test-id"}
            response = lambda_handler(event, {})

            assert response["statusCode"] == 400
            assert "Test validation error" in response["body"]

        # Test with unexpected exception
        with patch("src.lambda_function.lambda_handler.handle_create_event") as mock_create:
            mock_create.side_effect = Exception("Unexpected error")

            event = {"httpMethod": "POST", "path": "/service/test-id"}
            response = lambda_handler(event, {})

            assert response["statusCode"] == 500
            assert "Internal server error" in response["body"]
