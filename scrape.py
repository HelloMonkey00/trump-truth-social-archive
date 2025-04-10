import requests
import json
import os
import time
import csv
import re
import logging
from datetime import datetime, timedelta
from send_lark_notification import check_and_notify

# 确保所有必要的目录都存在
DATA_DIR = "./data"
LOG_DIR = "./data/logs"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

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

# Load credentials from environment variables
SCRAPEOPS_API_KEY = os.getenv("SCRAPE_PROXY_KEY")
SCRAPEOPS_ENDPOINT = "https://proxy.scrapeops.io/v1/"
OUTPUT_JSON_FILE = "./data/truth_archive.json"
OUTPUT_CSV_FILE = "./data/truth_archive.csv"
ARCHIVE_URL = "https://stilesdata.com/trump-truth-social-archive/truth_archive.json"
BASE_URL = "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses"

# 健康检查相关配置
HEALTH_CHECK_URL = os.getenv("HEALTH_CHECK_URL")
ERROR_THRESHOLD = 5  # 连续错误阈值
ERROR_COUNT_FILE = "./data/error_count.txt"
LAST_ALERT_FILE = "./data/last_alert.txt"

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
        logger.warning("Missing HEALTH_CHECK_URL environment variable")
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

def update_error_count(success=False):
    """
    更新错误计数
    如果success=True，重置计数
    否则递增计数
    """
    count = 0 if success else get_error_count() + 1
    
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

def scrape(url, headers=None):
    """
    Makes a GET request to the target URL through the ScrapeOps proxy.
    """
    if not SCRAPEOPS_API_KEY:
        raise ValueError("Missing SCRAPE_PROXY_KEY environment variable")

    session = requests.Session()
    if headers:
        session.headers.update(headers)

    proxy_params = {
        'api_key': SCRAPEOPS_API_KEY,
        'url': url, 
        'bypass': 'cloudflare_level_1'
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
        logger.info(f"Loading existing posts from {ARCHIVE_URL}")
        response = requests.get(ARCHIVE_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        existing_posts = {post["id"]: post for post in data}
        logger.info(f"Loaded {len(existing_posts)} existing posts")
        return existing_posts
    except requests.RequestException as e:
        logger.warning(f"Could not fetch existing archive, starting fresh. Error: {e}")
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
    Fetches posts with pagination up to a specified number of pages.
    """
    logger.info("Starting post fetch operation")
    headers = {
        'accept': 'application/json, text/plain, */*',
        'referer': 'https://truthsocial.com/@realDonaldTrump'
    }
    
    params = {
        "exclude_replies": "true",
        "only_replies": "false",
        "with_muted": "true",
        "limit": "20"
    }

    existing_posts = load_existing_posts()
    all_posts = list(existing_posts.values())  # Start with existing data
    page_count = 0
    new_posts = []
    found_new_posts = False
    success = False

    try:
        while page_count < max_pages:
            url = f"{BASE_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
            logger.info(f"Fetching page {page_count+1}/{max_pages}: {url}")

            try:
                response = scrape(url, headers=headers)
                if not response:  # Ensure response is valid
                    logger.warning(f"Empty response from {url}. Skipping.")
                    continue

                current_page_posts = extract_posts(response, existing_posts)
                if not current_page_posts:
                    logger.info("No new posts found. Exiting pagination.")
                    success = True  # 即使没有新帖子，也算成功
                    break  # No more new posts

                new_posts.extend(current_page_posts)
                found_new_posts = True
                params["max_id"] = current_page_posts[-1]["id"]  # Get older posts
                page_count += 1
                success = True  # 至少有一页抓取成功就算成功

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching posts: {e}")
                success = False
                break
                
        if new_posts:
            logger.info(f"Found {len(new_posts)} new posts in total")
            all_posts.extend(new_posts)  # Merge new posts
            
            # 排序帖子（按创建时间降序）
            all_posts.sort(key=lambda post: post["created_at"], reverse=True)
            
            # 保存到文件
            append_to_json_file(all_posts, OUTPUT_JSON_FILE)
            append_to_csv_file(all_posts, OUTPUT_CSV_FILE)
            
            logger.info(f"Scraping complete. {len(new_posts)} new posts added.")

            # 更新健康检查状态
            with open("./data/last_success.txt", "w") as f:
                f.write(str(int(time.time())))
            logger.info("Updated last success timestamp")

            # 立即调用通知功能
            logger.info("Sending notifications for new posts...")
            check_and_notify()
        else:
            logger.info("Scraping complete. No new posts found.")
            
        # 更新错误计数（成功时重置为0）
        update_error_count(success=success)
        logger.info(f"Updated error count. Success: {success}")
            
    except Exception as e:
        logger.error(f"Unexpected error during scraping: {str(e)}", exc_info=True)
        # 更新错误计数
        update_error_count(success=False)
    
    logger.info("Fetch operation completed")

if __name__ == "__main__":
    logger.info(f"=== Trump Truth Social Scraper started at {datetime.now().isoformat()} ===")
    fetch_posts(max_pages=3)
    logger.info(f"=== Scraper run completed at {datetime.now().isoformat()} ===")