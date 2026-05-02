DEFAULT_REPORT_LENGTH = "Standard"


REPORT_LENGTH_PROFILES = {
    "Ultra Short": {
        "top_items": 3,
        "llm_items": 8,
        "category_items": 0,
        "raw_chars": 0,
        "word_budget": "150-220 words",
        "tldr_bullets": "3 bullets max",
        "top_signals": 2,
        "watch_bullets": 0,
    },
    "Short": {
        "top_items": 3,
        "llm_items": 10,
        "category_items": 1,
        "raw_chars": 450,
        "word_budget": "300-450 words",
        "tldr_bullets": "3 to 4 bullets max",
        "top_signals": 3,
        "watch_bullets": 2,
    },
    "Standard": {
        "top_items": 5,
        "llm_items": 16,
        "category_items": 3,
        "raw_chars": 900,
        "word_budget": "500-750 words",
        "tldr_bullets": "4 to 6 bullets max",
        "top_signals": 3,
        "watch_bullets": 3,
    },
    "Deep": {
        "top_items": 7,
        "llm_items": 24,
        "category_items": 5,
        "raw_chars": 1300,
        "word_budget": "900-1300 words",
        "tldr_bullets": "6 to 8 bullets max",
        "top_signals": 5,
        "watch_bullets": 5,
    },
}


def normalize_report_length(value: str) -> str:
    if value in REPORT_LENGTH_PROFILES:
        return value

    return DEFAULT_REPORT_LENGTH


def report_length_profile(value: str) -> dict:
    return REPORT_LENGTH_PROFILES[normalize_report_length(value)]
