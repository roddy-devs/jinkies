# Running Jinkies on Raspberry Pi

This guide covers setting up and running the Jinkies Discord bot on a Raspberry Pi without any AWS resources.

## Supported Models

- Raspberry Pi 3B+ (1GB RAM)
- Raspberry Pi 4 (2GB+ RAM recommended)
- Raspberry Pi 5
- Other ARM-based devices running Raspberry Pi OS

## Prerequisites

- Raspberry Pi running Raspberry Pi OS (Bookworm or Bullseye)
- Internet connection
- Discord account and bot token
- GitHub account and personal access token
- (Optional) Django application for alert integration

## Installation

### 1. Prepare Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install python3 python3-pip python3-venv git -y

# Create directory for Jinkies
mkdir -p ~/jinkies
cd ~/jinkies
```

### 2. Clone Repository

```bash
git clone https://github.com/roddy-devs/jinkies.git
cd jinkies
```

### 3. Create Virtual Environment

```bash
# Create virtual environment (recommended for Pi)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 4. Install Dependencies

For Raspberry Pi, use the minimal requirements file:

```bash
# Install minimal dependencies (no AWS/CloudWatch needed)
pip install -r requirements-pi.txt

# This installs:
# - discord.py (Discord bot)
# - PyGithub (GitHub integration)
# - aiohttp (HTTP client)
# - python-dateutil (date handling)
```

### 5. Configure Environment

```bash
# Copy example configuration
cp .env.example .env

# Edit configuration
nano .env
```

Set the following (CloudWatch variables can be left empty):

```bash
# Discord (Required)
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_ALERT_CHANNEL_ID=123456789012345678
DISCORD_LOG_CHANNEL_ID=123456789012345678
DISCORD_ALLOWED_ROLES=Admin,DevOps

# GitHub (Required for PR/issue creation)
GITHUB_PRIVATE_KEY=ghp_your_github_token
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo
DEFAULT_BASE_BRANCH=main

# AWS (NOT REQUIRED - leave empty)
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
CLOUDWATCH_LOG_GROUP_API=
CLOUDWATCH_LOG_GROUP_CLOUDFRONT=

# Environment
ENVIRONMENT_NAME=production
LOG_LEVEL=INFO
```

### 6. Test Run

```bash
# Activate virtual environment if not already activated
source venv/bin/activate

# Run the bot
python3 run.py
```

You should see:
```
INFO - Logged in as YourBot#1234
INFO - Bot is ready!
```

## Running as System Service

To keep the bot running automatically:

### 1. Create Service File

```bash
sudo nano /etc/systemd/system/jinkies.service
```

Add the following:

```ini
[Unit]
Description=Jinkies Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/jinkies/jinkies
EnvironmentFile=/home/pi/jinkies/jinkies/.env
ExecStart=/home/pi/jinkies/jinkies/venv/bin/python3 -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable jinkies

# Start service
sudo systemctl start jinkies

# Check status
sudo systemctl status jinkies

# View logs
sudo journalctl -u jinkies -f
```

## Django Integration via SSH Tunnel

If your Django app is on a remote server, use SSH tunneling:

### Setup SSH Tunnel

On your Raspberry Pi, create a persistent tunnel:

```bash
# Create tunnel to Django server
ssh -N -L 8080:localhost:8000 user@django-server &

# Or use autossh for persistent connection
sudo apt install autossh
autossh -M 0 -N -L 8080:localhost:8000 user@django-server
```

### Configure Django Logging

In your Django app, set the webhook URL to the tunneled address:

```python
# settings.py
JINKIES_WEBHOOK_URL = "http://localhost:8080/jinkies/alert/"
```

### Make SSH Tunnel Persistent

Create `/etc/systemd/system/jinkies-tunnel.service`:

```ini
[Unit]
Description=SSH Tunnel to Django Server for Jinkies
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
ExecStart=/usr/bin/autossh -M 0 -N -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -L 8080:localhost:8000 user@django-server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl enable jinkies-tunnel
sudo systemctl start jinkies-tunnel
```

## Performance Optimization for Raspberry Pi

### 1. Reduce Memory Usage

The bot is already optimized for low memory, but you can:

```bash
# In .env, reduce log buffer sizes
MAX_LOG_LINES=25
ALERT_RETENTION_DAYS=7
```

### 2. Use Swap (if needed)

```bash
# Increase swap size for Pi 3B+ (1GB RAM)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Change CONF_SWAPSIZE=2048
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 3. Disable CloudWatch Integration

Already disabled by default when using `requirements-pi.txt`!

## Monitoring

### Check Bot Status

```bash
# Service status
sudo systemctl status jinkies

# View real-time logs
sudo journalctl -u jinkies -f

# Check memory usage
ps aux | grep python
```

### Restart Bot

```bash
sudo systemctl restart jinkies
```

### Update Bot

```bash
cd ~/jinkies/jinkies
git pull
source venv/bin/activate
pip install -r requirements-pi.txt
sudo systemctl restart jinkies
```

## Troubleshooting

### Bot Won't Start

```bash
# Check logs
sudo journalctl -u jinkies -n 50

# Run manually to see errors
cd ~/jinkies/jinkies
source venv/bin/activate
python3 run.py
```

### Out of Memory

```bash
# Check memory
free -h

# Increase swap or reduce MAX_LOG_LINES in .env
```

### Can't Connect to Django

```bash
# Test SSH tunnel
curl http://localhost:8080/jinkies/health/

# Check tunnel service
sudo systemctl status jinkies-tunnel
```

## Architecture (No AWS!)

```
Django App (anywhere)
         ↓
    SSH Tunnel
         ↓
Raspberry Pi (Jinkies Bot)
         ↓
   Discord API
```

## Benefits of This Setup

✅ **No AWS costs** - everything runs on your hardware  
✅ **Low power** - Raspberry Pi uses ~3-5W  
✅ **Always on** - reliable 24/7 operation  
✅ **SSH tunneling** - works with any network setup  
✅ **No CloudWatch** - uses Django webhooks instead  
✅ **Lightweight** - optimized for ARM processors  
✅ **Full featured** - alerts, GitHub integration, all commands work  

## What Doesn't Work Without CloudWatch

The following commands require CloudWatch and won't work:
- `/logs` - Query logs from CloudWatch
- `/logs-tail` - Stream logs from CloudWatch
- `/logs-stop` - Stop log streaming

**But you still get:**
- ✅ Alert management (`/alerts`, `/alert`, `/ack`)
- ✅ GitHub integration (`/create-pr`, `/create-issue`)
- ✅ Django webhook integration
- ✅ Real-time alerts to Discord
- ✅ All other bot features

## Cost Comparison

**Traditional AWS Setup:**
- EC2 instance: $10-50/month
- CloudWatch: $5-20/month
- **Total: $15-70/month**

**Raspberry Pi Setup:**
- Raspberry Pi 4 (2GB): $45 one-time
- Power: ~$1/month
- **Total: $1/month after initial investment**

**Savings: ~$14-69/month!**
