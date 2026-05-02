import os
import re
from datetime import date
from pathlib import Path
from typing import Dict
from collections import defaultdict

from core.database import get_top_items
from core.text_utils import truncate
from core.momentum import get_github_growth_metrics
from core.llm_summary import generate_strategic_read
from core.llm.providers import normalize_provider
from core.freshness import DEFAULT_RECENCY_DAYS, format_date_with_age
from core.report_length import DEFAULT_REPORT_LENGTH, report_length_profile


REPORTS_DIR = Path("reports")


CATEGORY_TITLES = {
    "frontier_ai": "🧠 Frontier AI",
    "robotics_physical_ai": "🤖 Robotics & Physical AI",
    "infrastructure_compute": "⚙️ Infrastructure & Chips",
    "business_startups_ma": "💼 Startups, Funding & M&A",
    "geopolitics_regulation": "🌍 Geopolitics & Regulation",
    "people_public_signals": "🗣️ People & Public Signals",
    "open_source_devtools": "🛠️ Open Source & Developer Ecosystem",
    "research_papers": "📄 Research Papers",
    "general": "📌 General Signals",
}

TOP_BRIEF_LIMITS = {
    "research_papers": 2,
    "github": 2,
    "business_startups_ma": 2,
    "infrastructure_or_geopolitics": 2,
}


def momentum_label(score: float) -> str:
    if score is None:
        return "Not available yet"
    if score >= 75:
        return "Very high"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    if score > 0:
        return "Low"
    return "None"


def format_growth(value: int, has_baseline: bool) -> str:
    if not has_baseline:
        return ""

    return f"+{value:,}"


def github_growth_metrics(item: Dict) -> Dict:
    if item.get("github_growth_source") == "github_stargazers":
        return {
            "has_24h_baseline": True,
            "has_7d_baseline": True,
            "stars_growth_24h": int(item.get("stars_growth_24h") or 0),
            "stars_growth_7d": int(item.get("stars_growth_7d") or 0),
            "forks_growth_7d": int(item.get("forks_growth_7d") or 0),
        }

    return get_github_growth_metrics(item["url"], item)


def format_github_metrics(item: Dict) -> str:
    if item.get("source_type") != "github":
        return ""

    growth = github_growth_metrics(item)
    growth_lines = []

    stars_growth_24h = format_growth(growth["stars_growth_24h"], growth["has_24h_baseline"])
    stars_growth_7d = format_growth(growth["stars_growth_7d"], growth["has_7d_baseline"])
    forks_growth_7d = format_growth(
        growth["forks_growth_7d"],
        item.get("github_growth_source") != "github_stargazers" and growth["has_7d_baseline"],
    )

    if stars_growth_24h:
        growth_lines.append(f"Stars growth 24h: {stars_growth_24h}<br>")
    if stars_growth_7d:
        growth_lines.append(f"Stars growth 7d: {stars_growth_7d}<br>")
    if forks_growth_7d:
        growth_lines.append(f"Forks growth 7d: {forks_growth_7d}<br>")

    if not growth_lines:
        growth_lines.append("Growth: not available yet<br>")

    return f"""<div style="float:right; min-width:220px; margin:0 0 12px 24px; padding:10px 12px; border-left:3px solid #d0d7de; background:#f6f8fa;">
<strong>GitHub metrics</strong><br>
Stars: {int(item.get("stars") or 0):,}<br>
Forks: {int(item.get("forks") or 0):,}<br>
Open issues: {int(item.get("open_issues") or 0):,}<br>
Watchers: {int(item.get("watchers") or 0):,}<br>
{"".join(growth_lines)}
</div>
"""


def item_momentum_label(item: Dict) -> str:
    momentum = item.get("momentum_score")

    if item.get("source_type") == "github":
        if item.get("github_growth_source") == "github_stargazers":
            return momentum_label(momentum)

        growth = github_growth_metrics(item)
        if not growth["has_24h_baseline"] and not growth["has_7d_baseline"]:
            return "Not available yet"
        momentum = growth["momentum_score"]

    if momentum is None:
        return "Not tracked"

    if item.get("source_type") != "github" and momentum == 0:
        return "Not tracked"

    return momentum_label(momentum)


