# SmartRetailX — Infrastructure as Code (Terraform)

This directory contains the Terraform configuration for deploying the **SmartRetailX** distributed microservices platform to AWS using containerized infrastructure (ECS Fargate) and event-driven messaging (Amazon SQS).

---

## AWS Architecture Mapping

| Component | AWS Service | Terraform Resource | Purpose in SmartRetailX |
|---|---|---|---|
| **Event Bus** | Amazon SQS | `aws_sqs_queue.order_events` | Asynchronous decoupled queue (`SmartRetailX-OrderEvents`) for order placement and cancellation events |
| **Dead Letter Queue** | Amazon SQS DLQ | `aws_sqs_queue.order_events_dlq` | Captures unprocessable/failed messages after 5 retries |
| **Container Orchestrator** | Amazon ECS | `aws_ecs_cluster.main` | Serverless container cluster (`smartretailx-cluster`) |
| **Compute Engine** | AWS Fargate | `aws_ecs_task_definition.order_service` | Serverless compute environment running microservice containers |
| **IAM Access Control** | AWS IAM | `aws_iam_role.ecs_task_role`, `aws_iam_policy.sqs_access` | Least-privilege IAM roles giving services SQS send/receive capabilities |
| **Observability** | Amazon CloudWatch | `aws_cloudwatch_log_group.ecs_logs` | Centralized log ingestion and container monitoring (`/ecs/smartretailx`) |

---

## Prerequisites

- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (>= 1.5.0)
- AWS CLI configured with appropriate credentials (`aws configure`)

---

## Terraform Workflow Commands

```bash
# 1. Initialize working directory & download providers
terraform init

# 2. Validate configuration syntax
terraform validate

# 3. Preview execution plan
terraform plan

# 4. Apply configuration to deploy infrastructure (DO NOT RUN FOR LOCAL TESTING)
# terraform apply
```
