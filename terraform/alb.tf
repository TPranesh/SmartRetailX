# terraform/alb.tf
# Application Load Balancer (ALB) and Target Groups for SmartRetailX ECS Microservices

# ── Security Group for ALB ───────────────────────────────────────────────────
resource "aws_security_group" "alb_sg" {
  name        = "smartretailx-alb-sg"
  description = "Allows inbound HTTP traffic to ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP Ingress from everywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "smartretailx-alb-sg"
    Environment = var.environment
  }
}

# ── Application Load Balancer ─────────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "smartretailx-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  enable_deletion_protection = false

  tags = {
    Name        = "smartretailx-alb"
    Environment = var.environment
  }
}

# ── Target Groups (IP Mode for Fargate) ───────────────────────────────────────
resource "aws_lb_target_group" "user_service" {
  name        = "smartretailx-user-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/users/health"
    port                = "8001"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Environment = var.environment
    Service     = "UserService"
  }
}

resource "aws_lb_target_group" "product_service" {
  name        = "smartretailx-product-tg"
  port        = 8002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/products/health"
    port                = "8002"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Environment = var.environment
    Service     = "ProductService"
  }
}

resource "aws_lb_target_group" "order_service" {
  name        = "smartretailx-order-tg"
  port        = 8003
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/orders/health"
    port                = "8003"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Environment = var.environment
    Service     = "OrderService"
  }
}

resource "aws_lb_target_group" "inventory_service" {
  name        = "smartretailx-inventory-tg"
  port        = 8004
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/inventory/health"
    port                = "8004"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = {
    Environment = var.environment
    Service     = "InventoryService"
  }
}

# ── ALB Listener on Port 80 ───────────────────────────────────────────────────
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "SmartRetailX Microservices Gateway — Central ALB Active"
      status_code  = "200"
    }
  }
}

# ── ALB Listener Rules for Microservice Path Routing ──────────────────────────
resource "aws_lb_listener_rule" "users_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.user_service.arn
  }

  condition {
    path_pattern {
      values = ["/users*"]
    }
  }
}

resource "aws_lb_listener_rule" "products_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.product_service.arn
  }

  condition {
    path_pattern {
      values = ["/products*"]
    }
  }
}

resource "aws_lb_listener_rule" "orders_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 30

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.order_service.arn
  }

  condition {
    path_pattern {
      values = ["/orders*"]
    }
  }
}

resource "aws_lb_listener_rule" "inventory_rule" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 40

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.inventory_service.arn
  }

  condition {
    path_pattern {
      values = ["/inventory*"]
    }
  }
}
