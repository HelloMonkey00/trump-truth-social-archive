import json
import os
import logging
import time
from datetime import datetime
import requests
from config import (
    OUTPUT_JSON_FILE,
    LARK_WEBHOOK_URL,
    DEEPSEEK_API_KEY
)

# 确保所有必要的目录都存在
DATA_DIR = "./data"
LOG_DIR = "./data/logs"
ANALYSIS_DIR = "./data/analysis"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# 配置日志
log_file = f"{LOG_DIR}/analysis_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger('trump_analyzer')

# Deepseek API配置 - 从环境变量或配置文件获取
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 提示词配置文件
PROMPTS_CONFIG_FILE = "./config/prompts.json"

class PostAnalyzer:
    def __init__(self, api_key=None):
        """初始化分析器"""
        self.api_key = api_key or DEEPSEEK_API_KEY 
        if not self.api_key:
            logger.warning("Missing Deepseek API key. AI analysis functions will not work.")
        self.last_analysis_file = f"{ANALYSIS_DIR}/last_analysis.txt"
        self.analysis_results_file = f"{ANALYSIS_DIR}/analysis_results.json"
        self.prompts = self.load_prompts()
        
    def load_prompts(self):
        """加载提示词配置"""
        default_prompts = {}
        default_prompts["market_impact"] = "分析以下文本内容与金融市场的关系。考虑内容是否会影响股票市场、特定行业、公司股价或者美元汇率等。详细分析可能的市场影响方向（利好/利空）、影响强度（1-5分，5为最强）及影响范围。文本: \"{text}\"\n请以JSON格式返回结果，包含impact_type（影响类型）、direction（方向：positive/negative/neutral）、intensity（1-5）和affected_sectors（受影响行业）字段。"
        default_prompts["extract_topics"] = "分析以下文本，提取3-5个主要主题或关键词，特别关注与经济、金融市场相关的内容。\n文本: \"{text}\"\n请以JSON数组格式返回结果。"
        default_prompts["summarize_post"] = "用中文简洁地总结以下内容，重点关注可能影响金融市场的方面（50字以内）:\n\"{text}\"\n"
        default_prompts["should_notify"] = '评估以下内容是否真的会对金融市场产生实质性影响。内容: "{text}"\n分析: {analysis}\n只返回"是"或"否"开头，并附加一句简短的理由。'
        
        if os.path.exists(PROMPTS_CONFIG_FILE):
            try:
                with open(PROMPTS_CONFIG_FILE, "r", encoding="utf-8") as f:
                    custom_prompts = json.load(f)
                    # 更新默认提示词，但保留默认值如果自定义配置中不存在
                    for key, value in custom_prompts.items():
                        default_prompts[key] = value
                logger.info("Successfully loaded custom prompts")
            except Exception as e:
                logger.error(f"Error loading prompts config: {str(e)}")
        else:
            # 如果配置文件不存在，创建默认配置
            os.makedirs(os.path.dirname(PROMPTS_CONFIG_FILE), exist_ok=True)
            try:
                with open(PROMPTS_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_prompts, f, indent=2, ensure_ascii=False)
                logger.info(f"Created default prompts config at {PROMPTS_CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Error creating default prompts config: {str(e)}")
                
        return default_prompts
            
    def _call_deepseek_api(self, prompt, model="deepseek-chat"):
        """调用Deepseek API进行分析"""
        if not self.api_key:
            logger.error("No Deepseek API key provided")
            return None
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful financial analyst assistant."},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        try:
            response = requests.post(
                DEEPSEEK_API_URL,
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling Deepseek API: {str(e)}")
            return None
    
    def analyze_market_impact(self, text):
        """分析文本与金融市场的关系"""
        prompt = self.prompts["market_impact"].format(text=text)
        
        result = self._call_deepseek_api(prompt)
        if not result:
            return {"impact_type": "unknown", "direction": "neutral", "intensity": 0, "affected_sectors": []}
            
        try:
            # 尝试解析JSON结果
            import json
            return json.loads(result)
        except:
            # 简单文本解析
            impact_type = "general"
            direction = "neutral"
            intensity = 1
            affected_sectors = []
            
            # 基本解析
            if "股市" in result or "股票" in result:
                impact_type = "stock_market"
            elif "美元" in result or "汇率" in result:
                impact_type = "currency"
            elif "经济" in result:
                impact_type = "economy"
                
            if "利好" in result or "positive" in result:
                direction = "positive"
            elif "利空" in result or "negative" in result:
                direction = "negative"
                
            # 尝试提取强度
            import re
            intensity_match = re.search(r'intensity[\"\']\s*:\s*(\d)', result)
            if intensity_match:
                intensity = int(intensity_match.group(1))
                
            # 尝试提取行业
            sectors_match = re.search(r'affected_sectors[\"\']\s*:\s*\[(.*?)\]', result)
            if sectors_match:
                sectors_text = sectors_match.group(1)
                affected_sectors = [s.strip().strip('"\'') for s in sectors_text.split(',')]
                
            return {
                "impact_type": impact_type, 
                "direction": direction, 
                "intensity": intensity, 
                "affected_sectors": affected_sectors
            }
    
    def extract_topics(self, text):
        """提取文本主题"""
        prompt = self.prompts["extract_topics"].format(text=text)
        
        result = self._call_deepseek_api(prompt)
        if not result:
            return []
            
        try:
            # 尝试解析JSON结果
            import json
            return json.loads(result)
        except:
            # 简单文本解析，提取引号内内容或以逗号分隔的项
            import re
            topics = re.findall(r'\"([^\"]+)\"', result)
            if not topics:
                topics = [t.strip() for t in result.split(',')]
            return topics[:5]  # 最多返回5个主题
    
    def summarize_post(self, text):
        """生成文本摘要"""
        prompt = self.prompts["summarize_post"].format(text=text)
        
        result = self._call_deepseek_api(prompt)
        return result or "无法生成摘要"
    
    def should_send_notification(self, post_content, market_impact):
        """
        AI自动判断是否需要发送通知
        
        Args:
            post_content (str): 帖子内容
            market_impact (dict): 市场影响分析结果
            
        Returns:
            bool: 是否需要发送通知
            str: 判断理由
        """
        if not post_content:
            return False, "帖子内容为空"
            
        # 首先检查基本的市场影响信息
        impact_direction = market_impact.get("direction", "neutral")
        impact_intensity = market_impact.get("intensity", 0)
        
        # 如果影响为中性或强度为0，则不发送
        if impact_direction == "neutral" or impact_intensity == 0:
            return False, "市场影响为中性或无影响"
            
        # 对于低强度的影响，进一步评估其真实性
        if impact_intensity < 3:
            # 使用AI进一步判断
            prompt = f"""
            请评估以下Trump发布的帖子内容是否真的会对金融市场产生实质性影响：
            
            帖子内容："{post_content}"
            
            初步市场影响分析：方向({impact_direction})，强度({impact_intensity}/5)
            
            请进行更深入评估，判断其是否确实对金融市场有影响。
            只返回"是"或"否"，以及简短的一句话理由。
            """
            
            result = self._call_deepseek_api(prompt)
            if not result:
                # 如果调用API失败，根据初步分析结果保守判断
                return impact_intensity >= 3, "基于初步分析结果的保守判断"
                
            # 解析结果
            if "否" in result[:10]:
                reason = result.split("否", 1)[1].strip() if len(result.split("否", 1)) > 1 else "内容不足以影响市场"
                return False, reason
            elif "是" in result[:10]:
                reason = result.split("是", 1)[1].strip() if len(result.split("是", 1)) > 1 else "内容可能影响市场"
                return True, reason
            else:
                # 无法解析结果，使用初步分析
                return impact_intensity >= 3, "无法解析深度分析结果，基于初步分析决定"
        
        # 对于高强度影响，直接发送
        return True, f"市场影响强度较高({impact_intensity}/5)"
    
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
        """发送分析结果通知"""
        if not LARK_WEBHOOK_URL:
            logger.warning("Missing Lark webhook URL. Cannot send notification.")
            return False
            
        # 构建市场影响标记
        market_impact = analysis.get("market_impact", {})
        impact_direction = market_impact.get("direction", "neutral")
        impact_emoji = "🟡"
        if impact_direction == "positive":
            impact_emoji = "🟢"
        elif impact_direction == "negative":
            impact_emoji = "🔴"
            
        # 构建受影响行业
        affected_sectors = market_impact.get("affected_sectors", [])
        sector_text = ", ".join(affected_sectors) if affected_sectors else "无明确行业影响"
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": f"Trump发帖市场影响分析 {impact_emoji}"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**原文**：\n{post.get('content', '无内容')}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**AI摘要**：\n{analysis.get('summary', '无摘要')}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**市场影响**：{impact_emoji} {impact_direction} (强度: {market_impact.get('intensity', 0)}/5)"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**影响类型**：{market_impact.get('impact_type', '未知')}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**受影响行业**：{sector_text}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**主题标签**：{' '.join([f'#{t}' for t in analysis.get('topics', [])[:3]])}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"发布于 {post.get('created_at')}"
                        }
                    ]
                }
            ]
        }
        
        # 媒体内容
        media_urls = post.get("media", [])
        if media_urls:
            # 只显示第一张图片
            card["elements"].insert(1, {
                "tag": "img",
                "img_key": media_urls[0],
                "alt": {
                    "tag": "plain_text",
                    "content": "帖子图片"
                }
            })
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        try:
            response = requests.post(
                LARK_WEBHOOK_URL,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully sent analysis notification for post {post.get('id')}")
                return True
            else:
                logger.error(f"Failed to send analysis notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending analysis notification: {str(e)}")
            return False
            
    def analyze_posts(self, limit=5):
        """
        分析最新的帖子，并存储分析结果
        仅分析尚未分析过的帖子（基于上次分析的最后一条ID）
        """
        # 加载帖子
        if not os.path.exists(OUTPUT_JSON_FILE):
            logger.error(f"Posts file not found: {OUTPUT_JSON_FILE}")
            return False
            
        try:
            with open(OUTPUT_JSON_FILE, "r", encoding="utf-8") as f:
                posts = json.load(f)
        except Exception as e:
            logger.error(f"Error loading posts: {str(e)}")
            return False
            
        if not posts:
            logger.info("No posts to analyze")
            return False
            
        # 获取上次分析的最后一条ID
        last_analyzed_id = self.get_last_analyzed_id()
        
        # 加载已有的分析结果
        analysis_results = self.load_analysis_results()
        
        # 仅分析新帖子
        new_posts = []
        for post in posts:
            post_id = post.get("id")
            
            # 如果已分析过该帖子，跳过
            if post_id in analysis_results:
                continue
                
            # 如果遇到了上次分析的最后一条，停止
            if last_analyzed_id and post_id == last_analyzed_id:
                break
                
            new_posts.append(post)
            
            # 限制分析的帖子数量
            if len(new_posts) >= limit:
                break
                
        if not new_posts:
            logger.info("No new posts to analyze")
            return False
            
        logger.info(f"Found {len(new_posts)} new posts to analyze")
        
        # 分析帖子
        for post in new_posts:
            post_id = post.get("id")
            post_content = post.get("content", "")
            
            if not post_content:
                logger.warning(f"Skipping post {post_id} with empty content")
                continue
                
            try:
                # 进行各种分析
                market_impact = self.analyze_market_impact(post_content)
                topics = self.extract_topics(post_content)
                summary = self.summarize_post(post_content)
                
                # 存储分析结果
                analysis = {
                    "market_impact": market_impact,
                    "topics": topics,
                    "summary": summary,
                    "analyzed_at": datetime.now().isoformat()
                }
                
                # 将结果添加到总表
                analysis_results[post_id] = analysis
                
                # 发送通知
                self.send_analysis_notification(post, analysis)
                
                # 更新上次分析的最后一条ID
                self.save_last_analyzed_id(post_id)
                
                # 简单的速率限制，避免API调用过快
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error analyzing post {post_id}: {str(e)}")
                continue
                
        # 保存分析结果
        self.save_analysis_results(analysis_results)
        
        return True

def main():
    """主函数"""
    logger.info(f"=== Trump Truth Social Market Impact Analyzer started at {datetime.now().isoformat()} ===")
    
    analyzer = PostAnalyzer()
    analyzer.analyze_posts(limit=5)
    
    logger.info(f"=== Analyzer run completed at {datetime.now().isoformat()} ===")

if __name__ == "__main__":
    main() 