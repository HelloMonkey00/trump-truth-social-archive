#!/bin/bash
set -e

echo "===> 容器初始化开始 <==="

# 创建必要的目录
mkdir -p /app/data/logs
mkdir -p /app/config

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
  "error_threshold": 5,
  "deepseek_api_key": "${DEEPSEEK_API_KEY}",
  "analyze_market": ${ANALYZE_MARKET:-true},
  "auto_notify_mode": ${AUTO_NOTIFY_MODE:-true}
}
EOF

# 生成AI提示词配置文件
if [ ! -f /app/config/prompts.json ]; then
  echo "生成AI提示词配置文件..."
  cat > /app/config/prompts.json << EOF
{
  "market_impact": "分析以下文本内容与金融市场的关系。考虑内容是否会影响股票市场、特定行业、公司股价或者美元汇率等。详细分析可能的市场影响方向（利好/利空）、影响强度（1-5分，5为最强）及影响范围。文本: \"{text}\"\n请以JSON格式返回结果，包含impact_type（影响类型）、direction（方向：positive/negative/neutral）、intensity（1-5）和affected_sectors（受影响行业）字段。",
  
  "extract_topics": "分析以下文本，提取3-5个主要主题或关键词，特别关注与经济、金融市场相关的内容。\n文本: \"{text}\"\n请以JSON数组格式返回结果。",
  
  "summarize_post": "用中文简洁地总结以下内容，重点关注可能影响金融市场的方面（50字以内）:\n\"{text}\"\n",
  
  "should_notify": "评估以下内容是否真的会对金融市场产生实质性影响。内容: \"{text}\"\n分析: {analysis}\n只返回\"是\"或\"否\"开头，并附加一句简短的理由。"
}
EOF
fi

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