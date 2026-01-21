#!/bin/bash
# Template deployment script - customize for your application
# Remove set -e to continue on non-critical errors
set +e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting deployment...${NC}"

# Configuration from environment variables
REPO_PATH="${DEPLOY_REPO_PATH}"
SSH_KEY="${DEPLOY_SSH_KEY}"
EC2_HOST="${DEPLOY_EC2_HOST}"
EC2_USER="${DEPLOY_EC2_USER:-ubuntu}"

# Validate required variables
if [ -z "$REPO_PATH" ] || [ -z "$SSH_KEY" ] || [ -z "$EC2_HOST" ]; then
  echo -e "${RED}Error: Missing required environment variables${NC}"
  echo "Required: DEPLOY_REPO_PATH, DEPLOY_SSH_KEY, DEPLOY_EC2_HOST"
  exit 1
fi

cd "$REPO_PATH"

# ============================================
# 1. PULL LATEST CODE
# ============================================
echo -e "${BLUE}📥 Pulling latest code...${NC}"
git fetch origin
git checkout main  # Change to your branch
git pull origin main

# ============================================
# 2. BUILD FRONTEND (if applicable)
# ============================================
echo -e "${BLUE}📦 Building frontend...${NC}"
# Example for React/Vite:
# cd frontend
# npm ci
# npm run build

# Example for Next.js:
# cd frontend
# npm ci
# npm run build

# ============================================
# 3. DEPLOY FRONTEND (if applicable)
# ============================================
echo -e "${BLUE}🚀 Deploying frontend...${NC}"
# Example for S3:
# aws s3 sync dist/ s3://your-bucket --delete

# Example for Netlify:
# netlify deploy --prod

# Example for Vercel:
# vercel --prod

# ============================================
# 4. DEPLOY BACKEND
# ============================================
echo -e "${BLUE}🚀 Deploying backend...${NC}"

# Create environment file for production
cat > .env.prod << 'EOF'
# Add your production environment variables here
DEBUG=False
DATABASE_URL=your_database_url
API_KEY=your_api_key
EOF

# Sync files to server
rsync -avz \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  -e "ssh -i $SSH_KEY" \
  ./ ${EC2_USER}@${EC2_HOST}:/path/to/your/app/

echo -e "${GREEN}✅ Files synced${NC}"

# ============================================
# 5. RUN MIGRATIONS & RESTART SERVICES
# ============================================
echo -e "${BLUE}🔄 Running migrations and restarting...${NC}"

ssh -i $SSH_KEY ${EC2_USER}@${EC2_HOST} << 'ENDSSH'
set -e
cd /path/to/your/app

# Load environment
set -a; source .env.prod; set +a

# Example for Python/Django:
# source venv/bin/activate
# pip install -r requirements.txt
# python manage.py migrate
# python manage.py collectstatic --noinput

# Example for Node.js:
# npm install
# npm run build

# Restart services
# Example for systemd:
# sudo systemctl restart your-app

# Example for PM2:
# pm2 restart your-app

# Example for Docker:
# docker-compose up -d --build

echo "Deployment complete"
ENDSSH

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Your app: https://yourapp.com${NC}"
