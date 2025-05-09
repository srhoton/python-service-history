output "lambda_function_name" {
  description = "Name of the deployed Lambda function"
  value       = aws_lambda_function.service_history.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function"
  value       = aws_lambda_function.service_history.arn
}

output "lambda_function_version" {
  description = "Latest published version of the Lambda function"
  value       = aws_lambda_function.service_history.version
}

output "lambda_function_last_modified" {
  description = "Date Lambda function was last modified"
  value       = aws_lambda_function.service_history.last_modified
}

output "lambda_iam_role_name" {
  description = "Name of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_execution_role.name
}

output "lambda_iam_role_arn" {
  description = "ARN of the IAM role used by the Lambda function"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch Log Group for Lambda function logs"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch Log Group for Lambda function logs"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}