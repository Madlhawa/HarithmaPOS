#!/bin/bash
# Quick deployment script for Harithma POS on Ubuntu Server

# Ensure we're running with bash
if [ -z "$BASH_VERSION" ]; then
    exec /bin/bash "$0" "$@"
fi

set -e  # Exit on any error

echo "🚀 Starting Harithma POS Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}This script must be run as root. Please use: sudo ./deploy.sh${NC}"
    exit 1
fi

# Create application user (if it doesn't exist)
APP_USER="harithma"
if ! id "$APP_USER" &>/dev/null; then
    echo -e "${YELLOW}👤 Creating application user: $APP_USER...${NC}"
    useradd -r -s /bin/bash -d /opt/harithma-pos -m $APP_USER || {
        echo -e "${YELLOW}User $APP_USER might already exist, continuing...${NC}"
    }
else
    echo -e "${GREEN}✅ User $APP_USER already exists${NC}"
fi

# Update system
echo -e "${YELLOW}📦 Updating system packages...${NC}"
apt update
apt upgrade -y

# Install required system packages
echo -e "${YELLOW}📦 Installing system dependencies...${NC}"
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git

# Install PostgreSQL client libraries
apt install -y libpq-dev python3-dev

# GitHub repository URL
GIT_REPO="https://github.com/Madlhawa/HarithmaPOS.git"
GIT_BRANCH="main"

# Create application directory
APP_DIR="/opt/harithma-pos"
echo -e "${YELLOW}📁 Creating application directory at $APP_DIR...${NC}"

# Check if directory already exists
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}📁 Directory $APP_DIR already exists.${NC}"
    read -p "Do you want to update from git? (y/n) " REPLY
    if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
        echo -e "${YELLOW}📥 Updating from git repository...${NC}"
        # Check if it's a git repository before changing directory
        if [ -d "$APP_DIR/.git" ]; then
            cd $APP_DIR
            git pull origin $GIT_BRANCH || {
                echo -e "${RED}❌ Failed to pull from git. Please check manually.${NC}"
                exit 1
            }
        else
            echo -e "${RED}❌ Directory exists but is not a git repository.${NC}"
            read -p "Remove and clone fresh? (y/n) " REPLY
            if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
                # Change to a safe directory before removing
                cd /tmp
                rm -rf $APP_DIR
                mkdir -p $APP_DIR
                chown $APP_USER:$APP_USER $APP_DIR
                cd $APP_DIR
                git clone -b $GIT_BRANCH $GIT_REPO . || {
                    echo -e "${RED}❌ Failed to clone repository.${NC}"
                    exit 1
                }
                cd $APP_DIR
            else
                echo -e "${RED}❌ Cannot proceed. Exiting.${NC}"
                exit 1
            fi
        fi
    else
        echo -e "${YELLOW}📥 Using existing directory...${NC}"
        cd $APP_DIR
    fi
else
    echo -e "${YELLOW}📥 Cloning from GitHub repository...${NC}"
    # Ensure we're in a safe directory before cloning
    cd /tmp
    mkdir -p $APP_DIR
    git clone -b $GIT_BRANCH $GIT_REPO $APP_DIR || {
        echo -e "${RED}❌ Failed to clone repository. Please check:${NC}"
        echo "   - Internet connection"
        echo "   - Repository URL: $GIT_REPO"
        echo "   - Branch: $GIT_BRANCH"
        exit 1
    }
    chown -R $APP_USER:$APP_USER $APP_DIR
    cd $APP_DIR
fi

# Ensure we're in the application directory for subsequent operations
if [ ! -d "$APP_DIR" ]; then
    echo -e "${RED}❌ Application directory $APP_DIR does not exist!${NC}"
    exit 1
fi

if [ "$PWD" != "$APP_DIR" ]; then
    cd $APP_DIR
fi

echo -e "${GREEN}✅ Code downloaded successfully!${NC}"

# Set ownership before creating virtual environment
chown -R $APP_USER:$APP_USER $APP_DIR

# Create virtual environment as application user
echo -e "${YELLOW}🐍 Creating Python virtual environment...${NC}"
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && python3 -m venv venv"

# Install Python dependencies as application user
echo -e "${YELLOW}📦 Installing Python dependencies...${NC}"
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && source venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt"

# Setup PostgreSQL database
echo -e "${YELLOW}🗄️  Setting up PostgreSQL database...${NC}"
DB_NAME="harithma_pos"
DB_USER="harithma_user"
DB_PASSWORD=$(openssl rand -base64 32)

