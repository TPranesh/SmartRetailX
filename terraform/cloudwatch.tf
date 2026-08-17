# terraform/cloudwatch.tf
# Amazon CloudWatch Centralized Logging & Observability Alarms

# Centralized CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs_user_logs" {
  name              = "/ecs/smartretailx-user"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "ecs_product_logs" {
  name              = "/ecs/smartretailx-product"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "ecs_order_logs" {
  name              = "/ecs/smartretailx-order"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "ecs_inventory_logs" {
  name              = "/ecs/smartretailx-inventory"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "lambda_notification_logs" {
  name              = "/aws/lambda/smartretailx-notifications"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/smartretailx-api"
  retention_in_days = 30
}

# ── CloudWatch Metric Alarms ──────────────────────────────────────────────────

# Alarm 1: ECS Cluster CPU Utilization > 80%
resource "aws_cloudwatch_metric_alarm" "ecs_cpu_high" {
  alarm_name          = "smartretailx-ecs-cpu-high-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggers when ECS container CPU utilization exceeds 80% over 2 consecutive 5-minute periods."

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
  }

  tags = {
    Environment = var.environment
    Service     = "Monitoring"
  }
}

# Alarm 2: API Gateway 5XX Error Rate Spike
resource "aws_cloudwatch_metric_alarm" "api_5xx_high" {
  alarm_name          = "smartretailx-api-5xx-spike-alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Triggers when API Gateway records more than 10 5XX server errors in 1 minute."

  dimensions = {
    ApiId = aws_apigatewayv2_api.http_api.id
  }

  tags = {
    Environment = var.environment
    Service     = "Monitoring"
  }
}
