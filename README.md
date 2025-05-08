# Service History Lambda

A serverless AWS Lambda function for logging and retrieving service history events through API Gateway and AppSync.

## Overview

This project provides a Lambda function that handles service event logging and retrieval with the following capabilities:

- Logs service events to CloudWatch Logs with searchable fields
- Retrieves historical service data within specified time ranges
- Supports both REST API (API Gateway) and GraphQL (AppSync) interfaces
- Blocks update and delete operations for data integrity

## Configuration

The Lambda function retrieves its configuration from AWS AppConfig:

- **Log Group Name**: Stored under the key `logGroup` in AppConfig

### Environment Variables

Set the following environment variables for the Lambda function:

```
APPCONFIG_APP_ID=ServiceHistoryApp
APPCONFIG_ENV_ID=Production  
APPCONFIG_CONFIG_PROFILE_ID=ServiceHistoryConfig
```

## API Usage

### Create Event

Logs a new service event to CloudWatch Logs.

**Endpoint**: `POST /service/{id}`

**Path Parameters**:
- `id` - Unique identifier for the service event

**Request Body**: JSON object with arbitrary name-value pairs that will be logged

**Example Request**:
```json
POST /service/customer-123
{
  "operation": "login",
  "source": "web",
  "duration_ms": 150,
  "success": true
}
```

**Example Response**:
```json
{
  "message": "Data successfully recorded",
  "id": "customer-123",
  "success": true
}
```

### Read Events

Retrieves service events for a specific ID within a time range.

**Endpoint**: `GET /service/{id}?start=&end=`

**Path Parameters**:
- `id` - Unique identifier to retrieve events for

**Query Parameters**:
- `start` - Start time in ISO 8601 format (optional, defaults to 1 hour ago)
- `end` - End time in ISO 8601 format (optional, defaults to current time)

**Example Request**:
```
GET /service/customer-123?start=2023-01-01T00:00:00Z&end=2023-01-02T00:00:00Z
```

**Example Response**:
```json
{
  "id": "customer-123",
  "startTime": "2023-01-01T00:00:00",
  "endTime": "2023-01-02T00:00:00",
  "count": 2,
  "records": [
    {
      "id": "customer-123",
      "operation": "login",
      "source": "web",
      "duration_ms": 150,
      "success": true,
      "timestamp": 1672531200000,
      "@timestamp": "2023-01-01 12:00:00.000"
    },
    {
      "id": "customer-123",
      "operation": "checkout",
      "source": "mobile",
      "duration_ms": 320,
      "success": true,
      "timestamp": 1672574400000,
      "@timestamp": "2023-01-02 00:00:00.000"
    }
  ]
}
```

### AppSync (GraphQL) Integration

The Lambda function can be used as a resolver for AppSync operations:

- **Query**: Maps to the Read operation
- **Mutation**: Maps to the Create operation

## Project Structure

```
python-service-history/
├── src/
│   ├── lambda_function/
│   │   ├── __init__.py
│   │   └── lambda_handler.py  # Main Lambda function
│   └── __init__.py
├── tests/
│   └── test_lambda_handler.py  # Unit tests
├── .gitignore
├── pyproject.toml  # Project configuration and dependencies
└── README.md
```

## Development

### Requirements

- Python 3.9 or later
- AWS account with access to Lambda, AppConfig, and CloudWatch Logs

### Local Development

1. Clone the repository
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Unix/macOS: `source .venv/bin/activate`
4. Install dependencies: `pip install -e ".[dev]"`
5. Run tests: `pytest`

### AWS Deployment

1. Create an AWS Lambda function with Python 3.9+ runtime
2. Ensure the Lambda has permissions to access:
   - AppConfig
   - CloudWatch Logs
3. Set up API Gateway or AppSync to trigger the Lambda function
4. Configure AppConfig with the required `logGroup` parameter

## License

Copyright © 2024