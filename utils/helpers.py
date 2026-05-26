"""
utils/helpers.py — General-purpose utility helpers.
"""
import datetime
import re
from typing import Any, List


def truncate(text: str, max_len: int = 200, suffix: str = "…") -> str:
    return text[:max_len] + suffix if len(text) > max_len else text


def find_sentence(text: str, keywords: List[str], max_len: int = 200) -> str:
    """Return the first sentence containing any keyword."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    for kw in keywords:
        for sent in sentences:
            if kw.lower() in sent.lower():
                return sent[:max_len]
    return text[:max_len]


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
