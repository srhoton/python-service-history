provider "aws" {
  region = var.aws_region

  default_tags {
    tags = var.tags
  }
}

resource "aws_lambda_function" "service_history" {
  function_name    = var.function_name
  description      = var.lambda_description
  filename         = "lambda_function.zip"
  source_code_hash = filebase64sha256("lambda_function.zip")
  handler          = var.lambda_handler
  runtime          = var.lambda_runtime
  memory_size      = var.lambda_memory
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

resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = var.log_retention_in_days
}
