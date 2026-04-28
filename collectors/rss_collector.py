from typing import List, Dict
from pathlib import Path
import yaml
import feedparser

from core.scoring import score_item


RSS_PATH = Path("config/rss_feeds.yaml")


def load_feeds() -> List[Dict]:
    with open(RSS_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("feeds", [])


def collect_rss(max_entries_per_feed: int = 6) -> List[Dict]:
    feeds = load_feeds()
    items = []

    for feed in feeds:
        name = feed["name"]
        url = feed["url"]
        category = feed.get("category", "general")

        try:
            parsed = feedparser.parse(url)

            if parsed.bozo:
                print(f"[RSS] Warning for {name}: feed may be malformed")

            for entry in parsed.entries[:max_entries_per_feed]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                published = entry.get("published", "")

                if not title or not link:
                    continue

                item = {
                    "source_type": "rss",
                    "source_name": name,
                    "category": category,
                    "title": title,
                    "url": link,
                    "author": entry.get("author", name),
                    "published_at": published,
                    "raw_text": summary,
                    "score": score_item(title, summary, category=category),
                }

                items.append(item)

        except Exception as e:
            print(f"[RSS] Error for {name}: {e}")

    return items
