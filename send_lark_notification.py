import requests
import json
import os
import time
import logging
from datetime import datetime
from config import LARK_WEBHOOK_URL

# 确保所有必要的目录都存在
DATA_DIR = "./data"
LOG_DIR = "./data/logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
log_file = f"{LOG_DIR}/lark_notification_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger('lark_notifier')

def send_lark_notification(post):
    """
    向Lark发送通知
    
    Args:
        post (dict): 单个Trump的帖子数据
    
    Returns:
        bool: 发送是否成功
    """
    if not LARK_WEBHOOK_URL:
        logger.warning("Missing lark_webhook_url in config file")
        return False
    
    # 准备媒体内容部分
    media_content = ""
    if post.get("media") and len(post["media"]) > 0:
        media_content = "\n\n🖼 *附带媒体文件*: " + post["media"][0]
    
    # 格式化创建时间
    try:
        created_at = datetime.fromisoformat(post["created_at"].replace('Z', '+00:00'))
        formatted_time = created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception as e:
        logger.warning(f"Error parsing date {post['created_at']}: {e}")
        formatted_time = post["created_at"]
    
    logger.info(f"Preparing notification for post ID: {post.get('id')}")
    
    # 构建Lark消息卡片
    message = {
        "msg_type": "interactive",
        "card": {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🚨 特朗普发布了新推文"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**发布时间**: {formatted_time}\n\n{post.get('content', '')}{media_content}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**回复**: {post.get('replies_count', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**转发**: {post.get('reblogs_count', 0)}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**点赞**: {post.get('favourites_count', 0)}"
                            }
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看原文"
                            },
                            "url": post.get("url", ""),
                            "type": "default"
                        }
                    ]
                }
            ]
        }
    }
    
    # 发送请求到Lark
    try:
        logger.info(f"Sending notification to Lark for post ID: {post.get('id')}")
        response = requests.post(
            LARK_WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(message),
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent notification for post {post.get('id')}")
            return True
        else:
            logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

def check_and_notify():
    """
    检查最新帖子并发送通知
    """
    logger.info("Starting notification check process")
    try:
        # 读取存储的最后通知的ID
        last_notified_id = ""
        last_id_file = "./data/last_notified_id.txt"
        
        if os.path.exists(last_id_file):
            with open(last_id_file, "r") as f:
                last_notified_id = f.read().strip()
                logger.info(f"Last notified post ID: {last_notified_id}")
        else:
            logger.info("No previous notification record found")
        
        # 加载当前存档
        archive_file = "./data/truth_archive.json"
        
        if not os.path.exists(archive_file):
            logger.error(f"Archive file not found: {archive_file}")
            return
            
        with open(archive_file, "r", encoding="utf-8") as f:
            archive = json.load(f)
        
        logger.info(f"Loaded archive with {len(archive)} posts")
        
        if not archive or len(archive) == 0:
            logger.warning("Empty archive, no posts to notify about")
            return
            
        # 找出需要通知的新帖子（按创建时间降序排序）
        new_posts = []
        for post in archive:
            if not last_notified_id or post["id"] > last_notified_id:
                new_posts.append(post)
                
        # 按创建时间降序排序
        new_posts.sort(key=lambda p: p["created_at"], reverse=True)
        
        if new_posts:
            logger.info(f"Found {len(new_posts)} new posts to notify about")
            
            # 最多通知5条，防止首次运行时发送过多
            notify_posts = new_posts[:5]
            logger.info(f"Will notify about {len(notify_posts)} posts (limited to max 5)")
            
            for post in notify_posts:
                success = send_lark_notification(post)
                if success and notify_posts.index(post) == 0:
                    # 保存最新通知的ID
                    with open(last_id_file, "w") as f:
                        f.write(post["id"])
                    logger.info(f"Updated last notified ID to: {post['id']}")
                    
                # 避免频繁发送通知
                time.sleep(1)
        else:
            logger.info("No new posts to notify about")
            
    except Exception as e:
        logger.error(f"Error in check_and_notify: {str(e)}", exc_info=True)
    
    logger.info("Notification check process completed")

if __name__ == "__main__":
    logger.info(f"=== Lark notification process started at {datetime.now().isoformat()} ===")
    check_and_notify()
    logger.info(f"=== Lark notification process completed at {datetime.now().isoformat()} ===") 