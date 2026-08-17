# SmartRetailX - Infrastructure as Code (Terraform)

This directory contains the complete cloud-native AWS infrastructure definition for **SmartRetailX** using Terraform.

## 🏗️ Architecture Overview

The Terraform configuration provisions:
* **VPC Networking (`vpc.tf`):** Multi-AZ public and private subnets, Internet Gateway, and Route Tables.
* **Managed Database (`database.tf`):** Amazon RDS PostgreSQL instance (`db.t3.micro`, 20GB gp3, Free Tier eligible) with Security Groups enforcing access control.
* **Serverless Notification Service (`lambda.tf`):** Python 3.10 AWS Lambda triggered via SQS Event Source Mapping from `SmartRetailX-OrderEvents` queue.
* **Frontend Static Hosting & CDN (`s3_cloudfront.tf`):** Amazon S3 bucket with CloudFront Distribution and Origin Access Control (OAC).
* **API Gateway Ingress (`api_gateway.tf`):** Central Amazon API Gateway HTTP API with CORS configured for CloudFront web origin.
* **Monitoring & Observability (`cloudwatch.tf`):** CloudWatch Log Groups for microservices + Metric Alarms for CPU utilization (>80%) and API Gateway 5XX errors.
* **Container Cluster (`main.tf`):** Amazon ECS Fargate cluster with IAM Execution and Task roles.

---

## 🔑 Step 1: Set AWS Environment Variables (Windows PowerShell)

Open PowerShell and set your AWS access credentials:

```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="eu-west-1"
```

*(Optionally, if using temporary session tokens)*:
```powershell
$env:AWS_SESSION_TOKEN="YOUR_AWS_SESSION_TOKEN"
```

---

## 🚀 Step 2: Deployment Execution Steps

From the project root directory, navigate to the `terraform/` directory:

```bash
cd terraform
```

### 1. Initialize Terraform
Downloads the required AWS, Random, and Archive providers:
```bash
terraform init
```

### 2. Validate Configuration
Validates syntax and configuration parameters:
```bash
terraform validate
```

### 3. Generate Execution Plan
Previews the AWS resources that will be provisioned:
```bash
terraform plan
```

### 4. Apply Infrastructure Changes
Provisions the resources on AWS:
```bash
terraform apply
```
*(Enter `yes` when prompted to confirm deployment)*

---

## 📦 Step 3: Deploy Frontend Assets to S3

Once `terraform apply` finishes, note the S3 bucket name output (`s3_frontend_bucket_name`).

Sync the frontend thin-client static assets from the repository to your S3 bucket using the AWS CLI:

```bash
aws s3 sync ../frontend s3://<s3_frontend_bucket_name>
```

---

## 📊 Terraform Outputs

After deployment, Terraform will display key operational outputs:
* `rds_endpoint` — Connection endpoint for PostgreSQL RDS instance
* `s3_frontend_bucket_name` — Name of the created S3 bucket
* `cloudfront_domain_name` — Domain name of the global CDN (HTTPS URL for users)
* `api_gateway_endpoint` — Base API URL for backend microservices
* `lambda_notification_arn` — ARN of the notification Lambda function
* `sqs_queue_url` — Order Events SQS Queue URL
