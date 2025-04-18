#!/usr/bin/env python3
"""
测试脚本：从现有数据中提取过去一个月的帖子并进行市场分析，然后发送结果到Lark
"""
import json
import os
import logging
import argparse
from datetime import datetime, timedelta
import sys

# 导入分析模块
from analyze_posts import PostAnalyzer
from config import (
    OUTPUT_JSON_FILE,
    DEEPSEEK_API_KEY,
    LARK_WEBHOOK_URL,
    AUTO_NOTIFY_MODE
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)
logger = logging.getLogger('market_analysis_test')

def load_posts(file_path=OUTPUT_JSON_FILE):
    """加载已有的帖子数据"""
    if not os.path.exists(file_path):
        logger.error(f"帖子文件不存在: {file_path}")
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        logger.info(f"成功加载 {len(posts)} 条帖子")
        return posts
    except Exception as e:
        logger.error(f"加载帖子数据时出错: {str(e)}")
        return []

def filter_posts_by_date(posts, days=30):
    """筛选指定天数内的帖子"""
    # 创建不带时区的截止日期
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_posts = []
    
    for post in posts:
        try:
            # 处理不同格式的日期
            created_at = post['created_at']
            
            # 去除所有时区信息，以便纯日期比较
            if 'Z' in created_at:
                # ISO格式带Z结尾 (UTC)
                created_at = created_at.replace('Z', '')
                post_date = datetime.fromisoformat(created_at)
            elif '+' in created_at:
                # ISO格式带显式时区偏移
                # 先将其转换为datetime with timezone，再去除时区信息
                dt_with_tz = datetime.fromisoformat(created_at)
                post_date = dt_with_tz.replace(tzinfo=None)
            else:
                # 无时区信息的日期
                post_date = datetime.fromisoformat(created_at)
            
            # 现在两个日期都不带时区，可以安全比较
            if post_date >= cutoff_date:
                filtered_posts.append(post)
                
        except (ValueError, KeyError) as e:
            logger.warning(f"处理帖子日期时出错: {str(e)}，日期值: {post.get('created_at', 'N/A')}")
            continue
    
    logger.info(f"找到过去 {days} 天内的 {len(filtered_posts)} 条帖子")
    return filtered_posts

