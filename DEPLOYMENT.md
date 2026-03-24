# AWS Deployment Guide - Production Profile (Headroom for 250 Concurrent Users)

## Target Profile

- App tier: EC2 `t3.large` (or larger)
- Database tier: RDS PostgreSQL `db.t4g.medium` (or larger)
- Goal: support 250 concurrent participants with margin and lower error risk

---

## Prerequisites

1. AWS Account
2. Domain name (optional, ~$12/year) OR use EC2 public IP

---

## Step 1: Setup RDS PostgreSQL (Production)

### Create RDS Instance
```bash
# Via AWS Console:
1. Go to RDS → Create Database
2. Engine: PostgreSQL (latest version)
3. Template: Production
4. DB Instance: **db.t4g.medium** (minimum)
5. Storage: gp3
6. Allocated Storage: 100 GB
7. Storage Autoscaling: ENABLED
8. Multi-AZ: YES (recommended)
9. Public Access: YES (for initial setup)
10. VPC Security Group: Create new (allow port 5432)
11. Database name: market-mindset
12. Master username: postgres
13. Master password: [strong password]

# Note the endpoint (e.g., mydb.abc123.us-east-1.rds.amazonaws.com)
```

### Configure Security Group (DO THIS AFTER EC2 SETUP)
```bash
# IMPORTANT: Come back to this step after creating your EC2 instance in Step 2
# You'll need the EC2 security group ID first

# Add inbound rule to RDS security group:
- Type: PostgreSQL
- Port: 5432
- Source: Custom - Select your EC2 instance's security group ID (sg-xxxxx)
# Example: sg-0a1b2c3d4e5f6g7h8

# For initial testing only, you can temporarily allow your IP:
- Source: My IP (for testing connection from your laptop)
# REMOVE this rule after setup is complete for security
```

---

## Step 2: Launch EC2 Instance (Production)

### Create EC2 Instance
```bash
# Via AWS Console:
1. Go to EC2 → Launch Instance
2. Name: market-mindset-server
3. AMI: Ubuntu Server 22.04 LTS
4. Instance Type: **t3.large** (minimum recommended)
5. Key Pair: Create new or use existing (download .pem file)
6. Network Settings:
   - Create security group: market-mindset-sg
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) from anywhere (0.0.0.0/0)
   - Allow HTTPS (port 443) from anywhere (0.0.0.0/0)
7. Storage: 60 GB gp3 (or more)
8. Launch Instance

# IMPORTANT: Note your security group ID (sg-xxxxx) 
# You'll need this to configure RDS security group in Step 1
```

### Allocate Elastic IP
```bash
# Via AWS Console:
1. EC2 → Elastic IPs → Allocate Elastic IP
2. Associate with your EC2 instance
# This gives you a static IP address
```

---

## Step 3: Setup EC2 Server

### Connect to EC2
```bash
# Set permissions on your key file
chmod 400 your-key.pem

# Connect to your EC2 instance
ssh -i your-key.pem ubuntu@your-elastic-ip
```

### First-Time Setup: Upload Your Code

**Option A: Using Git (Recommended)**
```bash
# On EC2:
cd /home/ubuntu
git clone https://github.com/yourusername/market-mindset.git app
cd app
```

**Option B: Using SCP (if not using Git)**
```bash
# On your LOCAL machine (not EC2):
# From your project directory:
scp -i your-key.pem -r /Users/amrita/uchicago/thesis/market-mindset ubuntu@your-elastic-ip:/home/ubuntu/app

# Then SSH into EC2:
ssh -i your-key.pem ubuntu@your-elastic-ip
cd /home/ubuntu/app
```

### Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3-pip python3-venv nginx git

# Install PostgreSQL client
sudo apt install -y postgresql-client

