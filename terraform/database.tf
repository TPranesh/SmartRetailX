# terraform/database.tf
# Amazon RDS PostgreSQL Database Provisioning

# Subnet Group for RDS
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "smartretailx-db-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name        = "SmartRetailX DB Subnet Group"
    Environment = var.environment
  }
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_sg" {
  name        = "smartretailx-ecs-sg"
  description = "Security Group for ECS microservices"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP traffic from Application Load Balancer"
    from_port       = 8000
    to_port         = 8005
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    description = "HTTP traffic from internal VPC"
    from_port   = 8000
    to_port     = 8005
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16", "0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "smartretailx-ecs-sg"
    Environment = var.environment
  }
}

# Security Group for RDS Instance
resource "aws_security_group" "rds_sg" {
  name        = "smartretailx-rds-sg"
  description = "Allows inbound PostgreSQL traffic from ECS tasks and VPC subnets"
  vpc_id      = aws_vpc.main.id

  # Allow PostgreSQL traffic from ECS security group
  ingress {
    description     = "PostgreSQL from ECS Cluster"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  # Allow PostgreSQL traffic from internal VPC CIDR
  ingress {
    description = "PostgreSQL from VPC subnets"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "smartretailx-rds-sg"
    Environment = var.environment
  }
}

# RDS PostgreSQL Instance (Free Tier Eligible)
resource "aws_db_instance" "postgres" {
  identifier             = "smartretailx-postgres"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  max_allocated_storage  = 100
  storage_type           = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password
  port     = 5432

  multi_az               = var.enable_multi_az
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]

  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    Name        = "SmartRetailX-PostgreSQL"
    Environment = var.environment
    Service     = "SmartRetailX"
  }
}
