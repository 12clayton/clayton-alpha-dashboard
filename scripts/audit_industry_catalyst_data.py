"""Audit local V4.1 industry catalyst framework data."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_catalyst_data import INDUSTRY_CATALYST_DATA
from src.industry_trend_data import industryTrendData


REQUIRED_TOP_FIELDS = [
    "heat_score",
    "heat_level",
    "heat_direction",
    "summary",
    "summaryZh",
    "events",
]

REQUIRED_EVENT_FIELDS = [
    "date",
    "title",
    "titleZh",
    "event_type",
    "event_typeZh",
    "impact",
    "impactZh",
    "confidence",
    "confidenceZh",
    "description",
    "descriptionZh",
]

ENGLISH_RESIDUE_PATTERNS = [
    "Framework data",
    "Local framework data",
    "key driver",
    "main watch item",
    "capacity focus",
]


def main() -> int:
    known_ids = {record["id"] for record in industryTrendData}
    missing_fields = []
    unknown_industries = []
    english_residue = []

    for industry_id, payload in INDUSTRY_CATALYST_DATA.items():
        if industry_id not in known_ids:
            unknown_industries.append(industry_id)

        missing = missing_top_fields(payload)
        for index, event in enumerate(payload.get("events", [])):
            for field in REQUIRED_EVENT_FIELDS:
                if not event.get(field):
                    missing.append(f"events[{index}].{field}")
        if missing:
            missing_fields.append({"id": industry_id, "missing": missing})

        residues = find_english_residue(payload)
        if residues:
            english_residue.append({"id": industry_id, "patterns": residues})

    print_report("CATALYST INDUSTRIES", sorted(INDUSTRY_CATALYST_DATA))
    print_report("UNKNOWN INDUSTRY IDS", unknown_industries)
    print_report("MISSING CATALYST FIELDS", missing_fields)
    print_report("ENGLISH RESIDUE IN ZH FIELDS", english_residue)

    return 1 if unknown_industries or missing_fields or english_residue else 0


def missing_top_fields(payload: dict) -> list[str]:
    return [field for field in REQUIRED_TOP_FIELDS if not payload.get(field)]


def find_english_residue(payload: dict) -> list[str]:
    zh_values = [str(payload.get("summaryZh", ""))]
    for event in payload.get("events", []):
        zh_values.extend(
            [
                str(event.get("titleZh", "")),
                str(event.get("event_typeZh", "")),
                str(event.get("impactZh", "")),
                str(event.get("confidenceZh", "")),
                str(event.get("descriptionZh", "")),
            ]
        )
    residues = []
    for pattern in ENGLISH_RESIDUE_PATTERNS:
        if any(pattern in value for value in zh_values):
            residues.append(pattern)
    return residues


def print_report(title: str, payload: object) -> None:
    print(f"\n## {title}")
    if not payload:
        print("None")
        return
    if isinstance(payload, list):
        for item in payload:
            print(f"- {item}")
        return
    print(payload)


if __name__ == "__main__":
    raise SystemExit(main())
