#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY_NAME="hill-hill-game-dev"
AWS_ACCOUNT_ID="714364484263"
IMAGE_TAG="${1:-latest}"  # Use argument or default to 'latest'

# Construct ECR URL
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

echo "=========================================="
echo "Building and Pushing to ECR"
echo "=========================================="
echo "Region: ${AWS_REGION}"
echo "Repository: ${ECR_REPOSITORY_NAME}"
echo "Tag: ${IMAGE_TAG}"
echo "ECR URL: ${ECR_URL}"
echo "=========================================="

# Authenticate Podman to ECR
echo "Authenticating to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | podman login --username AWS --password-stdin ${ECR_URL}

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to authenticate with ECR"
    exit 1
fi

# Build the image with Podman for AMD64 architecture (EKS nodes)
echo "Building image with Podman for linux/amd64..."
podman build --platform linux/amd64 -t ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} .

if [ $? -ne 0 ]; then
    echo "ERROR: Podman build failed"
    exit 1
fi

# Tag the image for ECR
echo "Tagging image for ECR..."
podman tag ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URL}:${IMAGE_TAG}

# Push to ECR
echo "Pushing image to ECR..."
podman push ${ECR_URL}:${IMAGE_TAG}

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to push image to ECR"
    exit 1
fi

echo "=========================================="
echo "Successfully pushed ${ECR_URL}:${IMAGE_TAG}"
echo "=========================================="

