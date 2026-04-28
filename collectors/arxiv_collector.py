from typing import List, Dict
import time
import arxiv

from core.scoring import score_item


ARXIV_QUERIES = [
    "robot learning",
    "embodied artificial intelligence",
    "world models robotics",
    "tactile sensing robotics",
    "soft robotics",
    "deformable object manipulation",
    "vision language action robotics",
    "robot foundation models",
    "sim2real robotics",
    "autonomous agents artificial intelligence",
]


def collect_arxiv(max_results_per_query: int = 3) -> List[Dict]:
    client = arxiv.Client(
        page_size=10,
        delay_seconds=4.0,
        num_retries=3,
    )

    items = []

    for query in ARXIV_QUERIES:
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

                item = {
                    "source_type": "arxiv",
                    "source_name": "arXiv",
                    "category": "research_papers",
                    "title": title,
                    "url": url,
                    "author": ", ".join(author.name for author in result.authors[:3]),
                    "published_at": result.published.isoformat(),
                    "raw_text": summary,
                    "score": score_item(title, summary, category="research_papers"),
                }

                items.append(item)

            time.sleep(4)

        except Exception as e:
            print(f"[arXiv] Error for query '{query}': {e}")
            time.sleep(8)

    return items
