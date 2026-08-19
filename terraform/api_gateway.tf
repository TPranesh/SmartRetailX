# terraform/api_gateway.tf
# Amazon API Gateway HTTP API Ingress & Central $default Proxy to ALB

resource "aws_apigatewayv2_api" "http_api" {
  name          = "smartretailx-api-gateway"
  protocol_type = "HTTP"
  description   = "Central API Gateway entry point for SmartRetailX microservices"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["*"]
    allow_headers = ["*"]
    max_age       = 300
  }

  tags = {
    Name        = "smartretailx-api-gateway"
    Environment = var.environment
  }
}

# Auto-deploy Stage ($default)
resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      httpMethod              = "$context.httpMethod"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      protocol                = "$context.protocol"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }

  tags = {
    Environment = var.environment
  }
}

# ── Central ALB Proxy Integration ─────────────────────────────────────────────
resource "aws_apigatewayv2_integration" "alb_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_lb.main.dns_name}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

# ── Catch-All ($default) Passthrough Route ────────────────────────────────────
resource "aws_apigatewayv2_route" "default_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.alb_integration.id}"
}
