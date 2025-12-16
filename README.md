# Ansieyes - GitHub PR Review Bot with Gemini API

An automated GitHub bot that reviews pull requests using Google's Gemini AI and posts comments directly on PRs.
### NOTE - Documentation and configuration structure is gerated by Cursor using the composer-1 model.

## Features

- 🤖 Automated PR reviews using Gemini AI
- 📝 Detailed code review comments
- 🔍 File-specific and inline comments
- ⚙️ GitHub Actions workflow monitoring and analysis
- ✅ Comments on workflow success/failure with AI insights
- 🔐 Secure webhook signature verification
- 🚀 Easy deployment setup

## Prerequisites

- Python 3.8+
- A GitHub App (see setup instructions below)
- Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a GitHub App

1. Go to your GitHub organization settings
2. Navigate to **Developer settings** > **GitHub Apps**
3. Click **New GitHub App**
4. Configure the app:
   - **Name**: Your bot name (e.g., "PR Review Bot")
   - **Homepage URL**: Your bot's homepage
   - **Webhook URL**: `https://your-domain.com/webhook`
   - **Webhook secret**: Generate a secure random string
   - **Permissions**:
     - **Pull requests**: Read & Write
     - **Contents**: Read
     - **Metadata**: Read-only
     - **Actions**: Read (for workflow run monitoring)
   - **Subscribe to events**:
     - Pull requests
     - Workflow runs (for GitHub Actions monitoring)
5. After creating, note down:
   - **App ID**
   - Generate and download a **Private Key** (.pem file)

### 3. Install the GitHub App

1. Go to your GitHub App settings
2. Click **Install App**
3. Select the repositories or organization where you want the bot to work
4. Note the **Installation ID** (you can get this from the webhook payload)

### 4. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/path/to/your-private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Server Configuration
PORT=3000
HOST=0.0.0.0
```

### 5. Run the Bot

```bash
python app.py
```

The bot will start listening on `http://0.0.0.0:3000` for webhook events.

## Deployment

### Using ngrok for Local Testing

1. Install ngrok: `brew install ngrok` or download from [ngrok.com](https://ngrok.com)
2. Start the bot: `python app.py`
3. In another terminal: `ngrok http 3000`
4. Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`)
5. Update your GitHub App webhook URL to: `https://abc123.ngrok.io/webhook`

### Production Deployment

**📖 See [HOSTING.md](HOSTING.md) for detailed hosting instructions!**

**🚀 AWS Deployment? See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for complete AWS guide!**

Quick options:
- **AWS EC2/Fargate**: Full control, scalable - see `AWS_DEPLOYMENT.md` and `aws-deploy.sh`
- **Railway**: Free tier, easy setup - see `railway.json`
- **Render**: Free tier, simple deployment - see `render.yaml`
- **Heroku**: Paid, reliable - use included `Procfile`
- **Docker**: Use included `Dockerfile` and `docker-compose.yml`

**Important:** For cloud hosting, encode your private key:
```bash
./scripts/encode_key.sh private-key.pem
```
Then use `GITHUB_PRIVATE_KEY_B64` environment variable instead of file path.

## How It Works

1. **Webhook Reception**: GitHub sends webhook events when PRs are opened/updated
2. **Signature Verification**: The bot verifies the webhook signature for security
3. **PR Analysis**: The bot fetches PR details and file changes
4. **AI Review**: Gemini AI analyzes the code changes and generates review comments
5. **Comment Posting**: The bot posts review comments directly on the PR

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /webhook` - GitHub webhook endpoint

## Webhook Events

The bot listens for these GitHub events:
- `pull_request` (actions: `opened`, `synchronize`, `reopened`)
- `workflow_run` (action: `completed`) - Monitors GitHub Actions workflows and comments on success/failure

## Customization

### Modify Review Prompts

Edit `pr_reviewer.py` to customize the review prompts sent to Gemini:

```python
def _build_review_prompt(self, title: str, body: str, file_changes: List[Dict]) -> str:
    # Customize your prompt here
    ...
```

### Adjust Review Criteria

Modify the prompt in `_build_review_prompt()` to focus on:
- Security vulnerabilities
- Performance issues
- Code style and best practices
- Test coverage
- Documentation

## Troubleshooting

### Bot not responding to PRs

1. Check webhook delivery in GitHub App settings
2. Verify webhook URL is accessible
3. Check logs for errors
4. Verify environment variables are set correctly

### Authentication errors

1. Verify `GITHUB_APP_ID` is correct
2. Check `GITHUB_PRIVATE_KEY_PATH` points to valid .pem file
3. Ensure the app is installed on the repository

### Gemini API errors

1. Verify `GEMINI_API_KEY` is valid
2. Check API quota/limits
3. Review error logs for specific issues

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or PR.

