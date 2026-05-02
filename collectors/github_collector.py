from typing import List, Dict
from datetime import timedelta
import os
from urllib.parse import parse_qs, urlparse
import requests
from dotenv import load_dotenv

from core.scoring import load_topics, score_item_breakdown
from core.database import insert_metric
from core.momentum import calculate_github_momentum_score, get_github_growth_metrics
from core.freshness import (
    DEFAULT_RECENCY_DAYS,
    freshness_score,
    is_recent,
    normalize_datetime,
    normalize_datetime_string,
    utc_now,
)


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"

MIN_STARS = 25
MAX_STARGAZER_GROWTH_LOOKUPS = 12
MAX_STARGAZER_PAGES = 3

load_dotenv()

EXCLUDED_GITHUB_TERMS = {
    "nvidia",
    "tsmc",
    "asml",
    "acquisition",
    "funding",
    "series a",
    "series b",
    "valuation",
    "export controls",
    "ai regulation",
    "us china tech war",
    "sovereign ai",
    "arxiv",
    "paper",
    "preprint",
    "benchmark",
    "dataset",
    "method",
    "experiments",
    "state of the art",
    "sota",
    "semiconductors",
}


def is_good_github_query(query: str) -> bool:
    q = query.lower().strip()

    if len(q) < 4:
        return False

    if q in EXCLUDED_GITHUB_TERMS:
        return False

    bad_fragments = [
        "funding",
        "acquisition",
        "valuation",
        "startup",
        "merger",
        "revenue",
        "sanctions",
        "export controls",
        "regulation",
        "national security",
    ]

    if any(fragment in q for fragment in bad_fragments):
        return False

    return True


def build_github_queries(max_queries: int = 12) -> List[str]:
    config = load_topics()
    queries = []

    focus_topics = config.get("focus_topics") or [
        {"topic": topic}
        for topic in config.get("priority_topics", [])
    ]

    for focus_topic in focus_topics:
        topic = focus_topic.get("topic", "")
        if is_good_github_query(topic):
            queries.append(topic)

    # Add GitHub-specific expansions for better results.
    expanded = []

    for query in queries:
        expanded.append(query)

        q = query.lower()

        if "agent" in q:
            expanded.append(f"{query} framework")

        if "robot" in q or "embodied" in q:
            expanded.append(f"{query} simulation")

        if "open source" in q or "open-source" in q:
            expanded.append(f"{query} inference")

    seen = set()
    clean_queries = []

    for query in expanded:
        q = query.strip()
        key = q.lower()

        if key in seen:
            continue

        seen.add(key)
        clean_queries.append(q)

        if len(clean_queries) >= max_queries:
            break

    return clean_queries


