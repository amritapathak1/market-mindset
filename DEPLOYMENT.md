# AWS Deployment Guide - Free Tier

## Total Estimated Cost: $0/month (first 12 months)

---

## Prerequisites

1. AWS Account (free tier eligible)
2. Domain name (optional, ~$12/year) OR use EC2 public IP

---

## Step 1: Setup RDS PostgreSQL (Free Tier)

### Create RDS Instance
```bash
# Via AWS Console:
1. Go to RDS → Create Database
2. Engine: PostgreSQL (latest version)
3. Template: **Free tier**
4. DB Instance: db.t2.micro (750 hrs/month free)
5. Storage: 20 GB GP2 (max for free tier)
6. Allocated Storage: 20 GB
7. Storage Autoscaling: DISABLE (to stay in free tier)
8. Multi-AZ: NO (required for free tier)
9. Public Access: YES (for initial setup)
10. VPC Security Group: Create new (allow port 5432)
11. Database name: investment_study
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

## Step 2: Launch EC2 Instance (Free Tier)

### Create EC2 Instance
```bash
# Via AWS Console:
1. Go to EC2 → Launch Instance
2. Name: market-mindset-server
3. AMI: Ubuntu Server 22.04 LTS (free tier eligible)
4. Instance Type: **t2.micro** (750 hrs/month free)
5. Key Pair: Create new or use existing (download .pem file)
6. Network Settings:
   - Create security group: market-mindset-sg
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) from anywhere (0.0.0.0/0)
   - Allow HTTPS (port 443) from anywhere (0.0.0.0/0)
7. Storage: 30 GB GP2 (30 GB free tier limit)
8. Launch Instance

# IMPORTANT: Note your security group ID (sg-xxxxx) 
# You'll need this to configure RDS security group in Step 1
```

### Allocate Elastic IP (Free while attached)
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
DB_NAME=investment_study
DB_USER=postgres
DB_PASSWORD=your-rds-password
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
```

### Initialize Database
```bash
# First, test the connection from EC2 to RDS:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d investment_study -c "SELECT version();"
# You'll be prompted for the password you set during RDS creation

# If connection works, initialize the database schema:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d investment_study -f schema.sql

# Verify tables were created:
psql -h your-rds-endpoint.us-east-1.rds.amazonaws.com -U postgres -d investment_study -c "\dt"
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
    --workers 2 \
    --bind 127.0.0.1:8050 \
    --timeout 120 \
    --access-logfile /home/ubuntu/app/logs/access.log \
    --error-logfile /home/ubuntu/app/logs/error.log \
    app:app.server

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
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
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

The app needs modifications to integrate with the database. I'll create those files next.

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
   psql -h your-rds-endpoint -U postgres -d investment_study -c "SELECT COUNT(*) FROM participants;"
   ```

---

## Monitoring & Maintenance

### View Logs
```bash
# Application logs
tail -f /home/ubuntu/app/logs/access.log
tail -f /home/ubuntu/app/logs/error.log

# System logs
sudo journalctl -u market-mindset -n 100 -f
sudo journalctl -u nginx -n 100 -f
```

### Database Backup
```bash
# Automated daily backup script
pg_dump -h your-rds-endpoint -U postgres investment_study > backup_$(date +%Y%m%d).sql
```

### Check Free Tier Usage
- Go to AWS Console → Billing → Free Tier
- Monitor RDS hours (should be <750/month)
- Monitor EC2 hours (should be <750/month)

---

## Costs Breakdown

- **EC2 t2.micro:** $0 (750 hrs/month free for 12 months)
- **RDS db.t2.micro:** $0 (750 hrs/month free for 12 months)
- **20 GB Storage:** $0 (included in RDS free tier)
- **Elastic IP:** $0 (while attached to running instance)
- **Data Transfer:** $0 (100 GB/month free for 12 months)
- **Total:** **$0/month** for first year

**After 12 months (if you keep it):**
- EC2 t2.micro: ~$8-10/month
- RDS db.t2.micro: ~$15-20/month
- Total: ~$25-30/month

---

## Data Export & Analysis

### Export Data for Analysis (Do this regularly during study)
```bash
# Connect to EC2
ssh -i your-key.pem ubuntu@your-elastic-ip

# Export participant data to CSV files
cd /home/ubuntu/app

# All participants summary
psql -h your-rds-endpoint -U postgres -d investment_study -c "
COPY (SELECT * FROM participant_summary ORDER BY created_at) 
TO STDOUT WITH CSV HEADER" > participants_export.csv

# Demographics data
psql -h your-rds-endpoint -U postgres -d investment_study -c "
COPY (SELECT p.participant_id, p.created_at, d.* FROM participants p 
LEFT JOIN demographics d ON p.participant_id = d.participant_id 
ORDER BY p.created_at) 
TO STDOUT WITH CSV HEADER" > demographics_export.csv

# Task responses (investment decisions)
psql -h your-rds-endpoint -U postgres -d investment_study -c "
COPY (SELECT p.participant_id, p.created_at, tr.* FROM participants p 
JOIN task_responses tr ON p.participant_id = tr.participant_id 
ORDER BY p.created_at, tr.task_id) 
TO STDOUT WITH CSV HEADER" > task_responses_export.csv

# Confidence and risk ratings
psql -h your-rds-endpoint -U postgres -d investment_study -c "
COPY (SELECT p.participant_id, p.created_at, cr.* FROM participants p 
LEFT JOIN confidence_risk cr ON p.participant_id = cr.participant_id) 
TO STDOUT WITH CSV HEADER" > confidence_risk_export.csv

# Portfolio performance
psql -h your-rds-endpoint -U postgres -d investment_study -c "
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
pg_dump -h your-rds-endpoint -U postgres investment_study > final_backup_$(date +%Y%m%d).sql

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
