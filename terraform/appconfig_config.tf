# AWS AppConfig Resources

# Creating AppConfig resources with IDs that conform to the required pattern [a-z0-9]{4,7}
resource "aws_appconfig_application" "service_history" {
  name        = "service-history" # Valid ID: 6 characters
  description = "Service History Application"
}

resource "aws_appconfig_environment" "service_history" {
  name           = "service-history" # Valid ID: 6 characters
  description    = "Service History Environment"
  application_id = aws_appconfig_application.service_history.id
}

resource "aws_appconfig_configuration_profile" "service_history" {
  name           = "service-history" # Valid ID: 6 characters
  description    = "Configuration for Service History Lambda"
  application_id = aws_appconfig_application.service_history.id
  location_uri   = "hosted"
}

# This resource creates the configuration content
resource "aws_appconfig_hosted_configuration_version" "service_history" {
  application_id           = aws_appconfig_application.service_history.id
  configuration_profile_id = aws_appconfig_configuration_profile.service_history.configuration_profile_id
  description              = "Service History Lambda Configuration"
  content_type             = "application/json"

  content = jsonencode({
    logGroup = "/aws/lambda/${var.function_name}"
  })

  depends_on = [
    aws_appconfig_configuration_profile.service_history
  ]
}

# Deploy the configuration to the environment
resource "aws_appconfig_deployment" "service_history" {
  application_id           = aws_appconfig_application.service_history.id
  environment_id           = aws_appconfig_environment.service_history.environment_id
  configuration_profile_id = aws_appconfig_configuration_profile.service_history.configuration_profile_id
  configuration_version    = aws_appconfig_hosted_configuration_version.service_history.version_number
  # Using predefined AWS AppConfig deployment strategy
  deployment_strategy_id = "AppConfig.AllAtOnce"
  description            = "Service History Lambda Configuration Deployment"
}