# Create database and user
echo -e "${YELLOW}Creating PostgreSQL database and user...${NC}"
su - postgres -c "psql -c \"CREATE DATABASE $DB_NAME;\""
su - postgres -c "psql -c \"CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';\""
su - postgres -c "psql -c \"ALTER ROLE $DB_USER SET client_encoding TO 'utf8';\""
su - postgres -c "psql -c \"ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';\""
su - postgres -c "psql -c \"ALTER ROLE $DB_USER SET timezone TO 'UTC';\""
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;\""

# Create .env file
echo -e "${YELLOW}⚙️  Creating environment configuration...${NC}"
cat > $APP_DIR/.env << EOF
# Database Configuration
HARITHMA_DATABASE_URI=postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME

# Flask Secret Key (CHANGE THIS IN PRODUCTION!)
HARITHMA_SECRET_KEY=$(openssl rand -hex 32)

# Email Configuration (Update with your values)
HARITHMA_EMAIL=your-email@example.com
HARITHMA_PASSWORD=your-email-password

# RabbitMQ Configuration (Optional)
RABBIT_MQ_HOST=localhost
RABBIT_MQ_USERNAME=guest
RABBIT_MQ_PASSWORD=guest

# Notify.lk Configuration (Optional)
NOTIFYLK_USER_ID=your-user-id
NOTIFYLK_API_KEY=your-api-key

# Flask Environment
FLASK_APP=app.py
FLASK_ENV=production
EOF

chown $APP_USER:$APP_USER $APP_DIR/.env
chmod 600 $APP_DIR/.env
echo -e "${GREEN}✅ Environment file created at $APP_DIR/.env${NC}"
echo -e "${YELLOW}⚠️  Please edit .env file with your actual configuration values!${NC}"

# Initialize database as application user
echo -e "${YELLOW}🗄️  Initializing database...${NC}"
su -s /bin/bash - $APP_USER -c "cd $APP_DIR && export \$(cat .env | xargs) && source venv/bin/activate && flask db upgrade" || {
    echo -e "${YELLOW}Running initial migration...${NC}"
    su -s /bin/bash - $APP_USER -c "cd $APP_DIR && export \$(cat .env | xargs) && source venv/bin/activate && flask db init && flask db migrate -m 'Initial migration' && flask db upgrade"
}

# Create systemd service
echo -e "${YELLOW}🔧 Creating systemd service...${NC}"
tee /etc/systemd/system/harithma-pos.service > /dev/null << EOF
[Unit]
Description=Harithma POS Gunicorn Application Server
After=network.target postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --config $APP_DIR/gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and start service
systemctl daemon-reload
systemctl enable harithma-pos
systemctl start harithma-pos

# Check service status
sleep 2
if systemctl is-active --quiet harithma-pos; then
    echo -e "${GREEN}✅ Service started successfully!${NC}"
else
    echo -e "${RED}❌ Service failed to start. Check logs with: journalctl -u harithma-pos -f${NC}"
fi

# Setup Nginx reverse proxy (optional)
read -p "Do you want to setup Nginx reverse proxy? (y/n) " REPLY
if [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ]; then
    echo -e "${YELLOW}🌐 Setting up Nginx...${NC}"
    
    read -p "Enter your domain name (or press Enter to use IP): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        DOMAIN="_"
    fi
    
    tee /etc/nginx/sites-available/harithma-pos > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static {
        alias $APP_DIR/harithmapos/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    ln -sf /etc/nginx/sites-available/harithma-pos /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    
    echo -e "${GREEN}✅ Nginx configured!${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Deployment completed!${NC}"
echo ""
echo "📋 Next steps:"
echo "1. Edit $APP_DIR/.env with your actual configuration"
echo "2. Create an admin user: su -s /bin/bash - $APP_USER -c 'cd $APP_DIR && source venv/bin/activate && export \$(cat .env | xargs) && flask create-user'"
echo "3. Check service status: systemctl status harithma-pos"
echo "4. View logs: journalctl -u harithma-pos -f"
echo "5. Restart service: systemctl restart harithma-pos"
echo ""
echo "🌐 Application should be running at:"
if [ -n "$DOMAIN" ] && [ "$DOMAIN" != "_" ]; then
    echo "   http://$DOMAIN"
else
    echo "   http://$(hostname -I | awk '{print $1}')"
fi
echo ""

