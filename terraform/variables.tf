# terraform/variables.tf

variable "aws_region" {
  type        = string
  default     = "eu-west-1"
  description = "AWS region for deployment"
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment"
}

variable "db_name" {
  type        = string
  default     = "smartretailx"
  description = "Name of the RDS PostgreSQL database"
}

variable "db_username" {
  type        = string
  default     = "srx_admin"
  description = "Database administrator username"
}

variable "db_password" {
  type        = string
  default     = "SmartRetailX2026SecurePass!"
  sensitive   = true
  description = "Database administrator password"
}

variable "enable_multi_az" {
  type        = bool
  default     = false
  description = "Enable Multi-AZ support for RDS database"
}