# Clone your repository (or upload files)
git clone your-repo-url
# OR upload using scp:
# scp -i your-key.pem -r /local/path ubuntu@your-elastic-ip:/home/ubuntu/
```

### Setup Python Environment
```bash
cd /home/ubuntu/app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Configure Environment Variables
```bash
# Create .env file
cp .env.example .env
nano .env

# Edit with your RDS details:
DB_HOST=your-rds-endpoint.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=market-mindset
DB_USER=postgres
DB_PASSWORD=your-rds-password
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Pooling and DB reliability
DB_POOL_MIN_CONN=2
DB_POOL_MAX_CONN=30
DB_CONNECT_TIMEOUT=5
```

### Initialize Database (First Deploy Only)
```bash
# First, test the connection from EC2 to RDS:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d market-mindset -c "SELECT version();"
# You'll be prompted for the password you set during RDS creation

# If connection works, initialize the database schema once on first deployment:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d market-mindset -f schema.sql

# Verify tables were created:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d market-mindset -c "\dt"
# You should see: participants, demographics, task_responses, portfolio, confidence_risk, feedback, page_visits, events
```

---

## Step 4: Setup Gunicorn Service

### Create Gunicorn Service File
```bash
sudo nano /etc/systemd/system/market-mindset.service
```

### Add this content:
```ini
[Unit]
Description=Market Mindset Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/app
Environment="PATH=/home/ubuntu/app/venv/bin"
EnvironmentFile=/home/ubuntu/app/.env
ExecStart=/home/ubuntu/app/venv/bin/gunicorn \
    --workers 6 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 60 \
    --keep-alive 5 \
    --worker-tmp-dir /dev/shm \
    --bind 127.0.0.1:8050 \
    --timeout 120 \
    --access-logfile /home/ubuntu/app/logs/access.log \
    --error-logfile /home/ubuntu/app/logs/error.log \
    application:application

Restart=always
RestartSec=5
TimeoutStartSec=180
TimeoutStopSec=60

LimitNOFILE=4096

[Install]
WantedBy=multi-user.target
```

### Create logs directory
```bash
mkdir -p /home/ubuntu/app/logs
```

### Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl start market-mindset
sudo systemctl enable market-mindset
sudo systemctl status market-mindset
```

---

## Step 5: Configure Nginx

### Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/market-mindset
```

### Add this content:
```nginx
server {
    listen 80;
    server_name your-elastic-ip;  # Or your domain name

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;

        # Buffering
        proxy_buffering off;
    }

    location = /healthz {
        access_log off;
        add_header Content-Type text/plain;
        return 200 "ok\n";
    }

    location = /nginx_status {
        stub_status;
        access_log off;
        allow 127.0.0.1;
        deny all;
    }
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/market-mindset /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 6: Setup SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (only if you have a domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

---

## Step 7: Update App for Production

The app is already integrated with PostgreSQL in this repository.

Before launch, verify these are present on the server:
- `database.py` (DB connection pool + persistence)
- `schema.sql` (tables and view creation)
- `.env` with valid `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

Quick DB integration check:
```bash
cd /home/ubuntu/app
source venv/bin/activate
python3 -c "from database import get_db_connection; \
with get_db_connection() as conn: \
    cur=conn.cursor(); cur.execute('SELECT 1'); print('DB OK')"
```

---

## Testing

1. **Access App:** http://your-elastic-ip (or https://yourdomain.com)
2. **Check Logs:** 
   ```bash
   sudo journalctl -u market-mindset -f
   tail -f /home/ubuntu/app/logs/error.log
   ```
3. **Database Check:**
   ```bash
   psql -h your-rds-endpoint -U postgres -d market-mindset -c "SELECT COUNT(*) FROM participants;"
   ```

---

## Monitoring & Maintenance

### View Logs
```bash
# Application logs
tail -f /home/ubuntu/app/logs/error.log
tail -f /home/ubuntu/app/logs/access.log

# System logs
sudo journalctl -u market-mindset -n 100 -f
sudo journalctl -u nginx -n 100 -f

# Nginx app logs
sudo tail -f /var/log/nginx/market-mindset_access.log
sudo tail -f /var/log/nginx/market-mindset_error.log

# Quick health checks
curl -fsS http://127.0.0.1/healthz
curl -fsS http://127.0.0.1/ >/dev/null && echo "app ok"
```

