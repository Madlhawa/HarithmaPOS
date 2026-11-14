#!/bin/bash
# Sets up Harithma POS on a new Ubuntu 22.04 server, matching production.
#
#   sudo bash deploy.sh --domain harithma.lk [options]
#
# Options:
#   --domain NAME        Site name. Gets an HTTPS certificate once DNS points here.
#                        Leave it out to serve plain HTTP by IP address (testing only).
#   --email ADDRESS      Contact address for Let's Encrypt expiry notices (optional).
#   --developer EMAILS   Who may open the developer page (comma-separated app emails).
#   --restore FILE       A pg_dump -Fc file from the old server, loaded into the new,
#                        empty database. Without it the database starts empty.
#   --deploy-key "KEY"   Public half of the GitHub Actions deploy key (ssh-ed25519 ...).
#                        It is locked so it can only run the deploy script.
#   --branch NAME        Branch to install (default main).
#   --no-swap            Do not add a 2 GB swap file.
#
# Safe to run again: it never deletes the app folder, the database or .env. Run it
# again with --domain once DNS points at this server to switch on HTTPS.
#
# What it sets up (each step is skipped when already done):
#   system packages, automatic security updates, firewall (22, 80, 443), swap,
#   the harithma user, code in /opt/harithma-pos, Python venv, PostgreSQL database,
#   .env, migrations (or a restore), the systemd service, nginx with the sign-in
#   rate limit, the HTTPS certificate and its renewal, nightly backups, the
#   developer page's data collector, the deploy script and the GitHub deploy key.
set -euo pipefail

APP_USER=harithma
APP_DIR=/opt/harithma-pos
GIT_REPO=https://github.com/Madlhawa/HarithmaPOS.git
DB_NAME=harithma_pos
DB_USER=harithma_user
SERVICE=harithma-pos

DOMAIN=""; EMAIL=""; DEVELOPERS=""; RESTORE=""; DEPLOY_KEY=""; BRANCH=main; SWAP=yes
while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain) DOMAIN=${2:?}; shift 2 ;;
        --email) EMAIL=${2:?}; shift 2 ;;
        --developer) DEVELOPERS=${2:?}; shift 2 ;;
        --restore) RESTORE=${2:?}; shift 2 ;;
        --deploy-key) DEPLOY_KEY=${2:?}; shift 2 ;;
        --branch) BRANCH=${2:?}; shift 2 ;;
        --no-swap) SWAP=no; shift ;;
        -h|--help) sed -n '2,26p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1 (see --help)"; exit 2 ;;
    esac
done

[[ $EUID -eq 0 ]] || { echo "Run as root: sudo bash $0 ..."; exit 1; }
[[ -z "$DOMAIN" || "$DOMAIN" =~ ^[a-z0-9.-]+\.[a-z]{2,}$ ]] || { echo "--domain must be a plain name like harithma.lk"; exit 2; }
[[ -z "$RESTORE" || -r "$RESTORE" ]] || { echo "Cannot read $RESTORE"; exit 2; }
if [[ -n "$DEPLOY_KEY" && ! "$DEPLOY_KEY" =~ ^ssh-(ed25519|rsa)\ [A-Za-z0-9+/=]+(\ .*)?$ ]]; then
    echo "--deploy-key must be a public key line (ssh-ed25519 AAAA...)"; exit 2
fi
RESTORE=${RESTORE:+$(realpath "$RESTORE")}
. /etc/os-release
[[ "${VERSION_ID:-}" == "22.04" ]] || echo "Note: tested on Ubuntu 22.04 (Python 3.10); this is ${PRETTY_NAME:-unknown}."

step() { echo; echo "==> $*"; }
as_app() { su -s /bin/bash - "$APP_USER" -c "cd $APP_DIR && $1"; }
env_set() {   # $1 = key, $2 = value: add or replace one line in .env
    if grep -q "^$1=" "$APP_DIR/.env"; then sed -i "s|^$1=.*|$1=$2|" "$APP_DIR/.env"; else echo "$1=$2" >> "$APP_DIR/.env"; fi
}
SRC=$APP_DIR/deployment/server

# ---------------------------------------------------------------- system
step "System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -yq
apt-get install -yq python3 python3-venv python3-pip python3-dev libpq-dev \
    postgresql postgresql-contrib nginx git curl ufw unattended-upgrades \
    certbot python3-certbot-nginx

step "Automatic security updates"
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

step "Firewall: SSH, HTTP and HTTPS only"
ufw allow OpenSSH >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ufw status | head -3

if [[ $SWAP == yes ]] && ! swapon --show | grep -q .; then
    step "2 GB swap file"
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# ---------------------------------------------------------------- code
step "App user and code"
id "$APP_USER" &>/dev/null || useradd --system --shell /bin/bash --home-dir "$APP_DIR" --user-group "$APP_USER"
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
    echo "Code already here; updating to origin/$BRANCH."
    as_app "git fetch --quiet origin && git checkout --quiet $BRANCH && git reset --hard --quiet origin/$BRANCH"
