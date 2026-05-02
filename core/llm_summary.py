from typing import List, Dict

from dotenv import load_dotenv
from core.text_utils import truncate
from core.llm.providers import NoLLMProvider, provider_from_env
from core.report_length import DEFAULT_REPORT_LENGTH, report_length_profile


load_dotenv()


def is_ceiling_breaker_candidate(item: Dict) -> bool:
    title = (item.get("title") or "").lower()
    text = (item.get("raw_text") or "").lower()
    category = item.get("category") or ""
    score = float(item.get("score") or 0)

    blob = f"{title} {text}"

    strong_terms = [
        "openai",
        "anthropic",
        "deepmind",
        "google",
        "meta",
        "nvidia",
        "microsoft",
        "apple",
        "tsmc",
        "asml",
        "frontier model",
        "reasoning model",
        "world model",
        "vision-language-action",
        "vla",
        "physical ai",
        "embodied ai",
        "humanoid",
        "robot foundation model",
        "acquisition",
        "acquired",
        "merger",
        "funding",
        "series a",
        "series b",
        "valuation",
        "export controls",
        "sanctions",
        "ai act",
        "sovereign ai",
        "national security",
        "open-source",
        "open weights",
        "agentic",
        "coding agent",
        "compute",
        "gpu",
        "data center",
    ]

    has_strong_term = any(term in blob for term in strong_terms)

    if score >= 85 and has_strong_term:
        return True

    if category in [
        "business_startups_ma",
        "infrastructure_compute",
        "geopolitics_regulation",
        "frontier_ai",
    ] and score >= 75:
        return True

    if category == "research_papers" and score >= 90 and has_strong_term:
        return True

    return False


def select_brief_items(items: List[Dict], max_items: int = 16) -> List[Dict]:
    """
    Select a compact, diverse set of high-impact signals.
    Avoid letting research papers completely take over the morning brief.
    """

    candidates = [item for item in items if is_ceiling_breaker_candidate(item)]

    if not candidates:
        candidates = items[:max_items]

    category_limits = {
        "research_papers": 5,
        "business_startups_ma": 4,
        "infrastructure_compute": 3,
        "frontier_ai": 3,
        "open_source_devtools": 3,
        "geopolitics_regulation": 3,
        "robotics_physical_ai": 4,
        "general": 2,
    }

    selected = []
    counts = {}

    for item in sorted(
        candidates,
        key=lambda x: (float(x.get("score") or 0), float(x.get("momentum_score") or 0)),
        reverse=True,
    ):
        category = item.get("category") or "general"
        limit = category_limits.get(category, 2)

        if counts.get(category, 0) >= limit:
            continue

        selected.append(item)
        counts[category] = counts.get(category, 0) + 1

        if len(selected) >= max_items:
            break

    return selected


def build_items_payload(items: List[Dict], max_items: int = 16) -> str:
    chunks = []

    selected_items = select_brief_items(items, max_items=max_items)

    for i, item in enumerate(selected_items, start=1):
        raw = truncate(item.get("raw_text") or "", max_chars=550)

        chunks.append(
            f"""
ITEM {i}
Title: {item.get("title")}
Source: {item.get("source_name")}
Type: {item.get("source_type")}
Category: {item.get("category")}
Score: {item.get("score")}
Momentum: {item.get("momentum_score", 0)}
URL: {item.get("url")}
Text: {raw}
"""
        )

    return "\n".join(chunks)


