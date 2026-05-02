from typing import List, Dict
import time
import arxiv

from core.scoring import load_topics, score_item_breakdown
from core.freshness import (
    DEFAULT_RECENCY_DAYS,
    freshness_score,
    is_recent,
    normalize_datetime_string,
)


EXCLUDED_ARXIV_TERMS = {
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
    "semiconductors",
    "arxiv",
    "paper",
    "preprint",
    "benchmark",
    "dataset",
    "method",
    "experiments",
    "state of the art",
    "sota",
}


def is_good_arxiv_query(query: str) -> bool:
    q = query.lower().strip()

    if len(q) < 4:
        return False

    if q in EXCLUDED_ARXIV_TERMS:
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
    ]

    if any(fragment in q for fragment in bad_fragments):
        return False

    return True


def build_arxiv_queries(max_queries: int = 12) -> List[str]:
    config = load_topics()

    queries = []

    focus_topics = config.get("focus_topics") or [
        {"topic": topic}
        for topic in config.get("priority_topics", [])
    ]

    # Highest priority: explicit focus topics from the UI.
    for focus_topic in focus_topics:
        topic = focus_topic.get("topic", "")
        if is_good_arxiv_query(topic):
            queries.append(topic)

    # Deduplicate while preserving order.
    seen = set()
    clean_queries = []

    for query in queries:
        q = query.strip()
        key = q.lower()

        if key in seen:
            continue

        seen.add(key)
        clean_queries.append(q)

        if len(clean_queries) >= max_queries:
            break

    return clean_queries


def collect_arxiv(
    max_results_per_query: int = 3,
    recency_days: int = DEFAULT_RECENCY_DAYS,
) -> List[Dict]:
    queries = build_arxiv_queries(max_queries=12)

    if not queries:
        print("[arXiv] No valid arXiv queries found in topics config.")
        return []

    client = arxiv.Client(
        page_size=10,
        delay_seconds=4.0,
        num_retries=3,
    )

    items = []

    for query in queries:
        print(f"[arXiv] Searching: {query}")

        search = arxiv.Search(
            query=f'all:"{query}"',
            max_results=max_results_per_query,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        try:
            for result in client.results(search):
                title = result.title.strip()
                summary = result.summary.strip()
                url = result.entry_id
                published_at = normalize_datetime_string(result.published)

                if not is_recent(published_at, recency_days):
                    continue

                item_freshness_score = freshness_score(published_at, recency_days)
                score_breakdown = score_item_breakdown(
                    title,
                    summary,
                    category="research_papers",
                    source_type="arxiv",
                    freshness_score=item_freshness_score,
                )

                item = {
                    "source_type": "arxiv",
                    "source_name": "arXiv",
                    "category": "research_papers",
                    "title": title,
                    "url": url,
                    "author": ", ".join(author.name for author in result.authors[:3]),
                    "published_at": published_at,
                    "raw_text": summary,
                    "score": score_breakdown["final_score"],
                    **score_breakdown,
                }

                items.append(item)

            time.sleep(4)

        except Exception as e:
            print(f"[arXiv] Error for query '{query}': {e}")
            time.sleep(8)

    return items