def display_relevance_score(item: Dict) -> float:
    return item.get("relevance_score") or item.get("score") or 0


def split_sentences(text: str) -> list:
    text = truncate(text, max_chars=3000)
    if not text:
        return []

    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
        if sentence.strip()
    ]


def concise_paper_summary(text: str, max_chars: int = 520) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return ""

    contribution_terms = [
        "we introduce",
        "we present",
        "we propose",
        "we develop",
        "we evaluate",
        "we show",
        "we find",
        "we demonstrate",
        "this work",
        "this paper",
    ]
    supporting_terms = [
        "benchmark",
        "dataset",
        "framework",
        "method",
        "results",
        "experiments",
    ]

    selected = []
    context_prefixes = ("yet,", "however,", "by contrast,", "existing ")

    for sentence in sentences:
        lower = sentence.lower()
        if any(term in lower for term in contribution_terms):
            selected.append(sentence)
        if len(selected) >= 2:
            break

    if len(selected) < 2:
        for sentence in sentences:
            if sentence in selected:
                continue
            lower = sentence.lower()
            if lower.startswith(context_prefixes):
                continue
            if any(term in lower for term in supporting_terms):
                selected.append(sentence)
            if len(selected) >= 2:
                break

    if not selected:
        selected = sentences[:2]

    summary = " ".join(selected)
    summary = re.sub(r"^(In this paper,\s*)", "", summary, flags=re.IGNORECASE)
    return truncate(summary, max_chars=max_chars)


def concise_general_summary(text: str, max_chars: int = 420) -> str:
    sentences = split_sentences(text)
    if not sentences:
        return truncate(text, max_chars=max_chars)

    selected = []

    for sentence in sentences:
        clean = re.sub(
            r"\s*(Stars|Forks|Open issues|Watchers|Language):\s*[^.]+",
            "",
            sentence,
            flags=re.IGNORECASE,
        ).strip()

        if not clean:
            continue

        selected.append(clean)

        if len(" ".join(selected)) >= max_chars * 0.65 or len(selected) >= 2:
            break

    return truncate(" ".join(selected), max_chars=max_chars)


def item_signal_text(item: Dict, raw_chars: int) -> tuple[str, str]:
    raw_text = item.get("raw_text") or ""
    if not raw_text or not raw_chars:
        return "", ""

    if item.get("source_type") == "arxiv" or item.get("category") == "research_papers":
        return "Source digest", concise_paper_summary(raw_text, max_chars=min(raw_chars, 520))

    return "Source digest", concise_general_summary(raw_text, max_chars=min(raw_chars, 420))


def is_ceiling_breaker(item: Dict) -> bool:
    return (
        (item.get("score") or 0) >= 88
        or (item.get("strategic_importance_score") or 0) >= 70
        or (item.get("market_impact_score") or 0) >= 70
        or (item.get("geopolitical_impact_score") or 0) >= 70
        or (item.get("momentum_score") or 0) >= 75
    )


def diversity_keys(item: Dict) -> list:
    keys = []
    category = item.get("category") or "general"

    if category == "research_papers":
        keys.append("research_papers")
    if item.get("source_type") == "github":
        keys.append("github")
    if category == "business_startups_ma":
        keys.append("business_startups_ma")
    if category in ["infrastructure_compute", "geopolitics_regulation"]:
        keys.append("infrastructure_or_geopolitics")

    return keys


def select_top_items(items: list, limit: int = 5) -> list:
    selected = []
    counts = {key: 0 for key in TOP_BRIEF_LIMITS}

    for item in items:
        keys = diversity_keys(item)
        over_limit = any(counts[key] >= TOP_BRIEF_LIMITS[key] for key in keys)
        override_available = all(counts[key] < TOP_BRIEF_LIMITS[key] + 1 for key in keys)

        if over_limit and (not is_ceiling_breaker(item) or not override_available):
            continue

        selected.append(item)
        for key in keys:
            counts[key] += 1

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        selected_urls = {item["url"] for item in selected}
        for item in items:
            if item["url"] in selected_urls:
                continue
            selected.append(item)
            if len(selected) >= limit:
                break

    return selected


