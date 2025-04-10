FROM python:3.10-slim

WORKDIR /app

# 安装cron
RUN apt-get update && apt-get install -y cron && apt-get clean && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY requirements.txt .
COPY scrape.py .
COPY send_lark_notification.py .
COPY crontab /etc/cron.d/scraper-cron

# 确保cron文件的权限正确
RUN chmod 0644 /etc/cron.d/scraper-cron

# 创建数据目录
RUN mkdir -p /app/data /app/data/logs

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建日志文件
RUN touch /var/log/cron.log

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 运行cron作为前台进程
CMD cron && tail -f /var/log/cron.log 