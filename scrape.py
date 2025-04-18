import requests
import json
import os
import time
import csv
import re
import logging
from datetime import datetime, timedelta
from send_lark_notification import check_and_notify
from config import (
    SCRAPEOPS_API_KEY, 
    SCRAPEOPS_ENDPOINT, 
    OUTPUT_JSON_FILE, 
    OUTPUT_CSV_FILE,
    ARCHIVE_URL, 
    BASE_URL, 
    HEALTH_CHECK_URL, 
    ERROR_THRESHOLD,
    ERROR_COUNT_FILE,
    LAST_ALERT_FILE,
    USE_LOCAL_ARCHIVE,
    ANALYZE_MARKET,
    DEEPSEEK_API_KEY,
    AUTO_NOTIFY_MODE
)

# 确保所有必要的目录都存在
DATA_DIR = "./data"
LOG_DIR = "./data/logs"
ANALYSIS_DIR = "./data/analysis"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(ANALYSIS_DIR, exist_ok=True)

# 配置日志
log_file = f"{LOG_DIR}/scraper_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # 同时输出到控制台
    ]
)
logger = logging.getLogger('trump_scraper')

# 检测是否需要进行市场分析
try:
    # 尝试导入市场分析模块 - 如果成功，则可以执行分析
    from analyze_posts import PostAnalyzer
    CAN_ANALYZE = True and ANALYZE_MARKET and DEEPSEEK_API_KEY
    if CAN_ANALYZE:
        logger.info("市场分析功能已启用")
    else:
        if not ANALYZE_MARKET:
            logger.info("市场分析功能已禁用 (ANALYZE_MARKET=False)")
        elif not DEEPSEEK_API_KEY:
            logger.warning("市场分析功能不可用：缺少DeepSeek API密钥")
except ImportError as e:
    logger.warning(f"市场分析功能不可用：{str(e)}")
    CAN_ANALYZE = False

