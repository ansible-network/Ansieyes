# AWS Quick Start Guide

Fastest way to deploy on AWS EC2.

## Prerequisites

- AWS Account
- Domain name (optional but recommended)
- GitHub App already created

## Step-by-Step Deployment

### 1. Launch EC2 Instance (5 minutes)

1. Go to **EC2 Console** → **Launch Instance**
2. Choose:
   - **AMI**: Ubuntu 22.04 LTS
   - **Instance Type**: t2.micro (free tier) or t3.small
   - **Key Pair**: Create/download new key pair
   - **Network**: Allow HTTP (80), HTTPS (443), SSH (22)
3. Click **Launch Instance**
4. Note your **Public IP** address

### 2. Connect to Instance

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### 3. Run Deployment Script

```bash
# On your local machine, copy deployment script to EC2
scp -i your-key.pem aws-deploy.sh ubuntu@YOUR_EC2_IP:~/

# SSH into instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Run deployment script
chmod +x aws-deploy.sh
./aws-deploy.sh https://github.com/KB-perByte/Ansieye.git
```

**OR** manually:

```bash
# Install dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Install Node.js and PM2
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# Clone repository
git clone https://github.com/KB-perByte/Ansieye.git
cd your-repo

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
nano .env
```

Add to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_B64=your_base64_encoded_private_key
GITHUB_WEBHOOK_SECRET=your_webhook_secret
PORT=3000
HOST=0.0.0.0
```

**Encode your private key** (on local machine):
```bash
cat private-key.pem | base64 -w 0
# Copy output and paste as GITHUB_PRIVATE_KEY_B64
```

### 4. Setup Nginx

```bash
sudo nano /etc/nginx/sites-available/Ansieyes
```

Paste:
```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/Ansieyes /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Start Application with PM2

```bash
# Create logs directory
mkdir -p ~/logs

# Update ecosystem.config.js path (if needed)
nano ecosystem.config.js  # Update cwd path

# Start application
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Run the command it outputs
```

### 6. Setup SSL (Required for GitHub Webhooks)

**Option A: With Domain Name**
```bash
sudo certbot --nginx -d your-domain.com
```

**Option B: Without Domain (IP only)**
GitHub requires HTTPS. Options:
1. Use a domain name (recommended)
2. Use AWS Certificate Manager + CloudFront
3. Use self-signed cert (not recommended)

### 7. Update GitHub App Webhook

1. Go to GitHub App settings
2. Update webhook URL:
   - With domain: `https://your-domain.com/webhook`
   - With IP: `https://YOUR_EC2_IP/webhook` (requires SSL)

### 8. Test Deployment

```bash
# Test locally
curl http://localhost:3000/health

# Test from outside
curl https://your-domain.com/health
```

## Verify Everything Works

1. ✅ Health check returns: `{"status": "healthy", "service": "github-pr-review-bot"}`
2. ✅ Create a test PR in your repository
3. ✅ Bot should automatically comment on the PR

## Useful Commands

```bash
# View application logs
pm2 logs Ansieyes

# Restart application
pm2 restart Ansieyes

# Check status
pm2 status

# View Nginx logs
sudo tail -f /var/log/nginx/error.log

# Check system resources
htop
df -h
```

## Troubleshooting

### Application not starting
```bash
pm2 logs Ansieyes --lines 50
# Check for errors in logs
```

### Webhook not working
1. Check security group allows HTTPS (443)
2. Verify webhook URL in GitHub App settings
3. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
4. Test webhook manually: `curl -X POST https://your-domain.com/webhook`

### SSL certificate issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew --dry-run
```

## Cost Optimization

- Use **t2.micro** for free tier (first 12 months)
- Stop instance when not in use (for development)
- Use **Reserved Instances** for production (save ~40%)
- Monitor costs in AWS Cost Explorer

## Next Steps

- ✅ Setup CloudWatch monitoring
- ✅ Configure automatic backups
- ✅ Setup CI/CD for deployments
- ✅ Review security groups

For detailed instructions, see [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)

