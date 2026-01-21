# Jinkies 🤖

A powerful Discord bot for DevOps automation, deployment management, and production monitoring.

## Features

- **🚀 One-Command Deployments** - Deploy to production with `/deploy`
- **📊 Deployment Tracking** - SQLite database tracks every deployment
- **🔔 Real-Time Alerts** - Production errors sent to Discord
- **🤖 AI-Powered Fixes** - OpenAI generates fix suggestions and creates PRs
- **👥 User Management** - Manage production database from Discord
- **📝 GitHub Integration** - Monitor PRs, create issues, track Copilot completions
- **☁️ AWS Integration** - S3, CloudFront, EC2, Parameter Store
- **🔥 Firebase Integration** - User management synced with Firebase Auth
- **📈 CloudWatch Logs** - Tail logs directly in Discord

## Why Jinkies?

Built for startups and solo founders who want powerful DevOps tools without the cost:
- ❌ No Slack subscription needed (use Discord)
- ❌ No GitHub Actions minutes wasted
- ❌ No expensive monitoring services
- ✅ Everything in one free Discord bot

## Quick Start

### Prerequisites

- Python 3.12+
- Discord Bot Token ([Create one here](https://discord.com/developers/applications))
- (Optional) AWS credentials
- (Optional) GitHub Personal Access Token
- (Optional) OpenAI API Key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/jinkies.git
cd jinkies
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
# or use the provided script for Raspberry Pi
./setup-pi.sh
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Run the bot**
```bash
python run.py
```

## Configuration

### Required Settings

```bash
# Discord (Required)
DISCORD_BOT_TOKEN=your_bot_token_here
DISCORD_ALERT_CHANNEL_ID=123456789
DISCORD_LOG_CHANNEL_ID=123456789
DISCORD_ALLOWED_ROLES=Admin,DevOps
```

### Optional: Deployment Automation

To enable `/deploy` command:

```bash
# Deployment Configuration
DEPLOY_REPO_PATH=/path/to/your/repo
DEPLOY_SSH_KEY=/path/to/ssh/key.pem
DEPLOY_EC2_HOST=your-ec2-host.amazonaws.com
DEPLOY_EC2_USER=ubuntu
DISCORD_DEPLOY_CHANNEL_ID=123456789
```

### Optional: GitHub Integration

For PR monitoring and issue creation:

```bash
# GitHub
GITHUB_PRIVATE_KEY=your_github_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=your_repo
DEFAULT_BASE_BRANCH=main
```

### Optional: AWS Integration

For CloudWatch logs and deployments:

```bash
# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

### Optional: AI Features

For AI-powered error analysis:

```bash
# OpenAI
OPENAI_API_KEY=your_openai_key
```

## Commands

### Deployment
- `/deploy` - Deploy to production
- `/deploy-status` - Check current deployment status

### User Management (Customize for your app)
- `/user get <email>` - Get user details
- `/user update <email>` - Update user information
- `/user delete <email>` - Delete user

### Alerts
- `/alert` - View recent alerts
- `/alerts` - List all alerts

### Logs
- `/logs tail <service>` - Tail CloudWatch logs
- `/logs stop` - Stop tailing logs

### Requests
- `/request pr <description>` - Request a PR from GitHub Copilot

## Customization

### 1. Add Your Deployment Script

Create `scripts/deploy-your-app.sh`:

```bash
#!/bin/bash
set -e

# Your deployment logic here
echo "Deploying..."
cd $DEPLOY_REPO_PATH
git pull origin develop
# Build, deploy, restart services, etc.
```

Make it executable:
```bash
chmod +x scripts/deploy-your-app.sh
```

Update `bot/services/deploy_executor.py` line 58 to point to your script:
```python
deploy_script = jinkies_path / "scripts" / "deploy-your-app.sh"
```

### 2. Customize User Management

Edit `bot/cogs/nomad_crud.py` to match your API endpoints and data models.

### 3. Add Custom Commands

Create a new cog in `bot/cogs/your_cog.py`:

```python
from discord.ext import commands
from discord import app_commands
from bot.utils.discord_helpers import has_required_role

class YourCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="yourcommand", description="Your command description")
    async def your_command(self, interaction):
        if not has_required_role(interaction):
            await interaction.response.send_message("❌ No permission", ephemeral=True)
            return
        
        await interaction.response.send_message("✅ Command executed!")

async def setup(bot):
    await bot.add_cog(YourCog(bot))
```

Load it in `bot/main.py` by adding to the cogs list.

### 4. Customize Alert Handling

Edit `bot/services/alert_store.py` to customize how alerts are stored and retrieved.

## Architecture

```
jinkies/
├── bot/
│   ├── cogs/              # Discord command modules
│   │   ├── alerts.py      # Alert management
│   │   ├── deploy.py      # Deployment automation
│   │   ├── logs.py        # CloudWatch log tailing
│   │   ├── nomad_crud.py  # User/business management (customize this)
│   │   ├── requests.py    # PR requests
│   │   ├── verification.py # User verification
│   │   └── webhook.py     # Webhook server for alerts
│   ├── services/          # Business logic
│   │   ├── alert_store.py        # Alert persistence
│   │   ├── ai_service.py         # OpenAI integration
│   │   ├── cloudwatch.py         # AWS CloudWatch
│   │   ├── deploy_executor.py    # Deployment execution
│   │   ├── deployment_store.py   # Deployment tracking
│   │   └── github_service.py     # GitHub API
│   ├── models/            # Data models
│   ├── utils/             # Helper functions
│   ├── config.py          # Configuration management
│   └── main.py            # Bot initialization
├── scripts/               # Deployment scripts (customize)
├── tests/                 # Unit tests
├── .env.example           # Example configuration
├── requirements.txt       # Python dependencies
└── run.py                 # Entry point
```

## Deployment

### Running on a Server

Create a systemd service:

```bash
sudo nano /etc/systemd/system/jinkies.service
```

```ini
[Unit]
Description=Jinkies Discord Bot
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/jinkies
ExecStart=/usr/bin/python3 /path/to/jinkies/run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable jinkies
sudo systemctl start jinkies
```

### Running on Raspberry Pi

```bash
./setup-pi.sh
```

### Running with Docker

```bash
docker build -t jinkies .
docker run -d --env-file .env --name jinkies jinkies
```

## Webhook Integration

To receive alerts from your application, send POST requests to `http://your-bot-host:8765/alert`:

```python
import requests

requests.post("http://localhost:8765/alert", json={
    "service": "api",
    "severity": "error",
    "message": "Database connection failed",
    "stack_trace": "...",
    "environment": "production"
})
```

## Database

Jinkies uses SQLite for:
- **Alert storage** (`alerts.db`) - All production alerts
- **Deployment tracking** (`deployments.db`) - Deployment history

Data persists in the bot's working directory.

## Security Best Practices

- ✅ Store credentials in `.env` (never commit)
- ✅ Use role-based access control for commands
- ✅ Restrict bot permissions in Discord
- ✅ Use SSH keys for server access
- ✅ Store AWS secrets in Parameter Store
- ✅ Run bot as non-root user
- ✅ Keep dependencies updated

## Troubleshooting

**Bot not responding to commands?**
- Ensure bot has proper Discord permissions
- Check `DISCORD_ALLOWED_ROLES` matches your Discord roles
- Run `/sync` to sync slash commands

**Deployment failing?**
- Verify `DEPLOY_*` environment variables are set
- Check SSH key permissions (should be 600)
- Ensure AWS credentials are configured
- Test deployment script manually first

**Alerts not appearing?**
- Check webhook server is running (port 8765)
- Verify `DISCORD_ALERT_CHANNEL_ID` is correct
- Check firewall allows incoming connections

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - feel free to use and modify for your needs.

## Support

- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/jinkies/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/jinkies/discussions)
- 📖 Documentation: [Wiki](https://github.com/yourusername/jinkies/wiki)

## Credits

Built with:
- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API wrapper
- [boto3](https://github.com/boto/boto3) - AWS SDK
- [OpenAI Python](https://github.com/openai/openai-python) - OpenAI API

## Roadmap

- [ ] Multi-server deployment support
- [ ] Rollback functionality
- [ ] Deployment approval workflow
- [ ] Slack integration (optional)
- [ ] Web dashboard
- [ ] Metrics and analytics
- [ ] Docker Compose support

---

**Made with ❤️ for startups who want powerful DevOps without the cost**

*Star ⭐ this repo if you find it useful!*