def send_health_alert(status, message):
    """
    发送健康状态警报，但每天只发送一次
    
    Args:
        status (str): 状态 - 'error' 或 'warning'
        message (str): 详细信息
        
    Returns:
        bool: 是否发送成功
    """
    if not HEALTH_CHECK_URL:
        logger.warning("Missing health_check_url in config file")
        return False
    
    # 检查今天是否已经发送过告警
    today = datetime.now().date()
    if os.path.exists(LAST_ALERT_FILE):
        with open(LAST_ALERT_FILE, "r") as f:
            try:
                last_alert_date = datetime.fromtimestamp(int(f.read().strip())).date()
                if last_alert_date == today:
                    logger.info(f"Alert already sent today ({today}). Skipping.")
                    return False
            except (ValueError, IOError) as e:
                logger.warning(f"Error reading last alert date: {e}")
    
    payload = {
        "status": status,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "service": "trump-truth-scraper"
    }
    
    try:
        response = requests.post(
            HEALTH_CHECK_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent health alert: {message}")
            
            # 记录今天已发送告警
            with open(LAST_ALERT_FILE, "w") as f:
                f.write(str(int(time.time())))
                
            return True
        else:
            logger.error(f"Failed to send health alert: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending health alert: {str(e)}")
        return False

def get_error_count():
    """获取当前错误计数"""
    if os.path.exists(ERROR_COUNT_FILE):
        try:
            with open(ERROR_COUNT_FILE, "r") as f:
                return int(f.read().strip())
        except (ValueError, IOError):
            return 0
    return 0

def update_error_count():
    """
    更新错误计数，递增计数
    """
    count = get_error_count() + 1
    
    try:
        with open(ERROR_COUNT_FILE, "w") as f:
            f.write(str(count))
        
        # 如果错误次数达到阈值，发送告警
        if count >= ERROR_THRESHOLD:
            logger.warning(f"Error threshold reached: {count} consecutive failures")
            send_health_alert(
                "error", 
                f"Scraper failed {count} consecutive times. The target site may be blocking requests or have changed its structure."
            )
    except IOError as e:
        logger.warning(f"Error updating error count: {e}")

def reset_error_count():
    """
    重置错误计数为0
    """
    try:
        with open(ERROR_COUNT_FILE, "w") as f:
            f.write("0")
        logger.info("Error count reset to 0")
    except IOError as e:
        logger.warning(f"Error resetting error count: {e}")

def scrape(url, headers=None):
    """
    Makes a GET request to the target URL through the ScrapeOps proxy.
    """
    if not SCRAPEOPS_API_KEY:
        raise ValueError("Missing scrape_proxy_key in config file")

    session = requests.Session()
    if headers:
        session.headers.update(headers)

    proxy_params = {
        'api_key': SCRAPEOPS_API_KEY,
        'url': url, 
        # 'bypass': 'cloudflare_level_1' # 如果需要绕过Cloudflare防护，请取消注释，但是会增加credit消耗
    }

    logger.info(f"Making request to: {url}")
    response = session.get(SCRAPEOPS_ENDPOINT, params=proxy_params, timeout=120)
    response.raise_for_status()
    logger.info(f"Request successful, received {len(response.text)} bytes")

    return response.json()

def load_existing_posts():
    """
    Loads existing posts from the archive.
    """
    try:
        # 首先检查是否使用本地存档
        if USE_LOCAL_ARCHIVE:
            if os.path.exists(OUTPUT_JSON_FILE):
                logger.info(f"Loading existing posts from local file: {OUTPUT_JSON_FILE}")
                with open(OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                existing_posts = {post["id"]: post for post in data}
                logger.info(f"Loaded {len(existing_posts)} existing posts from local file")
                return existing_posts
            else:
                logger.info(f"Local archive file not found: {OUTPUT_JSON_FILE}. Starting with empty archive.")
                return {}
        
        # 如果不使用本地存档且设置了远程URL，则从远程获取
        elif ARCHIVE_URL:
            logger.info(f"Loading existing posts from remote URL: {ARCHIVE_URL}")
            response = requests.get(ARCHIVE_URL, timeout=30)
            response.raise_for_status()
            data = response.json()
            existing_posts = {post["id"]: post for post in data}
            logger.info(f"Loaded {len(existing_posts)} existing posts from remote URL")
            return existing_posts
        
        # 如果既不使用本地存档，也没有设置远程URL
        else:
            logger.info("No archive source configured. Starting with empty archive.")
            return {}
            
    except Exception as e:
        logger.warning(f"Could not load existing archive, starting fresh. Error: {e}")
        return {}

def append_to_json_file(data, file_path):
    """
    Saves the full dataset to JSON (array format).
    """
    logger.info(f"Saving {len(data)} posts to JSON file: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def append_to_csv_file(data, file_path):
    """
    Saves the dataset to a CSV file, including engagement metrics.
    """
    logger.info(f"Saving {len(data)} posts to CSV file: {file_path}")
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "created_at", "content", "url", "media", "replies_count", "reblogs_count", "favourites_count"])
        for post in data:
            media_urls = "; ".join(post.get("media", []))
            writer.writerow([
                post.get("id"),
                post.get("created_at"),
                post.get("content", ""),
                post.get("url"),
                media_urls,
                post.get("replies_count", 0),
                post.get("reblogs_count", 0),
                post.get("favourites_count", 0)
            ])

def clean_html(raw_html):
    """
    Removes HTML tags from a string.
    This strips unwanted markup like anchor tags.
    """
    return re.sub('<.*?>', '', raw_html)

def fix_unicode(text):
    """
    Ensures that escaped Unicode sequences (e.g., \u2026, \u2014)
    are converted to their proper characters.
    """
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except Exception:
        return text

def extract_posts(json_response, existing_posts):
    """
    Extracts relevant data from the JSON response, including engagement metrics.
    Applies clean_html and fix_unicode to the post content.
    """
    extracted_data = []
    
    for post in json_response:
        post_id = post.get("id")
        if post_id in existing_posts:
            continue  # Skip duplicates

        media_urls = [media.get("url", "") for media in post.get("media_attachments", [])]

        extracted_data.append({
            "id": post_id,  # Needed for pagination
            "created_at": post.get("created_at"),
            "content": fix_unicode(clean_html(post.get("content", ""))).strip(),
            "url": post.get("url"),
            "media": media_urls,  # Store media in an array
            "replies_count": post.get("replies_count", 0),  # Number of replies
            "reblogs_count": post.get("reblogs_count", 0),  # Number of reblogs (shares)
            "favourites_count": post.get("favourites_count", 0)  # Number of likes
        })

    logger.info(f"Extracted {len(extracted_data)} new posts")
    return extracted_data

def fetch_posts(max_pages=3):
    """
    Fetches Truth Social posts from Trump's account.
    """
    if not SCRAPEOPS_API_KEY:
        logger.error("Missing scrape_proxy_key in config file")
        update_error_count()
        send_health_alert(status="error", message="Missing scrape_proxy_key in config file")
        return False
    
    logger.info(f"Starting to fetch posts (max pages: {max_pages})")
    all_posts = []
    existing_posts = {}
    
    # 如果已有数据，加载并构建查重字典
    if os.path.exists(OUTPUT_JSON_FILE):
        try:
            with open(OUTPUT_JSON_FILE, 'r', encoding='utf-8') as f:
                old_posts = json.load(f)
                logger.info(f"Loaded {len(old_posts)} existing posts")
                all_posts = old_posts
                existing_posts = {post.get("id"): True for post in old_posts}
        except Exception as e:
            logger.error(f"Error loading existing posts: {e}")
    
    if not existing_posts:
        logger.info("No existing posts found, starting fresh")
    
    # 设置API访问
    max_id = None
    total_new_posts = 0
    success = False
    
    for i in range(max_pages):
        try:
            # 构建URL
            url = f"{BASE_URL}?limit=20"
            if max_id:
                url = f"{url}&max_id={max_id}"
            
            logger.info(f"Fetching page {i+1}/{max_pages}")
            
            # 发起请求
            response_json = scrape(url)
            
            # 提取帖子数据
            new_posts = extract_posts(response_json, existing_posts)
            
            if not new_posts:
                logger.info("No new posts found, stopping pagination")
                break
                
            # 更新帖子集合
            all_posts = new_posts + all_posts
            total_new_posts += len(new_posts)
            
            # 保存中间结果
            if all_posts:
                append_to_json_file(all_posts, OUTPUT_JSON_FILE)
                append_to_csv_file(all_posts, OUTPUT_CSV_FILE)
            
            # 设置下一页的max_id参数（基于当前页的最后一个帖子ID）
            if response_json and len(response_json) > 0:
                max_id = response_json[-1].get("id")
            else:
                break
                
            # 设置爬取成功标志
            success = True
            
            # 避免请求过快
            if i < max_pages - 1:
                time.sleep(2)
                
        except Exception as e:
            logger.error(f"Error fetching posts on page {i+1}: {str(e)}")
            update_error_count()
            success = False
            break
    
    # 发送健康检查 ping
    send_health_alert(status="error" if not success else "success", message=f"Scraper completed with {'success' if success else 'failure'}")
    
    if success:
        reset_error_count()
        logger.info(f"Successfully fetched {total_new_posts} new posts")
        
        # 如果开启市场分析功能，则分析新抓取的帖子
        if CAN_ANALYZE and total_new_posts > 0:
            logger.info("开始进行市场分析...")
            try:
                analyzer = PostAnalyzer()
                
                # 分析最新的帖子
                analysis_results = {}
                posts_to_analyze = all_posts[:5]  # 最多分析最新的5条帖子
                analyzed_count = 0
                notified_count = 0
                
                # 获取已有的分析结果
                existing_results = analyzer.load_analysis_results()
                
                for post in posts_to_analyze:
                    post_id = post.get("id")
                    post_content = post.get("content", "")
                    
                    # 跳过空内容或已分析的帖子
                    if not post_content or post_id in existing_results:
                        continue
                        
                    try:
                        # 分析帖子
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
                        analyzed_count += 1
                        
                        # 检查市场影响强度是否超过阈值
                        impact_intensity = market_impact.get("intensity", 0)
                        impact_direction = market_impact.get("direction", "neutral")
                        
                        # 决定是否发送通知
                        should_notify = False
                        notify_reason = ""
                        
                        # 根据模式选择判断方法
                        if AUTO_NOTIFY_MODE:
                            # 使用AI自动判断
                            should_notify, notify_reason = analyzer.should_send_notification(post_content, market_impact)
                            logger.info(f"AI自动判断结果: {should_notify}, 理由: {notify_reason}")
                        else:
                            # 使用传统方式判断
                            should_notify = (impact_intensity >= 3 and impact_direction != "neutral")
                            notify_reason = f"根据阈值判断 (强度: {impact_intensity}/5)"
                        
                        if should_notify:
                            # 发送市场分析通知
                            if analyzer.send_analysis_notification(post, analysis):
                                logger.info(f"成功发送帖子 {post_id} 的分析结果通知 (影响强度: {impact_intensity}, 理由: {notify_reason})")
                                notified_count += 1
                            else:
                                logger.warning(f"发送帖子 {post_id} 的分析结果通知失败")
                        else:
                            logger.info(f"帖子 {post_id} 不需要发送通知 (理由: {notify_reason})")
                        
                        # 更新上次分析的最后一条ID
                        analyzer.save_last_analyzed_id(post_id)
                        
                    except Exception as e:
                        logger.error(f"分析帖子 {post_id} 时出错: {str(e)}")
                        continue
                
                # 保存分析结果
                analyzer.save_analysis_results(existing_results)
                
                if analyzed_count > 0:
                    logger.info(f"市场分析完成，共分析 {analyzed_count} 条帖子，发送通知 {notified_count} 条")
                else:
                    logger.warning("市场分析未找到需要分析的帖子")
                    
            except Exception as e:
                logger.error(f"市场分析过程中出错: {str(e)}")
        
        return True
    else:
        logger.error("Failed to fetch posts")
        return False

if __name__ == "__main__":
    logger.info(f"=== Trump Truth Social Scraper started at {datetime.now().isoformat()} ===")
    fetch_posts(max_pages=3)
    logger.info(f"=== Scraper run completed at {datetime.now().isoformat()} ===")