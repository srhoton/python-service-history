#!/bin/bash

# Set the source directory (default is "../src")
SOURCE_DIR="../src"

# Build the Lambda ZIP file
echo "Zipping Lambda source code..."
zip -r9 lambda_function.zip "$SOURCE_DIR"

# Check if zip was successful
if [ $? -ne 0 ]; then
  echo "Failed to zip Lambda source code. Aborting deployment."
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
