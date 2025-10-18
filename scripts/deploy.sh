#!/bin/bash

set -e

echo "Deploying Kisumu Aircraft Landing Tracker..."

# Check if required tools are installed
command -v terraform >/dev/null 2>&1 || { echo "ERROR: Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "ERROR: AWS CLI is required but not installed. Aborting." >&2; exit 1; }

# Check AWS credentials
aws sts get-caller-identity >/dev/null 2>&1 || { echo "ERROR: AWS credentials not configured. Run 'aws configure' first." >&2; exit 1; }

# Navigate to project root
cd "$(dirname "$0")/.."

# Create Lambda deployment package
echo "Creating Lambda deployment package..."
cd lambda
pip install -r requirements.txt -t .
zip -r landing_tracker.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Initialize and apply Terraform
echo "Initializing Terraform..."
cd terraform
terraform init

echo "Planning Terraform deployment..."
terraform plan

echo "Applying Terraform configuration..."
terraform apply -auto-approve

echo "Deployment completed successfully!"
echo ""
echo "Deployment outputs:"
terraform output

echo ""
echo "Don't forget to confirm your SNS email subscription!"
echo "Monitor the Lambda function logs in CloudWatch for landing detections."