def analyze_and_send_to_lark(posts, limit=None, force_all=False, legacy_mode=False):
    """分析帖子并发送到Lark"""
    if not posts:
        logger.error("没有帖子可供分析")
        return False
        
    if not DEEPSEEK_API_KEY:
        logger.error("缺少DeepSeek API密钥，无法进行分析")
        return False
        
    if not LARK_WEBHOOK_URL:
        logger.warning("缺少Lark Webhook URL，无法发送通知")
        
    # 初始化分析器
    analyzer = PostAnalyzer(api_key=DEEPSEEK_API_KEY)
    logger.info("初始化分析器完成")
    
    # 如果强制分析所有帖子，清空上次分析记录
    if force_all:
        if os.path.exists(analyzer.last_analysis_file):
            os.remove(analyzer.last_analysis_file)
            logger.info("已清除上次分析记录，将分析所有选定的帖子")
    
    # 加载已有的分析结果
    existing_results = analyzer.load_analysis_results()
    logger.info(f"加载了 {len(existing_results)} 条已有的分析结果")
    
    # 筛选需要分析的帖子
    posts_to_analyze = []
    for post in posts:
        post_id = post.get("id")
        # 如果帖子已经分析过，且不是强制重新分析
        if post_id in existing_results and not force_all:
            continue
        posts_to_analyze.append(post)
    
    if limit and not force_all:
        posts_to_analyze = posts_to_analyze[:limit]
    
    if not posts_to_analyze:
        logger.info("没有新帖子需要分析")
        return True
        
    logger.info(f"将分析 {len(posts_to_analyze)} 条帖子")
    
    # 开始分析
    success_count = 0
    notify_count = 0
    for i, post in enumerate(posts_to_analyze):
        post_id = post.get("id")
        post_content = post.get("content", "")
        
        if not post_content:
            logger.warning(f"跳过空内容帖子 {post_id}")
            continue
            
        logger.info(f"正在分析帖子 {i+1}/{len(posts_to_analyze)}: {post_id}")
        
        try:
            # 进行各种分析
            market_impact = analyzer.analyze_market_impact(post_content)
            topics = analyzer.extract_topics(post_content)
            summary = analyzer.summarize_post(post_content)
            
            # 存储分析结果
            analysis = {
                "market_impact": market_impact,
                "topics": topics,
                "summary": summary,
                "analyzed_at": datetime.now().isoformat()
            }
            
            # 将结果添加到总表
            existing_results[post_id] = analysis
            
            # 检查市场影响，决定是否发送通知
            impact_intensity = market_impact.get("intensity", 0)
            impact_direction = market_impact.get("direction", "neutral")
            
            # 决定是否需要发送通知
            should_notify = False
            notify_reason = ""
            
            # 根据模式选择判断方法
            if not legacy_mode and AUTO_NOTIFY_MODE:
                # 使用AI自动判断
                should_notify, notify_reason = analyzer.should_send_notification(post_content, market_impact)
                logger.info(f"AI自动判断结果: {should_notify}, 理由: {notify_reason}")
            else:
                # 使用传统方式判断 (兼容旧版脚本)
                should_notify = (impact_intensity >= 3 and impact_direction != "neutral")
                notify_reason = f"根据阈值判断 (强度: {impact_intensity}/5)"
            
            # 发送通知（如果符合条件）
            if LARK_WEBHOOK_URL and should_notify:
                if analyzer.send_analysis_notification(post, analysis):
                    logger.info(f"成功发送帖子 {post_id} 的分析结果通知 (影响强度: {impact_intensity}, 理由: {notify_reason})")
                    notify_count += 1
                else:
                    logger.warning(f"发送帖子 {post_id} 的分析结果通知失败")
            elif not should_notify:
                logger.info(f"帖子 {post_id} 不需要发送通知 (理由: {notify_reason})")
            
            # 更新上次分析的最后一条ID
            analyzer.save_last_analyzed_id(post_id)
            success_count += 1
            
        except Exception as e:
            logger.error(f"分析帖子 {post_id} 时出错: {str(e)}")
            continue
    
    # 保存分析结果
    analyzer.save_analysis_results(existing_results)
    logger.info(f"分析完成，成功分析 {success_count}/{len(posts_to_analyze)} 条帖子，发送通知 {notify_count} 条")
    
    return success_count > 0

def main():
    parser = argparse.ArgumentParser(description="测试Trump帖子的金融市场分析功能")
    parser.add_argument("--days", type=int, default=30, help="分析过去几天的帖子，默认30天")
    parser.add_argument("--limit", type=int, default=None, help="最多分析多少条帖子，默认不限制")
    parser.add_argument("--file", type=str, default=OUTPUT_JSON_FILE, help="帖子数据文件路径")
    parser.add_argument("--force", action="store_true", help="强制重新分析所有帖子，即使已经分析过")
    parser.add_argument("--legacy", action="store_true", help="使用传统阈值模式决定是否发送通知")
    args = parser.parse_args()
    
    # 检查DeepSeek API密钥
    if not DEEPSEEK_API_KEY:
        logger.error("未设置DeepSeek API密钥，请设置环境变量DEEPSEEK_API_KEY或在配置文件中指定")
        return 1
        
    # 检查Lark Webhook URL
    if not LARK_WEBHOOK_URL:
        logger.warning("未设置Lark Webhook URL，分析结果将不会发送通知")
        
    # 加载数据
    posts = load_posts(args.file)
    if not posts:
        return 1
        
    # 筛选指定天数内的帖子
    filtered_posts = filter_posts_by_date(posts, args.days)
    if not filtered_posts:
        logger.error(f"过去 {args.days} 天内没有找到帖子")
        return 1
        
    # 分析帖子并发送到Lark
    if analyze_and_send_to_lark(filtered_posts, args.limit, args.force, args.legacy):
        logger.info(f"测试完成，使用{'传统阈值模式' if args.legacy else 'AI自动判断模式'}")
        return 0
    else:
        logger.error("测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 