#!/bin/bash
# Removed set -e to see all errors
set +e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Nomadic Influence deployment...${NC}"

# Configuration from environment
REPO_PATH="${DEPLOY_REPO_PATH}"
SSH_KEY="${DEPLOY_SSH_KEY}"
EC2_HOST="${DEPLOY_EC2_HOST}"
EC2_USER="${DEPLOY_EC2_USER:-ubuntu}"
AWS_REGION="us-east-1"

if [ -z "$REPO_PATH" ] || [ -z "$SSH_KEY" ] || [ -z "$EC2_HOST" ]; then
  echo "Error: Missing required environment variables"
  exit 1
fi

cd "$REPO_PATH"

# Pull latest from develop
echo -e "${BLUE}📥 Pulling latest code from develop...${NC}"
git fetch origin
git checkout develop
git pull origin develop

echo -e "${BLUE}📦 Building frontend...${NC}"
cd frontend

npm ci

# Get frontend secrets from Parameter Store
echo "Fetching secrets from AWS Parameter Store..."
VITE_API_BASE_URL=$(aws ssm get-parameter --name "/nomadic-influence/frontend/api-base-url" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_STRIPE_PUBLISHABLE_KEY=$(aws ssm get-parameter --name "/nomadic-influence/frontend/stripe-publishable-key" --region $AWS_REGION --with-decryption --query 'Parameter.Value' --output text)
VITE_FIREBASE_API_KEY=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-api-key" --region $AWS_REGION --with-decryption --query 'Parameter.Value' --output text)
VITE_FIREBASE_AUTH_DOMAIN=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-auth-domain" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_FIREBASE_PROJECT_ID=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-project-id" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_FIREBASE_STORAGE_BUCKET=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-storage-bucket" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_FIREBASE_MESSAGING_SENDER_ID=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-messaging-sender-id" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_FIREBASE_APP_ID=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-app-id" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_FIREBASE_MEASUREMENT_ID=$(aws ssm get-parameter --name "/nomadic-influence/frontend/firebase-measurement-id" --region $AWS_REGION --query 'Parameter.Value' --output text)
VITE_MAPBOX_ACCESS_TOKEN=$(aws ssm get-parameter --name "/nomadic-influence/frontend/mapbox-token" --region $AWS_REGION --with-decryption --query 'Parameter.Value' --output text)

cat > .env.production << EOF
VITE_API_BASE_URL=$VITE_API_BASE_URL
VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY
VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET
VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID
VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
VITE_FIREBASE_MEASUREMENT_ID=$VITE_FIREBASE_MEASUREMENT_ID
VITE_MAPBOX_ACCESS_TOKEN=$VITE_MAPBOX_ACCESS_TOKEN
EOF

npm run build

echo -e "${GREEN}✅ Frontend built${NC}"

echo -e "${BLUE}🚀 Deploying frontend to S3...${NC}"
aws s3 sync dist/ s3://nomadic-influence-frontend --delete
echo -e "${GREEN}📦 Files uploaded to S3${NC}"

echo -e "${BLUE}🔄 Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id E3UI51LIT0BU2X \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text)

echo -e "${GREEN}✅ Invalidation created: $INVALIDATION_ID${NC}"

cd ..

echo -e "${BLUE}🚀 Deploying backend to EC2...${NC}"

# Create env file
cat > backend/.env << 'EOF'
DEBUG=False
DJANGO_SETTINGS_MODULE=config.settings.prod
DB_HOST=nomadic-influence-db.cgz0820gqltl.us-east-1.rds.amazonaws.com
DB_PORT=5432
FIREBASE_SERVICE_ACCOUNT_KEY=/opt/nomadic-influence/backend/firebase-service-account.json
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=email-smtp.us-east-1.amazonaws.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=info@nomadicinfluence.com
AWS_S3_REGION_NAME=us-east-1
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
FRONTEND_URL=https://nomadicinfluence.com
EOF

# Sync backend files
rsync -avz \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.pytest_cache' \
  --exclude 'db.sqlite3' \
  --exclude 'media/*' \
  --exclude 'staticfiles' \
  --exclude '*.log' \
  -e "ssh -i $SSH_KEY" \
  backend/ ${EC2_USER}@${EC2_HOST}:/opt/nomadic-influence/backend/

echo -e "${GREEN}✅ Backend files synced${NC}"

echo -e "${BLUE}🔄 Running migrations and restarting...${NC}"

# Run migrations and restart
ssh -i $SSH_KEY ${EC2_USER}@${EC2_HOST} << 'ENDSSH'
set -e
cd /opt/nomadic-influence/backend
export PATH="$HOME/.local/bin:$PATH"
set -a; source .env; set +a
poetry install --only main
poetry run python manage.py migrate --noinput
poetry run python manage.py seed_business_taxonomy
poetry run python manage.py collectstatic --noinput

# Kill existing gunicorn processes
pkill -9 gunicorn || true
sleep 2

# Start gunicorn in background
nohup poetry run gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120 > /tmp/gunicorn.log 2>&1 &
sleep 3

echo "Deployment complete"
ENDSSH

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Frontend: https://nomadicinfluence.com${NC}"
echo -e "${GREEN}🔧 Backend: https://api.nomadicinfluence.com${NC}"
