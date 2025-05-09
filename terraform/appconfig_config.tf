resource "aws_appconfig_configuration_profile" "service_history" {
  application_id = var.appconfig_app_id
  name = "service-history-config"
  description = "Configuration for Service History Lambda"
  content = jsonencode({
    logGroup = "/aws/lambda/${var.function_name}"
  })
  content_type = "JSON"
}