### Database Backup
```bash
# Automated daily backup script
pg_dump -h your-rds-endpoint -U postgres market-mindset > backup_$(date +%Y%m%d).sql
```

### Capacity Checks
- CloudWatch EC2: CPUUtilization, Memory (if agent), NetworkIn/Out
- CloudWatch RDS: CPUUtilization, DatabaseConnections, FreeableMemory, Read/Write latency
- Alert on sustained high CPU (>70%), elevated DB connections, or rising 5xx rates

---

## Cost Note

This guide targets reliability rather than free-tier cost minimization.
Exact cost depends on region and traffic, but this profile is intentionally above free tier to reduce failure risk under 250 concurrent participants.

---

## Data Export & Analysis

### Export Data for Analysis (Do this regularly during study)
```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@your-elastic-ip

# Export participant data to CSV files
cd /home/ubuntu/app

# All participants summary
psql -h your-rds-endpoint -U postgres -d market-mindset -c "
COPY (SELECT * FROM participant_summary ORDER BY created_at) 
TO STDOUT WITH CSV HEADER" > participants_export.csv

# Demographics data
psql -h your-rds-endpoint -U postgres -d market-mindset -c "
COPY (SELECT p.participant_id, p.created_at, d.* FROM participants p 
LEFT JOIN demographics d ON p.participant_id = d.participant_id 
ORDER BY p.created_at) 
TO STDOUT WITH CSV HEADER" > demographics_export.csv

# Task responses (investment decisions)
psql -h your-rds-endpoint -U postgres -d market-mindset -c "
COPY (SELECT p.participant_id, p.created_at, tr.* FROM participants p 
JOIN task_responses tr ON p.participant_id = tr.participant_id 
ORDER BY p.created_at, tr.task_id) 
TO STDOUT WITH CSV HEADER" > task_responses_export.csv

# Confidence and risk ratings
psql -h your-rds-endpoint -U postgres -d market-mindset -c "
COPY (SELECT p.participant_id, p.created_at, cr.* FROM participants p 
LEFT JOIN confidence_risk cr ON p.participant_id = cr.participant_id) 
TO STDOUT WITH CSV HEADER" > confidence_risk_export.csv

# Portfolio performance
psql -h your-rds-endpoint -U postgres -d market-mindset -c "
COPY (SELECT * FROM portfolio ORDER BY participant_id, task_id) 
TO STDOUT WITH CSV HEADER" > portfolio_export.csv

# Download to your local machine
# Run this from your LOCAL terminal:
scp -i your-key.pem ubuntu@your-elastic-ip:/home/ubuntu/app/*_export.csv ./study_data/
```

## Shutdown/Cleanup After Study

```bash
# 1. Export all data (full database backup)
ssh -i your-key.pem ubuntu@your-elastic-ip
pg_dump -h your-rds-endpoint -U postgres market-mindset > final_backup_$(date +%Y%m%d).sql

# 2. Export CSVs (see Data Export section above)

# 3. Download everything to local machine
# From your LOCAL terminal:
mkdir -p study_final_data
scp -i your-key.pem ubuntu@your-elastic-ip:/home/ubuntu/app/*_export.csv ./study_final_data/
scp -i your-key.pem ubuntu@your-elastic-ip:/home/ubuntu/final_backup_*.sql ./study_final_data/

# 4. Verify you have all the data locally
ls -lh study_final_data/

# 5. Delete AWS resources via Console:
- Terminate EC2 instance
- Delete RDS database (can create final snapshot if you want extra backup)
- Release Elastic IP
- Delete security groups
- Delete key pair (if not using elsewhere)

# This stops all charges immediately
```
