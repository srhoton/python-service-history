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
def mock_appconfig():
    with patch("src.lambda_function.lambda_handler.appconfig_client") as mock_client:
        mock_response = {
            "Content": MagicMock(
                read=MagicMock(return_value=json.dumps({"logGroup": "test-log-group"}).encode())
            )
        }
        mock_client.get_configuration.return_value = mock_response
        yield mock_client


@pytest.fixture
def set_environment_variables():
    os.environ["APPCONFIG_APP_ID"] = "TestApp"
    os.environ["APPCONFIG_ENV_ID"] = "TestEnv"
    os.environ["APPCONFIG_CONFIG_PROFILE_ID"] = "TestConfig"
    yield
    os.environ.pop("APPCONFIG_APP_ID", None)
    os.environ.pop("APPCONFIG_ENV_ID", None)
    os.environ.pop("APPCONFIG_CONFIG_PROFILE_ID", None)


class TestHelperFunctions:
    """Tests for helper functions in lambda_handler.py"""

    def test_extract_id_from_path(self):
        """Test extracting ID from path"""
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

    def test_get_log_group_name(self, mock_appconfig, set_environment_variables):
        """Test retrieval of log group name from AppConfig"""
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

    def test_validate_create_input(self):
        """Test validation of create input data"""
        # Valid inputs
        validate_create_input({"key": "value"})
        validate_create_input({"id": 123, "name": "test"})
        validate_create_input({"invalid": "not properly formatted"})
        validate_create_input({"empty": {}})

        # Invalid inputs
        with pytest.raises(ValidationError):
            validate_create_input({})
        with pytest.raises(ValidationError):
            validate_create_input(None)  # type: ignore

    def test_validate_read_input(self):
        """Test validation of read input parameters"""
        # Test with valid times
        start, end = validate_read_input(
            {"start": "2023-01-01T00:00:00Z", "end": "2023-01-02T00:00:00Z"},
            "test-id"
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

        # Test with start time after end time
        with pytest.raises(ValidationError):
            validate_read_input(
                {"start": "2023-01-02T00:00:00Z", "end": "2023-01-01T00:00:00Z"},
                "test-id"
            )

        # Test with missing ID
        with pytest.raises(ValidationError):
            validate_read_input({}, "")


class TestCloudWatchOperations:
    """Tests for CloudWatch Logs operations"""

    def setup_method(self, method):
        """Set up test environment"""
        self.log_group_name = "test-log-group"
        self.id_value = "test-id"

    def test_write_to_cloudwatch(self):
        """Test writing data to CloudWatch Logs"""
        test_data = {"message": "Test message", "value": 123}

        # Mock the CloudWatch Logs client
        mock_logs_client = MagicMock()

        # Mock describe_log_streams response
        mock_logs_client.describe_log_streams.return_value = {
            'logStreams': [
                {'logStreamName': f"{self.id_value}/123456789"}
            ]
        }

        # Mock get_log_events response
        timestamp = int(time.time() * 1000)
        expected_event_data = {
            "id": self.id_value,
            "timestamp": timestamp,
            "message": "Test message",
            "value": 123
        }
        mock_logs_client.get_log_events.return_value = {
            'events': [
                {'message': json.dumps(expected_event_data)}
            ]
        }

        # Patch time.time to return a consistent value
        with patch("time.time", return_value=timestamp/1000), \
             patch("src.lambda_function.lambda_handler.logs_client", mock_logs_client):

            write_to_cloudwatch(self.log_group_name, self.id_value, test_data)

        # Verify that create_log_group was called
        mock_logs_client.create_log_group.assert_called_once_with(
            logGroupName=self.log_group_name
        )

        # Verify that create_log_stream was called with correct arguments
        mock_logs_client.create_log_stream.assert_called_once()
        call_args = mock_logs_client.create_log_stream.call_args[1]
        assert call_args['logGroupName'] == self.log_group_name
        assert self.id_value in call_args['logStreamName']

        # Verify that put_log_events was called with correct arguments
        mock_logs_client.put_log_events.assert_called_once()
        call_args = mock_logs_client.put_log_events.call_args[1]
        assert call_args['logGroupName'] == self.log_group_name
        assert self.id_value in call_args['logStreamName']

        # Check the log event content
        log_events = call_args['logEvents']
        assert len(log_events) == 1
        assert log_events[0]['timestamp'] == timestamp

        # Verify the message content
        event_data = json.loads(log_events[0]['message'])
        assert event_data['id'] == self.id_value
        assert event_data['message'] == test_data['message']
        assert event_data['value'] == test_data['value']

    def test_query_cloudwatch_logs(self):
        """Test querying CloudWatch Logs"""
        # Mock the CloudWatch Logs client
        mock_logs_client = MagicMock()

        # Set up the mock responses
        timestamp = int(time.time() * 1000)
        mock_logs_client.start_query.return_value = {"queryId": "test-query-id"}
        mock_logs_client.get_query_results.return_value = {
            "status": "Complete",
            "results": [
                [
                    {"field": "@timestamp", "value": "2023-01-01 00:00:00.000"},
                    {"field": "@message", "value": json.dumps({
                        "id": self.id_value,
                        "message": "Query test",
                        "timestamp": timestamp
                    })}
                ]
            ]
        }

        # Test the query function
        with patch("src.lambda_function.lambda_handler.logs_client", mock_logs_client):
            start_time = datetime.now() - timedelta(hours=1)
            end_time = datetime.now()
            results = query_cloudwatch_logs(
                self.log_group_name,
                self.id_value,
                start_time,
                end_time
            )

        # Verify start_query was called with correct arguments
        mock_logs_client.start_query.assert_called_once()
        call_args = mock_logs_client.start_query.call_args[1]
        assert call_args['logGroupName'] == self.log_group_name
        assert 'startTime' in call_args
        assert 'endTime' in call_args
        assert 'queryString' in call_args
        assert self.id_value in call_args['queryString']

        # Verify get_query_results was called
        mock_logs_client.get_query_results.assert_called_once_with(
            queryId="test-query-id"
        )

        # Verify results were correctly processed
        assert len(results) == 1
        assert results[0]["id"] == self.id_value
        assert results[0]["message"] == "Query test"
        assert "@timestamp" in results[0]


class TestEventHandlers:
    """Tests for event handling functions"""

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.write_to_cloudwatch")
    def test_handle_create_event_api_gateway(self, mock_write, mock_get_log_group):
        """Test handling create event from API Gateway"""
        mock_get_log_group.return_value = "test-log-group"

        # Test with API Gateway event
        api_event = {
            "path": "/service/test-id",
            "body": json.dumps({"message": "Test message"})
        }

        response = handle_create_event(api_event)

        assert response["statusCode"] == 200
        assert "success" in json.loads(response["body"])
        assert json.loads(response["body"])["success"] is True
        assert json.loads(response["body"])["id"] == "test-id"

        mock_write.assert_called_once_with(
            "test-log-group",
            "test-id",
            {"message": "Test message"}
        )

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.write_to_cloudwatch")
    def test_handle_create_event_appsync(self, mock_write, mock_get_log_group):
        """Test handling create event from AppSync"""
        mock_get_log_group.return_value = "test-log-group"

        # Test with AppSync event
        appsync_event = {
            "info": {
                "fieldName": "createServiceRecord/test-id"
            },
            "arguments": {
                "message": "Test AppSync message"
            }
        }

        response = handle_create_event(appsync_event)

        assert response["statusCode"] == 200
        assert "success" in json.loads(response["body"])
        assert json.loads(response["body"])["success"] is True

        mock_write.assert_called_once_with(
            "test-log-group",
            "test-id",
            {"message": "Test AppSync message"}
        )

    @patch("src.lambda_function.lambda_handler.get_log_group_name")
    @patch("src.lambda_function.lambda_handler.query_cloudwatch_logs")
    def test_handle_read_event_api_gateway(self, mock_query, mock_get_log_group):
        """Test handling read event from API Gateway"""
        mock_get_log_group.return_value = "test-log-group"
        mock_query.return_value = [
            {"id": "test-id", "message": "Test record 1"},
            {"id": "test-id", "message": "Test record 2"}
        ]

        # Test with API Gateway event
        api_event = {
            "path": "/service/test-id",
            "queryStringParameters": {
                "start": "2023-01-01T00:00:00Z",
                "end": "2023-01-02T00:00:00Z"
            }
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
    def test_handle_read_event_appsync(self, mock_query, mock_get_log_group):
        """Test handling read event from AppSync"""
        mock_get_log_group.return_value = "test-log-group"
        mock_query.return_value = [{"id": "test-id", "message": "Test AppSync record"}]

        # Test with AppSync event
        appsync_event = {
            "info": {
                "fieldName": "getServiceRecords/test-id",
                "parentTypeName": "Query"
            },
            "arguments": {
                "start": "2023-01-01T00:00:00Z",
                "end": "2023-01-02T00:00:00Z"
            }
        }

        response = handle_read_event(appsync_event)

        assert response["statusCode"] == 200
        response_body = json.loads(response["body"])
        assert response_body["id"] == "test-id"
        assert response_body["count"] == 1

        mock_query.assert_called_once()


class TestLambdaHandler:
    """Tests for the main Lambda handler function"""

    @patch("src.lambda_function.lambda_handler.handle_create_event")
    @patch("src.lambda_function.lambda_handler.handle_read_event")
    def test_lambda_handler_api_gateway(self, mock_read, mock_create):
        """Test lambda_handler with API Gateway events"""
        # Setup mock return values
        mock_create.return_value = {"statusCode": 200, "body": json.dumps({"success": True})}
        mock_read.return_value = {"statusCode": 200, "body": json.dumps({"records": []})}

        # Test POST request
        post_event = {"httpMethod": "POST", "path": "/service/test-id"}
        response = lambda_handler(post_event, {})
        assert response["statusCode"] == 200
        mock_create.assert_called_once_with(post_event)

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
    def test_lambda_handler_appsync(self, mock_read, mock_create):
        """Test lambda_handler with AppSync events"""
        # Setup mock return values
        mock_create.return_value = {"statusCode": 200, "body": json.dumps({"success": True})}
        mock_read.return_value = {"statusCode": 200, "body": json.dumps({"records": []})}

        # Test mutation (create)
        mutation_event = {
            "info": {
                "fieldName": "createServiceRecord/test-id",
                "parentTypeName": "Mutation"
            }
        }
        response = lambda_handler(mutation_event, {})
        assert response["statusCode"] == 200
        mock_create.assert_called_once_with(mutation_event)

        # Test query (read)
        query_event = {
            "info": {
                "fieldName": "getServiceRecords/test-id",
                "parentTypeName": "Query"
            }
        }
        response = lambda_handler(query_event, {})
        assert response["statusCode"] == 200
        mock_read.assert_called_once_with(query_event)

    def test_lambda_handler_error_handling(self):
        """Test lambda_handler error handling"""
        # Test with ValidationError
        with patch("src.lambda_function.lambda_handler.handle_create_event") as mock_create:
            mock_create.side_effect = ValidationError("Test validation error", 400)

            event = {"httpMethod": "POST", "path": "/service/test-id"}
            response = lambda_handler(event, {})

            assert response["statusCode"] == 400
            assert "Test validation error" in response["body"]

        # Test with unexpected exception
        with patch("src.lambda_function.lambda_handler.handle_read_event") as mock_read:
            mock_read.side_effect = Exception("Unexpected error")

            event = {"httpMethod": "GET", "path": "/service/test-id"}
            response = lambda_handler(event, {})

            assert response["statusCode"] == 500
            assert "Internal server error" in response["body"]
