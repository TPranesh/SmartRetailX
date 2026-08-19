# terraform/outputs.tf

output "rds_endpoint" {
  value       = aws_db_instance.postgres.endpoint
  description = "Connection endpoint for the RDS PostgreSQL database"
}

output "rds_database_name" {
  value       = aws_db_instance.postgres.db_name
  description = "Name of the RDS database"
}

output "s3_frontend_bucket_name" {
  value       = aws_s3_bucket.frontend_bucket.id
  description = "Name of the S3 bucket hosting frontend static assets"
}

output "cloudfront_domain_name" {
  value       = aws_cloudfront_distribution.frontend_cdn.domain_name
  description = "Domain name of the CloudFront CDN distribution"
}

output "api_gateway_endpoint" {
  value       = aws_apigatewayv2_stage.default.invoke_url
  description = "Base URL endpoint of the API Gateway HTTP API"
}

output "lambda_notification_arn" {
  value       = aws_lambda_function.notification_service.arn
  description = "ARN of the Notification Service Lambda function"
}

output "sqs_queue_url" {
  value       = aws_sqs_queue.order_events.url
  description = "URL of the SQS Order Events Queue"
}

output "ecs_cluster_name" {
  value       = aws_ecs_cluster.main.name
  description = "Name of the ECS Cluster"
}

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "DNS domain name of the Application Load Balancer"
}
