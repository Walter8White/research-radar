from typing import List, Dict
from pathlib import Path
import yaml
import feedparser

from core.scoring import score_item_breakdown
from core.freshness import (
    DEFAULT_RECENCY_DAYS,
    freshness_score,
    is_recent,
    normalize_datetime_string,
)


RSS_PATH = Path("config/rss_feeds.yaml")


def load_feeds() -> List[Dict]:
    with open(RSS_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config.get("feeds", [])


def collect_rss(
    max_entries_per_feed: int = 6,
    recency_days: int = DEFAULT_RECENCY_DAYS,
) -> List[Dict]:
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
                published = normalize_datetime_string(
                    entry.get("published_parsed") or entry.get("updated_parsed") or entry.get("published") or entry.get("updated")
                )

                if not title or not link:
                    continue

                if not is_recent(published, recency_days):
                    continue

                item_freshness_score = freshness_score(published, recency_days)
                score_breakdown = score_item_breakdown(
                    title,
                    summary,
                    category=category,
                    source_type="rss",
                    freshness_score=item_freshness_score,
                )

                item = {
                    "source_type": "rss",
                    "source_name": name,
                    "category": category,
                    "title": title,
                    "url": link,
                    "author": entry.get("author", name),
                    "published_at": published,
                    "raw_text": summary,
                    "score": score_breakdown["final_score"],
                    **score_breakdown,
                }

                items.append(item)

        except Exception as e:
            print(f"[RSS] Error for {name}: {e}")

    return items
