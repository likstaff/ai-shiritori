import os

# サーバー設定
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 1
worker_class = "sync"
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# ログ設定
accesslog = "-"
errorlog = "-"
loglevel = "info"
