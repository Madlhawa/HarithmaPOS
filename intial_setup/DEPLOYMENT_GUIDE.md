# 🚀 Ubuntu Server Deployment Guide

## Prerequisites
- Ubuntu 20.04+ server with SSH access
- User with sudo privileges
- Domain name (optional, can use IP address)

---

## ⚡ Quick Start (5 Minutes)

### Automated Deployment (Recommended)

1. **Upload your code to server:**
   ```bash
   # From your local machine
   scp -r . user@your-server:/tmp/harithma-pos
   ```

2. **SSH into server and run:**
   ```bash
   ssh user@your-server
   cd /tmp/harithma-pos
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Follow prompts** - script does everything automatically!

4. **Create admin user:**
   ```bash
   cd /opt/harithma-pos
   source venv/bin/activate
   export $(cat .env | xargs)
   flask create-user
   ```

5. **Done!** Access at `http://your-server-ip` or your domain

### What the Script Does

✅ Installs Python, PostgreSQL, Nginx  
✅ Creates database and user  
✅ Sets up virtual environment  
✅ Installs dependencies  
✅ Creates systemd service (auto-start on boot)  
✅ Optionally configures Nginx reverse proxy  
✅ Generates secure passwords and keys  

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

### Step 4: Copy Application Files
```bash
# Copy your application files here
# Or clone from git:
git clone your-repo-url .
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
\q
```

**Or use one-liner:**
```bash
sudo -u postgres psql -c "CREATE DATABASE harithma_pos;"
sudo -u postgres psql -c "CREATE USER harithma_user WITH PASSWORD 'changeme123';"
sudo -u postgres psql -c "GRANT ALL ON DATABASE harithma_pos TO harithma_user;"
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
```

**Generate secret key:**
```bash
openssl rand -hex 32
```

### Step 8: Initialize Database
```bash
export $(cat .env | xargs)
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

Add (replace `your-username` with your actual username):
```ini
[Unit]
Description=Harithma POS Gunicorn Application Server
After=network.target postgresql.service

[Service]
User=your-username
Group=your-username
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

### Step 11: Create Admin User
```bash
cd /opt/harithma-pos
source venv/bin/activate
export $(cat .env | xargs)
flask create-user
```

---

## 🔧 Post-Deployment

### Useful Commands

**View logs:**
```bash
sudo journalctl -u harithma-pos -f
```

**Restart service:**
```bash
sudo systemctl restart harithma-pos
```

**Check status:**
```bash
sudo systemctl status harithma-pos
```

**Update application:**
```bash
cd /opt/harithma-pos
source venv/bin/activate
git pull  # if using git
pip install -r requirements.txt
flask db upgrade
sudo systemctl restart harithma-pos
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
   sudo ufw enable
   ```

3. **Secure PostgreSQL:**
   - Edit `/etc/postgresql/*/main/pg_hba.conf`
   - Restrict access to localhost only

4. **Regular Backups:**
   ```bash
   # Create backup directory
   sudo mkdir -p /backups
   sudo chown $USER:$USER /backups
   
   # Add to crontab (crontab -e)
   0 2 * * * pg_dump -U harithma_user harithma_pos > /backups/harithma_pos_$(date +\%Y\%m\%d).sql
   ```

---

## 🐛 Troubleshooting

### Service won't start:
```bash
sudo journalctl -u harithma-pos -n 50
# Check .env file exists and has correct values
# Check database is accessible
# Check user permissions
```

### Database connection errors:
```bash
sudo -u postgres psql -c "\l"  # List databases
sudo -u postgres psql harithma_pos  # Test connection
# Verify .env file has correct database URI
```

### Port already in use:
```bash
sudo netstat -tlnp | grep 8080
# Change port in gunicorn_config.py if needed
```

### Can't connect from browser:
- Check firewall: `sudo ufw status`
- Check service: `sudo systemctl status harithma-pos`
- Check Nginx: `sudo systemctl status nginx`
- Check logs: `sudo journalctl -u harithma-pos -n 50`

### Permission errors:
```bash
# Ensure correct ownership
sudo chown -R $USER:$USER /opt/harithma-pos
# Check service file has correct user
```

---

## ✅ Production Checklist

- [ ] Environment variables configured in `.env`
- [ ] SECRET_KEY is strong and unique (use `openssl rand -hex 32`)
- [ ] Database credentials are secure
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

---

## 📋 Quick Reference

**Application Directory:** `/opt/harithma-pos`  
**Service Name:** `harithma-pos`  
**Port:** `8080` (internal), `80/443` (Nginx)  
**Database:** PostgreSQL `harithma_pos`  
**Logs:** `sudo journalctl -u harithma-pos -f`  
**Environment File:** `/opt/harithma-pos/.env`  
**Nginx Config:** `/etc/nginx/sites-available/harithma-pos`  
**Service Config:** `/etc/systemd/system/harithma-pos.service`

---

## 🚨 Emergency Commands

**Stop application:**
```bash
sudo systemctl stop harithma-pos
```

**Start application:**
```bash
sudo systemctl start harithma-pos
```

**View real-time logs:**
```bash
sudo journalctl -u harithma-pos -f
```

**Check if port is listening:**
```bash
sudo ss -tlnp | grep 8080
```

**Test database connection:**
```bash
cd /opt/harithma-pos
source venv/bin/activate
export $(cat .env | xargs)
python -c "from harithmapos import create_app, db; app = create_app(); app.app_context().push(); print('DB OK' if db.engine.connect() else 'DB FAIL')"
```

---

**That's it! Your application should be running.** 🎉
