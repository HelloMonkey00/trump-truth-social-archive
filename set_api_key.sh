#!/bin/bash

# 检查是否提供了API密钥参数
if [ $# -eq 0 ]; then
    echo "请提供DeepSeek API密钥作为参数"
    echo "用法: ./set_api_key.sh YOUR_API_KEY"
    exit 1
fi

API_KEY=$1
CONFIG_FILE="./data/config.json"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 找不到配置文件 $CONFIG_FILE"
    exit 1
fi

# 读取配置文件
CONFIG=$(cat "$CONFIG_FILE")

# 检查是否已包含deepseek_api_key字段
if grep -q "deepseek_api_key" "$CONFIG_FILE"; then
    # 如果已存在，更新值
    NEW_CONFIG=$(echo "$CONFIG" | sed "s/\"deepseek_api_key\": \"[^\"]*\"/\"deepseek_api_key\": \"$API_KEY\"/g")
else
    # 如果不存在，添加新字段
    NEW_CONFIG=$(echo "$CONFIG" | sed "s/\"error_threshold\": 5/\"error_threshold\": 5,\n  \"deepseek_api_key\": \"$API_KEY\",\n  \"analyze_market\": true/g")
fi

# 写回配置文件
echo "$NEW_CONFIG" > "$CONFIG_FILE"

echo "DeepSeek API密钥已成功设置到配置文件"
echo "您现在可以运行测试脚本了: ./test_market_analysis.py" 