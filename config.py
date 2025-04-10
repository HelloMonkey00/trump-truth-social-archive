import json
import os
import logging

# 确保日志目录存在
os.makedirs("./data/logs", exist_ok=True)

# 配置文件路径
CONFIG_FILE = "./data/config.json"

# 默认配置
DEFAULT_CONFIG = {
    "scrape_proxy_key": "",
    "lark_webhook_url": "",
    "health_check_url": "",
    "archive_url": "",  # 移除远程URL
    "use_local_archive": True,  # 添加使用本地存档的标志
    "base_url": "https://truthsocial.com/api/v1/accounts/107780257626128497/statuses",
    "error_threshold": 5
}

def load_config():
    """
    从配置文件加载配置。
    如果配置文件不存在，则创建一个包含默认值的配置文件。
    """
    # 确保data目录存在
    os.makedirs("./data", exist_ok=True)
    
    config = DEFAULT_CONFIG.copy()
    
    # 如果配置文件存在，从文件加载配置
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # 更新默认配置
                config.update(file_config)
        except Exception as e:
            print(f"Error loading config file: {e}")
    else:
        # 如果配置文件不存在，尝试从环境变量获取配置
        env_mapping = {
            "SCRAPE_PROXY_KEY": "scrape_proxy_key",
            "LARK_WEBHOOK_URL": "lark_webhook_url",
            "HEALTH_CHECK_URL": "health_check_url"
        }
        
        for env_var, config_key in env_mapping.items():
            if os.getenv(env_var):
                config[config_key] = os.getenv(env_var)
        
        # 保存配置到文件
        save_config(config)
    
    return config

def save_config(config):
    """
    保存配置到文件
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"Error saving config file: {e}")

# 加载配置
config = load_config()

# 导出配置变量，方便其他模块直接使用
SCRAPEOPS_API_KEY = config.get("scrape_proxy_key")
LARK_WEBHOOK_URL = config.get("lark_webhook_url")
HEALTH_CHECK_URL = config.get("health_check_url")
ARCHIVE_URL = config.get("archive_url")
BASE_URL = config.get("base_url")
ERROR_THRESHOLD = config.get("error_threshold", 5)
USE_LOCAL_ARCHIVE = config.get("use_local_archive", True)

# 常量配置
SCRAPEOPS_ENDPOINT = "https://proxy.scrapeops.io/v1/"
OUTPUT_JSON_FILE = "./data/truth_archive.json"
OUTPUT_CSV_FILE = "./data/truth_archive.csv"
ERROR_COUNT_FILE = "./data/error_count.txt"
LAST_ALERT_FILE = "./data/last_alert.txt" 