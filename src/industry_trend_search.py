"""Search helpers for mock industry trend records."""

from __future__ import annotations

import re
from typing import Iterable

from src.industry_trend_data import GENERIC_INDUSTRY_TEMPLATE, industryTrendData


def normalize_industry_query(text: str) -> str:
    """Normalize English and Chinese search input for alias matching."""

    lowered = str(text or "").strip().lower()
    return re.sub(r"[\s/_\-&]+", "", lowered)


def _record_terms(record: dict) -> Iterable[str]:
    yield record.get("id", "")
    yield record.get("name", "")
    yield record.get("chineseName", "")
    yield record.get("category", "")
    yield from record.get("aliases", [])


def find_industry_trend(query: str) -> tuple[dict, bool]:
    """Return the best mock industry match and whether it was exact enough."""

    normalized_query = normalize_industry_query(query)
    if not normalized_query:
        return industryTrendData[0], True

    for record in industryTrendData:
        normalized_terms = [normalize_industry_query(term) for term in _record_terms(record)]
        if normalized_query in normalized_terms:
            return record, True

    for record in industryTrendData:
        normalized_terms = [normalize_industry_query(term) for term in _record_terms(record)]
        if any(normalized_query in term or term in normalized_query for term in normalized_terms if term):
            return record, True

    fallback = GENERIC_INDUSTRY_TEMPLATE.copy()
    fallback["name"] = f"General Framework: {str(query).strip() or 'Industry'}"
    return fallback, False