def format_item(item: Dict, index: int, raw_chars: int = 900) -> str:
    signal_label, signal_text = item_signal_text(item, raw_chars)
    relevance = display_relevance_score(item)

    if item.get("score", 0) >= 75:
        action = "Track closely"
    elif item.get("score", 0) >= 50:
        action = "Read / inspect"
    else:
        action = "Skim"

    github_metrics = format_github_metrics(item)

    raw_signal = f"""**{signal_label}:**  
{signal_text}

""" if signal_text else ""

    return f"""### {index}. {item["title"]}

**Source:** {item["source_name"]}  
**Type:** {item["source_type"]}  
**Category:** {item.get("category") or "general"}  
**Relevance:** {relevance:.1f}/100  
**Momentum:** {item_momentum_label(item)}  
**Published:** {format_date_with_age(item.get("published_at"))}  
**Author:** {item.get("author") or "Unknown"}  
**URL:** {item["url"]}
{github_metrics}
{raw_signal}
**Recommended action:**  
{action}

<div style="clear:both;"></div>

---
"""


def generate_report(
    limit: int = 50,
    recency_days: int = DEFAULT_RECENCY_DAYS,
    report_length: str = DEFAULT_REPORT_LENGTH,
    output_dir: str | Path = REPORTS_DIR,
) -> Path:
    reports_dir = Path(output_dir).expanduser()
    reports_dir.mkdir(parents=True, exist_ok=True)
    profile = report_length_profile(report_length)

    today = date.today().isoformat()
    report_path = reports_dir / f"{today}.md"
    llm_provider = normalize_provider(os.getenv("LLM_PROVIDER", "OpenAI"))

    items = get_top_items(limit=limit, recency_days=recency_days)
    top_items = select_top_items(items, limit=profile["top_items"])

    grouped = defaultdict(list)
    for item in items:
        grouped[item.get("category") or "general"].append(item)

    if report_length == "Ultra Short":
        strategic_read = generate_strategic_read(
            top_items + items[7 : 7 + profile["llm_items"]],
            report_length=report_length,
        )
        content = f"""# 📡 Daily Tech Intelligence Brief — {today}

Freshness window: last {recency_days} day(s)
Report length: {report_length}
LLM mode: {llm_provider}

{strategic_read}
"""
        report_path.write_text(content, encoding="utf-8")
        return report_path

    content = f"""# 📡 Daily Tech Intelligence Brief — {today}

Freshness window: last {recency_days} day(s)
Report length: {report_length}
LLM mode: {llm_provider}

## ☕ Executive Summary

"""

    if not top_items:
        content += "No items found today.\n\n"
    else:
        for i, item in enumerate(top_items, start=1):
            content += (
                f"{i}. **{item['title']}** "
                f"— {item.get('category') or 'general'} "
                f"— relevance {display_relevance_score(item):.1f}/100 "
                f"— published {format_date_with_age(item.get('published_at'))} "
                f"— momentum {item_momentum_label(item)}\n"
            )

    strategic_read = generate_strategic_read(
        top_items + items[7 : 7 + profile["llm_items"]],
        report_length=report_length,
    )

    content += f"""

---

{strategic_read}

---

"""

    if profile["category_items"] == 0:
        report_path.write_text(content, encoding="utf-8")
        return report_path

    preferred_order = [
        "frontier_ai",
        "robotics_physical_ai",
        "infrastructure_compute",
        "business_startups_ma",
        "geopolitics_regulation",
        "people_public_signals",
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

        for i, item in enumerate(category_items[: profile["category_items"]], start=1):
            content += format_item(item, i, raw_chars=profile["raw_chars"])

    report_path.write_text(content, encoding="utf-8")
    return report_path
