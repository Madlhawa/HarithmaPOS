#!/bin/bash
# /opt/harithma-pos/deployment/rollback.sh - Designed to be run by root/sudo

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

APP_DIR="/opt/harithma-pos"
APP_USER="harithma"
SERVICE_NAME="harithma-pos"

echo -e "${YELLOW}⏪ Starting Rollback Procedure...${NC}"

# Ensure we are running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script must be run as root. Please use: sudo ./rollback.sh${NC}"
    exit 1
fi

# Function to run commands as the application user
run_as_app_user() {
    su -s /bin/bash - $APP_USER -c "cd $APP_DIR && $1"
}

# 1. Revert Code (run as app user)
# We use git reset --hard HEAD@{1} to go back to where we were before the last pull
echo -e "${YELLOW}🔙 Reverting git repository to previous state (HEAD@{1})...${NC}"
run_as_app_user "git reset --hard HEAD@{1}"

# Make update.sh and rollback.sh executable
chmod +x $APP_DIR/deployment/update.sh
chmod +x $APP_DIR/deployment/rollback.sh

# Verify where we are now
CURRENT_COMMIT=$(run_as_app_user "git rev-parse --short HEAD")
echo -e "${GREEN}ℹ️  Now at commit: $CURRENT_COMMIT${NC}"

# 2. Re-install Dependencies (run as app user)
echo -e "${YELLOW}📦 Reverting Python dependencies...${NC}"
run_as_app_user "source venv/bin/activate && pip install -r requirements.txt"

# 3. Database Warning (run as app user for command check)
echo -e "${YELLOW}⚠️  NOTE: This script does NOT revert database migrations automatically.${NC}"
echo -e "${YELLOW}   If needed, run the downgrade command manually:${NC}"
echo -e "   ${YELLOW}sudo su -s /bin/bash - harithma -c 'cd $APP_DIR && source venv/bin/activate && flask db downgrade'${NC}"

# 4. Restart the Service (run as root)
echo -e "${YELLOW}🔄 Restarting application service: $SERVICE_NAME...${NC}"
systemctl restart $SERVICE_NAME

echo -e "${GREEN}✅ Rollback completed successfully! Service is running on commit $CURRENT_COMMIT.${NC}"