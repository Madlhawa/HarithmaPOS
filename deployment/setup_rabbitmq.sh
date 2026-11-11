#!/bin/bash
# RabbitMQ Setup Script for Harithma POS
# Run this script AFTER deploying the main application
# Usage: sudo ./setup_rabbitmq.sh

# Ensure we're running with bash
if [ -z "$BASH_VERSION" ]; then
    exec /bin/bash "$0" "$@"
fi

set -e  # Exit on any error

echo "🐰 Starting RabbitMQ Setup for Harithma POS..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root (works in both bash and sh)
if [ "$(id -u)" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root. Please use: sudo ./setup_rabbitmq.sh${NC}"
    exit 1
fi

# Check if RabbitMQ is already installed
if command -v rabbitmq-server >/dev/null 2>&1 || [ -f /usr/sbin/rabbitmq-server ] || [ -f /usr/bin/rabbitmq-server ]; then
    echo -e "${YELLOW}⚠️  RabbitMQ appears to be installed.${NC}"
    read -p "Do you want to reconfigure? (y/n) " REPLY
    if [ "$REPLY" != "y" ] && [ "$REPLY" != "Y" ]; then
        echo -e "${YELLOW}Exiting. RabbitMQ setup skipped.${NC}"
        exit 0
    fi
fi

# Detect Ubuntu/Debian version
echo -e "${YELLOW}🔍 Detecting system version...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
    CODENAME=$VERSION_CODENAME
    
    # Map version to codename if not set
    if [ -z "$CODENAME" ]; then
        case "$VERSION" in
            "20.04") CODENAME="focal" ;;
            "22.04") CODENAME="jammy" ;;
            "24.04") CODENAME="noble" ;;
            *) CODENAME="jammy" ;; # Default to jammy
        esac
    fi
    
    echo -e "${GREEN}Detected: $DISTRO $VERSION ($CODENAME)${NC}"
else
    echo -e "${RED}❌ Cannot detect system version. Defaulting to jammy.${NC}"
    CODENAME="jammy"
fi

# Check if architecture is supported (Team RabbitMQ repos only support amd64)
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" != "amd64" ]; then
    echo -e "${YELLOW}⚠️  Architecture $ARCH detected. Team RabbitMQ repos only support amd64.${NC}"
    echo -e "${YELLOW}For arm64, you'll need to use Launchpad PPA. Continuing with amd64 repos...${NC}"
fi

# Install prerequisites
echo -e "${YELLOW}📦 Installing prerequisites...${NC}"
apt-get install -y curl gnupg apt-transport-https

# Add Team RabbitMQ's signing key
echo -e "${YELLOW}🔑 Adding Team RabbitMQ signing key...${NC}"
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | gpg --dearmor | tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null

# Add apt repositories maintained by Team RabbitMQ
echo -e "${YELLOW}📦 Adding RabbitMQ apt repositories...${NC}"
# Check if repository already added
if ! grep -q "rabbitmq.com" /etc/apt/sources.list.d/rabbitmq.list 2>/dev/null; then
    tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
## Modern Erlang/OTP releases
##
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-erlang/ubuntu/$CODENAME $CODENAME main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-erlang/ubuntu/$CODENAME $CODENAME main

## Latest RabbitMQ releases
##
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb1.rabbitmq.com/rabbitmq-server/ubuntu/$CODENAME $CODENAME main
deb [arch=amd64 signed-by=/usr/share/keyrings/com.rabbitmq.team.gpg] https://deb2.rabbitmq.com/rabbitmq-server/ubuntu/$CODENAME $CODENAME main
EOF
else
    echo -e "${YELLOW}RabbitMQ repository already configured.${NC}"
fi

# Update package indices
echo -e "${YELLOW}📦 Updating package indices...${NC}"
apt-get update -y

# Install Erlang packages (required by RabbitMQ)
echo -e "${YELLOW}📦 Installing Erlang packages...${NC}"
apt-get install -y erlang-base \
                    erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
                    erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
                    erlang-runtime-tools erlang-snmp erlang-ssl \
                    erlang-syntax-tools erlang-tftp erlang-tools erlang-xmerl

# Install RabbitMQ Server
echo -e "${YELLOW}📦 Installing RabbitMQ Server...${NC}"
apt-get install rabbitmq-server -y --fix-missing

# Enable and start RabbitMQ
echo -e "${YELLOW}🔧 Starting RabbitMQ service...${NC}"
systemctl enable rabbitmq-server
systemctl start rabbitmq-server

