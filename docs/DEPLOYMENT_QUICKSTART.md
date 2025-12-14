# Quick Deployment Guide

## 🚀 Fastest Way: Railway (5 minutes)

1. **Sign up** at [railway.app](https://railway.app) (free tier available)

2. **Create new project** → Deploy from GitHub repo

3. **Add environment variables**:
   ```
   GEMINI_API_KEY=your_key
   GITHUB_APP_ID=123456
   GITHUB_PRIVATE_KEY_B64=<encoded_key>
   GITHUB_WEBHOOK_SECRET=your_secret
   PORT=3000
   HOST=0.0.0.0
   ```

4. **Encode your private key**:
   ```bash
   ./scripts/encode_key.sh private-key.pem
   ```
   Copy the output and paste as `GITHUB_PRIVATE_KEY_B64`

5. **Deploy** - Railway auto-deploys!

6. **Get your URL** from Railway dashboard (e.g., `https://your-app.railway.app`)

7. **Update GitHub App webhook** → `https://your-app.railway.app/webhook`

**Done!** 🎉

---

## 🎯 Alternative: Render (Similar to Railway)

1. Sign up at [render.com](https://render.com)
2. New → Web Service → Connect GitHub repo
3. Build: `pip install -r requirements.txt`
4. Start: `python app.py`
5. Add environment variables (same as Railway)
6. Deploy!

---

## 🐳 Docker Deployment

```bash
# Build
docker build -t Ansieyes .

# Run
docker run -d \
  -p 3000:3000 \
  -e GEMINI_API_KEY=your_key \
  -e GITHUB_APP_ID=123456 \
  -e GITHUB_PRIVATE_KEY_B64=$(cat private-key.pem | base64 -w 0) \
  -e GITHUB_WEBHOOK_SECRET=your_secret \
  Ansieyes
```

---

## 📋 Environment Variables Checklist

Required:
- ✅ `GEMINI_API_KEY` - From Google AI Studio
- ✅ `GITHUB_APP_ID` - From GitHub App settings
- ✅ `GITHUB_PRIVATE_KEY_B64` OR `GITHUB_PRIVATE_KEY_PATH` - Your app's private key
- ✅ `GITHUB_WEBHOOK_SECRET` - Your webhook secret

Optional:
- `PORT` - Default: 3000
- `HOST` - Default: 0.0.0.0

---

## 🔧 Private Key Setup

**Option 1: Base64 Encoded (Recommended for cloud)**
```bash
./scripts/encode_key.sh private-key.pem
# Use output as GITHUB_PRIVATE_KEY_B64
```

**Option 2: File Path (For local/dev)**
```bash
# Set GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
```

---

## ✅ Verify Deployment

1. Check health: `curl https://your-app-url/health`
2. Should return: `{"status": "healthy", "service": "github-pr-review-bot"}`
3. Create a test PR
4. Bot should comment automatically!

---

## 📚 Full Documentation

- **Detailed hosting options**: See [HOSTING.md](HOSTING.md)
- **Setup guide**: See [README.md](README.md)
- **Quick start**: See [QUICKSTART.md](QUICKSTART.md)

---

## 🆘 Troubleshooting

**Bot not responding?**
- Check webhook deliveries in GitHub App settings
- Verify environment variables are set
- Check application logs

**Authentication errors?**
- Verify `GITHUB_APP_ID` is correct
- Check private key is properly encoded/accessible
- Ensure app is installed on repository

**Gemini API errors?**
- Verify `GEMINI_API_KEY` is valid
- Check API quota/limits

