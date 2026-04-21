#!/bin/bash
# Quick deployment script for AWS EC2

set -euo pipefail

echo "🚀 Starting deployment..."

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

if [ ! -f ".env" ]; then
    echo "❌ Missing .env file in $APP_DIR"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "❌ Missing Python virtual environment at $APP_DIR/venv"
    exit 1
fi

echo "🔐 Loading environment variables from .env..."
set -a
source .env
set +a

echo "🔎 Running preflight checks..."
required_tools=(python3 pip systemctl nginx curl)
for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "❌ Missing required tool: $tool"
        exit 1
    fi
done

# Update code (if using git)
if [ -d .git ]; then
    echo "📦 Pulling latest code..."
    git pull --ff-only
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Ensure logs directory exists
echo "📁 Creating logs directory..."
mkdir -p logs

echo "🗄️  Verifying database connectivity..."
python3 - <<'PY'
from database import get_db_connection

with get_db_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        cur.fetchone()
print("Database connectivity check passed")
PY

# Restart services
echo "🔄 Restarting services..."
sudo cp market-mindset.service /etc/systemd/system/market-mindset.service
sudo systemctl daemon-reload
sudo systemctl restart market-mindset

echo "🧪 Validating nginx configuration..."
sudo nginx -t
sudo systemctl restart nginx

echo "⏳ Waiting for service warm-up..."
sleep 3

# Check status
echo "✅ Checking service status..."
sudo systemctl status market-mindset --no-pager -l
sudo systemctl is-active --quiet market-mindset

echo "🌐 Running HTTP health check..."
if ! curl -fsS --max-time 10 http://127.0.0.1/ >/dev/null; then
    echo "❌ Health check failed. Check logs with: sudo journalctl -u market-mindset -n 200 --no-pager"
    exit 1
fi

echo "✨ Deployment complete!"
echo "📊 View logs: sudo journalctl -u market-mindset -f"
