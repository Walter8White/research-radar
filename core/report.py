from datetime import date
from pathlib import Path
from typing import Dict
from collections import defaultdict

from core.database import get_top_items
from core.text_utils import truncate
from core.momentum import get_github_growth_metrics


REPORTS_DIR = Path("reports")


CATEGORY_TITLES = {
    "frontier_ai": "Frontier AI",
    "robotics_physical_ai": "Robotics & Physical AI",
    "infrastructure_compute": "Infrastructure & Chips",
    "business_startups_ma": "Startups, Funding & M&A",
    "geopolitics_regulation": "Geopolitics & Regulation",
    "open_source_devtools": "Open Source & Developer Ecosystem",
    "research_papers": "Research Papers",
    "general": "General Signals",
}


def momentum_label(score: float) -> str:
    if score >= 70:
        return "Surging"
    if score >= 40:
        return "Rising"
    if score >= 15:
        return "Moving"
    return "Flat / unknown"


def format_github_metrics(item: Dict) -> str:
    if item.get("source_type") != "github":
        return ""

    growth = get_github_growth_metrics(item["url"], item)

    return f"""
**GitHub metrics:**  
- Stars: {int(item.get("stars") or 0):,}
- Forks: {int(item.get("forks") or 0):,}
- Open issues: {int(item.get("open_issues") or 0):,}
- Watchers: {int(item.get("watchers") or 0):,}
- Stars growth 24h: +{growth["stars_growth_24h"]:,}
- Stars growth 7d: +{growth["stars_growth_7d"]:,}
- Forks growth 7d: +{growth["forks_growth_7d"]:,}
- Momentum: {growth["momentum_score"]:.1f}/100 — {momentum_label(growth["momentum_score"])}
"""


def format_item(item: Dict, index: int) -> str:
    raw_text = truncate(item.get("raw_text") or "", max_chars=900)
    score = item.get("score") or 0
    momentum = item.get("momentum_score") or 0

    if item.get("source_type") == "github":
        growth = get_github_growth_metrics(item["url"], item)
        momentum = growth["momentum_score"]

    if score >= 75:
        action = "Track closely"
    elif score >= 50:
        action = "Read / inspect"
    else:
        action = "Skim"

    github_metrics = format_github_metrics(item)

    return f"""### {index}. {item["title"]}

**Source:** {item["source_name"]}  
**Type:** {item["source_type"]}  
**Category:** {item.get("category") or "general"}  
**Score:** {score:.1f}/100  
**Momentum:** {momentum:.1f}/100 — {momentum_label(momentum)}  
**Author:** {item.get("author") or "Unknown"}  
**URL:** {item["url"]}
{github_metrics}
**Raw signal:**  
{raw_text}

**Recommended action:**  
{action}

---
"""


def generate_report(limit: int = 50) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    report_path = REPORTS_DIR / f"{today}.md"

    items = get_top_items(limit=limit)
    top_items = items[:7]

    grouped = defaultdict(list)
    for item in items:
        grouped[item.get("category") or "general"].append(item)

    content = f"""# Daily Tech Intelligence Brief — {today}

## Executive Summary

"""

    if not top_items:
        content += "No items found today.\n\n"
    else:
        for i, item in enumerate(top_items, start=1):
            momentum = item.get("momentum_score") or 0
            content += (
                f"{i}. **{item['title']}** "
                f"— {item.get('category') or 'general'} "
                f"— score {item['score']:.1f}/100 "
                f"— momentum {momentum:.1f}/100\n"
            )

    content += """

---

## Strategic Read

For now, this is a non-LLM report. Read the top signals through these questions:

- Does this affect who controls the AI stack?
- Does this change the robotics / embodied AI landscape?
- Does this indicate consolidation, regulation, or geopolitical tension?
- Does this affect compute access, chips, cloud, or infrastructure?
- Is this a weak signal worth tracking?

---

"""

    preferred_order = [
        "frontier_ai",
        "robotics_physical_ai",
        "infrastructure_compute",
        "business_startups_ma",
        "geopolitics_regulation",
        "open_source_devtools",
        "research_papers",
        "general",
    ]

    for category in preferred_order:
        category_items = grouped.get(category, [])

        if not category_items:
            continue

        title = CATEGORY_TITLES.get(category, category)
        content += f"\n## {title}\n\n"

        for i, item in enumerate(category_items[:8], start=1):
            content += format_item(item, i)

    report_path.write_text(content, encoding="utf-8")
    return report_path
