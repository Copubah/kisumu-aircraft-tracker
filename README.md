# Aircraft Landing Tracker for Kisumu International Airport

A real-time aircraft landing detection system using AWS services and the OpenSky Network API.

## Architecture Overview

The system consists of:
- AWS Lambda: Python function to fetch and process OpenSky API data
- EventBridge: Scheduled execution every 2 minutes
- DynamoDB: Storage for detected landings and aircraft state
- SNS: Notifications for landing events
- Terraform: Infrastructure as Code for deployment

## System Flow

1. EventBridge triggers Lambda function every 2 minutes
2. Lambda fetches aircraft data from OpenSky API for Kisumu airspace
3. System analyzes altitude and vertical rate to detect landings
4. Detected landings are stored in DynamoDB
5. SNS notifications are sent for new landings

## Landing Detection Logic

A landing is detected when:
- Aircraft altitude drops below 1000 feet AGL
- Vertical rate is negative (descending)
- Aircraft is within Kisumu airport vicinity (5km radius)
- Previous state shows aircraft was at higher altitude

## Project Structure

```
kisumu-aircraft-tracker/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── lambda.tf
├── lambda/
│   ├── landing_tracker.py
│   └── requirements.txt
├── scripts/
│   └── deploy.sh
└── README.md
```

## Quick Start

1. Configure AWS credentials
2. Update variables in `terraform/variables.tf`
3. Run deployment script: `./scripts/deploy.sh`

## Security Features

- IAM roles with least privilege access
- VPC endpoints for secure API communication
- Encrypted DynamoDB tables
- SNS topic access controls