# Jinkies Quick Start Guide

This guide will help you get Jinkies up and running quickly.

## Prerequisites

- Python 3.9 or higher
- A Discord account and server
- AWS account with CloudWatch access
- GitHub account

## Step 1: Discord Bot Setup

1. **Create a Discord Application**
   - Go to https://discord.com/developers/applications
   - Click "New Application"
   - Name it "Jinkies" and create

2. **Create a Bot**
   - Go to the "Bot" tab
   - Click "Add Bot"
   - Enable these "Privileged Gateway Intents":
     - Presence Intent
     - Server Members Intent
     - Message Content Intent
   - Copy the bot token (you'll need this later)

3. **Set Bot Permissions**
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: `bot`, `applications.commands`
   - Select permissions:
     - Send Messages
     - Send Messages in Threads
     - Embed Links
     - Attach Files
     - Read Message History
     - Use Slash Commands
   - Copy the generated URL

4. **Invite Bot to Server**
   - Paste the URL in your browser
   - Select your server
   - Authorize

5. **Get Channel IDs**
   - Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
   - Right-click on your alert channel → Copy ID
   - Right-click on your log channel → Copy ID

## Step 2: AWS Setup

1. **Create IAM User for Bot**
   ```bash
   # Create user
   aws iam create-user --user-name jinkies-bot
   ```

2. **Create IAM Policy**
   Save this as `jinkies-policy.json`:
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
         "Resource": "*"
       }
     ]
   }
   ```

   Apply the policy:
   ```bash
   aws iam create-policy --policy-name JinkiesCloudWatchAccess --policy-document file://jinkies-policy.json
   aws iam attach-user-policy --user-name jinkies-bot --policy-arn arn:aws:iam::YOUR_ACCOUNT:policy/JinkiesCloudWatchAccess
   ```

3. **Create Access Keys**
   ```bash
   aws iam create-access-key --user-name jinkies-bot
   ```
   Save the AccessKeyId and SecretAccessKey.

## Step 3: GitHub Setup

1. **Create Personal Access Token**
   - Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Select scopes:
     - `repo` (all)
     - `workflow`
   - Copy the token

## Step 4: Install Jinkies

1. **Clone the Repository**
   ```bash
   git clone https://github.com/roddy-devs/jinkies.git
   cd jinkies
   ```

2. **Run Setup**
   ```bash
   python setup.py
   ```

3. **Configure Environment**
   Edit `.env` file with your credentials:
   ```bash
   # Discord
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_ALERT_CHANNEL_ID=123456789012345678
   DISCORD_LOG_CHANNEL_ID=123456789012345678
   DISCORD_ALLOWED_ROLES=Admin,DevOps

   # GitHub
   GITHUB_PRIVATE_KEY=ghp_your_github_token
   GITHUB_REPO_OWNER=your-username
   GITHUB_REPO_NAME=your-repo
   DEFAULT_BASE_BRANCH=main

   # AWS
   AWS_REGION=us-east-1
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   CLOUDWATCH_LOG_GROUP_API=/aws/ec2/django-api

   # Environment
   ENVIRONMENT_NAME=production
   ```

## Step 5: Run the Bot

```bash
python run.py
```

You should see:
```
INFO - Logged in as Jinkies#1234 (ID: ...)
INFO - Connected to 1 guild(s)
INFO - Bot is ready!
```

## Step 6: Test Commands

In Discord, try these commands:

1. **View recent alerts**
   ```
   /alerts
   ```

2. **Get logs**
   ```
   /logs service:api limit:10
   ```

3. **Tail logs**
   ```
   /logs-tail service:api duration:60
   ```

## Step 7: Set Up Alert Webhook (Optional)

To receive real-time alerts from your application:

1. **Run webhook server**
   ```bash
   python -m bot.webhook
   ```

2. **Configure your Django app**
   Add the configuration from `examples/django_logging_config.py` to your Django settings.

3. **Set webhook URL**
   ```bash
   export JINKIES_WEBHOOK_URL=http://your-server:8080/webhook/alert
   ```

## Troubleshooting

### Bot doesn't respond to commands
- Check bot has "Use Application Commands" permission
- Ensure bot is online
- Verify you have the required role (set in DISCORD_ALLOWED_ROLES)
- Try restarting the bot

### CloudWatch errors
- Verify AWS credentials are correct
- Check log group names match your actual CloudWatch log groups
- Ensure IAM permissions are properly configured

### GitHub integration fails
- Verify GitHub token has correct permissions
- Check repository owner and name are correct
- Ensure token hasn't expired

### Commands not showing up
- Bot may need to re-sync commands
- Try kicking and re-inviting the bot
- Check bot has "applications.commands" scope

## Docker Deployment

For production, use Docker:

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Check logs
docker-compose logs -f jinkies-bot
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [examples/](examples/) for integration examples
- See [CONTRIBUTING.md](CONTRIBUTING.md) to contribute

## Getting Help

- Check existing GitHub issues
- Create a new issue for bugs or feature requests
- Review the documentation in README.md

Happy monitoring! 🔍
