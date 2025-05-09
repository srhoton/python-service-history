# Service History Lambda Terraform Module

This Terraform module deploys the Service History Lambda function along with all required AWS resources and permissions.

## Overview

The Service History Lambda function handles logging and retrieving service events through API Gateway and AppSync, with data stored in CloudWatch Logs and configuration managed through AWS AppConfig.

## Prerequisites

Before using this module, you should have:

- Terraform v1.0+ installed
- AWS CLI configured with appropriate credentials
- AWS AppConfig resources (Application, Environment, Configuration Profile) already created
- Python 3.9+ for local development

## Resources Created

This module creates the following AWS resources:

- Lambda Function
- IAM Role and Policies for Lambda execution
- CloudWatch Log Group for Lambda logs
- Lambda deployment package from source code

## Usage

```hcl
module "service_history" {
  source = "./terraform"

  function_name               = "my-service-history"
  aws_region                  = "us-west-2"
  appconfig_app_id            = "MyServiceApp"
  appconfig_env_id            = "Production"
  appconfig_config_profile_id = "ServiceHistoryConfig"
  
  lambda_memory_size          = 256
  lambda_timeout              = 60
  
  tags = {
    Environment = "production"
    Project     = "ServiceHistory"
    Owner       = "PlatformTeam"
  }
}
```

## Variables

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| aws_region | AWS region where resources will be deployed | string | "us-east-1" | no |
| function_name | Name of the Lambda function | string | "service-history-lambda" | no |
| lambda_description | Description for the Lambda function | string | "Service History Lambda for logging and retrieving service events" | no |
| lambda_handler | Handler for the Lambda function | string | "lambda_function.lambda_handler" | no |
| lambda_runtime | Runtime for the Lambda function | string | "python3.9" | no |
| lambda_memory_size | Memory size for the Lambda function in MB | number | 128 | no |
| lambda_timeout | Timeout for the Lambda function in seconds | number | 30 | no |
| source_dir | Directory containing Lambda function source code | string | "../src" | no |
| appconfig_app_id | AppConfig Application ID | string | "ServiceHistoryApp" | no |
| appconfig_env_id | AppConfig Environment ID | string | "Production" | no |
| appconfig_config_profile_id | AppConfig Configuration Profile ID | string | "ServiceHistoryConfig" | no |
| log_retention_in_days | Number of days to retain Lambda logs in CloudWatch | number | 14 | no |
| tags | Tags to apply to resources | map(string) | see variables.tf | no |

## Outputs

| Name | Description |
|------|-------------|
| lambda_function_name | Name of the deployed Lambda function |
| lambda_function_arn | ARN of the deployed Lambda function |
| lambda_function_version | Latest published version of the Lambda function |
| lambda_function_last_modified | Date Lambda function was last modified |
| lambda_iam_role_name | Name of the IAM role used by the Lambda function |
| lambda_iam_role_arn | ARN of the IAM role used by the Lambda function |
| cloudwatch_log_group_name | Name of the CloudWatch Log Group for Lambda function logs |
| cloudwatch_log_group_arn | ARN of the CloudWatch Log Group for Lambda function logs |

## Deployment

To deploy this module:

1. Initialize the Terraform directory:
   ```
   cd terraform
   terraform init
   ```

2. Preview the changes:
   ```
   terraform plan
   ```

3. Apply the changes:
   ```
   terraform apply
   ```

4. To destroy the resources:
   ```
   terraform destroy
   ```

## Note on AppConfig

This Lambda function expects AWS AppConfig to be already set up with the specified application, environment, and configuration profile. The configuration should include a `logGroup` parameter that specifies the CloudWatch Logs group for storing service history data.

## Extensions

To integrate with API Gateway or AppSync, uncomment and configure the Lambda permission resource in `main.tf` and add additional resources as needed.