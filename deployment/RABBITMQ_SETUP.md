# RabbitMQ Setup Guide

This guide explains how to set up RabbitMQ for Harithma POS after the main application deployment.

## Quick Setup

1. **After deploying the main application, run:**
   ```bash
   cd /path/to/deployment
   chmod +x setup_rabbitmq.sh
   sudo ./setup_rabbitmq.sh
   ```

2. **The script will:**
   - Install RabbitMQ server
   - Create a dedicated user
   - Set up required queues
   - Update your .env file with credentials
   - Enable management web UI

## What Gets Installed

- **RabbitMQ Server** - Message broker
- **Management Plugin** - Web UI for monitoring
- **Erlang Runtime** - Required dependency

## Access Points

- **AMQP Port:** `5672` (for application connections)
- **Management UI:** `http://your-server-ip:15672`
- **Default Credentials:** (created by script, stored in .env)

## Manual Setup (Alternative)

If you prefer to set up manually:

### 1. Install RabbitMQ
```bash
sudo apt update
sudo apt install -y erlang-base erlang-nox
# Add RabbitMQ repository (see script for details)
sudo apt install -y rabbitmq-server
```

### 2. Start and Enable
```bash
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

### 3. Enable Management UI
```bash
sudo rabbitmq-plugins enable rabbitmq_management
```

### 4. Create User
```bash
sudo rabbitmqctl add_user harithma_rabbitmq your_password
sudo rabbitmqctl set_user_tags harithma_rabbitmq administrator
sudo rabbitmqctl set_permissions -p / harithma_rabbitmq ".*" ".*" ".*"
```

### 5. Create Queue
```bash
sudo rabbitmqctl declare queue name=harithmaq durable=true
```

### 6. Update .env File
Add to `/opt/harithma-pos/.env`:
```env
RABBIT_MQ_HOST=localhost
RABBIT_MQ_USERNAME=harithma_rabbitmq
RABBIT_MQ_PASSWORD=your_password
```

## Security

- Default `guest` user is disabled
- Custom user with strong password is created
- Management UI should be behind firewall in production

## Firewall Configuration

If using UFW firewall:
```bash
# Allow RabbitMQ (only if accessing from external)
sudo ufw allow 5672/tcp
sudo ufw allow 15672/tcp  # Management UI (restrict to specific IPs in production)
```

## Troubleshooting

### Check Status
```bash
sudo systemctl status rabbitmq-server
```

### View Logs
```bash
sudo journalctl -u rabbitmq-server -f
```

### List Users
```bash
sudo rabbitmqctl list_users
```

### List Queues
```bash
sudo rabbitmqctl list_queues
```

### Reset (if needed)
```bash
sudo rabbitmqctl stop_app
sudo rabbitmqctl reset
sudo rabbitmqctl start_app
```

## Restart Application

After setting up RabbitMQ, restart your application:
```bash
sudo systemctl restart harithma-pos
```

## Verification

1. **Check RabbitMQ is running:**
   ```bash
   sudo systemctl status rabbitmq-server
   ```

2. **Access Management UI:**
   - Open browser: `http://your-server-ip:15672`
   - Login with credentials from .env file

3. **Test from application:**
   - The application will connect automatically when RabbitMQ functions are enabled

## Notes

- RabbitMQ is optional - the application works without it (functions are currently commented out)
- Queue name used: `harithmaq` (for invoice printing)
- All queues are set as durable (survive server restarts)

