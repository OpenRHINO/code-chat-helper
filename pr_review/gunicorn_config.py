# gunicorn_config.py

# 服务器套接字
bind = '0.0.0.0:8080'      # 绑定ip和端口号
backlog = 512               # 监听队列

# 工作进程设置
workers = 1                 # 进程数
worker_class = 'sync'       # 使用同步模型
worker_connections = 1000   # 最大客户端并发数量
timeout = 30                # 超时时间
keepalive = 2               # 在keep-alive连接上等待请求的秒数

# 安全设置
limit_request_line = 4094   # HTTP请求行的最大大小
limit_request_fields = 20   # HTTP请求头的最大数量
limit_request_field_size = 8190  # HTTP请求头的最大大小（字节）

# 调试设置
reload = False              # 开发环境下设置为True，生产环境下为False

# 日志记录
loglevel = 'info'           # 日志级别
accesslog = '-'             # 访问日志文件，'-' 表示输出到标准输出
errorlog = '-'              # 错误日志文件，'-' 表示输出到标准输出
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'  # 自定义访问日志格式
