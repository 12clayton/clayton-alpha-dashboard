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

from src.industry_catalyst_data import CATALYST_GUIDE, INDUSTRY_CATALYST_DATA
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

ALLOWED_EVENT_TYPES = {
    "policy",
    "earnings",
    "order",
    "capex",
    "technology",
    "macro",
    "supply_chain",
    "price_cycle",
    "regulation",
    "geopolitical",
    "product",
    "consumer_demand",
}

ALLOWED_IMPACTS = {"positive", "neutral", "negative", "mixed"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def main() -> int:
    known_ids = {record["id"] for record in industryTrendData}
    missing_fields = []
    missing_industries = []
    unknown_industries = []
    english_residue = []
    enum_issues = []
    guide_issues = audit_catalyst_guide()

    for record in industryTrendData:
        if record["id"] not in INDUSTRY_CATALYST_DATA:
            missing_industries.append(record["id"])

    for industry_id, payload in INDUSTRY_CATALYST_DATA.items():
        if industry_id not in known_ids:
            unknown_industries.append(industry_id)

        missing = missing_top_fields(payload)
        if not isinstance(payload.get("events"), list) or len(payload.get("events", [])) < 2:
            missing.append("events[min_2]")
        for index, event in enumerate(payload.get("events", [])):
            for field in REQUIRED_EVENT_FIELDS:
                if not event.get(field):
                    missing.append(f"events[{index}].{field}")
            enum_issues.extend(validate_event_enums(industry_id, index, event))
        if missing:
            missing_fields.append({"id": industry_id, "missing": missing})

        residues = find_english_residue(payload)
        if residues:
            english_residue.append({"id": industry_id, "patterns": residues})

    print_report("CATALYST INDUSTRIES", sorted(INDUSTRY_CATALYST_DATA))
    print_report("INDUSTRIES MISSING CATALYST DATA", missing_industries)
    print_report("UNKNOWN INDUSTRY IDS", unknown_industries)
    print_report("MISSING CATALYST FIELDS", missing_fields)
    print_report("CATALYST ENUM ISSUES", enum_issues)
    print_report("ENGLISH RESIDUE IN ZH FIELDS", english_residue)
    print_report("CATALYST GUIDE ISSUES", guide_issues)

    return 1 if missing_industries or unknown_industries or missing_fields or enum_issues or english_residue or guide_issues else 0


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


def validate_event_enums(industry_id: str, index: int, event: dict) -> list[str]:
    issues = []
    if event.get("event_type") not in ALLOWED_EVENT_TYPES:
        issues.append(f"{industry_id}.events[{index}].event_type={event.get('event_type')}")
    if event.get("impact") not in ALLOWED_IMPACTS:
        issues.append(f"{industry_id}.events[{index}].impact={event.get('impact')}")
    if event.get("confidence") not in ALLOWED_CONFIDENCE:
        issues.append(f"{industry_id}.events[{index}].confidence={event.get('confidence')}")
    return issues


def audit_catalyst_guide() -> list[str]:
    issues = []
    required_languages = ["zh", "en"]
    required_sections = [
        "title",
        "event_types_title",
        "impact_title",
        "confidence_title",
        "heat_title",
        "columns",
        "event_types",
        "impact",
        "confidence",
        "heat",
    ]
    for lang in required_languages:
        guide = CATALYST_GUIDE.get(lang)
        if not guide:
            issues.append(f"missing guide language: {lang}")
            continue
        for section in required_sections:
            if not guide.get(section):
                issues.append(f"{lang}.{section}")
        if len(guide.get("event_types", {})) < 12:
            issues.append(f"{lang}.event_types incomplete")
        if len(guide.get("impact", {})) < 4:
            issues.append(f"{lang}.impact incomplete")
        if len(guide.get("confidence", {})) < 3:
            issues.append(f"{lang}.confidence incomplete")
        if len(guide.get("heat", {})) < 3:
            issues.append(f"{lang}.heat incomplete")
    return issues


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
