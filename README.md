# 🔍 Jinkies - Raspberry Pi Discord Bot

A production-grade Discord bot for Raspberry Pi that monitors your applications, manages alerts, and creates GitHub PRs/issues automatically.

**Built specifically for Raspberry Pi 3B+, 4, and 5.**

## ✨ Features

- 🚨 **Real-time Alerts** - Get instant notifications in Discord when errors occur
- 📋 **Alert Management** - View, acknowledge, and track all alerts
- 🔧 **GitHub Integration** - Create PRs and issues directly from Discord
- �� **Secure** - Role-based access control for Discord commands
- 💾 **Persistent Storage** - SQLite database for all alerts
- 🐍 **Django Integration** - Works seamlessly with Django applications

## 💬 Discord Commands

- `/alerts` - List recent alerts
- `/alert <id>` - View detailed alert information
- `/ack <id>` - Acknowledge an alert
- `/create-pr <id>` - Create a GitHub PR from an alert
- `/create-issue <id>` - Create a GitHub issue from an alert

## 🚀 One-Command Setup

Run this single command to set up everything:

```bash
git clone https://github.com/roddy-devs/jinkies.git
cd jinkies
./setup-pi.sh
```

That's it! The script will:
1. ✅ Install all dependencies
2. ✅ Create virtual environment
3. ✅ Guide you through Discord/GitHub configuration
4. ✅ Set up systemd service for auto-start
5. ✅ Start the bot

## 📋 Prerequisites

Before running `setup-pi.sh`, you need:

### 1. Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Click "New Application" → Name it "Jinkies"
3. Go to "Bot" tab → Click "Add Bot"
4. Enable these intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
5. Copy the bot token

### 2. Discord Channel IDs

1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click on your alert channel → Copy ID
3. Right-click on your log channel → Copy ID (can be the same)

### 3. GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select `repo` scope
4. Copy the token

### 4. Invite Bot to Discord Server

1. In Discord Developer Portal, go to OAuth2 → URL Generator
2. Select scopes: `bot`, `applications.commands`
3. Select permissions:
   - Send Messages
   - Embed Links
   - Use Slash Commands
4. Copy the URL and open in browser
5. Select your server and authorize

## 🏗️ Architecture

```
Django App (your application)
         ↓
    Alert Handler (in your Django app)
         ↓
  Webhook Endpoint: /jinkies/alert/
         ↓
  Discord Webhook
         ↓
  Jinkies Bot (Raspberry Pi) → Discord Channel
```

## 🔧 Django Integration

### Step 1: Copy Webhook App

```bash
cp -r django_webhook/jinkies_webhook /path/to/your/django/project/
```

### Step 2: Update Django Settings

Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... your other apps
    'jinkies_webhook',
]
```

Add to `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... your other URLs
    path('jinkies/', include('jinkies_webhook.urls')),
]
```

### Step 3: Configure Django Logging

See `examples/django_logging_config.py` for the complete logging handler.

Quick version:
```python
# In your Django settings.py
JINKIES_WEBHOOK_URL = "http://localhost:8000/jinkies/alert/"

# Add JinkiesAlertHandler to your logging configuration
```

### Step 4: Create Discord Webhook

1. In Discord channel settings → Integrations
2. Create Webhook
3. Copy webhook URL
4. Set as environment variable: `DISCORD_WEBHOOK_URL`

### Step 5: Test

```bash
curl -X POST http://localhost:8000/jinkies/alert/ \
  -H "Content-Type: application/json" \
  -d '{"service_name": "test", "exception_type": "TestError", "error_message": "Test", "severity": "ERROR"}'
```

## 🔌 SSH Tunnel (Optional)

If your Django app is on a remote server:

```bash
# On Raspberry Pi, create tunnel to Django server
ssh -N -L 8080:localhost:8000 user@django-server

# Or use autossh for persistent connection
sudo apt install autossh
autossh -M 0 -N -L 8080:localhost:8000 user@django-server
```

Then set `JINKIES_WEBHOOK_URL=http://localhost:8080/jinkies/alert/` in Django.

## 🛠️ Managing the Bot

### View Status
```bash
sudo systemctl status jinkies
```

### View Logs
```bash
sudo journalctl -u jinkies -f
```

### Restart Bot
```bash
sudo systemctl restart jinkies
```

### Stop Bot
```bash
sudo systemctl stop jinkies
```

### Update Bot
```bash
cd ~/jinkies
git pull
source venv/bin/activate
pip install -r requirements-pi.txt
sudo systemctl restart jinkies
```

## 🔧 Manual Configuration

If you prefer to configure manually instead of using `setup-pi.sh`:

1. Install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-pi.txt
   ```

2. Copy and edit configuration:
   ```bash
   cp .env.example .env
   nano .env
   ```

3. Configure these variables:
   - `DISCORD_BOT_TOKEN` - Your Discord bot token
   - `DISCORD_ALERT_CHANNEL_ID` - Channel ID for alerts
   - `DISCORD_LOG_CHANNEL_ID` - Channel ID for logs
   - `GITHUB_PRIVATE_KEY` - Your GitHub token
   - `GITHUB_REPO_OWNER` - Your GitHub username
   - `GITHUB_REPO_NAME` - Your repository name

4. Run the bot:
   ```bash
   python3 run.py
   ```

## 📊 System Requirements

- **Raspberry Pi 3B+ or newer** (1GB+ RAM)
- **Raspberry Pi OS** (Bullseye or newer)
- **Python 3.9+**
- **~500MB disk space**
- **Internet connection**

## 💰 Cost

- **Raspberry Pi 4 (2GB)**: $45 one-time
- **Power consumption**: ~$1/month
- **Total ongoing cost**: **$1/month**

Compare to AWS: $15-70/month in CloudWatch + EC2 costs!

## 🆘 Troubleshooting

### Bot Won't Start

Check logs:
```bash
sudo journalctl -u jinkies -n 50
```

Or run manually to see errors:
```bash
cd ~/jinkies
source venv/bin/activate
python3 run.py
```

### Commands Not Showing in Discord

The bot needs to sync commands on first start. Wait 1-2 minutes after starting, then restart Discord.

### "Permission Denied" Errors

Make sure your Discord role is listed in `DISCORD_ALLOWED_ROLES` in `.env`

### Out of Memory

Increase swap:
```bash
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

## 📚 More Information

- `RASPBERRY_PI.md` - Detailed Raspberry Pi setup guide
- `django_webhook/README.md` - Django integration details
- `examples/django_logging_config.py` - Logging configuration example

## 📝 License

MIT License - See LICENSE file

## 🙏 Support

For issues or questions, create an issue on GitHub.
