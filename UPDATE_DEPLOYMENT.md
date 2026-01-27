# Deploying Updates to Production

Quick reference for deploying code changes to your AWS EC2 server.

---

## Method 1: Using Git (Recommended)

### On EC2 Server:

```bash
# SSH into your server
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip

# Navigate to app directory
cd /home/ubuntu/app

# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin main
# (or 'git pull origin master' depending on your branch name)

# Install any new dependencies
pip install -r requirements.txt

# Restart the application
sudo systemctl restart market-mindset

# Check status
sudo systemctl status market-mindset

# Check logs for any errors
tail -f /home/ubuntu/app/logs/error.log
```

---

## Method 2: Using SCP (If not using Git)

### On Your LOCAL Machine:

```bash
# From your project directory
cd /Users/amrita/uchicago/thesis/market-mindset

# Upload specific files
scp -i ~/.ssh/market-mindset.pem app.py ubuntu@your-elastic-ip:/home/ubuntu/app/
scp -i ~/.ssh/market-mindset.pem callbacks.py ubuntu@your-elastic-ip:/home/ubuntu/app/
scp -i ~/.ssh/market-mindset.pem components.py ubuntu@your-elastic-ip:/home/ubuntu/app/

# Or upload entire directory (overwrites everything)
scp -i ~/.ssh/market-mindset.pem -r . ubuntu@your-elastic-ip:/home/ubuntu/app/
```

### Then on EC2 Server:

```bash
# SSH into server
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip

# Navigate to app
cd /home/ubuntu/app

# Activate virtual environment
source venv/bin/activate

# Install any new dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Restart the application
sudo systemctl restart market-mindset

# Check status
sudo systemctl status market-mindset
```

---

## Method 3: Quick Script (Create on EC2)

Create this script on EC2 for one-command updates:

```bash
# On EC2, create update script
nano /home/ubuntu/update-app.sh
```

Add this content:

```bash
#!/bin/bash
cd /home/ubuntu/app
source venv/bin/activate
git pull origin main
pip install -r requirements.txt
sudo systemctl restart market-mindset
echo "Deployment complete!"
sudo systemctl status market-mindset
```

Make it executable:

```bash
chmod +x /home/ubuntu/update-app.sh
```

Use it:

```bash
./update-app.sh
```

---

## Database Schema Changes

If you update [schema.sql](schema.sql):

```bash
# SSH into EC2
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip

# Apply schema changes
psql -h your-rds-endpoint -U postgres -d market-mindset -f /home/ubuntu/app/schema.sql

# Or run specific SQL commands
psql -h your-rds-endpoint -U postgres -d market-mindset
# Then type your SQL commands
# \q to exit
```

---

## Troubleshooting

### Check Service Status
```bash
sudo systemctl status market-mindset
```

### View Real-Time Logs
```bash
# Application error logs
tail -f /home/ubuntu/app/logs/error.log

# System logs
sudo journalctl -u market-mindset -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Restart Services
```bash
# Restart app
sudo systemctl restart market-mindset

# Restart nginx (if config changed)
sudo systemctl restart nginx
```

### Check if App is Running
```bash
# Check if gunicorn is running on port 8050
sudo netstat -tlnp | grep 8050

# Or
curl http://localhost:8050
```

---

## Environment Variables Changes

If you change .env file:

```bash
# On EC2
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip

# Edit .env
nano /home/ubuntu/app/.env

# Make your changes, then restart
sudo systemctl restart market-mindset
```

---

## Full Rollback (Undo Changes)

### Using Git:
```bash
cd /home/ubuntu/app
git log  # Find commit hash you want to revert to
git checkout <commit-hash>
sudo systemctl restart market-mindset
```

### Using Backup:
```bash
# Restore from your local backup
scp -i ~/.ssh/market-mindset.pem -r /Users/amrita/uchicago/thesis/market-mindset/* ubuntu@your-elastic-ip:/home/ubuntu/app/
# Then restart as usual
```

---

## Pre-Deployment Checklist

Before deploying:

- [ ] Test changes locally: `python app.py`
- [ ] Commit changes to git (if using git)
- [ ] Backup current production (optional): `git log` to note current commit
- [ ] Check [requirements.txt](requirements.txt) is up to date
- [ ] Review error logs after deployment
- [ ] Test the live site in browser

---

## Quick Reference Commands

```bash
# One-liner full update (git method)
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip "cd /home/ubuntu/app && source venv/bin/activate && git pull && pip install -r requirements.txt && sudo systemctl restart market-mindset && sudo systemctl status market-mindset"

# View logs remotely
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip "tail -n 50 /home/ubuntu/app/logs/error.log"

# Quick restart
ssh -i ~/.ssh/market-mindset.pem ubuntu@your-elastic-ip "sudo systemctl restart market-mindset && sudo systemctl status market-mindset"
```
