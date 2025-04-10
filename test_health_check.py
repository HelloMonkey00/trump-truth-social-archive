#!/usr/bin/env python
"""
健康检查测试脚本 - 专门测试错误处理和健康告警功能

这个脚本可以:
1. 测试错误计数机制
2. 测试健康告警发送逻辑
3. 测试每日告警限制功能
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
import argparse

# 导入我们自己的模块
import scrape

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # 只输出到控制台
    ]
)
logger = logging.getLogger('health_check_test')

def setup_test():
    """设置测试环境"""
    # 创建临时测试目录
    os.makedirs("./test_data", exist_ok=True)
    
    # 修改全局变量，指向测试目录
    scrape.DATA_DIR = "./test_data"
    scrape.ERROR_COUNT_FILE = "./test_data/error_count.txt"
    scrape.LAST_ALERT_FILE = "./test_data/last_alert.txt"
    
    # 保存原始的send_health_alert函数
    global original_send_health_alert
    original_send_health_alert = scrape.send_health_alert
    
    # 记录发送的告警
    global sent_alerts
    sent_alerts = []
    
    # 替换为模拟函数
    def mock_send_health_alert(status, message):
        logger.info(f"模拟发送健康告警: 状态={status}, 消息={message}")
        sent_alerts.append({"status": status, "message": message, "time": datetime.now()})
        return True
    
    scrape.send_health_alert = mock_send_health_alert
    
    logger.info("测试环境已设置")

def test_error_counting():
    """测试错误计数机制"""
    logger.info("===== 测试错误计数机制 =====")
    
    # 确保初始状态为0
    if os.path.exists(scrape.ERROR_COUNT_FILE):
        os.remove(scrape.ERROR_COUNT_FILE)
    
    # 检查初始计数
    count = scrape.get_error_count()
    logger.info(f"初始错误计数: {count} (应为0)")
    
    # 递增错误计数
    for i in range(1, 6):
        scrape.update_error_count(success=False)
        count = scrape.get_error_count()
        logger.info(f"错误 #{i}: 当前计数 = {count}")
    
    # 测试成功重置
    scrape.update_error_count(success=True)
    count = scrape.get_error_count()
    logger.info(f"成功后错误计数: {count} (应为0)")
    
    # 再次递增
    for i in range(1, 3):
        scrape.update_error_count(success=False)
        count = scrape.get_error_count()
        logger.info(f"新错误 #{i}: 当前计数 = {count}")
    
    logger.info("错误计数测试完成")

def test_daily_alert_limit():
    """测试每日告警限制功能"""
    logger.info("===== 测试每日告警限制 =====")
    
    # 确保没有上次告警记录
    if os.path.exists(scrape.LAST_ALERT_FILE):
        os.remove(scrape.LAST_ALERT_FILE)
    
    # 重置告警列表
    global sent_alerts
    sent_alerts = []
    
    # 连续尝试发送三次告警
    for i in range(3):
        result = scrape.send_health_alert("error", f"测试告警 #{i+1}")
        logger.info(f"尝试 #{i+1}: 告警发送结果 = {result}")
        
        # 显示已发送的告警数量
        logger.info(f"已发送告警数量: {len(sent_alerts)}")
        
        # 短暂暂停
        time.sleep(1)
    
    # 检查结果 - 应该只有一个告警被发送
    if len(sent_alerts) == 1:
        logger.info("✅ 测试通过: 每日告警限制正常工作")
    else:
        logger.error(f"❌ 测试失败: 预期发送1个告警，实际发送了{len(sent_alerts)}个")
    
    logger.info("每日告警限制测试完成")

def test_error_threshold():
    """测试错误阈值触发告警"""
    logger.info("===== 测试错误阈值触发告警 =====")
    
    # 确保初始状态为0
    if os.path.exists(scrape.ERROR_COUNT_FILE):
        os.remove(scrape.ERROR_COUNT_FILE)
    
    # 确保没有上次告警记录
    if os.path.exists(scrape.LAST_ALERT_FILE):
        os.remove(scrape.LAST_ALERT_FILE)
    
    # 重置告警列表
    global sent_alerts
    sent_alerts = []
    
    # 模拟连续错误直到超过阈值
    threshold = scrape.ERROR_THRESHOLD
    logger.info(f"当前错误阈值设置为: {threshold}")
    
    for i in range(threshold + 2):
        logger.info(f"模拟错误 #{i+1}/{threshold+2}")
        scrape.update_error_count(success=False)
        time.sleep(0.5)  # 短暂暂停
    
    # 检查是否发送了告警
    if len(sent_alerts) > 0:
        logger.info(f"✅ 测试通过: 错误阈值达到后发送了告警")
        logger.info(f"告警消息: {sent_alerts[0]['message']}")
    else:
        logger.error("❌ 测试失败: 错误阈值达到后未发送告警")
    
    logger.info("错误阈值测试完成")

def cleanup():
    """清理测试环境"""
    # 恢复原始函数
    scrape.send_health_alert = original_send_health_alert
    
    # 删除临时文件
    try:
        import shutil
        shutil.rmtree("./test_data")
        logger.info("测试环境已清理")
    except Exception as e:
        logger.warning(f"清理测试环境时出错: {e}")

def main():
    parser = argparse.ArgumentParser(description="健康检查测试工具")
    parser.add_argument('--test', choices=['all', 'count', 'limit', 'threshold'], 
                      default='all', help='测试类型: count=错误计数, limit=每日告警限制, threshold=错误阈值')
    parser.add_argument('--keep', action='store_true', help='保留测试数据文件')
    
    args = parser.parse_args()
    
    logger.info("开始健康检查测试")
    setup_test()
    
    try:
        if args.test in ['all', 'count']:
            test_error_counting()
            
        if args.test in ['all', 'limit']:
            test_daily_alert_limit()
            
        if args.test in ['all', 'threshold']:
            test_error_threshold()
    
    finally:
        logger.info("健康检查测试完成")
        if not args.keep:
            cleanup()
        else:
            logger.info("保留测试数据")

if __name__ == "__main__":
    main() 