elif [[ -z "$(ls -A "$APP_DIR")" ]]; then
    as_app "git clone --quiet -b $BRANCH $GIT_REPO $APP_DIR"
else
    echo "$APP_DIR has files but is not a git checkout. Move them away and run again."; exit 1
fi
as_app "git log -1 --format='Code is at %h %s'"

step "Python packages"
[[ -x "$APP_DIR/venv/bin/python" ]] || as_app "python3 -m venv venv"
as_app "venv/bin/pip install --quiet --upgrade pip && venv/bin/pip install --quiet -r requirements.txt"

# ---------------------------------------------------------------- database
step "Database"
systemctl enable --now postgresql >/dev/null
psql_root() { (cd /tmp && sudo -u postgres psql -v ON_ERROR_STOP=1 -Atq "$@"); }
if [[ ! -f "$APP_DIR/.env" ]]; then
    DB_PASSWORD=$(openssl rand -hex 24)
    if [[ -n "$(psql_root -c "select 1 from pg_roles where rolname='$DB_USER'")" ]]; then
        psql_root -c "alter role $DB_USER with login password '$DB_PASSWORD'"
    else
        psql_root -c "create role $DB_USER with login password '$DB_PASSWORD'"
    fi
    psql_root -c "alter role $DB_USER set timezone to 'UTC'"
    cat > "$APP_DIR/.env" <<EOF
HARITHMA_DATABASE_URI=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
HARITHMA_SECRET_KEY=$(openssl rand -hex 32)
FLASK_APP=app.py
FLASK_ENV=production
# Secure cookies need HTTPS; deploy.sh turns this on once the certificate is in place.
HARITHMA_COOKIE_SECURE=false
HARITHMA_DEVELOPER_EMAILS=
# Fill these in by hand (copy them from the old server's .env):
HARITHMA_EMAIL=
HARITHMA_PASSWORD=
NOTIFYLK_USER_ID=
NOTIFYLK_API_KEY=
RABBIT_MQ_HOST=
RABBIT_MQ_USERNAME=
RABBIT_MQ_PASSWORD=
EOF
    echo "Wrote $APP_DIR/.env with a new database password and secret key."
else
    echo "Keeping the existing $APP_DIR/.env."
fi
chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
[[ -z "$DEVELOPERS" ]] || env_set HARITHMA_DEVELOPER_EMAILS "$DEVELOPERS"

if [[ -z "$(psql_root -c "select 1 from pg_database where datname='$DB_NAME'")" ]]; then
    psql_root -c "create database $DB_NAME owner $DB_USER"
fi

if [[ -n "$RESTORE" ]]; then
    if [[ -n "$(psql_root -d "$DB_NAME" -c "select 1 from pg_tables where schemaname='public' limit 1")" ]]; then
        echo "The database already has tables, so $RESTORE was NOT loaded."
    else
        echo "Loading $RESTORE ..."
        (cd /tmp && sudo -u postgres pg_restore --no-owner --no-privileges --role="$DB_USER" -d "$DB_NAME" < "$RESTORE")
    fi
fi
as_app "export \$(grep -v '^#' .env | grep -v '^$' | xargs) && venv/bin/flask db upgrade"

# ---------------------------------------------------------------- app service
step "App service"
install -m 644 "$SRC/harithma-pos.service" /etc/systemd/system/harithma-pos.service
systemctl daemon-reload
systemctl enable "$SERVICE" >/dev/null
systemctl restart "$SERVICE"
for _ in $(seq 1 20); do
    sleep 2
    curl -fsS -o /dev/null --max-time 5 http://127.0.0.1:8080/app/login && { echo "The app is answering."; break; }
done
curl -fsS -o /dev/null --max-time 5 http://127.0.0.1:8080/app/login || { echo "The app did not start: journalctl -u $SERVICE -n 50"; exit 1; }

