#!/usr/bin/env python3
"""
虚拟分析器 - 用于测试，不依赖实际API调用
"""
import json
import os
import logging
from datetime import datetime
import random

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)
logger = logging.getLogger('dummy_analyzer')

class DummyAnalyzer:
    def __init__(self, api_key=None):
        """初始化分析器"""
        self.api_key = api_key
        self.last_analysis_file = "./data/analysis/last_analysis.txt"
        self.analysis_results_file = "./data/analysis/analysis_results.json"
        
        # 确保分析目录存在
        os.makedirs("./data/analysis", exist_ok=True)
        
    def analyze_market_impact(self, text):
        """生成虚拟的市场影响分析"""
        # 随机生成市场影响
        impact_types = ["stock_market", "currency", "economy", "industry", "company"]
        directions = ["positive", "negative", "neutral"]
        
        sectors = ["technology", "healthcare", "finance", "energy", "retail", 
                   "manufacturing", "real_estate", "communication", "consumer_goods"]
        
        # 根据文本长度决定受影响的行业数量
        num_sectors = min(3, max(1, len(text) // 200)) 
        
        return {
            "impact_type": random.choice(impact_types),
            "direction": random.choice(directions),
            "intensity": random.randint(1, 5),
            "affected_sectors": random.sample(sectors, num_sectors)
        }
    
    def extract_topics(self, text):
        """生成虚拟的主题提取"""
        # 预定义的主题
        all_topics = [
            "经济", "通货膨胀", "就业", "美联储", "利率", "股市", 
            "贸易", "中国", "俄罗斯", "国债", "政治", "选举",
            "美元", "石油", "环保", "科技", "社交媒体", "加密货币"
        ]
        
        # 根据文本长度决定主题数量
        num_topics = min(5, max(2, len(text) // 150))
        
        return random.sample(all_topics, num_topics)
    
    def summarize_post(self, text):
        """生成虚拟的摘要"""
        # 简单截取文本开头部分作为摘要
        max_len = min(50, len(text))
        summary = text[:max_len] + ("..." if len(text) > max_len else "")
        return summary
    
    def get_last_analyzed_id(self):
        """获取上次分析的最后一条帖子ID"""
        if os.path.exists(self.last_analysis_file):
            try:
                with open(self.last_analysis_file, "r") as f:
                    return f.read().strip()
            except:
                return None
        return None
        
    def save_last_analyzed_id(self, post_id):
        """保存最后分析的帖子ID"""
        try:
            with open(self.last_analysis_file, "w") as f:
                f.write(post_id)
        except Exception as e:
            logger.error(f"Error saving last analyzed ID: {str(e)}")
    
    def load_analysis_results(self):
        """加载已有的分析结果"""
        if os.path.exists(self.analysis_results_file):
            try:
                with open(self.analysis_results_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading analysis results: {str(e)}")
                return {}
        return {}
        
    def save_analysis_results(self, results):
        """保存分析结果"""
        try:
            with open(self.analysis_results_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved analysis results to {self.analysis_results_file}")
        except Exception as e:
            logger.error(f"Error saving analysis results: {str(e)}")
    
    def send_analysis_notification(self, post, analysis):
        """模拟发送分析结果通知"""
        logger.info(f"模拟发送通知: 帖子ID {post.get('id')}")
        logger.info(f"市场影响: {analysis.get('market_impact')}")
        logger.info(f"主题: {analysis.get('topics')}")
        logger.info(f"摘要: {analysis.get('summary')}")
        return True 