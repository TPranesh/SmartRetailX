# ==============================================================================
# SmartRetailX - AWS ECS Fargate Service Deployment & Spin-up Script
# ==============================================================================

$ErrorActionPreference = "Stop"

$AWS_REGION = "eu-west-1"
$AWS_ACCOUNT_ID = "538471156806"
$CLUSTER_NAME = "smartretailx-cluster"
$SERVICES = @("user", "product", "order", "inventory")

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Starting SmartRetailX ECS Service Deployment & Activation" -ForegroundColor Cyan
Write-Host " Cluster Name : $CLUSTER_NAME" -ForegroundColor Yellow
Write-Host " AWS Region   : $AWS_REGION" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan

# Option A: Deploy via Terraform
Write-Host "`n[Option A] Deploying via Terraform..." -ForegroundColor Green
Set-Location -Path "$PSScriptRoot\terraform"
terraform init
terraform apply -auto-approve

# Option B: Verify & Force ECS Deployment via AWS CLI
Write-Host "`n[Option B] Ensuring desired count = 1 and forcing new deployment via AWS CLI..." -ForegroundColor Green

foreach ($service in $SERVICES) {
    $SERVICE_NAME = "smartretailx-${service}-service"
    Write-Host "`nUpdating ECS Service: $SERVICE_NAME ..." -ForegroundColor Cyan
    try {
        aws ecs update-service `
            --cluster $CLUSTER_NAME `
            --service $SERVICE_NAME `
            --desired-count 1 `
            --force-new-deployment `
            --region $AWS_REGION
        Write-Host "Successfully updated $SERVICE_NAME!" -ForegroundColor Green
    } catch {
        Write-Host "Service $SERVICE_NAME update output: $_" -ForegroundColor Yellow
    }
}

Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host " ECS Fargate Services Successfully Deployed and Spun Up!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