# ---------------------------------------------------------------- nginx and HTTPS
step "Web server"
mkdir -p /var/www/harithma /var/www/html
install -m 644 "$SRC/429.html" /var/www/harithma/429.html
rm -f /etc/nginx/sites-enabled/default
nginx_site() {   # $1 = template
    sed "s/__DOMAIN__/${DOMAIN:-_}/g" "$SRC/$1" > /etc/nginx/sites-available/harithma-pos
    ln -sf /etc/nginx/sites-available/harithma-pos /etc/nginx/sites-enabled/harithma-pos
    nginx -t -q
    systemctl reload nginx || systemctl restart nginx
}
HTTPS=no
if [[ -n "$DOMAIN" && -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
    HTTPS=yes
else
    nginx_site nginx-http.conf
fi
if [[ -n "$DOMAIN" && $HTTPS == no ]]; then
    # Does the name reach this server? Serve a random file and fetch it by name.
    TOKEN=check-$(openssl rand -hex 8)
    mkdir -p /var/www/html/.well-known/acme-challenge
    echo "$TOKEN" > "/var/www/html/.well-known/acme-challenge/$TOKEN"
    GOT=$(curl -fsS --max-time 10 "http://$DOMAIN/.well-known/acme-challenge/$TOKEN" 2>/dev/null || true)
    rm -f "/var/www/html/.well-known/acme-challenge/$TOKEN"
    if [[ "$GOT" == "$TOKEN" ]]; then
        step "HTTPS certificate for $DOMAIN"
        CONTACT=(--register-unsafely-without-email)
        [[ -z "$EMAIL" ]] || CONTACT=(-m "$EMAIL")
        certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos "${CONTACT[@]}" \
            --deploy-hook "systemctl reload nginx" && HTTPS=yes || echo "certbot failed; staying on plain HTTP."
    else
        echo "http://$DOMAIN does not reach this server yet (check its DNS record)."
        echo "Serving plain HTTP for now. Point DNS here, then run this script again with --domain $DOMAIN."
    fi
fi
if [[ $HTTPS == yes ]]; then
    nginx_site nginx-https.conf
    env_set HARITHMA_COOKIE_SECURE true
    systemctl restart "$SERVICE"
fi

# ---------------------------------------------------------------- root scripts and timers
step "Backups, monitoring and the deploy script"
install -o root -g root -m 755 "$APP_DIR/deployment/ci-deploy.sh" /usr/local/bin/harithma-ci-deploy
install -o root -g root -m 755 "$APP_DIR/deployment/monitor-collect.py" /usr/local/bin/harithma-monitor-collect
install -o root -g root -m 755 "$SRC/harithma-backup.sh" /usr/local/bin/harithma-backup
install -o root -g root -m 644 "$SRC/harithma-backup.cron" /etc/cron.d/harithma-backup
install -o root -g root -m 644 "$SRC/harithma-monitor.cron" /etc/cron.d/harithma-monitor
install -d -m 755 /var/lib/harithma-deploy
as_app "git rev-parse HEAD" > /var/lib/harithma-deploy/current
install -d -m 750 -o root -g "$APP_USER" /var/lib/harithma-monitor
/usr/local/bin/harithma-backup >> /var/log/harithma-backup.log 2>&1 \
    && echo "First backup taken." || echo "The first backup failed: see /var/log/harithma-backup.log"
/usr/local/bin/harithma-monitor-collect >> /var/log/harithma-monitor.log 2>&1 \
    && echo "Developer page data collected." || echo "The collector failed: see /var/log/harithma-monitor.log"

if [[ -n "$DEPLOY_KEY" ]]; then
    step "GitHub deploy key"
    install -d -m 700 /root/.ssh
    touch /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
    KEY_BODY=$(awk '{print $2}' <<< "$DEPLOY_KEY")
    if grep -qF "$KEY_BODY" /root/.ssh/authorized_keys; then
        echo "Already installed."
    else
        echo "restrict,command=\"/usr/local/bin/harithma-ci-deploy\" $DEPLOY_KEY" >> /root/.ssh/authorized_keys
        echo "Installed; it can only run the deploy script."
    fi
fi

# ---------------------------------------------------------------- summary
DEPLOY_HOST=${DOMAIN:-$(hostname -I | awk '{print $1}')}
HOST_KEY=$(awk '{print $1" "$2}' /etc/ssh/ssh_host_ed25519_key.pub)
URL=$([[ $HTTPS == yes ]] && echo "https://$DOMAIN" || echo "http://${DOMAIN:-$(hostname -I | awk '{print $1}')}")
cat <<EOF

Done. The app is at $URL/app/login

Still to do:
  1. Fill in the blank values in $APP_DIR/.env (email, SMS, RabbitMQ), then:
       systemctl restart $SERVICE
EOF
if [[ -z "$RESTORE" ]]; then cat <<EOF
  2. Create the first owner account:
       su -s /bin/bash - $APP_USER -c 'cd $APP_DIR && export \$(grep -v "^#" .env | grep -v "^\$" | xargs) && venv/bin/flask create-user'
EOF
fi
cat <<EOF
  3. Point GitHub's deploys at this server: in the repository, Settings → Secrets and
     variables → Actions → Variables, set
       DEPLOY_HOST      $DEPLOY_HOST
       DEPLOY_HOST_KEY  $HOST_KEY
EOF
[[ -n "$DEPLOY_KEY" ]] || echo "     and run this script again with --deploy-key \"<public half of the DEPLOY_SSH_KEY secret>\"."