# Wait for RabbitMQ to be ready
echo -e "${YELLOW}⏳ Waiting for RabbitMQ to be ready...${NC}"
MAX_WAIT=60
WAIT_COUNT=0
while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    if systemctl is-active --quiet rabbitmq-server && rabbitmqctl status >/dev/null 2>&1; then
        echo -e "${GREEN}✅ RabbitMQ is ready!${NC}"
        break
    fi
    echo -n "."
    sleep 2
    WAIT_COUNT=$((WAIT_COUNT + 2))
done

if [ $WAIT_COUNT -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ RabbitMQ failed to start within $MAX_WAIT seconds.${NC}"
    echo -e "${YELLOW}Checking service status...${NC}"
    systemctl status rabbitmq-server
    exit 1
fi

# Enable RabbitMQ Management Plugin (web UI)
echo -e "${YELLOW}🌐 Enabling RabbitMQ Management Plugin...${NC}"
rabbitmq-plugins enable rabbitmq_management

# Wait a bit more for plugin to be enabled
sleep 3

# Get configuration from environment or use defaults
APP_DIR="/opt/harithma-pos"
RABBITMQ_USER="${RABBITMQ_USERNAME:-harithma_rabbitmq}"
RABBITMQ_PASS="${RABBITMQ_PASSWORD:-$(openssl rand -base64 16)}"

# Check if .env file exists to get existing credentials
if [ -f "$APP_DIR/.env" ]; then
    echo -e "${YELLOW}📄 Reading RabbitMQ credentials from .env file...${NC}"
    # Get username from .env if present
    if grep -q "RABBIT_MQ_USERNAME" "$APP_DIR/.env"; then
        RABBITMQ_USER=$(grep "RABBIT_MQ_USERNAME" "$APP_DIR/.env" | cut -d '=' -f2 | tr -d ' ' | tr -d '"')
    fi
    # Get password from .env if present
    if grep -q "RABBIT_MQ_PASSWORD" "$APP_DIR/.env"; then
        RABBITMQ_PASS=$(grep "RABBIT_MQ_PASSWORD" "$APP_DIR/.env" | cut -d '=' -f2 | tr -d ' ' | tr -d '"')
    fi

    # Overwrite username if it's a default or unsafe value
    if [ "$RABBITMQ_USER" = "guest" ] || [ "$RABBITMQ_USER" = "guest" ] || [ -z "$RABBITMQ_USER" ] || [ "$RABBITMQ_USER" = "harithma_rabbitmq" ]; then
        echo -e "${YELLOW}⚠️  Detected default or empty RabbitMQ username in .env. Overwriting with secure default.${NC}"
        RABBITMQ_USER="harithma_rabbitmq"
    fi
    # Overwrite password if it's a default or unsafe value
    if [ "$RABBITMQ_PASS" = "guest" ] || [ -z "$RABBITMQ_PASS" ]; then
        echo -e "${YELLOW}⚠️  Detected default or empty RabbitMQ password in .env. Generating new password.${NC}"
        RABBITMQ_PASS=$(openssl rand -base64 16)
    fi
else
    echo -e "${YELLOW}⚠️  .env file not found. Using generated credentials.${NC}"
fi


# Verify RabbitMQ is still running before creating users
if ! systemctl is-active --quiet rabbitmq-server; then
    echo -e "${RED}❌ RabbitMQ service is not running. Starting it...${NC}"
    systemctl start rabbitmq-server
    sleep 5
fi

# Create RabbitMQ user
echo -e "${YELLOW}👤 Creating RabbitMQ user: $RABBITMQ_USER...${NC}"
# Wait for RabbitMQ to be fully ready
sleep 2

# Check if user exists
if rabbitmqctl list_users 2>/dev/null | grep -q "^$RABBITMQ_USER[[:space:]]"; then
    echo -e "${YELLOW}User $RABBITMQ_USER already exists. Updating password...${NC}"
    rabbitmqctl change_password "$RABBITMQ_USER" "$RABBITMQ_PASS" || {
        echo -e "${RED}❌ Failed to change password. Trying to recreate user...${NC}"
        rabbitmqctl delete_user "$RABBITMQ_USER" 2>/dev/null || true
        rabbitmqctl add_user "$RABBITMQ_USER" "$RABBITMQ_PASS"
    }
else
    rabbitmqctl add_user "$RABBITMQ_USER" "$RABBITMQ_PASS" || {
        echo -e "${RED}❌ Failed to create user. Retrying...${NC}"
        sleep 3
        rabbitmqctl add_user "$RABBITMQ_USER" "$RABBITMQ_PASS"
    }
fi

# Set user tags (administrator for full access)
echo -e "${YELLOW}Setting administrator tag...${NC}"
rabbitmqctl set_user_tags "$RABBITMQ_USER" administrator

# Grant permissions
echo -e "${YELLOW}🔐 Setting permissions for $RABBITMQ_USER...${NC}"
rabbitmqctl set_permissions -p / "$RABBITMQ_USER" ".*" ".*" ".*"

# Note: Queues will be created automatically when the application connects
# The application uses queue name: 'harithmaq'
echo -e "${YELLOW}📬 Queue Information:${NC}"
echo "   Queue name: harithmaq (will be created automatically by application)"

# Update .env file with RabbitMQ credentials
if [ -f "$APP_DIR/.env" ]; then
    echo -e "${YELLOW}⚙️  Updating .env file with RabbitMQ configuration...${NC}"
    # Update or add RABBIT_MQ_HOST
    if grep -q "RABBIT_MQ_HOST" "$APP_DIR/.env"; then
        sed -i "s|RABBIT_MQ_HOST=.*|RABBIT_MQ_HOST=localhost|" "$APP_DIR/.env"
    else
        echo "RABBIT_MQ_HOST=localhost" >> "$APP_DIR/.env"
    fi
    
    # Update or add RABBIT_MQ_USERNAME
    if grep -q "RABBIT_MQ_USERNAME" "$APP_DIR/.env"; then
        sed -i "s|RABBIT_MQ_USERNAME=.*|RABBIT_MQ_USERNAME=$RABBITMQ_USER|" "$APP_DIR/.env"
    else
        echo "RABBIT_MQ_USERNAME=$RABBITMQ_USER" >> "$APP_DIR/.env"
    fi
    
    # Update or add RABBIT_MQ_PASSWORD
    if grep -q "RABBIT_MQ_PASSWORD" "$APP_DIR/.env"; then
        sed -i "s|RABBIT_MQ_PASSWORD=.*|RABBIT_MQ_PASSWORD=$RABBITMQ_PASS|" "$APP_DIR/.env"
    else
        echo "RABBIT_MQ_PASSWORD=$RABBITMQ_PASS" >> "$APP_DIR/.env"
    fi
    
    # Ensure proper ownership
    chown harithma:harithma "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    
    echo -e "${GREEN}✅ .env file updated with RabbitMQ credentials${NC}"
else
    echo -e "${YELLOW}⚠️  .env file not found. Please add these manually:${NC}"
    echo "RABBIT_MQ_HOST=localhost"
    echo "RABBIT_MQ_USERNAME=$RABBITMQ_USER"
    echo "RABBIT_MQ_PASSWORD=$RABBITMQ_PASS"
fi

# Disable default guest user (security best practice)
echo -e "${YELLOW}🔒 Securing RabbitMQ (disabling guest user)...${NC}"
rabbitmqctl delete_user guest 2>/dev/null || echo "Guest user already removed or doesn't exist"

# Restart RabbitMQ to apply all changes
echo -e "${YELLOW}🔄 Restarting RabbitMQ...${NC}"
systemctl restart rabbitmq-server

# Wait for service to be ready
sleep 3

# Check service status
if systemctl is-active --quiet rabbitmq-server; then
    echo -e "${GREEN}✅ RabbitMQ is running!${NC}"
else
    echo -e "${RED}❌ RabbitMQ failed to start. Check logs with: journalctl -u rabbitmq-server -f${NC}"
    exit 1
fi

# Display connection information
echo ""
echo -e "${GREEN}🎉 RabbitMQ setup completed successfully!${NC}"
echo ""
echo "📋 Connection Information:"
echo "   Host: localhost"
echo "   Port: 5672 (AMQP)"
echo "   Management UI: http://localhost:15672"
echo "   Username: $RABBITMQ_USER"
echo "   Password: $RABBITMQ_PASS"
echo ""
echo "📋 Next Steps:"
echo "1. Access Management UI at: http://$(hostname -I | awk '{print $1}'):15672"
echo "2. Login with username: $RABBITMQ_USER"
echo "3. Restart your application to use RabbitMQ:"
echo "   sudo systemctl restart harithma-pos"
echo ""
echo "🔧 Useful Commands:"
echo "   Check status: sudo systemctl status rabbitmq-server"
echo "   View logs: sudo journalctl -u rabbitmq-server -f"
echo "   List users: sudo rabbitmqctl list_users"
echo "   List queues: sudo rabbitmqctl list_queues"
echo "   Restart: sudo systemctl restart rabbitmq-server"
echo ""

