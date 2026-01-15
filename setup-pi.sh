#!/bin/bash
# Jinkies One-Command Setup Script for Raspberry Pi
# Run this script to set up Jinkies in one go!

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║           🔍 Jinkies Raspberry Pi Setup Script 🔍             ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null && ! grep -q "BCM" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   Continuing anyway..."
    echo ""
fi

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "❌ Python 3.9+ required. Found: $PYTHON_VERSION"
    echo "   Install with: sudo apt install python3 python3-pip"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"
echo ""

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt update -qq
sudo apt install -y python3-pip python3-venv git sqlite3 >/dev/null 2>&1 || {
    echo "❌ Failed to install system dependencies"
    exit 1
}
echo "✅ System dependencies installed"
echo ""

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements-pi.txt || {
    echo "❌ Failed to install Python dependencies"
    exit 1
}
echo "✅ Python dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env configuration file..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    
    echo "⚙️  Configuration Required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "You need to configure the following in .env:"
    echo ""
    echo "1. Discord Bot Token"
    echo "   Get from: https://discord.com/developers/applications"
    echo "   → Your Application → Bot → Token"
    echo ""
    echo "2. Discord Channel IDs"
    echo "   Enable Developer Mode in Discord"
    echo "   Right-click channel → Copy ID"
    echo ""
    echo "3. GitHub Token"
    echo "   Get from: https://github.com/settings/tokens"
    echo "   Needs 'repo' scope"
    echo ""
    echo "4. GitHub Repository Details"
    echo "   Your username/org and repo name"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "Press Enter to open .env in nano editor..."
    nano .env
else
    echo "✅ .env file already exists"
    echo ""
fi

# Validate configuration
echo "🔍 Validating configuration..."
source .env

MISSING_VARS=()

if [ -z "$DISCORD_BOT_TOKEN" ] || [ "$DISCORD_BOT_TOKEN" = "your_discord_bot_token_here" ]; then
    MISSING_VARS+=("DISCORD_BOT_TOKEN")
fi

if [ -z "$DISCORD_ALERT_CHANNEL_ID" ] || [ "$DISCORD_ALERT_CHANNEL_ID" = "123456789012345678" ]; then
    MISSING_VARS+=("DISCORD_ALERT_CHANNEL_ID")
fi

if [ -z "$DISCORD_LOG_CHANNEL_ID" ] || [ "$DISCORD_LOG_CHANNEL_ID" = "123456789012345678" ]; then
    MISSING_VARS+=("DISCORD_LOG_CHANNEL_ID")
fi

if [ -z "$GITHUB_PRIVATE_KEY" ] || [ "$GITHUB_PRIVATE_KEY" = "your_github_private_key_or_path_to_key_file" ]; then
    MISSING_VARS+=("GITHUB_PRIVATE_KEY")
fi

if [ -z "$GITHUB_REPO_OWNER" ] || [ "$GITHUB_REPO_OWNER" = "your_github_username_or_org" ]; then
    MISSING_VARS+=("GITHUB_REPO_OWNER")
fi

if [ -z "$GITHUB_REPO_NAME" ] || [ "$GITHUB_REPO_NAME" = "your_repo_name" ]; then
    MISSING_VARS+=("GITHUB_REPO_NAME")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Configuration incomplete. Missing or not configured:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please edit .env and run this script again:"
    echo "   nano .env"
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Create systemd service
echo "🔧 Setting up systemd service..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="/tmp/jinkies.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Jinkies Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
EnvironmentFile=$SCRIPT_DIR/.env
ExecStart=$SCRIPT_DIR/venv/bin/python3 -m bot.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo mv "$SERVICE_FILE" /etc/systemd/system/jinkies.service
sudo systemctl daemon-reload
echo "✅ Systemd service created"
echo ""

# Test run
echo "🧪 Testing bot configuration..."
timeout 5s venv/bin/python3 -c "
import sys
sys.path.insert(0, '.')
from bot.config import config
errors = config.validate()
if errors:
    print('❌ Configuration errors:')
    for error in errors:
        print(f'   - {error}')
    sys.exit(1)
print('✅ Configuration valid')
" || {
    if [ $? -eq 124 ]; then
        echo "✅ Bot configuration looks good"
    else
        echo "❌ Configuration validation failed"
        exit 1
    fi
}
echo ""

# Ask if user wants to start the service now
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Setup Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose an option:"
echo ""
echo "1. Start bot now (foreground - for testing)"
echo "2. Install as service (runs automatically on boot)"
echo "3. Exit (start manually later)"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo ""
        echo "Starting Jinkies bot..."
        echo "Press Ctrl+C to stop"
        echo ""
        source venv/bin/activate
        python3 run.py
        ;;
    2)
        echo ""
        echo "Installing and starting service..."
        sudo systemctl enable jinkies
        sudo systemctl start jinkies
        echo ""
        echo "✅ Service installed and started!"
        echo ""
        echo "Useful commands:"
        echo "  sudo systemctl status jinkies   - Check status"
        echo "  sudo systemctl stop jinkies     - Stop bot"
        echo "  sudo systemctl restart jinkies  - Restart bot"
        echo "  sudo journalctl -u jinkies -f   - View logs"
        ;;
    3)
        echo ""
        echo "Setup complete! To start the bot manually:"
        echo "  source venv/bin/activate"
        echo "  python3 run.py"
        echo ""
        echo "Or install as service:"
        echo "  sudo systemctl enable jinkies"
        echo "  sudo systemctl start jinkies"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "🎊 Jinkies is ready to monitor your applications!"
