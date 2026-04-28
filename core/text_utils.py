from bs4 import BeautifulSoup
import re


def clean_html(text: str) -> str:
    if not text:
        return ""

    soup = BeautifulSoup(text, "html.parser")
    cleaned = soup.get_text(" ")

    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def truncate(text: str, max_chars: int = 900) -> str:
    text = clean_html(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars].strip() + "..."
