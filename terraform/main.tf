terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# DynamoDB table for aircraft state tracking
resource "aws_dynamodb_table" "aircraft_state" {
  name           = "${var.project_name}-aircraft-state"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "icao24"
  
  attribute {
    name = "icao24"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-aircraft-state"
    Environment = var.environment
  }
}

# DynamoDB table for landing records
resource "aws_dynamodb_table" "landings" {
  name           = "${var.project_name}-landings"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "landing_id"
  range_key      = "timestamp"

  attribute {
    name = "landing_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  attribute {
    name = "icao24"
    type = "S"
  }

  global_secondary_index {
    name            = "icao24-timestamp-index"
    hash_key        = "icao24"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-landings"
    Environment = var.environment
  }
}

# SNS topic for notifications
resource "aws_sns_topic" "landing_notifications" {
  name = "${var.project_name}-landing-notifications"

  tags = {
    Name        = "${var.project_name}-landing-notifications"
    Environment = var.environment
  }
}

# SNS topic subscription
resource "aws_sns_topic_subscription" "email_notification" {
  topic_arn = aws_sns_topic.landing_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# IAM role for Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

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

# IAM policy for Lambda function
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.aircraft_state.arn,
          aws_dynamodb_table.landings.arn,
          "${aws_dynamodb_table.landings.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.landing_notifications.arn
      }
    ]
  })
}

# EventBridge rule for scheduled execution
resource "aws_cloudwatch_event_rule" "schedule" {
  name                = "${var.project_name}-schedule"
  description         = "Trigger landing tracker every 2 minutes"
  schedule_expression = "rate(2 minutes)"
}

# EventBridge target
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.schedule.name
  target_id = "LandingTrackerTarget"
  arn       = aws_lambda_function.landing_tracker.arn
}

# Lambda permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.landing_tracker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.schedule.arn
}