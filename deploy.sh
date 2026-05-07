#!/bin/bash
set -e  # Exit on any error

# Configuration
PROJECT_NAME="chat"
SERVICE_NAME="onboarding"
DOCKERFILE_PATH="Dockerfile"

echo "=========================================="
echo "  Python FastAPI ECS Deployment via OIDC"
echo "=========================================="
echo "Environment: $BITBUCKET_DEPLOYMENT_ENVIRONMENT"
echo "AWS Region: $AWS_REGION"
echo "Commit: ${BITBUCKET_COMMIT:0:8}"
echo "Build: $BITBUCKET_BUILD_NUMBER"
echo ""

# Validate required environment variables
required_vars=("AWS_ROLE_ARN" "AWS_WEB_IDENTITY_TOKEN_FILE" "AWS_REGION" "BITBUCKET_COMMIT" "BITBUCKET_BUILD_NUMBER")
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "❌ Error: Required environment variable $var is not set"
    exit 1
  fi
done

echo "✓ Environment validation passed"
echo "✓ Role ARN: $AWS_ROLE_ARN"

# Configure AWS CLI and authenticate via OIDC
echo ""
echo "🔐 Authenticating with AWS via OIDC..."
export AWS_DEFAULT_REGION=$AWS_REGION

# AWS CLI will automatically use OIDC when these environment variables are set
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✓ Successfully authenticated to AWS Account: $AWS_ACCOUNT_ID"

# Fetch deployment configuration from SSM
echo ""
echo "📋 Fetching deployment configuration..."
ECR_REPO_NAME=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${SERVICE_NAME}/ecr/repositoryName" --query 'Parameter.Value' --output text)
echo "✓ ECR Repository: $ECR_REPO_NAME"

ECS_CLUSTER_NAME=$(aws ssm get-parameter --name "/${PROJECT_NAME}/shared/ecs/clusterName" --query 'Parameter.Value' --output text 2>/dev/null || echo "")
ECS_SERVICE_NAME=$(aws ssm get-parameter --name "/${PROJECT_NAME}/${SERVICE_NAME}/ecs/serviceName" --query 'Parameter.Value' --output text 2>/dev/null || echo "")

if [ -n "$ECS_CLUSTER_NAME" ] && [ -n "$ECS_SERVICE_NAME" ]; then
  echo "✓ ECS Cluster: $ECS_CLUSTER_NAME"
  echo "✓ ECS Service: $ECS_SERVICE_NAME"
  DEPLOY_ECS=true
else
  echo "⚠ ECS configuration not found - skipping deployment trigger"
  echo "  Required: /${PROJECT_NAME}/shared/ecs/clusterName"
  echo "  Required: /${PROJECT_NAME}/${SERVICE_NAME}/ecs/serviceName"
  DEPLOY_ECS=false
fi

# Prepare image configuration
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
IMAGE_TAG="${BITBUCKET_COMMIT:0:8}-${BITBUCKET_BUILD_NUMBER}"
FULL_IMAGE_URI="${ECR_URI}:${IMAGE_TAG}"
LATEST_IMAGE_URI="${ECR_URI}:latest"

echo "✓ Target ECR URI: $ECR_URI"
echo "✓ Image Tag: $IMAGE_TAG"

# Configure Docker for optimized builds
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

# Authenticate with ECR
echo ""
echo "🔑 Logging in to Amazon ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
echo "✓ ECR authentication successful"

# Optimize Docker builds with layer caching
echo ""
echo "🐳 Preparing Docker build with layer caching..."

# Load cached layers if available
if [ -d /tmp/docker-cache ] && [ "$(ls -A /tmp/docker-cache 2>/dev/null)" ]; then
  echo "Loading cached Docker layers..."
  for cache_file in /tmp/docker-cache/*.tar; do
    [ -f "$cache_file" ] && docker load < "$cache_file" || true
  done
  echo "✓ Cache loaded"
fi

# Attempt to pull latest image for additional layer caching
echo "Pulling latest image for cache optimization..."
docker pull $LATEST_IMAGE_URI || echo "No existing image found - building from scratch"

# Build the Python FastAPI application
echo ""
echo "🔨 Building Python FastAPI Docker image..."
echo "Source: $DOCKERFILE_PATH"
echo "Tags: $IMAGE_TAG, latest"

docker build \
  --cache-from $LATEST_IMAGE_URI \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --tag $FULL_IMAGE_URI \
  --tag $LATEST_IMAGE_URI \
  --file $DOCKERFILE_PATH \
  .

echo "✓ Docker image built successfully"

# Cache layers for future builds
echo ""
echo "💾 Caching Docker layers..."
mkdir -p /tmp/docker-cache
docker save $LATEST_IMAGE_URI -o /tmp/docker-cache/image-cache-$(date +%s).tar 2>/dev/null || true
# Clean old cache files (older than 7 days)
find /tmp/docker-cache -name "*.tar" -type f -mtime +7 -delete 2>/dev/null || true
echo "✓ Build cache updated"

# Push images to ECR
echo ""
echo "📤 Pushing images to Amazon ECR..."
docker push $FULL_IMAGE_URI
docker push $LATEST_IMAGE_URI

echo ""
echo "✅ Images successfully pushed to ECR:"
echo "   Tagged: $FULL_IMAGE_URI"
echo "   Latest: $LATEST_IMAGE_URI"

# Clean up local images to conserve disk space
echo ""
echo "🧹 Cleaning up local Docker images..."
docker rmi $FULL_IMAGE_URI $LATEST_IMAGE_URI 2>/dev/null || true
echo "✓ Local cleanup completed"

# Deploy to ECS (if configured)
echo ""
if [ "$DEPLOY_ECS" = true ]; then
  echo "🚀 Triggering ECS service deployment..."
  
  # Force new deployment of the ECS service
  # This will pull the latest image and deploy new tasks
  DEPLOYMENT_RESPONSE=$(aws ecs update-service \
    --cluster "$ECS_CLUSTER_NAME" \
    --service "$ECS_SERVICE_NAME" \
    --force-new-deployment \
    --query 'service.deployments[0].id' \
    --output text)
  
  echo "✅ ECS deployment initiated"
  echo "   Deployment ID: $DEPLOYMENT_RESPONSE"
  echo "   Cluster: $ECS_CLUSTER_NAME"
  echo "   Service: $ECS_SERVICE_NAME"
  echo ""
  echo "📊 Monitor deployment progress:"
  echo "   https://${AWS_REGION}.console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER_NAME}/services/${ECS_SERVICE_NAME}/health"
else
  echo "⏭️  ECS deployment skipped (not configured)"
fi

# Deployment summary
echo ""
echo "🎉 Deployment Summary"
echo "=================================="
echo "Environment: $BITBUCKET_DEPLOYMENT_ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Image: $FULL_IMAGE_URI"
echo "Build: $BITBUCKET_BUILD_NUMBER"
echo "Commit: ${BITBUCKET_COMMIT:0:8}"
echo "ECS: $([ "$DEPLOY_ECS" = true ] && echo "✓ Deployed" || echo "⏭️ Skipped")"
echo "=================================="
echo "✅ Pipeline completed successfully!"