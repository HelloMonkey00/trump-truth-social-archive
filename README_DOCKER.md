# Trump Truth Social 爬虫容器使用说明

本文档说明如何使用Docker容器来运行Trump Truth Social爬虫和金融市场分析系统。

## 功能概述

该容器可以:
1. 定期自动爬取特朗普在Truth Social上发布的内容
2. 对新发布的内容进行金融市场影响分析
3. 分析文本内容与股票市场、行业、公司股价或汇率的关系
4. 发送飞书通知

## 环境变量配置

在运行容器时，需要设置以下环境变量:

### 必需的环境变量

- `SCRAPE_PROXY_KEY`: ScrapeOps API密钥，用于网页爬取
- `LARK_WEBHOOK_URL`: 飞书机器人Webhook URL

### 可选的环境变量

- `HEALTH_CHECK_URL`: 健康检查URL (如有)
- `DEEPSEEK_API_KEY`: DeepSeek AI API密钥，用于市场分析功能
- `ANALYZE_MARKET`: 是否启用市场影响分析功能 (`true` 或 `false`，默认为 `true`)

## 使用示例

### 基本运行

```bash
docker run -d \
  --name trump-scraper \
  -e SCRAPE_PROXY_KEY=your_scrapeops_key \
  -e LARK_WEBHOOK_URL=your_lark_webhook_url \
  -v /path/to/data:/app/data \
  yourrepo/trump-social-scraper:latest
```

### 启用市场分析功能

```bash
docker run -d \
  --name trump-scraper \
  -e SCRAPE_PROXY_KEY=your_scrapeops_key \
  -e LARK_WEBHOOK_URL=your_lark_webhook_url \
  -e DEEPSEEK_API_KEY=your_deepseek_api_key \
  -e ANALYZE_MARKET=true \
  -v /path/to/data:/app/data \
  -v /path/to/config:/app/config \
  yourrepo/trump-social-scraper:latest
```

## 自定义提示词

市场分析功能使用AI进行帖子内容与金融市场的关系分析。您可以通过修改提示词来自定义分析内容和输出格式。

提示词配置文件位于 `/app/config/prompts.json`，包含以下三个配置项:

1. `market_impact`: 分析帖子内容与金融市场的关系
2. `extract_topics`: 提取帖子中的主题关键词
3. `summarize_post`: 生成帖子内容摘要

您可以通过挂载自定义的 `prompts.json` 文件到容器中:

```bash
docker run -d \
  ... other options ... \
  -v /path/to/your/prompts.json:/app/config/prompts.json \
  yourrepo/trump-social-scraper:latest
```

## 数据持久化

建议将数据目录挂载到宿主机以便持久化存储数据:

```bash
docker run -d \
  ... other options ... \
  -v /path/to/data:/app/data \
  yourrepo/trump-social-scraper:latest
```

## 查看日志

查看容器日志:

```bash
docker logs trump-scraper
```

查看爬虫日志:

```bash
docker exec trump-scraper cat /app/data/logs/scraper_YYYYMMDD.log
```

查看分析日志:

```bash
docker exec trump-scraper cat /app/data/logs/analysis_YYYYMMDD.log
```

## 自定义crontab

默认情况下，爬虫每分钟执行一次。如果需要修改执行频率:

1. 修改本地 `crontab` 文件
2. 在启动容器时挂载该文件:

```bash
docker run -d \
  ... other options ... \
  -v /path/to/your/crontab:/etc/cron.d/scraper-cron \
  yourrepo/trump-social-scraper:latest
``` 