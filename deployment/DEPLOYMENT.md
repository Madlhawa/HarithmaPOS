# 🚀 Complete Ubuntu Server Deployment Guide

## Prerequisites
- Ubuntu 20.04+ server with SSH access
- Root or sudo privileges
- Domain name (optional, can use IP address)

---

## ⚡ Quick Start (Automated - 10 Minutes)

### Complete Deployment (Application + RabbitMQ)

1. **SSH into your server:**
   ```bash
   ssh root@your-server
   ```

2. **Run the deployment script:**
   ```bash
   # Clone the repository
   git clone https://github.com/Madlhawa/HarithmaPOS.git /tmp/harithma-pos
   cd /tmp/harithma-pos/deployment
   
   # Make executable and run
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

3. **Follow the prompts:**
   - Script will deploy the application
   - Optionally set up Nginx
   - Optionally set up RabbitMQ

4. **Create admin user:**
   ```bash
   cd /opt/harithma-pos
   source venv/bin/activate
   export $(grep -v '^#' .env | grep -v '^$' | xargs)
   flask create-user
   ```

5. **Done!** Access at `http://your-server-ip` or your domain

### What the Scripts Do

**Main Deployment Script (`deploy.sh`):**
✅ Clones code from GitHub repository  
✅ Installs Python, PostgreSQL, Nginx  
✅ Creates database and user with proper permissions  
✅ Sets up virtual environment  
✅ Installs dependencies  
✅ Creates systemd service (auto-start on boot)  
✅ Optionally configures Nginx reverse proxy  
✅ Generates secure passwords and keys  
✅ Optionally runs RabbitMQ setup  

**RabbitMQ Setup Script (`setup_rabbitmq.sh`):**
✅ Installs RabbitMQ server using official repositories  
✅ Creates dedicated user with secure password  
✅ Sets up required queues  
✅ Updates .env file with credentials  
✅ Enables management web UI  

---

## 📖 Detailed Manual Deployment

### Step 1: Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### Step 2: Install Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git libpq-dev python3-dev
```

### Step 3: Create Application Directory
```bash
sudo mkdir -p /opt/harithma-pos
sudo chown $USER:$USER /opt/harithma-pos
cd /opt/harithma-pos
```

### Step 4: Clone Application from GitHub
```bash
# Clone the repository
git clone https://github.com/Madlhawa/HarithmaPOS.git .
```

### Step 5: Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 6: Configure Database

Create database and user:
```bash
sudo -u postgres psql
```

In PostgreSQL prompt:
```sql
CREATE DATABASE harithma_pos;
CREATE USER harithma_user WITH PASSWORD 'your_secure_password';
ALTER ROLE harithma_user SET client_encoding TO 'utf8';
ALTER ROLE harithma_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE harithma_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE harithma_pos TO harithma_user;
GRANT ALL ON SCHEMA public TO harithma_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO harithma_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO harithma_user;
\q
```

**Or use one-liner:**
```bash
sudo -u postgres psql -c "CREATE DATABASE harithma_pos;"
sudo -u postgres psql -c "CREATE USER harithma_user WITH PASSWORD 'changeme123';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE harithma_pos TO harithma_user;"
sudo -u postgres psql -d harithma_pos -c "GRANT ALL ON SCHEMA public TO harithma_user;"
```

### Step 7: Create Environment File
```bash
nano .env
```

Add:
```env
HARITHMA_DATABASE_URI=postgresql://harithma_user:your_secure_password@localhost:5432/harithma_pos
HARITHMA_SECRET_KEY=your-secret-key-here-generate-with-openssl-rand-hex-32
HARITHMA_EMAIL=your-email@example.com
HARITHMA_PASSWORD=your-email-password
FLASK_APP=app.py
FLASK_ENV=production

# RabbitMQ (optional - add after RabbitMQ setup)
RABBIT_MQ_HOST=localhost
RABBIT_MQ_USERNAME=harithma_rabbitmq
RABBIT_MQ_PASSWORD=your_rabbitmq_password
```

**Generate secret key:**
```bash
openssl rand -hex 32
```

### Step 8: Initialize Database
```bash
export $(grep -v '^#' .env | grep -v '^$' | xargs)
flask db upgrade
```

**If first time:**
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Step 9: Create Systemd Service
```bash
sudo nano /etc/systemd/system/harithma-pos.service
```

Add (replace `harithma` with your application user):
```ini
[Unit]
Description=Harithma POS Gunicorn Application Server
After=network.target postgresql.service

