#!/bin/bash
# 在Docker容器中运行市场分析测试脚本

# 设置默认值
DAYS=30
LIMIT=10
FORCE=false

# 解析命令行参数
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift
            ;;
        --limit)
            LIMIT="$2"
            shift
            ;;
        --force)
            FORCE=true
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
    shift
done

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "错误: 未设置DEEPSEEK_API_KEY环境变量!"
    echo "请先设置: export DEEPSEEK_API_KEY=your_api_key"
    exit 1
fi

if [ -z "$LARK_WEBHOOK_URL" ]; then
    echo "警告: 未设置LARK_WEBHOOK_URL环境变量，分析结果不会发送通知!"
    echo "建议设置: export LARK_WEBHOOK_URL=your_webhook_url"
fi

# 构建Docker命令
DOCKER_CMD="docker run --rm -it \
  -e DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY \
  -e LARK_WEBHOOK_URL=${LARK_WEBHOOK_URL:-''} \
  -v $(pwd):/app \
  -w /app \
  python:3.12-slim \
  bash -c \"pip install -r requirements.txt && python test_market_analysis.py --days $DAYS --limit $LIMIT"

# 添加force参数（如果需要）
if [ "$FORCE" = true ]; then
    DOCKER_CMD="$DOCKER_CMD --force"
fi

DOCKER_CMD="$DOCKER_CMD\""

echo "开始在Docker中运行市场分析测试..."
echo "分析过去 $DAYS 天的帖子，限制分析 $LIMIT 条"
if [ "$FORCE" = true ]; then
    echo "将强制重新分析所有帖子"
fi

echo "执行命令: $DOCKER_CMD"
eval $DOCKER_CMD 