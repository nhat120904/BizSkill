#!/bin/bash

# ===========================================
# BizSkill Deployment Script
# ===========================================

set -e

echo "🚀 Starting BizSkill deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo -e "${RED}Error: .env.production file not found!${NC}"
    echo "Please copy .env.production.example to .env.production and fill in your values."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env.production | xargs)

# Check required environment variables
required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "DOMAIN")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}Error: $var is not set in .env.production${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✓ Environment variables loaded${NC}"

# Create required directories
mkdir -p nginx/ssl
mkdir -p certbot/www
mkdir -p certbot/conf

echo -e "${GREEN}✓ Directories created${NC}"

# Build and start services
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose -f docker-compose.prod.yml --env-file .env.production build

echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 10

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ BizSkill deployed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Frontend: https://${DOMAIN}"
echo "API: https://${DOMAIN}/api/v1"
echo "API Docs: https://${DOMAIN}/docs"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set up SSL certificates with: ./scripts/setup-ssl.sh"
echo "2. Update nginx/nginx.conf with your domain"
echo "3. Restart nginx: docker-compose -f docker-compose.prod.yml restart nginx"
