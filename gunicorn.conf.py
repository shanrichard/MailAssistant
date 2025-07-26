"""
Gunicorn configuration for MailAssistant production deployment
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeouts
timeout = 120
keepalive = 30
graceful_timeout = 30

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "mailassistant"

# Server mechanics  
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (disabled, using Railway's SSL termination)
keyfile = None
certfile = None

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("MailAssistant backend server is ready")

def worker_int(worker):
    """Called just after a worker has been killed by a signal."""
    worker.log.info(f"Worker {worker.pid} received INT or QUIT signal")

def on_exit(server):
    """Called just before exiting."""
    server.log.info("MailAssistant backend server is shutting down")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    """Called just prior to forking the worker subprocess."""
    pass

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info(f"Worker {worker.pid} received SIGABRT signal")