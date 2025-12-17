#!/bin/bash

# ===========================================
# SSL Certificate Setup Script (Let's Encrypt)
# ===========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment variables
if [ ! -f .env.production ]; then
    echo -e "${RED}Error: .env.production file not found!${NC}"
    exit 1
fi

export $(grep -v '^#' .env.production | xargs)

if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Error: DOMAIN is not set in .env.production${NC}"
    exit 1
fi

EMAIL="${EMAIL:-admin@$DOMAIN}"

echo -e "${YELLOW}Setting up SSL for domain: $DOMAIN${NC}"

# Create temporary nginx config for certificate generation
cat > nginx/nginx-temp.conf << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $DOMAIN;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 301 https://\$host\$request_uri;
        }
    }
}
EOF

# Start nginx with temporary config
echo -e "${YELLOW}Starting nginx for certificate challenge...${NC}"
docker run -d --name temp-nginx \
    -p 80:80 \
    -v $(pwd)/nginx/nginx-temp.conf:/etc/nginx/nginx.conf:ro \
    -v $(pwd)/certbot/www:/var/www/certbot:ro \
    nginx:alpine

# Get certificate
echo -e "${YELLOW}Obtaining SSL certificate...${NC}"
docker run --rm \
    -v $(pwd)/certbot/www:/var/www/certbot \
    -v $(pwd)/certbot/conf:/etc/letsencrypt \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Stop temporary nginx
docker stop temp-nginx
docker rm temp-nginx
rm nginx/nginx-temp.conf

# Update nginx config with correct domain
sed -i.bak "s/yourdomain.com/$DOMAIN/g" nginx/nginx.conf
rm -f nginx/nginx.conf.bak

echo -e "${GREEN}✅ SSL certificate obtained successfully!${NC}"
echo ""
echo "Restart your deployment with:"
echo "docker-compose -f docker-compose.prod.yml restart nginx"
