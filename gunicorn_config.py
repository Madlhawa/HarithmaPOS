# Gunicorn configuration for production
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8080"  # Only listen on localhost (use Nginx as reverse proxy)
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1  # Optimal worker count
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Process naming
proc_name = "harithma-pos"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed, uncomment and configure)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"