def github_headers(accept: str = "application/vnd.github+json") -> Dict[str, str]:
    headers = {
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    return headers


def get_last_page(response: requests.Response) -> int:
    last_url = response.links.get("last", {}).get("url")
    if not last_url:
        return 1

    query = parse_qs(urlparse(last_url).query)
    try:
        return int(query.get("page", ["1"])[0])
    except (TypeError, ValueError):
        return 1


def count_recent_starred_at(stargazers: List[Dict]) -> Dict[str, int]:
    now = utc_now()
    since_24h = now - timedelta(days=1)
    since_7d = now - timedelta(days=7)

    stars_growth_24h = 0
    stars_growth_7d = 0

    for stargazer in stargazers:
        starred_datetime = normalize_datetime(stargazer.get("starred_at"))
        if not starred_datetime:
            continue

        if starred_datetime >= since_7d:
            stars_growth_7d += 1
            if starred_datetime >= since_24h:
                stars_growth_24h += 1

    return {
        "stars_growth_24h": stars_growth_24h,
        "stars_growth_7d": stars_growth_7d,
    }


def fetch_recent_star_growth(full_name: str) -> Dict:
    url = f"https://api.github.com/repos/{full_name}/stargazers"
    params = {"per_page": 100, "page": 1}
    headers = github_headers(accept="application/vnd.github.star+json")

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
    except requests.RequestException:
        return {"available": False}

    if response.status_code != 200:
        return {"available": False}

    last_page = get_last_page(response)
    page_numbers = range(last_page, max(0, last_page - MAX_STARGAZER_PAGES), -1)
    stargazers = []

    for page in page_numbers:
        page_params = {"per_page": 100, "page": page}
        try:
            page_response = requests.get(url, params=page_params, headers=headers, timeout=15)
        except requests.RequestException:
            continue

        if page_response.status_code != 200:
            continue

        stargazers.extend(page_response.json())

    growth = count_recent_starred_at(stargazers)
    growth["available"] = True
    return growth


def collect_github(
    max_results_per_topic: int = 6,
    recency_days: int = DEFAULT_RECENCY_DAYS,
) -> List[Dict]:
    queries = build_github_queries(max_queries=12)

    if not queries:
        print("[GitHub] No valid GitHub queries found in topics config.")
        return []

    items = []
    seen_urls = set()
    stargazer_growth_lookups = 0

    for topic in queries:
        print(f"[GitHub] Searching: {topic}")
        since = (utc_now() - timedelta(days=recency_days)).date().isoformat()

        params = {
            "q": f"{topic} in:name,description,readme stars:>{MIN_STARS} updated:>={since}",
            "sort": "updated",
            "order": "desc",
            "per_page": max_results_per_topic,
        }

        try:
            response = requests.get(
                GITHUB_SEARCH_URL,
                params=params,
                headers=github_headers(),
                timeout=20,
            )

            if response.status_code != 200:
                print(f"[GitHub] Error for topic '{topic}': {response.status_code}")
                continue

            data = response.json()

            for repo in data.get("items", []):
                title = repo.get("full_name", "")
                description = repo.get("description") or ""
                url = repo.get("html_url", "")

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                stars = int(repo.get("stargazers_count") or 0)
                forks = int(repo.get("forks_count") or 0)
                open_issues = int(repo.get("open_issues_count") or 0)
                watchers = int(repo.get("watchers_count") or 0)
                language = repo.get("language") or "Unknown"

                if stars < MIN_STARS:
                    continue

                if not description:
                    continue

                published_at = normalize_datetime_string(repo.get("updated_at") or repo.get("created_at"))

                if not is_recent(published_at, recency_days):
                    continue

                bad_terms = [
                    "leetcode",
                    "interview",
                    "portfolio",
                    "personal website",
                    "tutorial only",
                    "awesome list",
                    "awesome-",
                    "jobs",
                    "job",
                    "new-grad",
                ]

                blob = f"{title} {description}".lower()

                if any(term in blob for term in bad_terms):
                    continue

                text = (
                    f"{description}\n"
                    f"Stars: {stars}\n"
                    f"Forks: {forks}\n"
                    f"Open issues: {open_issues}\n"
                    f"Watchers: {watchers}\n"
                    f"Language: {language}"
                )

                star_bonus = min(stars / 250, 15)

                current_metrics = {
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "watchers": watchers,
                }

                growth = get_github_growth_metrics(url, current_metrics)
                growth_source = "local_snapshots"

                if stargazer_growth_lookups < MAX_STARGAZER_GROWTH_LOOKUPS:
                    absolute_growth = fetch_recent_star_growth(title)
                    stargazer_growth_lookups += 1

                    if absolute_growth.get("available"):
                        growth["stars_growth_24h"] = absolute_growth["stars_growth_24h"]
                        growth["stars_growth_7d"] = absolute_growth["stars_growth_7d"]
                        growth["has_24h_baseline"] = True
                        growth["has_7d_baseline"] = True
                        growth["momentum_score"] = calculate_github_momentum_score(
                            stars_growth_24h=growth["stars_growth_24h"],
                            stars_growth_7d=growth["stars_growth_7d"],
                            forks_growth_7d=growth["forks_growth_7d"],
                            issue_activity_7d=growth["issue_activity_7d"],
                        )
                        growth_source = "github_stargazers"

                momentum_score = growth["momentum_score"]

                item_freshness_score = freshness_score(published_at, recency_days)
                score_breakdown = score_item_breakdown(
                    title,
                    text,
                    category="open_source_devtools",
                    source_type="github",
                    freshness_score=item_freshness_score,
                    momentum_score=momentum_score,
                )
                final_score = min(score_breakdown["final_score"] + star_bonus, 95)

                item = {
                    "source_type": "github",
                    "source_name": "GitHub",
                    "category": "open_source_devtools",
                    "title": title,
                    "url": url,
                    "author": repo.get("owner", {}).get("login"),
                    "published_at": published_at,
                    "raw_text": text,
                    "score": final_score,
                    **score_breakdown,
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "watchers": watchers,
                    "stars_growth_24h": growth["stars_growth_24h"],
                    "stars_growth_7d": growth["stars_growth_7d"],
                    "forks_growth_7d": growth["forks_growth_7d"],
                    "issue_activity_7d": growth["issue_activity_7d"],
                    "github_growth_source": growth_source,
                }

                items.append(item)

                insert_metric(
                    item_url=url,
                    stars=stars,
                    forks=forks,
                    open_issues=open_issues,
                    watchers=watchers,
                )

        except Exception as e:
            print(f"[GitHub] Error for topic '{topic}': {e}")

    return items
