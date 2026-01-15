# Jinkies Django Webhook Integration

This Django app integrates Jinkies alert functionality into your existing Django project.

## Features

- **No separate server required** - runs as part of your Django application
- **No AWS resources needed** - direct integration via Django endpoints
- **SSH tunnel support** - works with your existing Django deployment
- **Raspberry Pi optimized** - lightweight and efficient for ARM devices
- **Automatic alert forwarding** - sends alerts directly to Discord via webhook

## Installation

### 1. Copy the App

Copy the `jinkies_webhook` directory into your Django project:

```bash
cp -r django_webhook/jinkies_webhook /path/to/your/django/project/
```

### 2. Install Dependencies

Add to your `requirements.txt`:
```
discord.py==2.3.2
aiohttp==3.13.3
python-dateutil==2.8.2
```

### 3. Update Django Settings

Add to `INSTALLED_APPS` in your `settings.py`:
```python
INSTALLED_APPS = [
    # ... your other apps
    'jinkies_webhook',
]
```

### 4. Configure URLs

In your main `urls.py`:
```python
from django.urls import path, include

urlpatterns = [
    # ... your other URLs
    path('jinkies/', include('jinkies_webhook.urls')),
]
```

### 5. Set Environment Variables

Add to your `.env` or environment:
```bash
# Discord webhook URL (create in Discord channel settings)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Optional: Environment name for alerts
ENVIRONMENT_NAME=production
```

### 6. Configure Logging Handler

Add the Jinkies logging handler to your `settings.py`:

```python
import os

JINKIES_WEBHOOK_URL = "http://localhost:8000/jinkies/alert/"

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'jinkies': {
            'level': 'ERROR',
            'class': 'path.to.JinkiesAlertHandler',  # See examples/django_logging_config.py
        },
    },
    'root': {
        'handlers': ['jinkies'],
        'level': 'INFO',
    },
}
```

See `examples/django_logging_config.py` for the complete handler implementation.

## Usage with SSH Tunnel

If your Django app is behind a firewall, use SSH tunneling:

### From Development Machine to Production

```bash
# Forward local port 8000 to production Django server
ssh -L 8000:localhost:8000 user@production-server

# Now your local Discord bot can access alerts at:
# http://localhost:8000/jinkies/alert/
```

### From Bot Server to Django App

```bash
# On the Raspberry Pi (bot server), create tunnel to Django app
ssh -L 8080:localhost:8000 user@django-server

# Configure Jinkies logging handler to use:
JINKIES_WEBHOOK_URL=http://localhost:8080/jinkies/alert/
```

## Raspberry Pi Setup

The Jinkies bot is optimized to run on Raspberry Pi (tested on Pi 3B+ and Pi 4):

### Install on Raspberry Pi

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip -y

# Clone Jinkies
git clone https://github.com/roddy-devs/jinkies.git
cd jinkies

# Install dependencies (may take a while on Pi)
pip3 install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your credentials

# Run the bot
python3 run.py
```

### Run as System Service on Pi

Create `/etc/systemd/system/jinkies.service`:

```ini
[Unit]
Description=Jinkies Discord Bot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/jinkies
EnvironmentFile=/home/pi/jinkies/.env
ExecStart=/usr/bin/python3 -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jinkies
sudo systemctl start jinkies
sudo systemctl status jinkies
```

## Testing

Test the webhook endpoint:

```bash
curl -X POST http://localhost:8000/jinkies/alert/ \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "test",
    "exception_type": "TestError",
    "error_message": "Test alert",
    "severity": "ERROR"
  }'
```

## Discord Webhook Setup

1. Open your Discord channel
2. Go to Channel Settings → Integrations
3. Click "Create Webhook"
4. Copy the webhook URL
5. Set it as `DISCORD_WEBHOOK_URL` environment variable

## Architecture (No AWS Required!)

```
Django App (with jinkies_webhook)
         ↓
    Alert Handler
         ↓
  Local Endpoint: /jinkies/alert/
         ↓
  Discord Webhook → Discord Channel
         ↓
  Jinkies Bot (on Raspberry Pi) reads from channel
```

## No CloudWatch Required

This setup does NOT require:
- AWS Lambda functions
- CloudWatch Logs subscriptions  
- SNS topics
- EC2 instances
- Any AWS resources

Everything runs on your infrastructure!

## Benefits

- ✅ No additional infrastructure
- ✅ Works with existing Django deployment
- ✅ SSH tunnel friendly
- ✅ No AWS costs
- ✅ Simple to maintain
- ✅ Real-time alerts to Discord
- ✅ Runs on Raspberry Pi
- ✅ Low power consumption
