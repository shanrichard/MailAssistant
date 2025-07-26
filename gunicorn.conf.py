"""
Gunicorn configuration for MailAssistant production deployment
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
# 使用较少的工作进程以避免数据库连接池耗尽
# Railway 环境通常有限的资源，使用 2-4 个工作进程较为合适
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout
timeout = 120
graceful_timeout = 30
keepalive = 5

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming
proc_name = 'mailassistant'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (如果需要)
keyfile = None
certfile = None

# Worker timeout
# 对于邮件同步这种长时间运行的任务，需要较长的超时时间
worker_timeout = 300

# Preload app
# 预加载应用以节省内存
preload_app = True

# 限制请求大小（10MB）
limit_request_line = 0
limit_request_fields = 100
limit_request_field_size = 0

def when_ready(server):
    """当服务器准备就绪时调用"""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """工作进程被中断时调用"""
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    """在fork工作进程之前调用"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_exec(server):
    """在重新执行主进程之前调用"""
    server.log.info("Forked child, re-executing.")

def on_starting(server):
    """在主进程初始化时调用"""
    server.log.info("Starting MailAssistant Gunicorn server")

def on_reload(server):
    """在重新加载时调用"""
    server.log.info("Reloading MailAssistant Gunicorn server")