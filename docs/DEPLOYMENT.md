# 🚀 Complete Ubuntu Server Deployment Guide

## Setting up a new server

`deployment/deploy.sh` builds a server that matches production in one run. It is safe
to run again: it never deletes the app folder, the database or `.env`.

### What you need
- A fresh **Ubuntu 22.04** server (1 GB memory works; 2 GB gives more headroom), with root SSH access.
- The domain name, if the site should have HTTPS (it can point at the new server later).
- To move existing data: a fresh backup from the old server, taken just before the move:
  ```bash
  sudo -u postgres pg_dump -Fc harithma_pos > /root/harithma_pos_move.dump
  ```
  Copy it to the new server (for example with `scp`). Stop the old app first
  (`systemctl stop harithma-pos`) so no sales are made after the backup.
- The public half of the GitHub deploy key, for `--deploy-key` (see below).

### GitHub deploy key

GitHub Actions deploys by logging in to the server with this key. Pass its public
half to `--deploy-key`, in quotes:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIItRF0RcRzYO0X43G/sliz8rIh2XWzcEtsiAC1Dv9Og7 github-actions-deploy harithma.lk
```

- **It is safe to publish.** A public key only lets in whoever holds the matching
  private key. The private half is only in GitHub's `DEPLOY_SSH_KEY` secret; it is
  never written to the server or to this repository.
- **It can only deploy.** `deploy.sh` adds it to `/root/.ssh/authorized_keys` with
  `restrict,command="/usr/local/bin/harithma-ci-deploy"`: no shell, no port forwarding,
  only "deploy a commit" or "roll back", and the script checks its arguments.
- **If the private key leaks** (or you want to replace it): make a new pair with
  `ssh-keygen -t ed25519 -N "" -C github-actions-deploy -f deploy_key`, put the
  contents of `deploy_key` in the `DEPLOY_SSH_KEY` secret, run `deploy.sh` again with
  `--deploy-key "$(cat deploy_key.pub)"`, delete the old line from
  `/root/.ssh/authorized_keys`, delete the `deploy_key` file, and update the key above.

### Steps
1. **Get the script and run it** on the new server as root:
   ```bash
   curl -fsSLo deploy.sh https://raw.githubusercontent.com/Madlhawa/HarithmaPOS/main/deployment/deploy.sh
   sudo bash deploy.sh --domain harithma.lk --developer you@example.com \
       --restore /root/harithma_pos_move.dump \
       --deploy-key "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIItRF0RcRzYO0X43G/sliz8rIh2XWzcEtsiAC1Dv9Og7 github-actions-deploy harithma.lk"
   ```
   Leave out `--restore` to start with an empty database. `--email you@example.com` adds
   a contact address for certificate expiry notices. `sudo bash deploy.sh --help` lists the options.
2. **Fill in `.env`.** The script writes `/opt/harithma-pos/.env` with a new database
   password and secret key. Copy the email and SMS (`NOTIFYLK_*`) values
   from the old server's `.env`, then `systemctl restart harithma-pos`.
3. **New, empty database only:** create the first owner account with the command the
   script prints at the end (`flask create-user`).
4. **Point DNS at the new server.** Until it does, the site is served over plain
   HTTP by IP address. Once it does, run the script again with the same `--domain`:
   it gets the HTTPS certificate, switches nginx to HTTPS and turns on secure cookies.
5. **Point GitHub's deploys at the new server.** In the repository, Settings → Secrets
   and variables → Actions → **Variables**, set the two values the script printed:
   - `DEPLOY_HOST`: the domain (for example `harithma.lk`).
   - `DEPLOY_HOST_KEY`: the new server's SSH key (`ssh-ed25519 AAAA...`).

   The `DEPLOY_SSH_KEY` secret stays the same. Without these variables the workflows
   use the current server's values, so deploys are refused (safely) until they are set.
6. **Check:** open the site and sign in, open *Developer → Monitor*, and push a small
   change (or run *Test and deploy* by hand from the Actions tab) to see a deploy succeed.
   Keep the old server for a few days before deleting it.

### What the script sets up

| Piece | Details | Source in the repository |
|---|---|---|
| System | Package updates, automatic security updates, firewall (SSH, 80, 443 only; an address opening 6+ SSH connections in 30 s is blocked), 2 GB swap | `deployment/deploy.sh` |
| SSH | Keys only (no passwords, root by key only), 4 tries per connection, 30 s to log in, no X11 forwarding | `deployment/server/sshd-harithma.conf` |
| App | `harithma` user, code in `/opt/harithma-pos`, Python venv, `.env` | `deployment/deploy.sh` |
| Database | PostgreSQL database `harithma_pos` owned by `harithma_user`; restore or `flask db upgrade` | `deployment/deploy.sh` |
| Service | `harithma-pos` (gunicorn on 127.0.0.1:8080), starts on boot | `deployment/server/harithma-pos.service` |
| Web server | nginx: HTTP until the certificate exists, then HTTPS with HSTS, gzip, no framing by other sites, no version number shown, and sign-in posts (`/app`, `/app/login`, `/app/reset_password`) limited to 10 a minute per address | `deployment/server/nginx-http.conf`, `deployment/server/nginx-https.conf`, `deployment/server/429.html` |
| HTTPS | Let's Encrypt certificate, renewed automatically by certbot's timer | `deployment/deploy.sh` |
| Nightly backup | 21:00 UTC (02:30 Sri Lanka) to `/root/backups/nightly`, kept 14 days | `deployment/server/harithma-backup.sh`, `deployment/server/harithma-backup.cron` |
| Deploys | `/usr/local/bin/harithma-ci-deploy` and the restricted GitHub key | `deployment/ci-deploy.sh` |
| Developer page | Collector every 5 minutes | `deployment/monitor-collect.py`, `deployment/server/harithma-monitor.cron` |

The root-owned scripts in `/usr/local/bin` are copies. After changing one in the
repository, run `deploy.sh` again or reinstall that file with `install -o root -g root -m 755`.

Backups stay on the same server. Copy them somewhere else as well (see Security Recommendations).

**Receipts** are printed from the browser at the counter (see "Receipt printing" in the user guide), so the server needs no printer setup.

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

### Step 11: Create Admin User
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

# Update application by hand (normally GitHub Actions does this; see below)
sudo bash /opt/harithma-pos/deployment/update.sh
```

