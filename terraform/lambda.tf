# terraform/lambda.tf
# Serverless Notification Service (AWS Lambda + SQS Event Mapping)

# Zip archive for notification service Lambda code
data "archive_file" "notification_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../notification_service"
  output_path = "${path.module}/notification_service.zip"
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_execution_role" {
  name = "smartretailx-lambda-execution-role"

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

  tags = {
    Environment = var.environment
  }
}

# Attach AWS managed policy for CloudWatch Logs
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach AWS managed policy for SQS Queue Execution
resource "aws_iam_role_policy_attachment" "lambda_sqs_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

# AWS Lambda Function
resource "aws_lambda_function" "notification_service" {
  function_name    = "smartretailx-notifications"
  runtime          = "python3.10"
  handler          = "lambda_function.lambda_handler"
  role             = aws_iam_role.lambda_execution_role.arn
  filename         = data.archive_file.notification_lambda_zip.output_path
  source_code_hash = data.archive_file.notification_lambda_zip.output_base64sha256

  timeout     = 30
  memory_size = 128

  environment {
    variables = {
      ENVIRONMENT = var.environment
      LOG_LEVEL   = "INFO"
    }
  }

  tags = {
    Name        = "smartretailx-notifications"
    Environment = var.environment
    Service     = "NotificationService"
  }
}

# SQS Event Source Mapping to trigger Lambda from Order Events Queue
resource "aws_lambda_event_source_mapping" "sqs_notification_trigger" {
  event_source_arn = aws_sqs_queue.order_events.arn
  function_name    = aws_lambda_function.notification_service.arn
  batch_size       = 10
  enabled          = true
}
