# 🔍 Jinkies

A production-grade Discord bot for AWS monitoring, logs, alerts, and interactive PR/issue creation.

Jinkies serves as a **real-time observability and incident-response control plane** for AWS-hosted applications, allowing your team to monitor, triage, and respond to incidents directly from Discord.

## ✨ Features

### 📜 Log Management
- **On-demand log retrieval** from CloudWatch Logs
- **Real-time log streaming** (tail mode)
- Advanced filtering by level, time, and service
- Automatic pagination for Discord message limits
- Support for multiple log sources (API, CloudFront, etc.)

### 🚨 Alert System
- Real-time error alerts with full context
- Persistent alert storage with SQLite
- Rich embeds with stack traces and logs
- Alert acknowledgment tracking
- Automatic alert deduplication

### 🔄 GitHub Integration
- **Interactive PR creation** from alerts
- **Issue creation** with error context
- Auto-generated PR/issue descriptions
- Branch creation and draft PR workflow
- Link tracking between alerts and GitHub

### 💬 Discord Commands
- `/logs` - Retrieve application logs
- `/logs-tail` - Stream logs in real-time
- `/logs-stop` - Stop log streaming
- `/alerts` - List recent alerts
- `/alert <id>` - View alert details
- `/ack <id>` - Acknowledge an alert
- `/create-pr <id>` - Create PR from alert
- `/create-issue <id>` - Create issue from alert

### 🔐 Security
- Role-based access control
- Environment separation
- Rate limiting and message length protection
- Graceful error handling
- Secure credential management

## 🏗️ Architecture

```
┌─────────────────┐
│  Django App     │
│  (EC2)          │
└────────┬────────┘
         │ Logs
         ↓
┌─────────────────┐      ┌──────────────┐
│  CloudWatch     │◄────►│  Jinkies Bot │
│  Logs           │      │  (Discord)   │
└─────────────────┘      └──────┬───────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
         ↓                      ↓                      ↓
┌────────────────┐    ┌─────────────────┐    ┌───────────────┐
│  Discord       │    │  GitHub API     │    │  Alert Store  │
│  Slash Cmds    │    │  (PRs/Issues)   │    │  (SQLite)     │
└────────────────┘    └─────────────────┘    └───────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Discord bot with appropriate permissions
- AWS credentials with CloudWatch access
- GitHub Personal Access Token or App credentials

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/roddy-devs/jinkies.git
   cd jinkies
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Run the bot**
   ```bash
   python -m bot.main
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

#### Discord Configuration
```bash
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_ALERT_CHANNEL_ID=123456789012345678
DISCORD_LOG_CHANNEL_ID=123456789012345678
DISCORD_ALLOWED_ROLES=Admin,DevOps,Engineer
```

#### GitHub Configuration
```bash
GITHUB_PRIVATE_KEY=ghp_your_personal_access_token
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo
DEFAULT_BASE_BRANCH=develop
```

#### AWS Configuration
```bash
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
CLOUDWATCH_LOG_GROUP_API=/aws/ec2/django-api
CLOUDWATCH_LOG_GROUP_CLOUDFRONT=/aws/cloudfront/access-logs
```

#### Application Settings
```bash
ENVIRONMENT_NAME=production
LOG_LEVEL=INFO
MAX_LOG_LINES=50
LOG_TAIL_INTERVAL=10
ALERT_RETENTION_DAYS=30
```

### Discord Bot Setup

1. **Create Discord Application**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to "Bot" section and create a bot
   - Copy the bot token

2. **Configure Bot Permissions**
   Required permissions:
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Attach Files
   - Read Message History
   - Use Slash Commands

3. **Invite Bot to Server**
   Generate invite URL with required permissions and add to your server.

4. **Enable Slash Commands**
   - Go to "OAuth2" → "URL Generator"
   - Select `bot` and `applications.commands` scopes
   - Select required permissions

### AWS IAM Permissions

