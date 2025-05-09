#!/bin/bash

# This script deploys the Lambda function using Terraform
# Note: The lambda_function.zip file is now created by Terraform's archive_file data source in main.tf

# Initialize Terraform (only needed first time or when changing backends/providers)
echo "Initializing Terraform..."
terraform init

# Format Terraform files for consistency
echo "Formatting Terraform files..."
terraform fmt

# Validate Terraform configuration
echo "Validating Terraform configuration..."
terraform validate

if [ $? -ne 0 ]; then
  echo "Terraform validation failed. Aborting deployment."
  exit 1
fi

# Run Terraform to deploy the Lambda function
echo "Deploying Lambda function with Terraform..."
terraform apply -auto-approve

# Check if Terraform deployment was successful
if [ $? -ne 0 ]; then
  echo "Terraform deployment failed. Aborting."
  exit 1
fi

echo "Lambda function deployed successfully!"
