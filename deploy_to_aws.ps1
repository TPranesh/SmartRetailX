# ==============================================================================
# SmartRetailX - AWS ECR Docker Image Deployment Script
# ==============================================================================

# Stop script execution on error
$ErrorActionPreference = "Stop"

# 1. AWS Configuration
$AWS_REGION = "eu-west-1"
$AWS_ACCOUNT_ID = "538471156806"
$ECR_REGISTRY = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

$SERVICES = @("user", "product", "inventory", "order")

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host " Starting SmartRetailX AWS ECR Deployment Process" -ForegroundColor Cyan
Write-Host " AWS Region     : $AWS_REGION" -ForegroundColor Yellow
Write-Host " AWS Account ID : $AWS_ACCOUNT_ID" -ForegroundColor Yellow
Write-Host " ECR Registry   : $ECR_REGISTRY" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan

# 2. Authenticate Docker to AWS ECR
Write-Host "`n[Step 1/3] Authenticating Docker to AWS ECR..." -ForegroundColor Green
try {
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY
    if ($LASTEXITCODE -ne 0) {
        throw "Docker ECR authentication failed."
    }
    Write-Host "Successfully authenticated Docker to $ECR_REGISTRY!" -ForegroundColor Green
} catch {
    Write-Host "Error during ECR authentication: $_" -ForegroundColor Red
    exit 1
}

# 3. Process Each Microservice Image (Tag and Push)
Write-Host "`n[Step 2/3] Tagging and Pushing Microservice Images to ECR..." -ForegroundColor Green

foreach ($service in $SERVICES) {
    $LOCAL_IMAGE = "smartretailx-${service}-service:latest"
    $ECR_REPO = "smartretailx-${service}-service"
    $TARGET_IMAGE = "${ECR_REGISTRY}/${ECR_REPO}:latest"

    Write-Host "`n------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host " Processing Service: $service" -ForegroundColor Yellow
    Write-Host " Local Image  : $LOCAL_IMAGE" -ForegroundColor Gray
    Write-Host " Target ECR   : $TARGET_IMAGE" -ForegroundColor Gray
    Write-Host "------------------------------------------------------------------" -ForegroundColor DarkGray

    # Tag local image
    Write-Host "Tagging $LOCAL_IMAGE -> $TARGET_IMAGE ..." -ForegroundColor Cyan
    docker tag $LOCAL_IMAGE $TARGET_IMAGE
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to tag image $LOCAL_IMAGE. Ensure local image exists." -ForegroundColor Red
        continue
    }

    # Push image to ECR
    Write-Host "Pushing $TARGET_IMAGE to AWS ECR..." -ForegroundColor Cyan
    docker push $TARGET_IMAGE
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to push image $TARGET_IMAGE to ECR." -ForegroundColor Red
    } else {
        Write-Host "Successfully pushed $service service image to ECR!" -ForegroundColor Green
    }
}

# Summary
Write-Host "`n==================================================================" -ForegroundColor Cyan
Write-Host " Deployment Complete for All SmartRetailX Microservices!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