[Service]
User=harithma
Group=harithma
WorkingDirectory=/opt/harithma-pos
Environment="PATH=/opt/harithma-pos/venv/bin"
EnvironmentFile=/opt/harithma-pos/.env
ExecStart=/opt/harithma-pos/venv/bin/gunicorn --config /opt/harithma-pos/gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable harithma-pos
sudo systemctl start harithma-pos
sudo systemctl status harithma-pos
```

### Step 10: Setup Nginx (Optional but Recommended)
```bash
sudo nano /etc/nginx/sites-available/harithma-pos
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your server IP or _ for any

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/harithma-pos/harithmapos/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/harithma-pos /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### Step 11: Setup RabbitMQ (Optional)

#### Option A: Using Setup Script (Recommended)
```bash
cd /opt/harithma-pos/deployment
chmod +x setup_rabbitmq.sh
sudo ./setup_rabbitmq.sh
```

#### Option B: Manual Setup

**1. Install RabbitMQ:**
```bash
# Install prerequisites
sudo apt-get install -y curl gnupg apt-transport-https

# Add Team RabbitMQ signing key
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | sudo gpg --dearmor | sudo tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null

# Detect Ubuntu version
CODENAME=$(lsb_release -cs)  # or manually: jammy, focal, noble

# Add repositories (replace $CODENAME with your version)
sudo tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-erlang/ubuntu/$CODENAME $CODENAME main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-erlang/ubuntu/$CODENAME $CODENAME main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-server/ubuntu/$CODENAME $CODENAME main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-server/ubuntu/$CODENAME $CODENAME main
EOF

# Update and install
sudo apt-get update -y
sudo apt-get install -y erlang-base erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
                        erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
                        erlang-runtime-tools erlang-snmp erlang-ssl \
                        erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl
sudo apt-get install rabbitmq-server -y --fix-missing
```

**2. Start and Enable:**
```bash
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

**3. Wait for RabbitMQ to be ready:**
```bash
# Wait until this command succeeds
sudo rabbitmqctl status
```

**4. Enable Management UI:**
```bash
sudo rabbitmq-plugins enable rabbitmq_management
```

**5. Create User:**
```bash
sudo rabbitmqctl add_user harithma_rabbitmq your_secure_password
sudo rabbitmqctl set_user_tags harithma_rabbitmq administrator
sudo rabbitmqctl set_permissions -p / harithma_rabbitmq ".*" ".*" ".*"
```

**6. Disable Guest User (Security):**
```bash
sudo rabbitmqctl delete_user guest
```

**7. Update .env File:**
Add to `/opt/harithma-pos/.env`:
```env
RABBIT_MQ_HOST=localhost
RABBIT_MQ_USERNAME=harithma_rabbitmq
RABBIT_MQ_PASSWORD=your_secure_password
```

**8. Restart Application:**
```bash
sudo systemctl restart harithma-pos
```

### Step 12: Create Admin User
```bash
cd /opt/harithma-pos
source venv/bin/activate
export $(grep -v '^#' .env | grep -v '^$' | xargs)
flask create-user
```

---

## 🔧 Post-Deployment

### Useful Commands

**Application:**
```bash
# View logs
sudo journalctl -u harithma-pos -f

# Restart service
sudo systemctl restart harithma-pos

# Check status
sudo systemctl status harithma-pos

# Update application
cd /opt/harithma-pos
source venv/bin/activate
git pull
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart harithma-pos
```

**RabbitMQ:**
```bash
# Check status
sudo systemctl status rabbitmq-server

# View logs
sudo journalctl -u rabbitmq-server -f

# List users
sudo rabbitmqctl list_users

# List queues
sudo rabbitmqctl list_queues

