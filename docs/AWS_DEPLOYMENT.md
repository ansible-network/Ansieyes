# AWS Deployment Guide for GitHub PR Review Bot

Complete guide to deploy your GitHub bot on AWS.

## Table of Contents

1. [Option 1: EC2 (Recommended)](#option-1-ec2-recommended)
2. [Option 2: ECS/Fargate (Containerized)](#option-2-ecsfargate-containerized)
3. [Option 3: Elastic Beanstalk](#option-3-elastic-beanstalk)
4. [Cost Estimation](#cost-estimation)
5. [Security Best Practices](#security-best-practices)
6. [Monitoring & Logging](#monitoring--logging)

---

## Option 1: EC2 (Recommended)

### Prerequisites

- AWS Account
- AWS CLI installed and configured
- SSH key pair for EC2 access

### Step 1: Launch EC2 Instance

#### Via AWS Console:

1. **Go to EC2 Dashboard** → Launch Instance

2. **Configure Instance**:

   - **Name**: github-pr-review-bot
   - **AMI**: Ubuntu 22.04 LTS (Free tier eligible)
   - **Instance Type**: t2.micro (Free tier) or t3.small ($0.0208/hour)
   - **Key Pair**: Create new or select existing
   - **Network Settings**:
     - Allow HTTP (port 80)
     - Allow HTTPS (port 443)
     - Allow SSH (port 22) from your IP

3. **Configure Storage**: 8 GB (Free tier) or 20 GB

4. **Launch Instance**

#### Via AWS CLI:

```bash
# Create security group
aws ec2 create-security-group \
  --group-name Ansieyes-sg \
  --description "Security group for GitHub PR Review Bot"

# Allow HTTP, HTTPS, and SSH
aws ec2 authorize-security-group-ingress \
  --group-name Ansieyes-sg \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name Ansieyes-sg \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-name Ansieyes-sg \
  --protocol tcp \
  --port 22 \
  --cidr YOUR_IP/32

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.small \
  --key-name your-key-name \
  --security-groups Ansieyes-sg \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=github-pr-review-bot}]'
```

### Step 2: Connect to Instance

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### Step 3: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3-pip python3-venv git nginx certbot python3-certbot-nginx

# Install Node.js (for PM2 process manager - optional but recommended)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 globally
sudo npm install -g pm2
```

### Step 4: Clone and Setup Application

```bash
# Clone your repository
git clone https://github.com/KB-perByte/Ansieye.git
cd Ansieye

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

```bash
# Create .env file
nano .env
```

Add your configuration:

```env
GEMINI_API_KEY=your_gemini_api_key
GITHUB_APP_ID=your_app_id
GITHUB_PRIVATE_KEY_B64=your_base64_encoded_private_key
GITHUB_WEBHOOK_SECRET=your_webhook_secret
PORT=3000
HOST=0.0.0.0
```

**To encode your private key:**

```bash
# On your local machine
cat private-key.pem | base64 -w 0
# Copy the output and paste as GITHUB_PRIVATE_KEY_B64
```

### Step 6: Setup Domain (Optional but Recommended)

#### Option A: Use EC2 Public IP

Skip to Step 7 if using IP directly.

#### Option B: Use Domain Name

1. **Point domain to EC2 IP**:

   - Go to your domain registrar
   - Add A record: `@` → `YOUR_EC2_IP`
   - Add A record: `www` → `YOUR_EC2_IP`

2. **Wait for DNS propagation** (5-30 minutes)

### Step 7: Setup Nginx Reverse Proxy

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/Ansieyes
```

Add this configuration:

```nginx
server {
    listen 80;
    # server_name your-domain.com www.your-domain.com;

    # If using IP only, remove server_name line above

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/Ansieyes /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### Step 8: Setup SSL with Let's Encrypt

```bash
# If using domain name
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow prompts:
# - Enter email
# - Agree to terms
# - Choose redirect HTTP to HTTPS (option 2)

# If using IP only, skip SSL (but GitHub requires HTTPS for webhooks)
# Consider using a domain or AWS Certificate Manager with CloudFront
```

### Step 9: Setup Process Manager (PM2)

```bash
# Create PM2 ecosystem file
nano ecosystem.config.js
```

Add:

```javascript
module.exports = {
  apps: [
    {
      name: 'Ansieyes',
      script: 'app.py',
      interpreter: 'python3',
      cwd: '/home/ubuntu/Ansieye',
      env: {
        GEMINI_API_KEY: 'your_key',
        GITHUB_APP_ID: 'your_app_id',
        GITHUB_PRIVATE_KEY_B64: 'your_encoded_key',
        GITHUB_WEBHOOK_SECRET: 'your_secret',
        PORT: 3000,
        HOST: '0.0.0.0',
      },
      error_file: '/home/ubuntu/logs/err.log',
      out_file: '/home/ubuntu/logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
    },
  ],
};
```

**Or use .env file with PM2:**

```bash
# Install pm2-logrotate to manage logs
pm2 install pm2-logrotate

# Start application
cd /home/ubuntu/Ansieye
source venv/bin/activate
pm2 start app.py --name Ansieyes --interpreter python3 --env production

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
# Run the command it outputs (usually starts with 'sudo')
```

### Step 10: Alternative - Systemd Service

If you prefer systemd over PM2:

```bash
sudo nano /etc/systemd/system/Ansieyes.service
```

Add:

```ini
[Unit]
Description=GitHub PR Review Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Ansieye
Environment="PATH=/home/ubuntu/Ansieye/venv/bin"
ExecStart=/home/ubuntu/Ansieye/venv/bin/python app.py
Restart=always
RestartSec=10

# Environment variables
EnvironmentFile=/home/ubuntu/Ansieye/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable Ansieyes
sudo systemctl start Ansieyes
sudo systemctl status Ansieyes
```

### Step 11: Update GitHub App Webhook

1. Go to your GitHub App settings
2. Update webhook URL:
   - With domain: `https://your-domain.com/webhook`
   - With IP only: `https://YOUR_EC2_IP/webhook` (requires self-signed cert or domain)

### Step 12: Test Deployment

```bash
# Check if app is running
curl http://localhost:3000/health

# Check from outside (should work through Nginx)
curl https://your-domain.com/health

# Check logs
pm2 logs Ansieyes
# OR
sudo journalctl -u Ansieyes -f
```

### Step 13: Setup Auto-Deploy (Optional)

Create a deployment script:

```bash
nano ~/deploy.sh
```

```bash
#!/bin/bash
cd /home/ubuntu/Ansieye
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pm2 restart Ansieyes
```

Make executable:

```bash
chmod +x ~/deploy.sh
```

---

## Option 2: ECS/Fargate (Containerized)

### Prerequisites

- Docker image built and pushed to ECR
- ECS cluster created

### Step 1: Build and Push Docker Image

```bash
# On your local machine
aws ecr create-repository --repository-name Ansieyes

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t Ansieyes .

# Tag image
docker tag Ansieyes:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/Ansieyes:latest

# Push image
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/Ansieyes:latest
```

### Step 2: Create ECS Task Definition

Create `task-definition.json`:

```json
{
  "family": "Ansieyes",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "Ansieyes",
      "image": "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/Ansieyes:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "GEMINI_API_KEY",
          "value": "your_key"
        },
        {
          "name": "GITHUB_APP_ID",
          "value": "your_app_id"
        },
        {
          "name": "GITHUB_PRIVATE_KEY_B64",
          "value": "your_encoded_key"
        },
        {
          "name": "GITHUB_WEBHOOK_SECRET",
          "value": "your_secret"
        },
        {
          "name": "PORT",
          "value": "3000"
        },
        {
          "name": "HOST",
          "value": "0.0.0.0"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/Ansieyes",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register task definition:

```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster your-cluster-name \
  --service-name Ansieyes \
  --task-definition Ansieyes \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### Step 4: Setup Application Load Balancer

1. Create ALB in AWS Console
2. Create target group pointing to ECS service
3. Setup HTTPS listener with ACM certificate
4. Update GitHub webhook to ALB URL

---

## Option 3: Elastic Beanstalk

### Step 1: Install EB CLI

```bash
pip install awsebcli
```

### Step 2: Initialize EB Application

```bash
eb init -p python-3.11 Ansieyes --region us-east-1
```

### Step 3: Create Environment

```bash
eb create Ansieyes-env
```

### Step 4: Set Environment Variables

```bash
eb setenv \
  GEMINI_API_KEY=your_key \
  GITHUB_APP_ID=your_app_id \
  GITHUB_PRIVATE_KEY_B64=your_encoded_key \
  GITHUB_WEBHOOK_SECRET=your_secret \
  PORT=3000 \
  HOST=0.0.0.0
```

### Step 5: Deploy

```bash
eb deploy
```

### Step 6: Get URL

```bash
eb status
# Update GitHub webhook with the CNAME URL
```

---

## Cost Estimation

### EC2 (t3.small)

- **Instance**: ~$15/month (if running 24/7)
- **Data Transfer**: First 100 GB free, then $0.09/GB
- **Storage**: 20 GB EBS ~$2/month
- **Total**: ~$17-20/month

### ECS Fargate

- **CPU**: 0.25 vCPU × $0.04048/hour = ~$7.30/month
- **Memory**: 0.5 GB × $0.004445/hour = ~$3.20/month
- **ALB**: ~$16/month
- **Total**: ~$26-30/month

### Elastic Beanstalk

- Similar to EC2 costs
- Additional management overhead

**Free Tier**: t2.micro instance free for 12 months (750 hours/month)

---

## Security Best Practices

### 1. Use IAM Roles

```bash
# Create IAM role for EC2
aws iam create-role --role-name EC2-GitHubBot-Role \
  --assume-role-policy-document file://trust-policy.json

# Attach minimal permissions
aws iam attach-role-policy \
  --role-name EC2-GitHubBot-Role \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
```

### 2. Use AWS Secrets Manager

Store sensitive data in Secrets Manager:

```bash
# Store secrets
aws secretsmanager create-secret \
  --name Ansieyes-secrets \
  --secret-string '{"GEMINI_API_KEY":"your_key","GITHUB_APP_ID":"123","GITHUB_WEBHOOK_SECRET":"secret"}'

# Update app.py to read from Secrets Manager
```

### 3. Restrict Security Groups

Only allow necessary ports:

- SSH: Only from your IP
- HTTP/HTTPS: From anywhere (for webhooks)

### 4. Regular Updates

```bash
# Setup automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 5. Enable CloudWatch Logs

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Configure and start
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -c ssm:AmazonCloudWatch-linux -s
```

---

## Monitoring & Logging

### CloudWatch Metrics

Monitor:

- CPU utilization
- Memory usage
- Network traffic
- Application health (custom metric from `/health` endpoint)

### CloudWatch Logs

View logs:

```bash
# Via AWS Console: CloudWatch → Log Groups
# Or via CLI:
aws logs tail /aws/ec2/Ansieyes --follow
```

### Setup Alarms

```bash
# Create alarm for high CPU
aws cloudwatch put-metric-alarm \
  --alarm-name Ansieyes-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

---

## Troubleshooting

### Application not starting

```bash
# Check PM2 status
pm2 status
pm2 logs Ansieyes

# Check systemd status
sudo systemctl status Ansieyes
sudo journalctl -u Ansieyes -n 50

# Check Nginx
sudo nginx -t
sudo systemctl status nginx
```

### Webhook not receiving requests

1. Check security group allows HTTPS (443)
2. Verify webhook URL is correct
3. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
4. Verify SSL certificate is valid

### High memory usage

```bash
# Check memory
free -h
ps aux --sort=-%mem | head

# Restart application
pm2 restart Ansieyes
```

---

## Quick Reference Commands

```bash
# View logs
pm2 logs Ansieyes
sudo journalctl -u Ansieyes -f

# Restart application
pm2 restart Ansieyes
sudo systemctl restart Ansieyes

# Check status
pm2 status
sudo systemctl status Ansieyes

# Update application
cd /home/ubuntu/Ansieye
git pull
source venv/bin/activate
pip install -r requirements.txt
pm2 restart Ansieyes
```

---

## Next Steps

1. ✅ Deploy application
2. ✅ Setup monitoring and alerts
3. ✅ Configure backups (if needed)
4. ✅ Setup CI/CD for automatic deployments
5. ✅ Review and optimize costs

For more details, see the main [HOSTING.md](HOSTING.md) guide.
