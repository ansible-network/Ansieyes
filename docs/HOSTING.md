# Hosting Guide for GitHub PR Review Bot

This guide covers various hosting options for deploying your GitHub bot.

## Table of Contents

1. [Quick Comparison](#quick-comparison)
2. [Option 1: Railway (Recommended for Beginners)](#option-1-railway-recommended-for-beginners)
3. [Option 2: Render](#option-2-render)
4. [Option 3: Heroku](#option-3-heroku)
5. [Option 4: AWS EC2](#option-4-aws-ec2)
6. [Option 5: Docker Deployment](#option-5-docker-deployment)
7. [Option 6: GitHub Actions (Serverless)](#option-6-github-actions-serverless)
8. [Option 7: DigitalOcean App Platform](#option-7-digitalocean-app-platform)

## Quick Comparison

| Platform | Cost | Difficulty | Best For |
|----------|------|------------|----------|
| Railway | Free tier available | ⭐ Easy | Quick deployment |
| Render | Free tier available | ⭐ Easy | Simple hosting |
| Heroku | Paid ($7+/mo) | ⭐⭐ Medium | Established platform |
| AWS EC2 | Pay-as-you-go | ⭐⭐⭐ Hard | Full control |
| Docker | Varies | ⭐⭐ Medium | Self-hosted |
| GitHub Actions | Free for public repos | ⭐⭐ Medium | Serverless |

---

## Option 1: Railway (Recommended for Beginners)

**Best for:** Quick deployment with minimal setup

### Steps:

1. **Sign up** at [railway.app](https://railway.app)

2. **Create a new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo" (connect your repo)
   - Or use "Empty Project" and connect later

3. **Add environment variables**:
   - Go to your project → Variables
   - Add all variables from `.env`:
     ```
     GEMINI_API_KEY=your_key
     GITHUB_APP_ID=123456
     GITHUB_PRIVATE_KEY_PATH=/app/private-key.pem
     GITHUB_WEBHOOK_SECRET=your_secret
     PORT=3000
     HOST=0.0.0.0
     ```

4. **Add private key**:
   - Create a file `private-key.pem` in your repo root (or use Railway's file storage)
   - Or paste the key content as an environment variable `GITHUB_PRIVATE_KEY` and modify code to read from env

5. **Deploy**:
   - Railway auto-detects Python projects
   - It will run `python app.py` automatically
   - Check the logs for the public URL

6. **Update GitHub App webhook**:
   - Copy Railway's public URL (e.g., `https://your-app.railway.app`)
   - Update webhook URL to: `https://your-app.railway.app/webhook`

**Pros:** Free tier, auto-deploy, easy setup
**Cons:** Free tier has limitations

---

## Option 2: Render

**Best for:** Simple, reliable hosting

### Steps:

1. **Sign up** at [render.com](https://render.com)

2. **Create a new Web Service**:
   - Connect your GitHub repository
   - Select "Web Service"

3. **Configure**:
   - **Name**: Ansieyes
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
   - **Plan**: Free (or paid for better performance)

4. **Add environment variables**:
   - Go to Environment section
   - Add all variables from `.env`

5. **Add private key**:
   - Option A: Store as environment variable `GITHUB_PRIVATE_KEY` (multiline)
   - Option B: Use Render's file system (create `private-key.pem`)

6. **Deploy**:
   - Render will build and deploy automatically
   - Get your public URL from the dashboard

7. **Update GitHub App webhook**:
   - URL: `https://your-app.onrender.com/webhook`

**Pros:** Free tier, automatic SSL, easy
**Cons:** Free tier spins down after inactivity

---

## Option 3: Heroku

**Best for:** Established platform with good documentation

### Steps:

1. **Install Heroku CLI**:
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku

   # Linux
   wget -qO- https://toolbelt.heroku.com/install.sh | sh
   ```

2. **Login**:
   ```bash
   heroku login
   ```

3. **Create app**:
   ```bash
   heroku create your-bot-name
   ```

4. **Set environment variables**:
   ```bash
   heroku config:set GEMINI_API_KEY=your_key
   heroku config:set GITHUB_APP_ID=123456
   heroku config:set GITHUB_WEBHOOK_SECRET=your_secret
   heroku config:set PORT=3000
   heroku config:set HOST=0.0.0.0
   ```

5. **Add private key**:
   ```bash
   # Option 1: Store as config var (base64 encoded)
   cat private-key.pem | base64 | heroku config:set GITHUB_PRIVATE_KEY_B64=-

   # Option 2: Use Heroku's file system (requires dyno restart)
   ```

6. **Deploy**:
   ```bash
   git push heroku main
   ```

7. **Update webhook URL**:
   - `https://your-bot-name.herokuapp.com/webhook`

**Pros:** Reliable, good docs, add-ons available
**Cons:** Paid plans required ($7+/month)

---

## Option 4: AWS EC2

**Best for:** Full control, production workloads

### Steps:

1. **Launch EC2 instance**:
   - Choose Ubuntu 22.04 LTS
   - t2.micro (free tier) or t3.small
   - Configure security group: Allow HTTP (80) and HTTPS (443)

2. **SSH into instance**:
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv git nginx
   ```

4. **Clone and setup**:
   ```bash
   git clone your-repo-url
   cd test_ai
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Create systemd service** (`/etc/systemd/system/Ansieyes.service`):
   ```ini
   [Unit]
   Description=GitHub PR Review Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/test_ai
   Environment="PATH=/home/ubuntu/test_ai/venv/bin"
   ExecStart=/home/ubuntu/test_ai/venv/bin/python app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. **Start service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable Ansieyes
   sudo systemctl start Ansieyes
   ```

7. **Setup Nginx reverse proxy** (`/etc/nginx/sites-available/Ansieyes`):
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

8. **Enable site and restart**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/Ansieyes /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

9. **Setup SSL with Let's Encrypt**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

**Pros:** Full control, scalable, production-ready
**Cons:** Requires server management knowledge

---

## Option 5: Docker Deployment

**Best for:** Containerized deployments, Kubernetes

### Using Docker Compose:

1. **Update docker-compose.yml** with your environment variables

2. **Run**:
   ```bash
   docker-compose up -d
   ```

### Using Docker directly:

1. **Build image**:
   ```bash
   docker build -t Ansieyes .
   ```

2. **Run container**:
   ```bash
   docker run -d \
     --name Ansieyes \
     -p 3000:3000 \
     -e GEMINI_API_KEY=your_key \
     -e GITHUB_APP_ID=123456 \
     -e GITHUB_WEBHOOK_SECRET=your_secret \
     -e GITHUB_PRIVATE_KEY_PATH=/app/private-key.pem \
     -v $(pwd)/private-key.pem:/app/private-key.pem:ro \
     Ansieyes
   ```

### Deploy to cloud with Docker:

- **Fly.io**: `flyctl launch` and follow prompts
- **Google Cloud Run**: `gcloud run deploy`
- **AWS ECS/Fargate**: Use AWS console or CLI
- **Azure Container Instances**: Use Azure CLI

---

## Option 6: GitHub Actions (Serverless)

**Best for:** Free hosting for public repositories

### Create `.github/workflows/webhook-handler.yml`:

```yaml
name: PR Review Bot

on:
  repository_dispatch:
    types: [pr-review]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Review PR
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python review_pr.py ${{ github.event.client_payload.pr_number }}
```

**Note:** This requires a separate webhook receiver service or GitHub App that triggers the workflow.

---

## Option 7: DigitalOcean App Platform

**Best for:** Simple PaaS with good performance

### Steps:

1. **Sign up** at [digitalocean.com](https://digitalocean.com)

2. **Create App**:
   - Connect GitHub repository
   - Select "Web Service"

3. **Configure**:
   - **Run Command**: `python app.py`
   - **Environment Variables**: Add all from `.env`
   - **Plan**: Basic ($5/month) or Pro

4. **Deploy**:
   - DigitalOcean handles the rest
   - Get your URL: `https://your-app.ondigitalocean.app`

---

## Important Considerations

### 1. Private Key Storage

**Best Practice:** Store private key as environment variable (base64 encoded) or use secrets management:

```python
# Modify app.py to support base64 encoded key
import base64
if os.getenv('GITHUB_PRIVATE_KEY_B64'):
    private_key = base64.b64decode(os.getenv('GITHUB_PRIVATE_KEY_B64')).decode()
else:
    with open(GITHUB_PRIVATE_KEY_PATH, 'r') as f:
        private_key = f.read()
```

### 2. Webhook URL Requirements

- Must be HTTPS (except localhost)
- Must be publicly accessible
- Should verify webhook signatures

### 3. Monitoring

Add health checks and monitoring:
- Use `/health` endpoint
- Set up uptime monitoring (UptimeRobot, Pingdom)
- Monitor logs for errors

### 4. Scaling

- Most platforms auto-scale
- For high traffic, consider:
  - Multiple instances behind load balancer
  - Queue system (Redis/RabbitMQ)
  - Rate limiting

---

## Recommended Setup for Production

1. **Start with Railway or Render** (free tier)
2. **Monitor usage** and upgrade if needed
3. **Add monitoring** (health checks, logs)
4. **Set up CI/CD** for automatic deployments
5. **Use secrets management** for sensitive data

---

## Quick Deploy Commands

### Railway:
```bash
railway login
railway init
railway up
```

### Render:
- Use web interface (recommended)

### Heroku:
```bash
heroku create
git push heroku main
```

### Docker:
```bash
docker-compose up -d
```

---

## Need Help?

- Check platform-specific documentation
- Review error logs in your hosting dashboard
- Test locally first with ngrok
- Verify environment variables are set correctly

