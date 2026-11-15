# Gunicorn configuration for production
import os

# Server socket
bind = "127.0.0.1:8080"  # Only listen on localhost (use Nginx as reverse proxy)
backlog = 2048

# Worker processes
# Threads, not one-request-per-process "sync" workers: the dashboard and floor
# board keep a live-updates connection open (server-sent events), and each one
# holds a thread. 2 processes x 16 threads leaves plenty for a handful of screens
# and uses less memory than 3 sync processes.
workers = 2
worker_class = "gthread"
threads = 16
timeout = 30            # for gthread this watches the worker process, not one long request
graceful_timeout = 10   # on restart, live connections are cut after 10 s and reconnect
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