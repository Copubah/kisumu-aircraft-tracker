# Lambda function
resource "aws_lambda_function" "landing_tracker" {
  filename         = "../lambda/landing_tracker.zip"
  function_name    = "${var.project_name}-landing-tracker"
  role            = aws_iam_role.lambda_role.arn
  handler         = "landing_tracker.lambda_handler"
  runtime         = "python3.11"
  timeout         = 60
  memory_size     = 256

  environment {
    variables = {
      AIRCRAFT_STATE_TABLE = aws_dynamodb_table.aircraft_state.name
      LANDINGS_TABLE       = aws_dynamodb_table.landings.name
      SNS_TOPIC_ARN       = aws_sns_topic.landing_notifications.arn
      AIRPORT_LAT         = var.airport_lat
      AIRPORT_LON         = var.airport_lon
      DETECTION_RADIUS_KM = var.detection_radius_km
      LANDING_ALTITUDE_THRESHOLD = var.landing_altitude_threshold
      OPENSKY_USERNAME    = var.opensky_username
      OPENSKY_PASSWORD    = var.opensky_password
    }
  }

  depends_on = [
    aws_iam_role_policy.lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
  ]

  tags = {
    Name        = "${var.project_name}-landing-tracker"
    Environment = var.environment
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-landing-tracker"
  retention_in_days = 14

  tags = {
    Name        = "${var.project_name}-lambda-logs"
    Environment = var.environment
  }
}

# Data source for Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "../lambda"
  output_path = "../lambda/landing_tracker.zip"
  excludes    = ["landing_tracker.zip"]
}