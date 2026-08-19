# terraform/main.tf
# SmartRetailX - Core AWS Infrastructure (ECS Fargate + SQS)

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Amazon SQS Event Bus ─────────────────────────────────────────────────────
# OrderPlaced & OrderCancelled events bus between Order, Inventory & Notification services
resource "aws_sqs_queue" "order_events_dlq" {
  name                      = "SmartRetailX-OrderEvents-DLQ"
  message_retention_seconds = 1209600 # 14 days
}

resource "aws_sqs_queue" "order_events" {
  name                       = "SmartRetailX-OrderEvents"
  delay_seconds              = 0
  max_message_size           = 262144
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Enable SQS Long Polling
  visibility_timeout_seconds = 30

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_events_dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Environment = var.environment
    Service     = "SmartRetailX"
  }
}

# ── Amazon ECS Cluster ────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "smartretailx-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Environment = var.environment
    Service     = "SmartRetailX"
  }
}

# ── IAM Execution Role for ECS Fargate ────────────────────────────────────────
resource "aws_iam_role" "ecs_execution_role" {
  name = "smartretailx-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Task Role for SQS permissions
resource "aws_iam_role" "ecs_task_role" {
  name = "smartretailx-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "sqs_access" {
  name        = "smartretailx-sqs-access"
  description = "Allows ECS tasks to interact with SQS queues"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          aws_sqs_queue.order_events.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_sqs_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.sqs_access.arn
}


