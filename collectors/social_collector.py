import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import requests
import yaml
from dotenv import dotenv_values

from core.freshness import DEFAULT_RECENCY_DAYS, freshness_score, is_recent, normalize_datetime_string
from core.scoring import load_topics, score_item_breakdown


SOCIAL_PATH = Path("config/social_sources.yaml")
X_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"


def load_social_sources() -> Dict:
    if not SOCIAL_PATH.exists():
        return {
            "enabled": True,
            "max_results": 25,
            "language": "en",
            "include_reposts": False,
            "include_replies": False,
            "accounts": [],
        }

    with open(SOCIAL_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_social_sources(config: Dict) -> None:
    SOCIAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SOCIAL_PATH, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True, width=100)


def x_bearer_token() -> str:
    env = {key: value for key, value in os.environ.items()}
    env.update({key: value for key, value in dotenv_values(".env").items() if value is not None})
    return env.get("X_BEARER_TOKEN", "").strip()


def quote_term(term: str) -> str:
    term = term.strip().replace('"', "")
    if not term:
        return ""

    if " " in term:
        return f'"{term}"'

    return term


def watched_terms(topics_config: Dict) -> List[str]:
    terms = []

    for item in topics_config.get("focus_topics", []):
        topic = item.get("topic", "").strip()
        if topic:
            terms.append(topic)

    for key in ["companies_focus", "people_focus"]:
        for value in topics_config.get(key, []):
            value = str(value).strip()
            if value:
                terms.append(value)

    seen = set()
    deduped = []

    for term in terms:
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)

    return deduped


def watched_accounts(social_config: Dict) -> List[str]:
    accounts = []

    for account in social_config.get("accounts", []):
        handle = str(account.get("handle", "")).strip().lstrip("@")
        if handle:
            accounts.append(handle)

    return accounts


def build_x_query(topics_config: Dict, social_config: Dict, max_chars: int = 420) -> str:
    term_parts = [quote_term(term) for term in watched_terms(topics_config)]
    account_parts = [f"from:{handle}" for handle in watched_accounts(social_config)]
    candidates = [part for part in term_parts + account_parts if part]

    if not candidates:
        return ""

    selected = []
    for candidate in candidates:
        trial = " OR ".join(selected + [candidate])
        wrapped = f"({trial})"
        if len(wrapped) > max_chars:
            break
        selected.append(candidate)

    query = f"({' OR '.join(selected)})"

    language = str(social_config.get("language", "en")).strip()
    if language:
        query += f" lang:{language}"

    if not social_config.get("include_reposts", False):
        query += " -is:retweet"

    if not social_config.get("include_replies", False):
        query += " -is:reply"

    return query


def user_lookup(response_json: Dict) -> Dict:
    users = response_json.get("includes", {}).get("users", [])
    return {user["id"]: user for user in users if user.get("id")}


def tweet_url(tweet: Dict, user: Dict) -> str:
    username = user.get("username") or "i"
    return f"https://x.com/{username}/status/{tweet['id']}"


def engagement_score(tweet: Dict) -> float:
    metrics = tweet.get("public_metrics") or {}
    total = (
        int(metrics.get("like_count") or 0)
        + int(metrics.get("retweet_count") or 0) * 3
        + int(metrics.get("reply_count") or 0) * 2
        + int(metrics.get("quote_count") or 0) * 3
    )

    if total >= 5000:
        return 100
    if total >= 1000:
        return 80
    if total >= 250:
        return 60
    if total >= 50:
        return 40
    if total > 0:
        return 20
    return 0


def collect_social(recency_days: int = DEFAULT_RECENCY_DAYS) -> List[Dict]:
    social_config = load_social_sources()
    if not social_config.get("enabled", True):
        print("[Social] Disabled in config/social_sources.yaml.")
        return []

    token = x_bearer_token()
    if not token:
        print("[Social] X_BEARER_TOKEN is not set; skipping X recent search.")
        return []

    topics_config = load_topics()
    query = build_x_query(topics_config, social_config)
    if not query:
        print("[Social] No topics, companies, people, or accounts configured for X search.")
        return []

    max_results = max(10, min(int(social_config.get("max_results") or 25), 100))
    print(f"[Social] X recent search: {query}")

    response = requests.get(
        X_SEARCH_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "query": query,
            "max_results": max_results,
            "tweet.fields": "created_at,author_id,public_metrics,lang,referenced_tweets",
            "expansions": "author_id",
            "user.fields": "username,name,verified,public_metrics",
        },
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    users = user_lookup(data)
    items = []

    for tweet in data.get("data", []):
        published_at = normalize_datetime_string(tweet.get("created_at"))
        if not is_recent(published_at, recency_days):
            continue

        user = users.get(tweet.get("author_id"), {})
        author = user.get("name") or user.get("username") or "X user"
        username = user.get("username") or ""
        text = tweet.get("text", "").strip()
        url = tweet_url(tweet, user)
        title_text = text.splitlines()[0][:90] if text else url
        title = f"{author}: {title_text}"
        item_freshness_score = freshness_score(published_at, recency_days)
        item_momentum_score = engagement_score(tweet)

        score_breakdown = score_item_breakdown(
            title,
            text,
            category="people_public_signals",
            source_type="x_api",
            freshness_score=item_freshness_score,
            momentum_score=item_momentum_score,
        )

        if user.get("verified"):
            score_breakdown["source_quality_score"] = min(
                100,
                score_breakdown["source_quality_score"] + 8,
            )
            score_breakdown["final_score"] = min(
                95,
                score_breakdown["final_score"] + 4,
            )

        items.append(
            {
                "source_type": "x_api",
                "source_name": "X / Twitter",
                "category": "people_public_signals",
                "title": title,
                "url": url,
                "author": f"@{username}" if username else author,
                "published_at": published_at or datetime.now(timezone.utc).isoformat(),
                "raw_text": text,
                "score": score_breakdown["final_score"],
                **score_breakdown,
            }
        )

    return items
