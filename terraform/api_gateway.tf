# terraform/api_gateway.tf
# Amazon API Gateway HTTP API Ingress & Routing to Application Load Balancer (ALB)

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

# ── Integrations (HTTP Proxy to Application Load Balancer DNS) ───────────────
resource "aws_apigatewayv2_integration" "user_service" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_lb.main.dns_name}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "product_service" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_lb.main.dns_name}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "order_service" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_lb.main.dns_name}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "inventory_service" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "HTTP_PROXY"
  integration_uri        = "http://${aws_lb.main.dns_name}"
  integration_method     = "ANY"
  payload_format_version = "1.0"
}

# ── Routes ───────────────────────────────────────────────────────────────────
# /users routes
resource "aws_apigatewayv2_route" "users_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /users/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.user_service.id}"
}

resource "aws_apigatewayv2_route" "users_root_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /users"
  target    = "integrations/${aws_apigatewayv2_integration.user_service.id}"
}

# /products routes
resource "aws_apigatewayv2_route" "products_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /products/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.product_service.id}"
}

resource "aws_apigatewayv2_route" "products_root_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /products"
  target    = "integrations/${aws_apigatewayv2_integration.product_service.id}"
}

# /orders routes
resource "aws_apigatewayv2_route" "orders_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /orders/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.order_service.id}"
}

resource "aws_apigatewayv2_route" "orders_root_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /orders"
  target    = "integrations/${aws_apigatewayv2_integration.order_service.id}"
}

# /inventory routes
resource "aws_apigatewayv2_route" "inventory_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /inventory/{proxy+}"
  target    = "integrations/${aws_apigatewayv2_integration.inventory_service.id}"
}

resource "aws_apigatewayv2_route" "inventory_root_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "ANY /inventory"
  target    = "integrations/${aws_apigatewayv2_integration.inventory_service.id}"
}
