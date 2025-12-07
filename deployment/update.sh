#!/bin/bash
# /opt/harithma-pos/deployment/update.sh

set -e

APP_DIR="/opt/harithma-pos"
APP_USER="harithma"
SERVICE_NAME="harithma-pos"

echo "🚀 Starting Update..."

# 1. Pull latest code (run as app user)
echo "📥 Pulling changes from Git..."
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && git fetch --all && git reset --hard origin/main"

# 2. Update Python dependencies (run as app user)
echo "📦 Updating dependencies..."
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && source venv/bin/activate && pip install -r requirements.txt"

# 3. Run Database Migrations (run as app user)
echo "🗄️  Running database migrations..."
# We export env vars exactly as you did in deploy.sh
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && export \$(grep -v '^#' .env | grep -v '^$' | xargs) && source venv/bin/activate && flask db upgrade"

# 4. Restart the Service (must be run as root)
echo "🔄 Restarting application service..."
systemctl restart $SERVICE_NAME

echo "✅ Update completed successfully!"