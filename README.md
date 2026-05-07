# Ansieyes - AI-Powered GitHub Bot

AI bot for PR reviews and issue triage using Google's Gemini AI.

## Quick Start

```bash
./setup-ansieyes.sh
```

**That's it!** The script handles everything.

## Usage

Comment on GitHub:
- **`/ansieyes_prreview`** - Review a PR
- **`/ansieyes_triage`** - Analyze an issue (includes prompt-injection check)
- **`/ansieyes_triage_force`** - Same as triage but skips prompt-injection screening

**Important**: Exact match only, no extra text!

## Full Documentation

**→ See [GUIDE.md](GUIDE.md) for complete setup and usage instructions**

## Features

- 🤖 AI PR code reviews
- 📚 Two-pass issue analysis (Librarian + Surgeon)
- 🔍 Duplicate detection
- 🏷️ Auto-labeling
- ✅ Smart validation

## Requirements

- Python 3.8+, Node.js, Git
- Gemini API key
- GitHub App

## Support

- Full Guide: **[GUIDE.md](GUIDE.md)**
- Issues: Open a GitHub issue
- License: MIT
