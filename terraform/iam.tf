#--------------------------------------------------
# Lambda IAM Role and Policies
#--------------------------------------------------

data "aws_caller_identity" "current" {}

resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.function_name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

#--------------------------------------------------
# CloudWatch Logs Policy
#--------------------------------------------------

resource "aws_iam_policy" "lambda_cloudwatch_policy" {
  name        = "${var.function_name}-cloudwatch-policy"
  description = "IAM policy for Lambda to write and query CloudWatch Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.function_name}:*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:StartQuery",
          "logs:GetQueryResults",
          "logs:DescribeLogGroups"
        ]
        Effect   = "Allow"
        Resource = "*" # The specific log group name is retrieved from AppConfig
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_policy.arn
}

#--------------------------------------------------
# AWS AppConfig Policy
#--------------------------------------------------

resource "aws_iam_policy" "lambda_appconfig_policy" {
  name        = "${var.function_name}-appconfig-policy"
  description = "IAM policy for Lambda to access AppConfig"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "appconfig:GetConfiguration",
          "appconfig:StartConfigurationSession"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:appconfig:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${aws_appconfig_application.service_history.id}",
          "arn:aws:appconfig:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${aws_appconfig_application.service_history.id}/environment/${aws_appconfig_environment.service_history.environment_id}",
          "arn:aws:appconfig:${var.aws_region}:${data.aws_caller_identity.current.account_id}:application/${aws_appconfig_application.service_history.id}/configurationprofile/${aws_appconfig_configuration_profile.service_history.configuration_profile_id}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_appconfig" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_appconfig_policy.arn
}
