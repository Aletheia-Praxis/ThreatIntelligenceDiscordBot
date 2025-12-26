import os
import requests
import time
import json
from enum import Enum
from typing import cast, List, Dict, Any, Callable, Tuple
import signal
import sys
import atexit
import logging

import feedparser  # type: ignore
from configparser import ConfigParser, NoOptionError
from dotenv import load_dotenv

from .. import webhooks, config
from ..Formatting import format_single_article

logger = logging.getLogger("rss")

# Load environment variables
load_dotenv(os.path.join(os.getcwd(), 'OriginFeeds', '.env.rss_feeds'))

private_rss_feed_list: List[List[str]] = json.loads(os.getenv("PRIVATE_RSS_FEED_LIST", "[]"))

gov_rss_feed_list: List[List[str]] = json.loads(os.getenv("GOV_RSS_FEED_LIST", "[]"))

FeedTypes = Enum("FeedTypes", "RSS JSON")

source_details: Dict[str, Dict[str, Any]] = {
    "Private RSS Feed": {
        "source": private_rss_feed_list,
        "hook": webhooks["PrivateSectorFeed"],
        "type": FeedTypes.RSS,
    },
    "Gov RSS Feed": {
        "source": gov_rss_feed_list,
        "hook": webhooks["GovermentFeed"],
        "type": FeedTypes.RSS,
    },
    "Ransomware News": {
        "source": "https://raw.githubusercontent.com/joshhighet/ransomwatch/main/posts.json",
        "hook": webhooks["RansomwareFeed"],
        "type": FeedTypes.JSON,
    },
}

rss_log_file_path = os.path.join(
    os.getcwd(),
    "Source",
    str(config["RSS"].get("RSSLogFile", "RSSLog.txt")),
)


rss_log = ConfigParser()
rss_log.read(rss_log_file_path)

if not rss_log.has_section("main"):
    rss_log.add_section("main")


def get_ransomware_news(source: str) -> List[Dict[str, Any]]:
    logger.debug("Querying latest ransomware information")
    posts = requests.get(source, timeout=30).json()

    for post in posts:
        post["publish_date"] = post["discovered"]
        post["title"] = "Post: " + post["post_title"]
        post["source"] = post["group_name"]

    return cast(List[Dict[str, Any]], posts)


def get_news_from_rss(rss_item: List[str]) -> List[Any]:
    logger.debug(f"Querying RSS feed at {rss_item[0]}")
    feed_entries = feedparser.parse(rss_item[0]).entries

    # This is needed to ensure that the oldest articles are proccessed first. See https://github.com/vxunderground/ThreatIntelligenceDiscordBot/issues/9 for reference
    for rss_object in feed_entries:
        rss_object["source"] = rss_item[1]
        try:
            rss_object["publish_date"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S", cast(time.struct_time, rss_object.published_parsed)
            )
        except (AttributeError, TypeError):
            rss_object["publish_date"] = time.strftime(
                "%Y-%m-%dT%H:%M:%S", cast(time.struct_time, rss_object.updated_parsed)
            )

    return cast(List[Any], feed_entries)


def proccess_articles(articles: List[Any]) -> Tuple[List[Any], List[Any]]:
    messages, new_articles = [], []
    articles.sort(key=lambda article: article["publish_date"])

    for article in articles:
        try:
            config_entry = rss_log.get("main", article["source"])
        except NoOptionError:  # automatically add newly discovered groups to config
            rss_log.set("main", article["source"], " = ?")
            config_entry = rss_log.get("main", article["source"])

        if config_entry.endswith("?"):
            rss_log.set("main", article["source"], article["publish_date"])
        else:
            if config_entry >= article["publish_date"]:
                continue

        messages.append(format_single_article(article))
        new_articles.append(article)

    return messages, new_articles


def send_messages(hook: Any, messages: List[Any], articles: List[Any], batch_size: int = 10) -> None:
    logger.debug(f"Sending {len(messages)} messages in batches of {batch_size}")
    for i in range(0, len(messages), batch_size):
        hook.send(embeds=messages[i : i + batch_size])

        for article in articles[i : i + batch_size]:
            rss_log.set("main", article["source"], article["publish_date"])

        time.sleep(3)


def process_source(post_gathering_func: Callable[[Any], List[Any]], source: Any, hook: Any) -> None:
    raw_articles = post_gathering_func(source)

    processed_articles, new_raw_articles = proccess_articles(raw_articles)
    send_messages(hook, processed_articles, new_raw_articles)


def handle_rss_feed_list(rss_feed_list: List[List[str]], hook: Any) -> None:
    for rss_feed in rss_feed_list:
        logger.info(f"Handling RSS feed for {rss_feed[1]}")
        webhooks["StatusMessages"].send(f"> {rss_feed[1]}")

        process_source(get_news_from_rss, rss_feed, hook)


def write_status_message(message: str) -> None:
    webhooks["StatusMessages"].send(f"**{time.ctime()}**: *{message}*")
    logger.info(message)


def clean_up_and_close() -> None:
    logger.critical("Writing last things to rss log file and closing up")
    with open(rss_log_file_path, "w") as f:
        rss_log.write(f)

    sys.exit(0)


def main() -> None:
    logger.debug("Registering clean-up handlers")
    atexit.register(clean_up_and_close)
    signal.signal(signal.SIGTERM, lambda num, frame: clean_up_and_close())

    while True:
        for detail_name, details in source_details.items():
            write_status_message(f"Checking {detail_name}")

            if details["type"] == FeedTypes.JSON:
                process_source(get_ransomware_news, details["source"], details["hook"])
            elif details["type"] == FeedTypes.RSS:
                handle_rss_feed_list(details["source"], details["hook"])

            time.sleep(3)

        logger.debug("Writing new time to rss log file")
        with open(rss_log_file_path, "w") as f:
            rss_log.write(f)

        write_status_message("All done, going to sleep")

        time.sleep(1800)


if __name__ == "__main__":
    main()
