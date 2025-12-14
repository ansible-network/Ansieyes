#!/bin/bash
# AWS Deployment Script for GitHub PR Review Bot
# Run this script on your EC2 instance after initial setup

set -e

echo "🚀 AWS Deployment Script for GitHub PR Review Bot"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo -e "${RED}Please do not run as root. Use a regular user (ubuntu).${NC}"
   exit 1
fi

# Variables
APP_DIR="$HOME/Ansieyes"
REPO_URL="${1:-https://github.com/KB-perByte/Ansieye.git}"

echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

echo ""
echo "📥 Cloning repository..."
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}Directory exists. Pulling latest changes...${NC}"
    cd "$APP_DIR"
    git pull
else
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo ""
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "📝 Checking environment variables..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found!${NC}"
    echo "Please create .env file with required variables:"
    echo "  - GEMINI_API_KEY"
    echo "  - GITHUB_APP_ID"
    echo "  - GITHUB_PRIVATE_KEY_B64"
    echo "  - GITHUB_WEBHOOK_SECRET"
    echo ""
    read -p "Press Enter to continue after creating .env file..."
fi

echo ""
echo "📋 Setting up Nginx..."
sudo tee /etc/nginx/sites-available/Ansieyes > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/Ansieyes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

echo ""
echo "📦 Installing PM2..."
if ! command -v pm2 &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
    sudo npm install -g pm2
fi

echo ""
echo "🚀 Starting application with PM2..."
# Create logs directory
mkdir -p "$HOME/logs"

# Update ecosystem.config.js with correct path
sed -i "s|/home/ubuntu/Ansieyes|$APP_DIR|g" ecosystem.config.js 2>/dev/null || true

pm2 start ecosystem.config.js || pm2 restart Ansieyes
pm2 save
pm2 startup | grep -v "PM2" | bash || true

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📊 Application Status:"
pm2 status

echo ""
echo "🌐 Your application should be running at:"
echo "   http://$(curl -s ifconfig.me)/health"
echo ""
echo "📝 Next steps:"
echo "   1. Setup SSL: sudo certbot --nginx -d your-domain.com"
echo "   2. Update GitHub App webhook URL"
echo "   3. Test: curl http://localhost:3000/health"
echo ""
echo "📋 Useful commands:"
echo "   - View logs: pm2 logs Ansieyes"
echo "   - Restart: pm2 restart Ansieyes"
echo "   - Status: pm2 status"

