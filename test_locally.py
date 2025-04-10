#!/usr/bin/env python
"""
本地测试脚本 - 用于测试Trump Truth Social抓取和通知系统

这个脚本可以:
1. 模拟抓取过程
2. 测试Lark通知功能
3. 模拟错误并测试健康检查
4. 验证日志系统是否正常工作
"""

import os
import sys
import json
import time
import shutil
import logging
from datetime import datetime
import argparse

# 导入我们自己的模块
import scrape
from send_lark_notification import check_and_notify, send_lark_notification

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # 只输出到控制台
    ]
)
logger = logging.getLogger('test_locally')

# 测试数据 - 用于模拟API响应
SAMPLE_POSTS = [
    {
        "id": "114132050804394743",
        "created_at": datetime.now().isoformat(),
        "content": "这是一条测试推文，模拟特朗普的新推文。",
        "url": "https://truthsocial.com/@realDonaldTrump/114132050804394743",
        "media": [
            "https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/media_attachments/files/114/132/050/631/878/172/original/f0e7d14a580b0bc6.mp4"
        ],
        "replies_count": 925,
        "reblogs_count": 2938,
        "favourites_count": 13166
    },
    {
        "id": "114130744626893259",
        "created_at": datetime.now().isoformat(),
        "content": "另一条测试推文，测试系统能否正确处理多条推文。",
        "url": "https://truthsocial.com/@realDonaldTrump/114130744626893259",
        "media": [
            "https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/media_attachments/files/114/130/744/449/958/273/original/56b8a2c4e789ede9.jpg"
        ],
        "replies_count": 2451,
        "reblogs_count": 3833,
        "favourites_count": 16848
    }
]

class MockResponse:
    """模拟请求响应"""
    def __init__(self, json_data, status_code=200, text=""):
        self.json_data = json_data
        self.status_code = status_code
        self.text = text if text else json.dumps(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

def setup_test_environment():
    """设置测试环境，创建必要的目录和文件"""
    # 创建临时测试目录
    os.makedirs("./test_data", exist_ok=True)
    os.makedirs("./test_data/logs", exist_ok=True)
    
    # 修改全局变量，指向测试目录
    scrape.DATA_DIR = "./test_data"
    scrape.LOG_DIR = "./test_data/logs"
    scrape.OUTPUT_JSON_FILE = "./test_data/truth_archive.json"
    scrape.OUTPUT_CSV_FILE = "./test_data/truth_archive.csv"
    scrape.ERROR_COUNT_FILE = "./test_data/error_count.txt"
    scrape.LAST_ALERT_FILE = "./test_data/last_alert.txt"
    
    logger.info("测试环境已设置")

def cleanup_test_environment():
    """清理测试环境"""
    try:
        shutil.rmtree("./test_data")
        logger.info("测试环境已清理")
    except Exception as e:
        logger.warning(f"清理测试环境时出错: {e}")

def mock_scrape_request(test_mode="success"):
    """
    模拟抓取请求
    
    Args:
        test_mode (str): 测试模式
            - "success": 成功响应
            - "empty": 空响应
            - "error": 异常响应
    """
    # 保存原始函数，以便后续恢复
    original_scrape = scrape.scrape
    original_load_existing = scrape.load_existing_posts
    
    def mock_scrape(url, headers=None):
        logger.info(f"模拟抓取请求: {url}")
        
        if test_mode == "empty":
            return []
            
        if test_mode == "error":
            raise Exception("模拟的网络错误")
            
        # 成功模式返回测试数据
        return SAMPLE_POSTS
    
    def mock_load_existing():
        logger.info("模拟加载现有帖子")
        # 返回空字典，表示没有现有帖子
        return {}
    
    # 替换为模拟函数
    scrape.scrape = mock_scrape
    scrape.load_existing_posts = mock_load_existing
    
    try:
        # 执行抓取
        scrape.fetch_posts(max_pages=1)
    except Exception as e:
        logger.error(f"抓取过程中出现错误: {e}")
    finally:
        # 恢复原始函数
        scrape.scrape = original_scrape
        scrape.load_existing_posts = original_load_existing

def test_notification():
    """测试通知功能"""
    if not os.environ.get("LARK_WEBHOOK_URL"):
        logger.warning("未设置LARK_WEBHOOK_URL环境变量，通知测试将被跳过")
        return False
    
    logger.info("测试Lark通知功能")
    
    # 测试单条通知
    post = SAMPLE_POSTS[0]
    post["content"] = "这是一条测试通知，来自本地测试脚本。" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    success = send_lark_notification(post)
    return success

def test_error_handling():
    """测试错误处理和健康检查"""
    logger.info("测试错误处理和健康检查")
    
    # 清除任何现有的错误计数
    if os.path.exists(scrape.ERROR_COUNT_FILE):
        os.remove(scrape.ERROR_COUNT_FILE)
    
    # 模拟连续错误
    for i in range(scrape.ERROR_THRESHOLD + 1):
        logger.info(f"模拟第 {i+1} 次错误")
        scrape.update_error_count(success=False)
        
        # 读取当前错误计数
        count = scrape.get_error_count()
        logger.info(f"当前错误计数: {count}")
        
        # 如果达到阈值，检查是否尝试发送告警
        if count >= scrape.ERROR_THRESHOLD:
            logger.info("错误计数已达到阈值，应该尝试发送告警")
        
        time.sleep(0.5)  # 短暂暂停，让日志有序显示
    
    # 测试成功重置计数
    logger.info("测试成功重置错误计数")
    scrape.update_error_count(success=True)
    count = scrape.get_error_count()
    logger.info(f"重置后的错误计数: {count} (应为0)")

def test_full_workflow():
    """测试完整工作流程"""
    logger.info("测试完整工作流程")
    
    # 1. 模拟成功抓取
    logger.info("1. 模拟成功抓取")
    mock_scrape_request("success")
    
    # 2. 检查是否创建了JSON和CSV文件
    json_exists = os.path.exists(scrape.OUTPUT_JSON_FILE)
    csv_exists = os.path.exists(scrape.OUTPUT_CSV_FILE)
    logger.info(f"JSON文件存在: {json_exists}, CSV文件存在: {csv_exists}")
    
    if json_exists:
        # 读取JSON文件内容
        with open(scrape.OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"抓取到 {len(data)} 条帖子")
    
    # 3. 手动运行通知逻辑
    if os.environ.get("LARK_WEBHOOK_URL"):
        logger.info("3. 手动测试通知逻辑")
        check_and_notify()
    else:
        logger.info("跳过通知测试 (未设置LARK_WEBHOOK_URL)")

def main():
    parser = argparse.ArgumentParser(description="Trump Truth Social 爬虫本地测试工具")
    parser.add_argument('--mode', choices=['full', 'scrape', 'notify', 'error'], 
                      default='full', help='测试模式: full=完整测试, scrape=仅爬虫, notify=仅通知, error=错误处理')
    parser.add_argument('--clean', action='store_true', help='测试后清理测试数据')
    
    args = parser.parse_args()
    
    logger.info("===== 开始本地测试 =====")
    setup_test_environment()
    
    try:
        if args.mode in ['full', 'scrape']:
            mock_scrape_request("success")
            
        if args.mode in ['full', 'notify']:
            test_notification()
            
        if args.mode in ['full', 'error']:
            test_error_handling()
            
        if args.mode == 'full':
            test_full_workflow()
            
    finally:
        logger.info("===== 测试完成 =====")
        if args.clean:
            cleanup_test_environment()
        else:
            logger.info(f"测试数据保留在 ./test_data/ 目录")

if __name__ == "__main__":
    main() 