### Continuous deployment (GitHub Actions)

Pushing to `main` runs `.github/workflows/ci.yaml`:

1. **Tests** run on GitHub (Python 3.10, the pinned `requirements-dev.txt`). Pull requests run them too.
2. If they pass, **Deploy** connects to the server over SSH and runs `deploy <commit>`. The server then:
   - checks the commit exists (nothing changes if not);
   - backs up the database to `/root/backups/predeploy/` (the last 20 are kept);
   - checks out that exact commit, installs requirements and runs `flask db upgrade`;
   - restarts the service and checks `http://127.0.0.1:8080/app/login` for up to 40 seconds;
   - if anything fails, puts the previous commit back and restarts. Database changes are not undone; restore the backup if needed.
3. The workflow then checks the live site answers.

Changes only to `docs/` or Markdown files do not deploy.

**Rolling back:** Actions → *Roll back* → *Run workflow*. Leave the commit empty for the version before the last deploy, or enter one. On the server: `sudo bash /opt/harithma-pos/deployment/rollback.sh [commit]`.

**How the server side is set up** (all done once; repeat only to rebuild the server):

| Piece | Where |
|---|---|
| Deploy script (root-owned copy of `deployment/ci-deploy.sh`) | `/usr/local/bin/harithma-ci-deploy`. After changing the script in the repository, reinstall it: `sudo install -o root -g root -m 755 deployment/ci-deploy.sh /usr/local/bin/harithma-ci-deploy` |
| Deploy key | A line in `/root/.ssh/authorized_keys` starting `restrict,command="/usr/local/bin/harithma-ci-deploy"`, so the key can only deploy or roll back. The private half is only in the GitHub secret |
| GitHub secret | `DEPLOY_SSH_KEY` = the private key above (Settings → Secrets and variables → Actions) |
| Server name and host key | Repository variables `DEPLOY_HOST` and `DEPLOY_HOST_KEY`; the workflow files fall back to the current server's values. Set them when moving to a new server (`deploy.sh` prints both) |
| Log | `/var/log/harithma-deploy.log` |

`update.sh` and `rollback.sh` in this folder call the same script, so a manual deploy gets the same backup, health check and automatic recovery.

**Deploy history:** each deploy and rollback adds a line to `/var/lib/harithma-deploy/history.jsonl` (time, result, commits, test counts from GitHub, duration, backup file). The developer page shows it.

### Developer page (monitoring)

*Menu → Developer → Monitor* (`/app/dev`). Only for emails listed in `HARITHMA_DEVELOPER_EMAILS` in `/opt/harithma-pos/.env` (comma-separated); everyone else, owners included, gets "page not found". Restart the service after changing it.

It shows deploys and GitHub Actions runs (with test counts), users online and their sign-ins (including failed ones), unique users per day, website traffic per hour with attack and scanner requests, SSH break-in attempts and successful SSH logins, app errors with tracebacks, 5xx responses, nginx errors and server health (services, disk, memory, backups, certificate, updates). A "Needs attention" list at the top picks out what matters.

| Piece | Where |
|---|---|
| Collector (root-owned copy of `deployment/monitor-collect.py`) | `/usr/local/bin/harithma-monitor-collect`, run every 5 minutes by `/etc/cron.d/harithma-monitor`. Reinstall after changing it: `sudo install -o root -g root -m 755 deployment/monitor-collect.py /usr/local/bin/harithma-monitor-collect` |
| Its output | `/var/lib/harithma-monitor/snapshot.json` (root:harithma, 640), log in `/var/log/harithma-monitor.log` |
| Sign-ins and activity | In the database: `login_event`, `user_activity_day` and `user.last_seen_dttm` |
| App errors | Warnings and errors go to the journal in one format (`time LEVEL logger [METHOD /path user=id] message`), which the collector reads back |

**Library versions** are pinned in `requirements.txt` to what production runs. To upgrade, change a version, push, and let the tests pass before it is deployed.

### Security

`deploy.sh` already sets up HTTPS, the firewall, key-only SSH, the sign-in rate limit,
a database reachable only from the server itself, and nightly backups.

Expect a steady stream of scanner traffic (requests for `.env`, `wp-login.php` and
the like) and SSH password guesses: every public server gets them. They show on the
developer page and cannot succeed here, because the app has none of those files and
SSH accepts no passwords.

Still worth doing:
- **Copy backups off the server.** `/root/backups` is on the same disk as the database.
- **Protect the SSH keys that open this server**: a passphrase on your own key, and
  keep the GitHub deploy key only in the `DEPLOY_SSH_KEY` secret.
- **Develop somewhere else.** Work on your own computer or a separate server and let
  GitHub deploy, rather than editing on the production server.

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
