import yaml
from pathlib import Path
from typing import Dict, List


TOPICS_PATH = Path("config/topics.yaml")


def load_topics() -> Dict:
    with open(TOPICS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def keyword_hits(content: str, keywords: List[str]) -> int:
    return sum(1 for keyword in keywords if keyword.lower() in content)


def score_item(title: str, text: str = "", category: str = "") -> float:
    config = load_topics()
    content = f"{title} {text}".lower()

    score = 0

    domains = config.get("domains", {})
    priority_topics = config.get("priority_topics", [])
    negative_topics = config.get("negative_topics", [])

    for domain_name, domain in domains.items():
        keywords = domain.get("keywords", [])
        hits = keyword_hits(content, keywords)

        if hits == 0:
            continue

        priority = domain.get("priority", "medium")

        if priority == "high":
            score += hits * 8
        elif priority == "medium":
            score += hits * 5
        else:
            score += hits * 3

        if category == domain_name:
            score += 8

    for topic in priority_topics:
        if topic.lower() in content:
            score += 10

    for topic in negative_topics:
        if topic.lower() in content:
            score -= 25

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
            score += 6

    for keyword in technical_keywords:
        if keyword in content:
            score += 4

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
            score -= 12

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
            score += 8

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
            score += 7

    # Avoid saturation: scores above 90 should be rare.
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

    if category == "business_startups_ma" and generic_hits >= 2 and structural_hits == 0:
        score = min(score, 82)

    if category == "research_papers":
        if personal_hits >= 3:
            score = min(score, 93)
        elif personal_hits >= 1:
            score = min(score, 86)
        else:
            score = min(score, 74)

    if category == "infrastructure_compute":
        if structural_hits >= 2:
            score = min(score, 90)
        elif structural_hits >= 1:
            score = min(score, 82)
        else:
            score = min(score, 65)

    if category == "open_source_devtools":
        score = min(score, 78)

    # Only multi-signal items can exceed 90.
    if score > 90 and strong_signal_count < 3:
        score = 88

    return max(0, min(score, 95))
