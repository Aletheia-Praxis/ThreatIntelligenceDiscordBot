import sys
import os
from dotenv import load_dotenv
from discord import SyncWebhook

from .Utils import verify_config_section

from os import mkdir

# Load environment variables
load_dotenv()

# Need to create folder before running script, as the logger will otherwise throw error
try:
    mkdir("logs")
except OSError:
    pass # Most likely simply means the folder already exists

from typing import Dict, Any

# Configuration dictionary to replace ConfigParser
config: Dict[str, Dict[str, Any]] = {
    "Webhooks": {
        "PrivateSectorFeed": os.getenv("WEBHOOK_PRIVATE_SECTOR_FEED"),
        "GovermentFeed": os.getenv("WEBHOOK_GOVERNMENT_FEED"),
        "RansomwareFeed": os.getenv("WEBHOOK_RANSOMWARE_FEED"),
        "TelegramFeed": os.getenv("WEBHOOK_TELEGRAM_FEED"),
        "StatusMessages": os.getenv("WEBHOOK_STATUS_MESSAGES"),
    },
    "Telegram": {
        "BotName": os.getenv("TELEGRAM_BOT_NAME"),
        "APIID": os.getenv("TELEGRAM_API_ID"),
        "APIHash": os.getenv("TELEGRAM_API_HASH"),
        "ImageDownloadFolder": os.getenv("TELEGRAM_IMAGE_DOWNLOAD_FOLDER", "TelegramImages"),
    },
    "RSS": {
        "RSSLogFile": os.getenv("RSS_LOG_FILE", "RSSLog.txt"),
    }
}

for section in ["Webhooks", "Telegram"]:
    if not section in config:
        sys.exit(f'Please specify a "{section}" section in the config file')

if verify_config_section(config, "Webhooks"):
    webhooks = {
        hook_name: SyncWebhook.from_url(hook_url)
        for hook_name, hook_url in config["Webhooks"].items()
        if hook_url # Ensure url is not None
    }
