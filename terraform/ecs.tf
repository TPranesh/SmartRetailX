# terraform/ecs.tf
# Amazon ECS Fargate Task Definitions & Services for SmartRetailX Microservices

# ── 1. User Service ──────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "user_service" {
  family                   = "smartretailx-user-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "user-service"
      image     = "538471156806.dkr.ecr.${var.aws_region}.amazonaws.com/smartretailx-user-service:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8001
          hostPort      = 8001
        }
      ]
      environment = [
        { name = "PYTHONPATH", value = "/app" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_user_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "user-service"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "UserService"
  }
}

resource "aws_ecs_service" "user_service" {
  name            = "smartretailx-user-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.user_service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
}

# ── 2. Product Service ───────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "product_service" {
  family                   = "smartretailx-product-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "product-service"
      image     = "538471156806.dkr.ecr.${var.aws_region}.amazonaws.com/smartretailx-product-service:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8002
          hostPort      = 8002
        }
      ]
      environment = [
        { name = "PYTHONPATH", value = "/app" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_product_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "product-service"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "ProductService"
  }
}

resource "aws_ecs_service" "product_service" {
  name            = "smartretailx-product-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.product_service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
}

# ── 3. Order Service ─────────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "order_service" {
  family                   = "smartretailx-order-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "order-service"
      image     = "538471156806.dkr.ecr.${var.aws_region}.amazonaws.com/smartretailx-order-service:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8003
          hostPort      = 8003
        }
      ]
      environment = [
        { name = "PYTHONPATH", value = "/app" },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.order_events.url },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_order_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "order-service"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "OrderService"
  }
}

resource "aws_ecs_service" "order_service" {
  name            = "smartretailx-order-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.order_service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
}

# ── 4. Inventory Service ─────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "inventory_service" {
  family                   = "smartretailx-inventory-service"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "inventory-service"
      image     = "538471156806.dkr.ecr.${var.aws_region}.amazonaws.com/smartretailx-inventory-service:latest"
      essential = true
      portMappings = [
        {
          containerPort = 8004
          hostPort      = 8004
        }
      ]
      environment = [
        { name = "PYTHONPATH", value = "/app" },
        { name = "SQS_QUEUE_URL", value = aws_sqs_queue.order_events.url },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${var.db_name}" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_inventory_logs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "inventory-service"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
    Service     = "InventoryService"
  }
}

resource "aws_ecs_service" "inventory_service" {
  name            = "smartretailx-inventory-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.inventory_service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.public_1.id, aws_subnet.public_2.id]
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = true
  }
}
