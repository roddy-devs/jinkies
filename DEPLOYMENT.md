# Jinkies Deployment Feature

Jinkies can now handle deployments directly without GitHub Actions!

## Features

- **Direct Deployment**: Execute deployments from your local machine via Discord commands
- **Deployment Status**: Check current production deployment status
- **Deployment Monitoring**: Monitor GitHub Actions deployments (existing feature)
- **Flexible Methods**: Choose between direct execution or GitHub Actions

## Setup

### 1. Configure Environment Variables

Add these to your `.env` file:

```bash
# Deployment Configuration
DEPLOY_REPO_PATH=/Users/your-username/source/nomadic-influence
DEPLOY_SSH_KEY=/Users/your-username/.ssh/nomadic-influence.pem
DEPLOY_EC2_HOST=your-ec2-host.compute.amazonaws.com
DEPLOY_EC2_USER=ubuntu

# Discord Channels
DISCORD_DEPLOY_CHANNEL_ID=your_deploy_channel_id
DISCORD_COPILOT_CHANNEL_ID=your_copilot_channel_id
```

### 2. Ensure Deployment Script Exists

The deployment executor looks for `scripts/deploy.sh` in your repository. This script should:
- Build the frontend
- Deploy to S3
- Sync backend to EC2
- Run migrations
- Restart services

### 3. Configure AWS CLI

Ensure AWS CLI is configured on the machine running Jinkies:

```bash
aws configure
```

### 4. Test SSH Access

Verify SSH access to your EC2 instance:

```bash
ssh -i ~/.ssh/nomadic-influence.pem ubuntu@your-ec2-host.compute.amazonaws.com
```

## Discord Commands

### `/deploy`

Trigger a deployment.

**Parameters:**
- `ref` (optional): Branch name to deploy (default: `develop`)
- `method` (optional): Deployment method - `direct` or `github` (default: `direct`)

**Examples:**
```
/deploy
/deploy ref:main
/deploy ref:develop method:github
```

**Direct Method:**
- Runs deployment script locally
- Shows real-time progress
- Displays output/errors
- Takes 5-10 minutes

**GitHub Method:**
- Triggers GitHub Actions workflow
- Requires Actions billing configured
- Monitors workflow status

### `/deploy-status`

Check current production deployment status.

**Shows:**
- Service status (running/stopped)
- Last deployed commit
- Commit author and time
- Commit message

**Example:**
```
/deploy-status
```

## How It Works

### Direct Deployment Flow

1. User runs `/deploy` command in Discord
2. Jinkies pulls latest code from specified branch
3. Runs `scripts/deploy.sh` with proper environment variables
4. Monitors execution and reports progress
5. Posts success/failure to deploy channel

### Architecture

```
Discord Command
      ↓
DeploymentCommands Cog
      ↓
DeploymentExecutor Service
      ↓
   ┌──┴──┐
   ↓     ↓
Git Pull  Run deploy.sh
   ↓     ↓
Update   Deploy
Repo     App
```

### Security

- **Role-based access**: Only users with configured roles can deploy
- **SSH key authentication**: Uses SSH keys for EC2 access
- **AWS credentials**: Uses local AWS CLI configuration
- **Audit trail**: All deployments logged in Discord

## Troubleshooting

### "Direct deployment not configured"

Ensure all `DEPLOY_*` environment variables are set in `.env`.

### "Deployment timed out"

Deployments have a 10-minute timeout. Check:
- Network connectivity
- EC2 instance status
- Deployment script errors

### "SSH connection failed"

Verify:
- SSH key path is correct
- SSH key has proper permissions (600)
- EC2 security group allows SSH from your IP
- EC2 instance is running

### "AWS credentials not configured"

Run `aws configure` on the machine running Jinkies.

## Benefits Over GitHub Actions

1. **No billing issues**: Bypasses GitHub Actions billing problems
2. **Faster feedback**: See deployment output in real-time
3. **Local control**: Run from your development machine
4. **Debugging**: Easier to debug deployment issues
5. **Flexibility**: Can deploy from any branch instantly

## Limitations

1. **Machine dependency**: Jinkies bot must be running on a machine with:
   - Access to the repository
   - AWS CLI configured
   - SSH access to EC2
2. **Single executor**: Only one deployment can run at a time
3. **Network dependency**: Requires stable internet connection

## Future Enhancements

- [ ] Queue multiple deployments
- [ ] Rollback command
- [ ] Deployment history
- [ ] Multi-environment support (staging, production)
- [ ] Deployment approval workflow
- [ ] Automated rollback on failure
- [ ] Health check after deployment
