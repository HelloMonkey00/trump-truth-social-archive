#!/usr/bin/env python
"""
Lark通知测试脚本 - 专门测试Lark通知功能

这个脚本可以:
1. 测试单条Lark通知
2. 测试带有媒体文件的通知
3. 测试批量通知功能
4. 测试通知去重机制
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
import argparse

# 导入我们自己的模块
from send_lark_notification import send_lark_notification, check_and_notify

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # 只输出到控制台
    ]
)
logger = logging.getLogger('lark_test')

# 测试数据
TEST_POSTS = [
    {
        "id": "114132050804394743",
        "created_at": datetime.now().isoformat(),
        "content": "这是一条测试通知，来自本地测试脚本。时间戳: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": "https://truthsocial.com/@realDonaldTrump/114132050804394743",
        "media": [],
        "replies_count": 925,
        "reblogs_count": 2938,
        "favourites_count": 13166
    },
    {
        "id": "114130744626893259",
        "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "content": "这是一条带有媒体文件的测试通知。时间戳: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": "https://truthsocial.com/@realDonaldTrump/114130744626893259",
        "media": [
            "https://static-assets-1.truthsocial.com/tmtg:prime-ts-assets/media_attachments/files/114/130/744/449/958/273/original/56b8a2c4e789ede9.jpg"
        ],
        "replies_count": 2451,
        "reblogs_count": 3833,
        "favourites_count": 16848
    },
    {
        "id": "114130123456789012",
        "created_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "content": "这是第三条测试通知，用于测试批量发送。时间戳: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "url": "https://truthsocial.com/@realDonaldTrump/114130123456789012",
        "media": [],
        "replies_count": 1234,
        "reblogs_count": 5678,
        "favourites_count": 9012
    }
]

def setup_test_environment():
    """设置测试环境"""
    logger.info("设置测试环境")
    
    # 创建必要的目录
    os.makedirs("./test_data", exist_ok=True)
    os.makedirs("./test_data/logs", exist_ok=True)
    
    # 创建测试存档文件
    with open("./test_data/truth_archive.json", "w", encoding="utf-8") as f:
        json.dump(TEST_POSTS, f, indent=2)
    
    # 设置模块变量
    from send_lark_notification import check_and_notify
    check_and_notify.__globals__["last_id_file"] = "./test_data/last_notified_id.txt"
    check_and_notify.__globals__["archive_file"] = "./test_data/truth_archive.json"

def test_single_notification():
    """测试单条Lark通知"""
    logger.info("===== 测试单条Lark通知 =====")
    
    # 检查环境变量是否设置
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        logger.error("未设置LARK_WEBHOOK_URL环境变量，无法进行测试")
        return False
    
    logger.info(f"使用webhook URL: {webhook_url[:20]}...{webhook_url[-8:]}")
    
    # 发送单条通知
    post = TEST_POSTS[0]
    logger.info(f"发送测试通知: ID={post['id']}")
    
    success = send_lark_notification(post)
    
    if success:
        logger.info("✅ 通知发送成功")
    else:
        logger.error("❌ 通知发送失败")
    
    return success

def test_media_notification():
    """测试带有媒体文件的通知"""
    logger.info("===== 测试带有媒体文件的通知 =====")
    
    # 检查环境变量是否设置
    webhook_url = os.environ.get("LARK_WEBHOOK_URL")
    if not webhook_url:
        logger.error("未设置LARK_WEBHOOK_URL环境变量，无法进行测试")
        return False
    
    # 发送带媒体的通知
    post = TEST_POSTS[1]
    logger.info(f"发送带媒体的测试通知: ID={post['id']}, 媒体URL={post['media'][0]}")
    
    success = send_lark_notification(post)
    
    if success:
        logger.info("✅ 带媒体的通知发送成功")
    else:
        logger.error("❌ 带媒体的通知发送失败")
    
    return success

def test_batch_notification():
    """测试批量通知功能"""
    logger.info("===== 测试批量通知功能 =====")
    
    # 确保没有以前的通知记录
    last_id_file = "./test_data/last_notified_id.txt"
    if os.path.exists(last_id_file):
        os.remove(last_id_file)
        logger.info("清除通知历史记录")
    
    # 运行批量通知检查
    logger.info("运行批量通知检查")
    check_and_notify()
    
    # 验证最后通知ID是否已设置
    if os.path.exists(last_id_file):
        with open(last_id_file, "r") as f:
            last_id = f.read().strip()
            logger.info(f"最后通知ID已设置: {last_id}")
            return True
    else:
        logger.error("❌ 批量通知失败，未能设置最后通知ID")
        return False

def test_deduplication():
    """测试通知去重机制"""
    logger.info("===== 测试通知去重机制 =====")
    
    # 第一次运行，应该发送通知
    logger.info("第一次运行批量通知检查")
    check_and_notify()
    
    # 短暂暂停
    time.sleep(2)
    
    # 第二次运行，应该不再发送通知
    logger.info("第二次运行批量通知检查 (应该跳过已通知的帖子)")
    check_and_notify()
    
    # 验证是否已跳过重复通知
    logger.info("通知去重测试完成，请查看日志确认是否正确跳过了已通知的帖子")
    return True

def cleanup():
    """清理测试环境"""
    try:
        import shutil
        shutil.rmtree("./test_data")
        logger.info("测试环境已清理")
    except Exception as e:
        logger.warning(f"清理测试环境时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description="Lark通知测试工具")
    parser.add_argument('--test', choices=['all', 'single', 'media', 'batch', 'dedup'], 
                      default='all', help='测试类型: single=单条通知, media=带媒体通知, batch=批量通知, dedup=去重机制')
    parser.add_argument('--keep', action='store_true', help='保留测试数据文件')
    
    args = parser.parse_args()
    
    # 检查环境变量
    if not os.environ.get("LARK_WEBHOOK_URL"):
        logger.error("未设置LARK_WEBHOOK_URL环境变量")
        logger.error("请先设置环境变量: export LARK_WEBHOOK_URL='你的Lark Webhook URL'")
        return
    
    logger.info("开始Lark通知测试")
    setup_test_environment()
    
    try:
        if args.test in ['all', 'single']:
            test_single_notification()
            
        if args.test in ['all', 'media']:
            test_media_notification()
            
        if args.test in ['all', 'batch']:
            test_batch_notification()
            
        if args.test in ['all', 'dedup']:
            test_deduplication()
    
    finally:
        logger.info("Lark通知测试完成")
        if not args.keep:
            cleanup()
        else:
            logger.info("保留测试数据")

if __name__ == "__main__":
    main() 