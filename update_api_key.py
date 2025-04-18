#!/usr/bin/env python3
"""
简单脚本用于更新Deepseek API密钥
"""
import os
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('api_key_updater')

def update_api_key(api_key):
    """更新API密钥到环境变量并保存到.env文件"""
    # 设置当前环境变量
    os.environ["DEEPSEEK_API_KEY"] = api_key
    logger.info("已设置DEEPSEEK_API_KEY环境变量")
    
    # 创建或更新.env文件
    env_file = ".env"
    lines = []
    
    # 如果.env文件存在，读取其内容
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
    
    # 查找并替换DEEPSEEK_API_KEY行，如果不存在则添加
    key_exists = False
    for i, line in enumerate(lines):
        if line.startswith("DEEPSEEK_API_KEY="):
            lines[i] = f"DEEPSEEK_API_KEY={api_key}\n"
            key_exists = True
            break
    
    if not key_exists:
        lines.append(f"DEEPSEEK_API_KEY={api_key}\n")
    
    # 写回.env文件
    with open(env_file, "w") as f:
        f.writelines(lines)
    
    logger.info(f"已将DEEPSEEK_API_KEY保存到{env_file}文件")
    return True

def main():
    parser = argparse.ArgumentParser(description="更新Deepseek API密钥")
    parser.add_argument("--key", help="Deepseek API密钥")
    args = parser.parse_args()
    
    # 如果未提供密钥，从标准输入获取
    api_key = args.key
    if not api_key:
        print("请输入您的Deepseek API密钥: ", end="")
        api_key = input().strip()
    
    if not api_key:
        logger.error("未提供API密钥，操作取消")
        return False
    
    return update_api_key(api_key)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 