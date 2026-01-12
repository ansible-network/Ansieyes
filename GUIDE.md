# Ansieyes - Complete Setup & Usage Guide

**THE ONLY GUIDE YOU NEED** - Everything from installation to usage in one place.

---

## Table of Contents
1. [Quick Overview](#quick-overview)
2. [Automated Setup](#automated-setup)
3. [Manual Setup](#manual-setup)
4. [Usage](#usage)
5. [Troubleshooting](#troubleshooting)

---

## Quick Overview

**What is Ansieyes?**
- AI-powered GitHub bot for PR reviews and issue triage
- Uses Google's Gemini AI
- Mention-based triggers: `\ansieyes_prreview` and `\ansieyes_triage`

**What you need:**
- Python 3.8+, Node.js, Git
- Gemini API key: https://makersuite.google.com/app/apikey
- GitHub account with admin access

**Time to setup:** 5-10 minutes with automated script

**Where to run:**
- **Development**: Your laptop + ngrok (for testing)
- **Production**: EC2/VPS/server with public IP (for 24/7 operation)

---

## Automated Setup

### One-Click Installation

```bash
cd Ansieyes
./setup-ansieyes.sh
```

The script will:
1. ✅ Check and install dependencies (Node.js, repomix, Python packages)
2. ✅ Clone and setup AI-Issue-Triage
3. ✅ Guide you through GitHub App creation
4. ✅ Configure environment variables
5. ✅ Test the setup
6. ✅ (Optional) Deploy to AWS

**Just follow the prompts - that's it!**

---

## Manual Setup

### Step 1: Install Dependencies

```bash
# Install Node.js (if not installed)
# macOS: brew install node
# Linux: sudo apt install nodejs npm

# Install repomix (required for issue triage)
npm install -g repomix

# Verify
repomix --version
node --version
python3 --version
```

### Step 2: Clone and Setup AI-Issue-Triage

```bash
# Clone AI-Issue-Triage
cd ~  # or your preferred directory
git clone https://github.com/shvenkat-rh/AI-Issue-Triage.git
cd AI-Issue-Triage
git checkout feature/pr-analyzer

# Install dependencies
pip install -r requirements.txt

# Note this path - you'll need it
pwd  # Example: /Users/username/AI-Issue-Triage
```

### Step 3: Install Ansieyes Dependencies

```bash
cd /path/to/Ansieyes
pip install -r requirements.txt
```

### Step 4: Create GitHub App

1. Go to: **https://github.com/settings/apps**
2. Click **"New GitHub App"**

#### App Configuration:

**Basic Information:**
- **GitHub App name**: `ansieyes-bot` (or your choice)
- **Homepage URL**: `https://github.com/your-username/Ansieyes`
- **Webhook URL**: `https://your-domain.com/webhook`
  - For testing: Use ngrok URL (see Step 6)
- **Webhook secret**: Generate strong random string (save it!)

**Repository Permissions:**
- **Contents**: Read-only
- **Issues**: Read and write ✓
- **Pull requests**: Read and write ✓
- **Metadata**: Read-only (auto-selected)
- **Actions**: Read-only

**Subscribe to Events:**
- ☑ Issue comment (REQUIRED)
- ☑ Pull request
- ☑ Workflow run

#### After Creation:
1. **Save the App ID** (you'll see it at top of settings)
2. Click **"Generate a private key"** (downloads .pem file)
3. Click **"Install App"** → Select your repositories

### Step 5: Configure Environment

```bash
cd /path/to/Ansieyes
cp env_example.txt .env
```

Edit `.env` with your values:

```env
# Get from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_gemini_api_key

# From GitHub App settings page
GITHUB_APP_ID=123456

# Full path to the .pem file you downloaded
GITHUB_PRIVATE_KEY_PATH=/absolute/path/to/your-app.private-key.pem

# The webhook secret you created
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Path to AI-Issue-Triage from Step 2
AI_TRIAGE_PATH=/Users/username/AI-Issue-Triage

# Server settings (defaults are fine)
PORT=3000
HOST=0.0.0.0
```

**Important**: Use absolute paths, not relative paths!

### Step 6: Test Locally with ngrok

#### Install ngrok

```bash
# macOS
brew install ngrok

# Or download from https://ngrok.com/download
```

#### Start Everything

**Terminal 1 - Start Ansieyes:**
```bash
cd /path/to/Ansieyes
python3 app.py
```

You should see:
```
INFO:__main__:Starting GitHub PR Review Bot on 0.0.0.0:3000
```

**Terminal 2 - Start ngrok:**
```bash
ngrok http 3000
```

You'll see:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:3000
```

**Copy the ngrok URL** (e.g., `https://abc123.ngrok.io`)

#### Update GitHub App Webhook

1. Go to your GitHub App settings
2. Edit webhook URL to: `https://abc123.ngrok.io/webhook`
3. Save changes

### Step 7: Test the Bot

#### Test PR Review:
1. Go to a test repository where the app is installed
2. Create a test pull request
3. Add a comment: `\ansieyes_prreview`
4. Bot should respond with code review (~10-30 seconds)

#### Test Issue Triage:
1. Create a test issue
2. Add a comment: `\ansieyes_triage`
3. Bot should respond with analysis (~30-70 seconds)

#### Test Validation:
1. Try `\ansieyes_triage` on a PR → Should get error message ✓
2. Try `\ansieyes_prreview` on an issue → Should get error message ✓

**If all tests pass, you're ready!**

---

## Usage

### Commands

| Command | Use On | What It Does | Time |
|---------|--------|--------------|------|
| `\ansieyes_prreview` | Pull Requests ONLY | AI code review | 10-30s |
| `\ansieyes_triage` | Issues ONLY | Two-pass analysis + labeling | 30-70s |

### ⚠️ IMPORTANT: Exact Match Required

Commands must be **exact** with **no extra text**:

✅ **Correct:**
```
\ansieyes_triage
```

❌ **Wrong:**
```
\ansieyes_triage please analyze
Hey \ansieyes_triage
\ansieyes_triage!
@ab_triage (missing underscore)
```

### What Each Command Does

#### `\ansieyes_prreview` - PR Code Review

**Uses**: Direct Gemini API (NOT AI-Issue-Triage)

**What it does:**
1. Fetches all changed files from PR
2. Analyzes code with Gemini AI
3. Identifies bugs, security issues, code quality problems
4. Suggests improvements and best practices
5. Posts detailed review comment

**Example output:**
```markdown
## 🤖 AI Code Review (Powered by Gemini)

### Overall Assessment
This PR adds user authentication...

### Strengths
- Well-structured code
- Good test coverage

### Issues Found
- Security: API keys hardcoded
- Performance: N+1 query in loop

### Suggestions
1. Move secrets to environment variables
2. Optimize database queries with eager loading
...
```

#### `\ansieyes_triage` - Issue Analysis

**Uses**: AI-Issue-Triage package with two-pass architecture

**What it does:**
1. **Clones your repository** to fetch:
   - `triage.config.json` (if exists)
   - `.omit-triage` (if exists)
2. **Duplicate Check**: Compares with existing open issues
3. **Librarian Pass**: Identifies relevant files from codebase
4. **Surgeon Pass**: Deep analysis of identified code
5. **Auto-labeling**: Applies type and severity labels
6. Posts comprehensive analysis

**Example output:**
```markdown
## 🤖 AI Two-Pass Issue Triage

### 📚 Pass 1: Librarian (File Identification)
Identified 5 relevant file(s):
1. src/auth/login.py
2. src/middleware/auth.py
...

### 🔬 Pass 2: Surgeon (Deep Analysis)
Type: BUG
Severity: HIGH
Confidence: 85%

#### Summary
The login failure is caused by...

#### Root Cause
> The authentication middleware is not properly...

#### Proposed Solutions
1. Update the middleware to handle edge cases...
```

### Repository Configuration (Optional)

You can add these files to **your repository root** to customize triage:

#### `triage.config.json`

```json
{
  "repository": {
    "url": "https://github.com/your-org/your-repo.git",
    "description": "Your repository description"
  },
  "omit_directories": [
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".git"
  ]
}
```

#### `.omit-triage`

```
# Directories to exclude from analysis
node_modules
vendor
dist
build
.git
__pycache__
.venv
```

**Note**: Bot automatically fetches these from your repo when triage runs. If they don't exist, defaults are used.

### Auto-Applied Labels

When triage completes successfully, these labels are automatically created (if they don't exist) and added:

**Type Labels (from AI-Issue-Triage):**
- `Type : Bug` 🐛
- `Type : Enhancement` ✨
- `Type : Feature Request` 🚀

**Severity Labels (from AI-Issue-Triage):**
- `Severity : Critical` 🔴
- `Severity : High` 🟠
- `Severity : Medium` 🟡
- `Severity : Low` 🟢

**Status Labels:**
- `ai-triaged` - Analysis completed
- `duplicate` - Duplicate issue detected
- `Prompt injection blocked` - High/critical risk prompt injection attempt detected

**Note:** Labels are automatically created in your repository with appropriate colors if they don't already exist.

---

## Deployment to Production

### Where to Run the Setup Script

**For Development/Testing:**
- Run on your **local machine** (laptop/desktop)
- Use ngrok for webhook URL
- Test everything locally

**For Production:**
- Run on your **production server** (EC2, VPS, etc.)
- Use server's public IP or domain for webhook URL
- Bot runs 24/7 on the server

### Option 1: AWS EC2 (Recommended for Production)

**Step-by-step for EC2:**

1. **Launch EC2 instance** (Ubuntu 22.04 recommended, t3.small or larger)

2. **SSH into EC2**:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. **Clone and setup Ansieyes ON THE EC2 INSTANCE**:
```bash
# On EC2 instance
git clone <ansieyes-repo-url>
cd Ansieyes
./setup-ansieyes.sh
```

4. **Script will install everything on EC2**:
   - Python dependencies
   - Node.js and repomix
   - AI-Issue-Triage
   - Configure environment

5. **Get your EC2 webhook URL**:

   **Option A: Use EC2 Public IP (Quick)**
   ```bash
   # On EC2, get your public IP
   curl ifconfig.me
   # Example output: 54.123.45.67
   
   # Your webhook URL is:
   # http://54.123.45.67:3000/webhook
   ```
   
   **Option B: Use EC2 Public DNS (Better)**
   ```bash
   # Find in AWS Console → EC2 → Instance → Public IPv4 DNS
   # Example: ec2-54-123-45-67.compute-1.amazonaws.com
   
   # Your webhook URL is:
   # http://ec2-54-123-45-67.compute-1.amazonaws.com:3000/webhook
   ```
   
   **Option C: Use Elastic IP + Domain (Best for Production)**
   ```bash
   # 1. In AWS Console, allocate Elastic IP
   # 2. Associate it with your EC2 instance
   # 3. Point your domain to the Elastic IP (Route53 or your DNS)
   # Example: ansieyes.yourdomain.com → 54.123.45.67
   
   # Your webhook URL is:
   # https://ansieyes.yourdomain.com/webhook (with SSL)
   ```

6. **Configure GitHub webhook**:
   - Go to your GitHub App settings
   - Set Webhook URL to one of the URLs above
   - For Option C with domain, set up nginx with SSL (see below)

7. **Important: Open port 3000 in EC2 Security Group**:
   ```
   AWS Console → EC2 → Security Groups → Edit inbound rules
   Add rule:
   - Type: Custom TCP
   - Port: 3000
   - Source: 0.0.0.0/0 (or restrict to GitHub IPs)
   ```

8. **Keep bot running**:
```bash
# Option A: Use screen
screen -S ansieyes
python3 app.py
# Press Ctrl+A then D to detach

# Option B: Use systemd (better)
sudo nano /etc/systemd/system/ansieyes.service
# (See service file example below)
sudo systemctl start ansieyes
sudo systemctl enable ansieyes
```

**Systemd service file example**:
```ini
[Unit]
Description=Ansieyes GitHub Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Ansieyes
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/python3 /home/ubuntu/Ansieyes/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Security considerations for EC2:**
- Open port 3000 in Security Group
- Use HTTPS with reverse proxy (nginx/Apache)
- Keep credentials secure
- Regular updates

**Optional: Setup nginx with SSL (Recommended for production)**

```bash
# Install nginx and certbot
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/ansieyes

# Paste this:
server {
    server_name ansieyes.yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/ansieyes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate (free from Let's Encrypt)
sudo certbot --nginx -d ansieyes.yourdomain.com

# Now your webhook URL is:
# https://ansieyes.yourdomain.com/webhook
```

**After nginx setup:**
- Change Security Group: Close port 3000, open ports 80 and 443
- Bot still runs on port 3000 internally
- Nginx forwards requests from 443 → 3000
- GitHub webhooks use: `https://ansieyes.yourdomain.com/webhook`

For detailed AWS setup, see `docs/AWS_DEPLOYMENT.md` or use the setup script:

```bash
./setup-ansieyes.sh
# Choose option 3 (AWS Deployment)
```

### Option 2: Railway (Easy Free Tier)

```bash
# Install Railway CLI
npm install -g railway

# Login and initialize
railway login
railway init

# Deploy
railway up

# Set environment variables in Railway dashboard
# Add all variables from .env file
```

### Option 3: Render (Easy Free Tier)

1. Push code to GitHub
2. Go to https://render.com/
3. New Web Service → Connect your Ansieyes repo
4. Set environment variables (from .env)
5. Click "Create Web Service"

### Option 4: Docker

```bash
# Build and run with docker-compose
docker-compose up -d

# Or build manually
docker build -t ansieyes .
docker run -d -p 3000:3000 --env-file .env ansieyes
```

### Option 5: Traditional Server

```bash
# On your server
cd /opt/ansieyes
python3 app.py

# Or use systemd service
sudo systemctl start ansieyes
sudo systemctl enable ansieyes
```

---

## Troubleshooting

### Bot Not Responding to Commands

#### Check 1: Command Format
- Must be **exact match**: `\ansieyes_triage` or `\ansieyes_prreview`
- No extra text allowed
- No typos (check underscore placement)

#### Check 2: GitHub App Configuration
```bash
# Verify these in GitHub App settings:
- App is installed on the repository
- Permissions: Issues (RW), PRs (RW), Contents (R)
- Events: Issue comment is checked ✓
- Webhook URL is correct and accessible
```

**To check webhook deliveries:**
1. Go to GitHub App settings → Advanced tab
2. Click "Recent Deliveries"
3. Check for errors in delivery logs

#### Check 3: Bot Logs
```bash
# Check terminal where bot is running
# Look for errors in output

# Or if running as service
tail -f /var/log/ansieyes.log
```

### "AI-Issue-Triage not found" Error

```bash
# Verify the path exists
ls -la $AI_TRIAGE_PATH

# Update .env with correct ABSOLUTE path
nano .env
# Change AI_TRIAGE_PATH to correct value

# Restart bot
```

### "Repomix command not found" Error

```bash
# Install repomix globally
npm install -g repomix

# Verify installation
which repomix
repomix --version

# If still not found, add to PATH
export PATH=$PATH:/usr/local/bin
# Or wherever npm global packages are installed
```

### Wrong Trigger Error

**This is EXPECTED behavior!** The bot validates context:

**Example 1: Wrong command on PR**
```
User comments on PR: \ansieyes_triage

Bot responds:
⚠️ Invalid Command
\ansieyes_triage can only be used on issues.
For PR reviews, use \ansieyes_prreview instead.
```

**Solution**: Use `\ansieyes_prreview` on PRs

**Example 2: Wrong command on Issue**
```
User comments on Issue: \ansieyes_prreview

Bot responds:
⚠️ Invalid Command
\ansieyes_prreview can only be used on pull requests.
For issue triage, use \ansieyes_triage instead.
```

**Solution**: Use `\ansieyes_triage` on issues

### Gemini API Errors

```bash
# Test API key
python3 << EOF
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash-001')
response = model.generate_content('Hello')
print(response.text)
EOF

# If error:
# - Check API key is valid
# - Check API quota limits
# - Verify internet connectivity
```

### GitHub Authentication Errors

```bash
# Verify private key file exists
cat $GITHUB_PRIVATE_KEY_PATH

# Should show PEM format key starting with:
# -----BEGIN RSA PRIVATE KEY-----

# Check environment variables
env | grep GITHUB

# Verify App ID is correct (numbers only)
# Verify webhook secret matches what's in GitHub
```

### Bot Responds Slowly

**Normal timing:**
- PR Review: 10-30 seconds (depends on PR size)
- Issue Triage: 30-70 seconds (includes cloning, duplicate check, 2 passes)

**If much slower:**
1. Check network connectivity
2. Large repository? First clone takes longer
3. Gemini API rate limits? Check quota
4. Server resources? Check CPU/memory

### Configuration Files Not Found

**This is OK!** Bot will use defaults if files don't exist in your repo.

**To add configuration:**
1. Create `triage.config.json` in your repo root
2. Create `.omit-triage` in your repo root
3. Commit and push
4. Next `\ansieyes_triage` will use them

**To verify bot is fetching configs:**
Check bot logs for:
```
INFO:issue_triager:Cloning repository to fetch configuration files...
INFO:issue_triager:Repository cloned to /tmp/...
```

---

## Architecture

### System Architecture

```
GitHub Event
    │
    ├─── Webhook (POST /webhook)
    │
    ▼
Ansieyes (app.py)
    │
    ├─── Signature Verification
    │
    ├─── Event Type Detection
    │         │
    │         ├─── pull_request → pr_reviewer.py
    │         │                        │
    │         │                        └──→ Gemini API (direct)
    │         │
    │         └─── issue_comment → Check comment text
    │                                  │
    │                                  ├─── "\ansieyes_prreview" → pr_reviewer.py
    │                                  │                            │
    │                                  │                            └──→ Gemini API
    │                                  │
    │                                  └─── "\ansieyes_triage" → issue_triager.py
    │                                                             │
    │                                                             ├─── Clone repo (get configs)
    │                                                             │
    │                                                             ├─── AI-Issue-Triage/duplicate_check
    │                                                             │         └──→ Gemini API
    │                                                             │
    │                                                             ├─── AI-Issue-Triage/librarian (Pass 1)
    │                                                             │         └──→ Gemini API
    │                                                             │
    │                                                             └─── AI-Issue-Triage/analyzer (Pass 2)
    │                                                                       └──→ Gemini API
    │
    └─── Post Results to GitHub
```

### Key Points

1. **PR Review**: Uses `pr_reviewer.py` directly with Gemini (does NOT use AI-Issue-Triage)
2. **Issue Triage**: Uses AI-Issue-Triage package with two-pass architecture
3. **Config Fetching**: Bot clones repository to get `triage.config.json` and `.omit-triage`
4. **Exact Matching**: Commands must be exact (`\ansieyes_triage` or `\ansieyes_prreview` only)
5. **Context Validation**: Wrong command on wrong context shows helpful error

---

## FAQ

**Q: Can I change the trigger commands?**  
A: Yes, edit `app.py` around line 150. Change `'\ansieyes_triage'` and `'\ansieyes_prreview'` to your preferred strings.

**Q: Does PR review use AI-Issue-Triage?**  
A: No. Only issue triage uses AI-Issue-Triage. PR review uses Gemini directly.

**Q: What if I don't have triage.config.json in my repo?**  
A: That's fine! Bot will use defaults. Add config files for better results.

**Q: Can I use this on private repositories?**  
A: Yes, if your GitHub App is installed on those repositories.

**Q: How much does it cost?**  
A: Depends on usage. Gemini API pricing is per token. Rough estimate: $0.01-0.05 per triage.

**Q: Can I self-host this?**  
A: Yes! Run on any server with Python 3.8+ and Node.js.

**Q: Does it work with GitHub Enterprise?**  
A: Yes, but you need to configure your GitHub Enterprise API endpoint.

**Q: Can multiple people trigger analysis simultaneously?**  
A: Yes, bot handles concurrent requests.

**Q: What happens if analysis fails?**  
A: Bot posts an error message to the issue/PR with troubleshooting info.

**Q: Can I disable duplicate detection?**  
A: Yes, modify `issue_triager.py` to skip the duplicate check step.

---

## Environment Variables Reference

### Required Variables

```env
# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key
# Get from: https://makersuite.google.com/app/apikey

# GitHub App Configuration  
GITHUB_APP_ID=123456
# From GitHub App settings page

GITHUB_PRIVATE_KEY_PATH=/absolute/path/to/private-key.pem
# Full path to .pem file downloaded from GitHub

GITHUB_WEBHOOK_SECRET=your_webhook_secret
# The secret you created for your GitHub App

# AI-Issue-Triage Path
AI_TRIAGE_PATH=/absolute/path/to/AI-Issue-Triage
# Where you cloned AI-Issue-Triage repository
```

### Optional Variables

```env
# Server Configuration (defaults shown)
PORT=3000
HOST=0.0.0.0

# Alternative: Use base64 encoded private key (for cloud deployments)
GITHUB_PRIVATE_KEY_B64=your_base64_encoded_key
```

---

## Quick Reference

### Setup Commands

```bash
# Automated setup
./setup-ansieyes.sh

# Manual setup
npm install -g repomix
pip install -r requirements.txt
cp env_example.txt .env
# Edit .env, then:
python3 app.py
```

### Usage Commands

```
\ansieyes_triage      # Issue triage (exact match only)
\ansieyes_prreview    # PR review (exact match only)
```

### Testing Commands

```bash
# Start bot
python3 app.py

# Start ngrok (different terminal)
ngrok http 3000

# Check logs
tail -f app.log

# Test API key
python3 -c "import google.generativeai as genai; genai.configure(api_key='your_key'); print('OK')"
```

---

## Support

- **Issues**: Open a GitHub issue
- **Setup Help**: Re-run `./setup-ansieyes.sh`
- **AI-Issue-Triage**: https://github.com/shvenkat-rh/AI-Issue-Triage
- **Gemini API**: https://ai.google.dev/

---

## Summary

1. **Run**: `./setup-ansieyes.sh` (or follow manual steps)
2. **Create**: GitHub App with correct permissions
3. **Test**: Use `\ansieyes_triage` on issue, `\ansieyes_prreview` on PR
4. **Deploy**: To AWS/Railway/Render for production
5. **Customize**: Add `triage.config.json` to your repos

**That's it! You're ready to use Ansieyes.**

---

**Version**: 2.0  
**Last Updated**: January 2, 2026  
**License**: MIT


