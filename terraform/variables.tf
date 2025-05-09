variable "aws_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "service-history-lambda"
}

variable "lambda_description" {
  description = "Description for the Lambda function"
  type        = string
  default     = "Service History Lambda for logging and retrieving service events"
}

variable "lambda_handler" {
  description = "Handler for the Lambda function"
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "lambda_runtime" {
  description = "Runtime for the Lambda function"
  type        = string
  default     = "python3.9"
}

variable "lambda_memory_size" {
  description = "Memory size for the Lambda function in MB"
  type        = number
  default     = 128

  validation {
    condition     = var.lambda_memory_size >= 128 && var.lambda_memory_size <= 10240
    error_message = "Lambda memory size must be between 128 MB and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for the Lambda function in seconds"
  type        = number
  default     = 30

  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "source_dir" {
  description = "Directory containing Lambda function source code"
  type        = string
  default     = "../src"
}

variable "appconfig_app_id" {
  description = "AppConfig Application ID"
  type        = string
  default     = "ServiceHistoryApp"
}

variable "appconfig_env_id" {
  description = "AppConfig Environment ID"
  type        = string
  default     = "Production"
}

variable "appconfig_config_profile_id" {
  description = "AppConfig Configuration Profile ID"
  type        = string
  default     = "ServiceHistoryConfig"
}

variable "log_retention_in_days" {
  description = "Number of days to retain Lambda logs in CloudWatch"
  type        = number
  default     = 14

  validation {
    condition     = contains([0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_in_days)
    error_message = "Log retention period must be one of the allowed values: 0, 1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653."
  }
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Environment = "dev"
    ManagedBy   = "terraform"
    Project     = "ServiceHistory"
  }
}
