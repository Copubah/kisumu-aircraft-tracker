output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.landing_tracker.function_name
}

output "aircraft_state_table_name" {
  description = "Name of the aircraft state DynamoDB table"
  value       = aws_dynamodb_table.aircraft_state.name
}

output "landings_table_name" {
  description = "Name of the landings DynamoDB table"
  value       = aws_dynamodb_table.landings.name
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  value       = aws_sns_topic.landing_notifications.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.schedule.name
}