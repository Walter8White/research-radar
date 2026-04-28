from typing import List, Dict
import requests

from core.scoring import score_item
from core.database import insert_metric
from core.momentum import get_github_growth_metrics


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


GITHUB_TOPICS = [
    "agentic AI framework",
    "AI agents framework",
    "robot learning",
    "embodied AI robotics",
    "world models robotics",
    "LLM agent framework",
    "open source AI inference",
    "robotics simulation",
    "vision language action",
]


MIN_STARS = 25


def collect_github(max_results_per_topic: int = 6) -> List[Dict]:
    items = []
    seen_urls = set()

    for topic in GITHUB_TOPICS:
        params = {
            "q": f"{topic} in:name,description,readme stars:>25",
            "sort": "updated",
            "order": "desc",
            "per_page": max_results_per_topic,
        }

        try:
            response = requests.get(GITHUB_SEARCH_URL, params=params, timeout=20)

            if response.status_code != 200:
                print(f"[GitHub] Error for topic '{topic}': {response.status_code}")
                continue

            data = response.json()

            for repo in data.get("items", []):
                title = repo.get("full_name", "")
                description = repo.get("description") or ""
                url = repo.get("html_url", "")

                if url in seen_urls:
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

                bad_terms = [
                    "leetcode",
                    "interview",
                    "portfolio",
                    "personal website",
                    "tutorial only",
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

                base_score = score_item(title, text, category="open_source_devtools")
                star_bonus = min(stars / 250, 15)

                current_metrics = {
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "watchers": watchers,
                }

                growth = get_github_growth_metrics(url, current_metrics)
                momentum_score = growth["momentum_score"]

                # Momentum affects final score, but cannot dominate it.
                momentum_bonus = min(momentum_score * 0.20, 12)

                item = {
                    "source_type": "github",
                    "source_name": "GitHub",
                    "category": "open_source_devtools",
                    "title": title,
                    "url": url,
                    "author": repo.get("owner", {}).get("login"),
                    "published_at": repo.get("updated_at"),
                    "raw_text": text,
                    "score": max(0, min(base_score + star_bonus + momentum_bonus, 95)),
                    "momentum_score": momentum_score,
                    "stars": stars,
                    "forks": forks,
                    "open_issues": open_issues,
                    "watchers": watchers,
                    "stars_growth_24h": growth["stars_growth_24h"],
                    "stars_growth_7d": growth["stars_growth_7d"],
                    "forks_growth_7d": growth["forks_growth_7d"],
                    "issue_activity_7d": growth["issue_activity_7d"],
                }

                items.append(item)

                # Store today's metrics snapshot.
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
