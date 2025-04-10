import requests
import json
import os
import time
from datetime import datetime, timedelta

# 健康检查URL - 如果爬虫出现问题，将发送通知到此URL
HEALTH_CHECK_URL = os.getenv("HEALTH_CHECK_URL")

# ScrapeOps API密钥 - 用于测试目标网站可访问性
SCRAPEOPS_API_KEY = os.getenv("SCRAPE_PROXY_KEY")
SCRAPEOPS_ENDPOINT = "https://proxy.scrapeops.io/v1/"
TARGET_URL = "https://truthsocial.com/@realDonaldTrump"

# 检查阈值
MAX_HOURS_WITHOUT_SUCCESS = 2  # 最长允许无成功抓取时间（小时）

def send_health_alert(status, message):
    """
    发送健康状态警报
    
    Args:
        status (str): 状态 - 'error' 或 'warning'
        message (str): 详细信息
    """
    if not HEALTH_CHECK_URL:
        print("⚠️ Missing HEALTH_CHECK_URL environment variable")
        return False
    
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
            print(f"✅ Successfully sent health alert: {message}")
            return True
        else:
            print(f"❌ Failed to send health alert: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending health alert: {str(e)}")
        return False

def test_target_site_access():
    """
    测试是否可以访问目标网站
    
    Returns:
        bool: 是否可访问
    """
    if not SCRAPEOPS_API_KEY:
        print("⚠️ Missing SCRAPE_PROXY_KEY environment variable")
        return False
    
    try:
        proxy_params = {
            'api_key': SCRAPEOPS_API_KEY,
            'url': TARGET_URL,
            'bypass': 'cloudflare_level_1'
        }
        
        response = requests.get(SCRAPEOPS_ENDPOINT, params=proxy_params, timeout=60)
        
        if response.status_code == 200:
            print("✅ Target site is accessible")
            return True
        else:
            print(f"❌ Failed to access target site: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing target site access: {str(e)}")
        return False

def check_scraper_health():
    """
    检查爬虫健康状态
    """
    # 检查最后成功抓取时间
    last_success_file = "./data/last_success.txt"
    current_time = time.time()
    
    if not os.path.exists(last_success_file):
        print("⚠️ No last success record found")
        send_health_alert("warning", "No scraping success record found. Scraper may not have run successfully yet.")
        return
    
    with open(last_success_file, "r") as f:
        try:
            last_success_time = int(f.read().strip())
            last_success_datetime = datetime.fromtimestamp(last_success_time)
            time_since_last_success = datetime.fromtimestamp(current_time) - last_success_datetime
            
            print(f"ℹ️ Last successful scrape: {last_success_datetime} ({time_since_last_success} ago)")
            
            # 检查是否超过阈值
            if time_since_last_success > timedelta(hours=MAX_HOURS_WITHOUT_SUCCESS):
                # 检查网站可访问性
                site_accessible = test_target_site_access()
                
                if site_accessible:
                    # 网站可访问但爬虫有问题
                    message = f"Scraper has not succeeded in {time_since_last_success}. Target site is accessible, but scraper may be experiencing issues."
                    send_health_alert("warning", message)
                else:
                    # 网站不可访问
                    message = f"Scraper has not succeeded in {time_since_last_success}. Target site is NOT accessible. Possible site changes or blocking."
                    send_health_alert("error", message)
            else:
                print("✅ Scraper health check passed")
            
        except ValueError as e:
            print(f"❌ Error reading last success time: {str(e)}")
            send_health_alert("warning", "Error reading last success time file. File may be corrupted.")

if __name__ == "__main__":
    print("🔍 Running health check...")
    check_scraper_health() 