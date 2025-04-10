#!/bin/bash
set -e

echo "===> 容器初始化开始 <==="

# 创建必要的目录
mkdir -p /app/data/logs

# 生成配置文件
echo "生成配置文件..."
cat > /app/data/config.json << EOF
{
  "scrape_proxy_key": "${SCRAPE_PROXY_KEY}",
  "lark_webhook_url": "${LARK_WEBHOOK_URL}",
  "health_check_url": "${HEALTH_CHECK_URL}",
  "archive_url": "",
  "use_local_archive": true,
  "base_url": "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses",
  "error_threshold": 5
}
EOF

# 打印配置文件内容（隐藏敏感信息）
echo "配置文件已生成:"
cat /app/data/config.json | sed 's/"[^"]*key[^"]*": "[^"]*"/"key": "***"/g; s/"[^"]*url[^"]*": "http[^"]*"/"url": "***"/g'

# 设置crontab并启动cron服务
echo "设置crontab..."
# 确保已将crontab文件加载到root用户
crontab /etc/cron.d/scraper-cron

# 打印当前crontab配置
echo "当前crontab配置:"
crontab -l

# 记录初始化完成
echo "===> 容器初始化完成 <==="

# 启动cron服务，保持在前台运行
echo "启动cron服务..."
cron -f 