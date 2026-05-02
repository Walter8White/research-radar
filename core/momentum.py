import math
from typing import Dict

from core.database import get_latest_metric_before


def calculate_growth(current: int, previous: int) -> int:
    return max(0, (current or 0) - (previous or 0))


def calculate_github_momentum_score(
    stars_growth_24h: int = 0,
    stars_growth_7d: int = 0,
    forks_growth_7d: int = 0,
    issue_activity_7d: int = 0,
) -> float:
    """
    Momentum is intentionally sublinear.
    A repo going viral should matter, but not hijack the whole ranking.
    """

    raw = (
        3.0 * stars_growth_24h
        + 1.2 * stars_growth_7d
        + 4.0 * forks_growth_7d
        + 0.5 * issue_activity_7d
    )

    if raw <= 0:
        return 0.0

    return min(100.0, 18.0 * math.log1p(raw))


def get_github_growth_metrics(item_url: str, current: Dict) -> Dict:
    current_stars = int(current.get("stars") or 0)
    current_forks = int(current.get("forks") or 0)
    current_issues = int(current.get("open_issues") or 0)

    metric_24h = get_latest_metric_before(item_url, hours_ago=24)
    metric_7d = get_latest_metric_before(item_url, hours_ago=24 * 7)

    stars_growth_24h = 0
    stars_growth_7d = 0
    forks_growth_7d = 0
    issue_activity_7d = 0

    if metric_24h:
        stars_growth_24h = calculate_growth(current_stars, int(metric_24h.get("stars") or 0))

    if metric_7d:
        stars_growth_7d = calculate_growth(current_stars, int(metric_7d.get("stars") or 0))
        forks_growth_7d = calculate_growth(current_forks, int(metric_7d.get("forks") or 0))
        issue_activity_7d = abs(current_issues - int(metric_7d.get("open_issues") or 0))

    momentum_score = calculate_github_momentum_score(
        stars_growth_24h=stars_growth_24h,
        stars_growth_7d=stars_growth_7d,
        forks_growth_7d=forks_growth_7d,
        issue_activity_7d=issue_activity_7d,
    )

    return {
        "has_24h_baseline": metric_24h is not None,
        "has_7d_baseline": metric_7d is not None,
        "stars_growth_24h": stars_growth_24h,
        "stars_growth_7d": stars_growth_7d,
        "forks_growth_7d": forks_growth_7d,
        "issue_activity_7d": issue_activity_7d,
        "momentum_score": momentum_score,
    }