def generate_fallback_read(items: List[Dict], report_length: str = DEFAULT_REPORT_LENGTH) -> str:
    profile = report_length_profile(report_length)
    selected_items = select_brief_items(items, max_items=profile["top_signals"])

    if not selected_items:
        return "## Rule-Based Brief (LLM Disabled)\n\nNo high-signal items found for this report length. No LLM call was made."

    if report_length == "Ultra Short":
        lines = [
            "## Rule-Based Brief (LLM Disabled)",
            "",
            "_Generated from scores and source metadata only. No LLM call was made._",
            "",
        ]
        for item in selected_items[: profile["top_items"]]:
            lines.append(
                f"- **{item.get('title')}** — {item.get('category') or 'general'}; "
                f"relevance {float(item.get('score') or 0):.1f}/100."
            )
        return "\n".join(lines)

    lines = [
        "## Rule-Based Brief (LLM Disabled)",
        "",
        "_Generated from scores and source metadata only. No LLM call was made._",
        "",
        "### Highest-Ranked Signals",
    ]

    for item in selected_items[: profile["top_items"]]:
        lines.append(
            f"- **{item.get('title')}** — {item.get('category') or 'general'}; "
            f"relevance {float(item.get('score') or 0):.1f}/100."
        )

    lines.extend(["", "### Source Excerpts"])

    for index, item in enumerate(selected_items[: profile["top_signals"]], start=1):
        raw = truncate(item.get("raw_text") or "", max_chars=240)
        lines.extend(
            [
                f"{index}. **{item.get('title')}**",
                f"   - Excerpt: {raw or 'No source excerpt available.'}",
                f"   - Source: {item.get('source_name')} — {item.get('url')}",
            ]
        )

    if profile["watch_bullets"] > 0:
        lines.extend(["", "### Watch List"])
        for item in selected_items[: profile["watch_bullets"]]:
            lines.append(f"- {item.get('source_name')}: {item.get('title')}")

    return "\n".join(lines)


def generate_strategic_read(
    items: List[Dict],
    report_length: str = DEFAULT_REPORT_LENGTH,
) -> str:
    profile = report_length_profile(report_length)
    provider = provider_from_env()

    if isinstance(provider, NoLLMProvider):
        return generate_fallback_read(items, report_length=report_length)

    items_payload = build_items_payload(items, max_items=profile["llm_items"])

    if report_length == "Ultra Short":
        prompt = f"""
You are writing an ultra-short morning tech intelligence brief for an engineer/researcher.

The user selected report length: Ultra Short.
Target length: {profile["word_budget"]}.

Focus only on ceiling-breaker signals. Do not summarize every item.
Do not overhype. Be direct and useful.

Output exactly this format:

## LLM Brief
- Bullet 1
- Bullet 2
- Bullet 3
- Bullet 4
- Bullet 5

Rules:
- Maximum 5 bullets total.
- No sections other than "## LLM Brief".
- No paragraphs.
- No Watch Next.
- No Top Signals.

Signals:
{items_payload}
"""

        try:
            return provider.generate(prompt, max_tokens=450)
        except Exception as exc:
            return f"{generate_fallback_read(items, report_length=report_length)}\n\nLLM provider failed: {exc}"

    watch_next_instruction = (
        f"- {profile['watch_bullets']} bullets max: people, companies, repos, papers, regulations, or debates to track."
        if profile["watch_bullets"] > 0
        else "- Omit this section."
    )

    prompt = f"""
You are writing a very concise morning tech intelligence brief for an engineer/researcher.

The user selected report length: {report_length}.
Target length: {profile["word_budget"]}.

Focus only on ceiling-breaker signals:
- major frontier AI releases or model capability shifts
- acquisitions, funding, M&A, strategic partnerships
- important statements from major AI/robotics figures
- big open-source releases that may change developer workflows
- robotics / physical AI breakthroughs with real strategic implications
- compute, GPU, cloud, semiconductor, export-control, regulation signals
- papers only if they suggest a meaningful paradigm shift, not incremental work

Do NOT summarize every item.
Do NOT sound like a newsletter.
Do NOT overhype.
Do NOT include generic customer stories unless strategically important.
Separate "actually important" from "interesting but not urgent".

Write in English.
Be concise, dense, and readable.

Output exactly this format:

## LLM Brief

### TL;DR
- {profile["tldr_bullets"]}.

### Top Signals
Include exactly {profile["top_signals"]} signals.
For each:
N. **Signal title**
   - What happened:
   - Why it matters:
   - Implication:

### Watch Next
{watch_next_instruction}

Signals:
{items_payload}
"""

    try:
        return provider.generate(prompt, max_tokens=1400 if report_length == "Deep" else 900)
    except Exception as exc:
        return f"{generate_fallback_read(items, report_length=report_length)}\n\nLLM provider failed: {exc}"
