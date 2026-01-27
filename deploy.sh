#!/bin/bash
# Quick deployment script for AWS EC2

set -e

echo "🚀 Starting deployment..."

# Update code (if using git)
if [ -d .git ]; then
    echo "📦 Pulling latest code..."
    git pull
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Ensure logs directory exists
echo "📁 Creating logs directory..."
mkdir -p logs

# Run database migrations if needed
if [ -f schema.sql ]; then
    echo "🗄️  Checking database..."
    # Uncomment if you want to auto-run migrations
    # python3 -c "from database import init_database; init_database()"
fi

# Restart services
echo "🔄 Restarting services..."
sudo systemctl restart investment-study
sudo systemctl restart nginx

# Check status
echo "✅ Checking service status..."
sudo systemctl status investment-study --no-pager -l

echo "✨ Deployment complete!"
echo "📊 View logs: sudo journalctl -u investment-study -f"
