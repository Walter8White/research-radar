import yaml
from pathlib import Path
from typing import Dict, List


TOPICS_PATH = Path("config/topics.yaml")


def load_topics() -> Dict:
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def keyword_hits(content: str, keywords: List[str]) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in content)


def clamp_score(score: float) -> float:
    return max(0, min(score, 100))


def load_focus_topics(config: Dict) -> List[Dict]:
    focus_topics = config.get("focus_topics")

    if focus_topics:
        return focus_topics

    return [
        {
            "topic": topic,
            "priority": "high",
        }
        for topic in config.get("priority_topics", [])
    ]


def focus_priority_boost(priority: str) -> int:
    if priority == "critical":
        return 18
    if priority == "high":
        return 12
    if priority == "medium":
        return 7
    if priority == "low":
        return 4

    return 8


def score_item_breakdown(
    title: str,
    text: str = "",
    category: str = "",
    source_type: str = "",
    freshness_score: float = 0,
    momentum_score: float = 0,
) -> Dict[str, float]:
    config = load_topics()
    content = f"{title} {text}".lower()

    relevance_score = 0
    technical_depth_score = 0
    strategic_importance_score = 0
    market_impact_score = 0
    geopolitical_impact_score = 0
    source_quality_score = 45
    noise_penalty = 0

    domains = config.get("domains", {})
    focus_topics = load_focus_topics(config)
    negative_topics = config.get("negative_topics", [])

    for domain_name, domain in domains.items():
        keywords = domain.get("keywords", [])
        hits = keyword_hits(content, keywords)

        if hits == 0:
            continue

        priority = domain.get("priority", "medium")

        if priority == "high":
            relevance_score += hits * 8
        elif priority == "medium":
            relevance_score += hits * 5
        else:
            relevance_score += hits * 3

        if category == domain_name:
            relevance_score += 10

    for item in focus_topics:
        topic = item.get("topic", "").strip()
        if topic and topic.lower() in content:
            relevance_score += focus_priority_boost(item.get("priority", "high"))

    for topic in negative_topics:
        if topic.lower() in content:
            noise_penalty += 25

    strategic_keywords = [
        "acquisition",
        "acquired",
        "merger",
        "funding",
        "valuation",
        "partnership",
        "export controls",
        "regulation",
        "national security",
        "sanctions",
        "sovereign",
        "infrastructure",
        "data center",
        "gpu",
        "chips",
        "semiconductor",
        "defense",
        "military",
    ]

    market_keywords = [
        "funding",
        "series a",
        "series b",
        "valuation",
        "revenue",
        "ipo",
        "customer",
        "enterprise",
        "commercial",
        "pricing",
    ]

    geopolitical_keywords = [
        "export controls",
        "sanctions",
        "regulation",
        "national security",
        "defense",
        "military",
        "china",
        "eu",
        "sovereign",
        "policy",
    ]

    technical_keywords = [
        "paper",
        "code",
        "benchmark",
        "dataset",
        "github",
        "architecture",
        "training",
        "evaluation",
        "experiments",
        "open-source",
        "model",
        "simulation",
        "robot",
    ]

    for keyword in strategic_keywords:
        if keyword in content:
            strategic_importance_score += 8

    for keyword in technical_keywords:
        if keyword in content:
            technical_depth_score += 7

    for keyword in market_keywords:
        if keyword in content:
            market_impact_score += 8

    for keyword in geopolitical_keywords:
        if keyword in content:
            geopolitical_impact_score += 9

    # Penalize shallow/vendor/customer-story content unless it has strong strategic signals.
    shallow_terms = [
        "customer story",
        "boost productivity",
        "unlock growth",
        "personalised",
        "workforce",
        "marketing",
        "customer satisfaction",
        "case study",
    ]

    for term in shallow_terms:
        if term in content:
            noise_penalty += 12

    # Personal relevance boost for robotics / embodied AI / world models.
    personal_relevance_terms = [
        "robot learning",
        "embodied",
        "physical ai",
        "world model",
        "world models",
        "vla",
        "vision-language-action",
        "tactile",
        "manipulation",
        "sim2real",
        "soft robotics",
        "humanoid",
        "deformable",
    ]

    for term in personal_relevance_terms:
        if term in content:
            relevance_score += 6
            technical_depth_score += 5

    # Strong strategic boost, but only for truly structural tech power signals.
    structural_terms = [
        "export controls",
        "sanctions",
        "national security",
        "sovereign ai",
        "data center",
        "gpu cluster",
        "semiconductor",
        "tsmc",
        "asml",
        "nvidia",
        "hyperscaler",
        "acquisition",
        "merger",
    ]

    for term in structural_terms:
        if term in content:
            strategic_importance_score += 9

    personal_hits = sum(1 for term in personal_relevance_terms if term in content)
    structural_hits = sum(1 for term in structural_terms if term in content)

    strong_signal_count = personal_hits + structural_hits

    # Generic business / agent news should not dominate the whole report.
    generic_agent_terms = [
        "claude code",
        "coding assistant",
        "ai agent",
        "productivity",
        "workplace assistant",
        "customer interviews",
    ]

    generic_hits = sum(1 for term in generic_agent_terms if term in content)

    if generic_hits >= 2 and structural_hits == 0:
        noise_penalty += 12

    if source_type == "arxiv" or category == "research_papers":
        source_quality_score = 65
        technical_depth_score += 15
    elif source_type == "github" or category == "open_source_devtools":
        source_quality_score = 60
        technical_depth_score += 8
    elif category in ["infrastructure_compute", "geopolitics_regulation"]:
        source_quality_score = 58
    elif category == "business_startups_ma":
        source_quality_score = 52
    elif source_type == "social_manual" or category == "people_public_signals":
        source_quality_score = 58
        strategic_importance_score += 8

    if category == "research_papers":
        if personal_hits >= 3:
            relevance_score += 12
        elif personal_hits >= 1:
            relevance_score += 6
        else:
            noise_penalty += 8

    if category == "infrastructure_compute":
        if structural_hits >= 2:
            strategic_importance_score += 12
        elif structural_hits >= 1:
            strategic_importance_score += 6

    ceiling_breaker_terms = [
        "major model",
        "frontier model",
        "breakthrough",
        "state-of-the-art",
        "sota",
        "acquired",
        "acquisition",
        "billion",
        "$1b",
        "$1.0b",
        "$1.1b",
        "export controls",
        "nvidia",
        "tsmc",
        "asml",
        "open-source release",
        "humanoid",
        "robotics breakthrough",
    ]

    ceiling_breaker_score = 0
    for term in ceiling_breaker_terms:
        if term in content:
            ceiling_breaker_score += 8

    relevance_score = clamp_score(relevance_score)
    technical_depth_score = clamp_score(technical_depth_score)
    strategic_importance_score = clamp_score(strategic_importance_score + ceiling_breaker_score)
    market_impact_score = clamp_score(market_impact_score)
    geopolitical_impact_score = clamp_score(geopolitical_impact_score)
    source_quality_score = clamp_score(source_quality_score)
    freshness_score = clamp_score(freshness_score or 0)
    momentum_score = clamp_score(momentum_score or 0)
    noise_penalty = clamp_score(noise_penalty)

    final_score = (
        relevance_score * 0.28
        + freshness_score * 0.14
        + technical_depth_score * 0.14
        + strategic_importance_score * 0.18
        + market_impact_score * 0.07
        + geopolitical_impact_score * 0.07
        + source_quality_score * 0.07
        + momentum_score * 0.10
        - noise_penalty * 0.20
    )

    if ceiling_breaker_score >= 16:
        final_score += 10

    if category == "research_papers" and strategic_importance_score < 20 and personal_hits == 0:
        final_score = min(final_score, 72)

    if category == "open_source_devtools" and momentum_score < 25 and strategic_importance_score < 20:
        final_score = min(final_score, 78)

    return {
        "relevance_score": clamp_score(relevance_score),
        "freshness_score": clamp_score(freshness_score),
        "technical_depth_score": clamp_score(technical_depth_score),
        "strategic_importance_score": clamp_score(strategic_importance_score),
        "market_impact_score": clamp_score(market_impact_score),
        "geopolitical_impact_score": clamp_score(geopolitical_impact_score),
        "source_quality_score": clamp_score(source_quality_score),
        "momentum_score": clamp_score(momentum_score),
        "noise_penalty": clamp_score(noise_penalty),
        "final_score": max(0, min(final_score, 95)),
    }


def score_item(title: str, text: str = "", category: str = "") -> float:
    return score_item_breakdown(title, text, category=category)["final_score"]
