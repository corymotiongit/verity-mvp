#!/bin/bash
# =============================================================================
# Verity MVP - Deploy Script
# =============================================================================
# Deploys to Google Cloud Run
# Usage: ./scripts/deploy.sh [dev|staging|prod]
# =============================================================================
# ⚠️  REQUIRES MANUAL CONFIRMATION - NO AUTO-DEPLOY
# =============================================================================

set -e

# Default to dev environment
ENV=${1:-dev}

echo "========================================"
echo "  Verity MVP - Cloud Run Deployment"
echo "========================================"
echo ""
echo "Environment: $ENV"
echo ""

# Require confirmation
echo "⚠️  WARNING: This will deploy to Cloud Run ($ENV)"
echo ""
read -p "Are you sure you want to deploy? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

# Configuration
PROJECT_ID="verity-mvp"
REGION="us-central1"
SERVICE_NAME="verity-api-$ENV"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo ""
echo "[1/4] Authenticating with GCP..."
gcloud auth configure-docker gcr.io --quiet

echo ""
echo "[2/4] Building Docker image..."
docker build -t $IMAGE_NAME:latest .

echo ""
echo "[3/4] Pushing image to Container Registry..."
docker push $IMAGE_NAME:latest

echo ""
echo "[4/4] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --set-env-vars "APP_ENV=$ENV" \
    --set-secrets "SUPABASE_URL=supabase-url:latest,SUPABASE_ANON_KEY=supabase-anon-key:latest,SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key:latest,SUPABASE_JWT_SECRET=supabase-jwt-secret:latest,GCP_SA_SECRET_NAME=verity-service-account" \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 60

echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
gcloud run services describe $SERVICE_NAME --region $REGION --format "value(status.url)"