The bot requires the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents",
        "logs:GetLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:*:*:log-group:/aws/ec2/*",
        "arn:aws:logs:*:*:log-group:/aws/cloudfront/*"
      ]
    }
  ]
}
```

### GitHub Access Token

Create a Personal Access Token with the following scopes:
- `repo` (Full control of private repositories)
- `workflow` (Update GitHub Action workflows)

Or use a GitHub App with:
- Repository permissions: Contents (Read & Write), Pull Requests (Read & Write), Issues (Read & Write)

## 📖 Usage Guide

### Viewing Logs

**Basic log retrieval:**
```
/logs service:api
```

**Filter by log level:**
```
/logs service:api level:ERROR
```

**Custom time range:**
```
/logs service:api since:30 limit:100
```

**Stream logs in real-time:**
```
/logs-tail service:api level:ERROR duration:120
```

**Stop streaming:**
```
/logs-stop service:api
```

### Managing Alerts

**List recent alerts:**
```
/alerts limit:10
```

**View unacknowledged alerts only:**
```
/alerts unacknowledged_only:True
```

**View specific alert:**
```
/alert alert_id:a1b2c3d4
```

**Acknowledge an alert:**
```
/ack alert_id:a1b2c3d4
```

### Creating PRs and Issues

**Create a PR from an alert:**
```
/create-pr alert_id:a1b2c3d4 base_branch:develop fix_notes:"Add error handling for duplicate keys"
```

**Create an issue from an alert:**
```
/create-issue alert_id:a1b2c3d4
```

## 🔗 Django Integration

To integrate Jinkies with your Django application, add the logging configuration from `examples/django_logging_config.py` to your Django settings.

### Quick Integration Steps:

1. **Install required packages:**
   ```bash
   pip install watchtower python-json-logger
   ```

2. **Add logging configuration to `settings.py`:**
   ```python
   from examples.django_logging_config import LOGGING, JinkiesAlertHandler
   ```

3. **Add middleware to `MIDDLEWARE`:**
   ```python
   MIDDLEWARE = [
       # ... other middleware
       'path.to.RequestLoggingMiddleware',
   ]
   ```

4. **Set webhook URL:**
   ```bash
   export JINKIES_WEBHOOK_URL=http://your-jinkies-instance:8080/webhook/alert
   ```

5. **Run the webhook server:**
   ```bash
   python -m bot.webhook
   ```

## 🧪 Testing

The bot includes comprehensive error handling and logging. To test:

1. **Test CloudWatch connection:**
   ```python
   from bot.services.cloudwatch import CloudWatchService
   cw = CloudWatchService()
   print(cw.test_connection("/aws/ec2/django-api"))
   ```

2. **Test GitHub connection:**
   ```python
   from bot.services.github_service import GitHubService
   gh = GitHubService()
   print(gh.test_connection())
   ```

3. **Create a test alert:**
   ```python
   from bot.models.alert import Alert
   from bot.services.alert_store import AlertStore
   
   alert = Alert(
       service_name="api",
       exception_type="TestError",
       error_message="Test alert",
       environment="testing"
   )
   
   store = AlertStore()
   store.save_alert(alert)
   ```

## 🚢 Deployment

### Using Docker (Recommended)

Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
```

Build and run:
```bash
docker build -t jinkies .
docker run -d --env-file .env jinkies
```

### Using systemd

Create `/etc/systemd/system/jinkies.service`:
```ini
[Unit]
Description=Jinkies Discord Bot
After=network.target

[Service]
Type=simple
User=jinkies
WorkingDirectory=/opt/jinkies
EnvironmentFile=/opt/jinkies/.env
ExecStart=/usr/bin/python3 -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable jinkies
sudo systemctl start jinkies
```

## 📊 Monitoring & Maintenance

### Log Rotation

The bot creates a `bot.log` file. Configure log rotation with logrotate:

```bash
/opt/jinkies/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 jinkies jinkies
}
```

### Alert Cleanup

Alerts older than `ALERT_RETENTION_DAYS` can be cleaned up manually:

```python
from bot.services.alert_store import AlertStore
store = AlertStore()
deleted = store.cleanup_old_alerts(days=30)
print(f"Deleted {deleted} old alerts")
```

### Database Backup

Backup the alerts database regularly:
```bash
cp alerts.db alerts.db.backup.$(date +%Y%m%d)
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues, questions, or feature requests, please create an issue on GitHub.

## 🙏 Acknowledgments

Built with:
- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [boto3](https://github.com/boto/boto3) - AWS SDK for Python
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API wrapper
