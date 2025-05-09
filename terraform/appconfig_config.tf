resource "aws_appconfig_configuration" "service_history" {
  application_id = var.appconfig_app_id
  environment_id = var.appconfig_env_id
  configuration_profile_id = var.appconfig_config_profile_id
  name = "service-history-config"
  description = "Configuration for Service History Lambda"
  content_type = "JSON"
  content = jsonencode({
    logGroup = "/aws/lambda/${var.function_name}"
  })
}
