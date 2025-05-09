provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

#--------------------------------------------------
# Lambda Function
#--------------------------------------------------

data "archive_file" "lambda_package" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "service_history" {
  function_name    = var.function_name
  description      = var.lambda_description
  filename         = data.archive_file.lambda_package.output_path
  source_code_hash = data.archive_file.lambda_package.output_base64sha256
  handler          = var.lambda_handler
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory_size
  timeout          = var.lambda_timeout
  role             = aws_iam_role.lambda_execution_role.arn

  environment {
    variables = {
      APPCONFIG_APP_ID            = var.appconfig_app_id
      APPCONFIG_ENV_ID            = var.appconfig_env_id
      APPCONFIG_CONFIG_PROFILE_ID = var.appconfig_config_profile_id
      LOG_GROUP_CONFIG_KEY        = "logGroup"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy_attachment.lambda_appconfig
  ]
}

#--------------------------------------------------
# CloudWatch Log Group
#--------------------------------------------------

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_in_days
}

#--------------------------------------------------
# Lambda Permissions (if needed for API Gateway/AppSync)
#--------------------------------------------------

# Uncomment and configure as needed:
/*
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.service_history.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.service_history_api.execution_arn}"
}
*/
