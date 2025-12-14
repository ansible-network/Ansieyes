# Local Testing Guide

Yes, you can test the app locally! Here are several ways to do it:

## Quick Start

### 1. Setup Environment

```bash
# Run the setup script
./setup.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required for basic testing
GEMINI_API_KEY=your_gemini_api_key_here

# Required for full webhook testing
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/path/to/your-private-key.pem
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# Server configuration
PORT=3000
HOST=0.0.0.0
```

**Note:** For basic testing (without GitHub webhooks), you only need `GEMINI_API_KEY`.

---

## Testing Methods

### Method 1: Test Gemini API Connection (No GitHub Required)

This tests the core functionality without needing GitHub credentials:

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test script
python test_bot.py
```

This will:

- ✅ Test Gemini API connection
- ✅ Test PR review generation with mock data
- ✅ Verify the review logic works

**What you need:** Only `GEMINI_API_KEY` in your `.env` file.

---

### Method 2: Test Flask App Locally

Test the Flask server and health endpoint:

```bash
# Activate virtual environment
source venv/bin/activate

# Start the Flask app
python app.py
```

The app will start on `http://localhost:3000`.

**Test the health endpoint:**

```bash
# In another terminal
curl http://localhost:3000/health
```

Expected response:

```json
{ "status": "healthy", "service": "github-pr-review-bot" }
```

**What you need:** `GEMINI_API_KEY` (required to start the app).

---

### Method 3: Test with Docker

Run the app in a Docker container:

```bash
# Build and run with docker-compose
docker-compose up --build

# Or build and run manually
docker build -t Ansieyes .
docker run -p 3000:3000 --env-file .env Ansieyes
```

**What you need:** All environment variables in `.env` file.

---

### Method 4: Full Webhook Testing with ngrok

To test the complete webhook flow (GitHub → Your Bot):

1. **Start the bot:**

   ```bash
   source venv/bin/activate
   python app.py
   ```

2. **In another terminal, start ngrok:**

   ```bash
   ngrok http 3000
   ```

3. **Copy the HTTPS URL** (e.g., `https://abc123.ngrok.io`)

4. **Update GitHub App webhook URL:**

   - Go to your GitHub App settings
   - Update the webhook URL to: `https://abc123.ngrok.io/webhook`

5. **Test it:**
   - Create a test PR in your repository
   - The bot should automatically review it!

**What you need:** All environment variables configured, including GitHub App credentials.

---

## Testing Checklist

### ✅ Basic Functionality Test

- [ ] Run `python test_bot.py` - Should pass Gemini connection test
- [ ] Run `python app.py` - Should start without errors
- [ ] Test `/health` endpoint - Should return healthy status

### ✅ Full Integration Test

- [ ] Configure all environment variables
- [ ] Start bot with `python app.py`
- [ ] Expose with ngrok
- [ ] Update GitHub App webhook URL
- [ ] Create a test PR
- [ ] Verify bot posts review comments

---

## Troubleshooting

### "GEMINI_API_KEY not set"

- Make sure you have a `.env` file with `GEMINI_API_KEY=your_key`
- Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

### "Port 3000 already in use"

- Change the port in `.env`: `PORT=3001`
- Or stop the process using port 3000

### "Module not found" errors

- Make sure virtual environment is activated: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Webhook not receiving events

- Check ngrok is running and URL is correct
- Verify webhook URL in GitHub App settings matches ngrok URL
- Check GitHub App webhook deliveries for errors
- Verify `GITHUB_WEBHOOK_SECRET` matches your GitHub App secret

### Authentication errors

- Verify `GITHUB_APP_ID` is correct
- Check `GITHUB_PRIVATE_KEY_PATH` points to valid .pem file
- Ensure the GitHub App is installed on the repository

---

## Quick Test Commands

```bash
# Test Gemini API only
python test_bot.py

# Start Flask server
python app.py

# Test health endpoint (in another terminal)
curl http://localhost:3000/health

# Run with Docker
docker-compose up

# Run with ngrok (after starting app)
ngrok http 3000
```

---

## Next Steps

Once local testing works:

- Deploy to production (see `DEPLOYMENT_QUICKSTART.md`)
- Customize review prompts in `pr_reviewer.py`
- Add more features as needed!