# Restart
sudo systemctl restart rabbitmq-server
```

### Security Recommendations

1. **Setup SSL/HTTPS** with Let's Encrypt:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

2. **Configure Firewall:**
   ```bash
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   # RabbitMQ ports (only if accessing externally)
   # sudo ufw allow 5672/tcp
   # sudo ufw allow 15672/tcp
   sudo ufw enable
   ```

3. **Secure PostgreSQL:**
   - Edit `/etc/postgresql/*/main/pg_hba.conf`
   - Restrict access to localhost only

4. **Secure RabbitMQ:**
   - Management UI should be behind firewall
   - Use strong passwords
   - Disable guest user (done automatically by script)

5. **Regular Backups:**
   ```bash
   # Create backup directory
   sudo mkdir -p /backups
   sudo chown $USER:$USER /backups
   
   # Add to crontab (crontab -e)
   0 2 * * * pg_dump -U harithma_user harithma_pos > /backups/harithma_pos_$(date +\%Y\%m\%d).sql
   ```

---

## 🐛 Troubleshooting

### Application Issues

**Service won't start:**
```bash
sudo journalctl -u harithma-pos -n 50
# Check .env file exists and has correct values
# Check database is accessible
# Check user permissions
```

**Database connection errors:**
```bash
sudo -u postgres psql -c "\l"  # List databases
sudo -u postgres psql harithma_pos  # Test connection
# Verify .env file has correct database URI
# Check schema permissions: sudo -u postgres psql -d harithma_pos -c "\dn"
```

**Port already in use:**
```bash
sudo netstat -tlnp | grep 8080
# Change port in gunicorn_config.py if needed
```

**Can't connect from browser:**
- Check firewall: `sudo ufw status`
- Check service: `sudo systemctl status harithma-pos`
- Check Nginx: `sudo systemctl status nginx`
- Check logs: `sudo journalctl -u harithma-pos -n 50`

**Permission errors:**
```bash
# Ensure correct ownership
sudo chown -R harithma:harithma /opt/harithma-pos
# Check service file has correct user
```

### RabbitMQ Issues

**RabbitMQ won't start:**
```bash
sudo systemctl status rabbitmq-server
sudo journalctl -u rabbitmq-server -f
# Check if Erlang is installed correctly
```

**Can't connect to RabbitMQ:**
```bash
# Check if service is running
sudo systemctl status rabbitmq-server

# Check if RabbitMQ is ready
sudo rabbitmqctl status

# Check Erlang cookie (if clustering)
sudo cat /var/lib/rabbitmq/.erlang.cookie
```

**User creation fails:**
```bash
# Wait for RabbitMQ to be fully ready
sudo rabbitmqctl status

# Try again
sudo rabbitmqctl add_user harithma_rabbitmq password
```

**Reset RabbitMQ (if needed):**
```bash
sudo systemctl stop rabbitmq-server
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl start_app
sudo systemctl start rabbitmq-server
```

---

## ✅ Production Checklist

- [ ] Environment variables configured in `.env`
- [ ] SECRET_KEY is strong and unique (use `openssl rand -hex 32`)
- [ ] Database credentials are secure
- [ ] Database schema permissions granted (PostgreSQL 15+)
- [ ] SSL/HTTPS configured (Let's Encrypt)
- [ ] Firewall rules set (UFW)
- [ ] Regular backups scheduled
- [ ] Monitoring/logging configured
- [ ] Admin user created
- [ ] Debug mode disabled (check app.py - should use FLASK_DEBUG env var)
- [ ] Static files served correctly
- [ ] Nginx reverse proxy configured
- [ ] Systemd service enabled and running
- [ ] PostgreSQL secured (local access only)
- [ ] RabbitMQ installed and configured (if needed)
- [ ] RabbitMQ user created with strong password
- [ ] RabbitMQ guest user disabled
- [ ] Application restarted after RabbitMQ setup

---

## 📋 Quick Reference

**Application:**
- **Directory:** `/opt/harithma-pos`
- **Service:** `harithma-pos`
- **Port:** `8080` (internal), `80/443` (Nginx)
- **Database:** PostgreSQL `harithma_pos`
- **User:** `harithma`
- **Logs:** `sudo journalctl -u harithma-pos -f`
- **Environment File:** `/opt/harithma-pos/.env`
- **Nginx Config:** `/etc/nginx/sites-available/harithma-pos`
- **Service Config:** `/etc/systemd/system/harithma-pos.service`

**RabbitMQ:**
- **Service:** `rabbitmq-server`
- **AMQP Port:** `5672`
- **Management UI:** `http://your-server-ip:15672`
- **Logs:** `sudo journalctl -u rabbitmq-server -f`
- **Queue Name:** `harithmaq` (created automatically)
- **Config:** `/etc/rabbitmq/rabbitmq.conf`

---

## 🚨 Emergency Commands

**Application:**
```bash
# Stop
sudo systemctl stop harithma-pos

# Start
sudo systemctl start harithma-pos

# View real-time logs
sudo journalctl -u harithma-pos -f

# Check port
sudo ss -tlnp | grep 8080

# Test database
cd /opt/harithma-pos
source venv/bin/activate
export $(grep -v '^#' .env | grep -v '^$' | xargs)
python -c "from harithmapos import create_app, db; app = create_app(); app.app_context().push(); print('DB OK' if db.engine.connect() else 'DB FAIL')"
```

**RabbitMQ:**
```bash
# Stop
sudo systemctl stop rabbitmq-server

# Start
sudo systemctl start rabbitmq-server

# Check status
sudo rabbitmqctl status

# View logs
sudo journalctl -u rabbitmq-server -f
```

---

## 📝 Running SQL Files

To run SQL files manually:

```bash
# Run sample items insert
sudo -u postgres psql -d harithma_pos -f /opt/harithma-pos/deployment/manual_setup/sample_items_insert.sql

# Or from application directory
cd /opt/harithma-pos
sudo -u postgres psql -d harithma_pos -f deployment/manual_setup/sample_items_insert.sql
```

---

**That's it! Your application should be running.** 🎉
