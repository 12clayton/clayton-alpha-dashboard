"""Audit Industry Trend Search Engine mock data and V3 market mappings."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_market_data import EXPLICIT_NO_MARKET_MAPPING, INDUSTRY_MARKET_TICKERS
from src.industry_trend_data import industryTrendData
from src.industry_trend_search import normalize_industry_query


REQUIRED_RECORD_FIELDS = [
    "chineseName",
    "categoryZh",
    "overviewZh",
    "summaryZh",
    "trendStageZh",
    "catalystsZh",
    "riskSignalsZh",
    "industryChainZh",
]

ENGLISH_RESIDUE_PATTERNS = [
    "is tracked with a neutral trend framework",
    "demand cycle",
    "Policy and capex visibility",
    "Supply-chain pricing power",
    "Capacity cycle changes",
    "Narrative runs ahead of validation",
    "Raw inputs",
    "Manufacturing",
    "Enterprise demand",
    "Consumer adoption",
    "Public projects",
    "Global channels",
    "Infrastructure Providers",
    "Application Layer",
    "Component Suppliers",
]


def main() -> int:
    missing_zh = []
    english_residue = []
    missing_mapping = []
    alias_groups = build_alias_groups()

    for record in industryTrendData:
        missing = missing_zh_fields(record)
        if missing:
            missing_zh.append({"id": record["id"], "name": record["name"], "missing": missing})

        residues = find_english_residue(record)
        if residues:
            english_residue.append({"id": record["id"], "name": record["name"], "patterns": residues})

        if record["id"] not in INDUSTRY_MARKET_TICKERS:
            reason = (
                "explicit_no_market_mapping"
                if record["id"] in EXPLICIT_NO_MARKET_MAPPING
                else "missing_market_mapping"
            )
            missing_mapping.append(
                {
                    "id": record["id"],
                    "name": record.get("name", ""),
                    "chineseName": record.get("chineseName", ""),
                    "aliases": record.get("aliases", []),
                    "reason": reason,
                }
            )

    ambiguous_aliases = [
        {"alias": alias, "industries": sorted(ids)}
        for alias, ids in alias_groups.items()
        if len(ids) > 1
    ]

    passed = [
        record["id"]
        for record in industryTrendData
        if not missing_zh_fields(record)
        and not find_english_residue(record)
    ]

    print_report("PASSED INDUSTRIES", passed)
    print_report("INDUSTRIES MISSING ZH FIELDS", missing_zh)
    print_report("INDUSTRIES WITH ENGLISH RESIDUE IN ZH MODE", english_residue)
    print_report("INDUSTRIES WITHOUT V3 MARKET MAPPING", missing_mapping)
    print_report("POTENTIALLY AMBIGUOUS ALIASES", ambiguous_aliases)

    failed = bool(missing_zh or english_residue)
    return 1 if failed else 0


def missing_zh_fields(record: dict) -> list[str]:
    missing = [field for field in REQUIRED_RECORD_FIELDS if not record.get(field)]
    for index, driver in enumerate(record.get("keyDrivers", [])):
        if not driver.get("nameZh"):
            missing.append(f"keyDrivers[{index}].nameZh")
        if not driver.get("explanationZh"):
            missing.append(f"keyDrivers[{index}].explanationZh")
    for index, sector in enumerate(record.get("subSectors", [])):
        if not sector.get("nameZh"):
            missing.append(f"subSectors[{index}].nameZh")
    return missing


def find_english_residue(record: dict) -> list[str]:
    zh_values = collect_zh_values(record)
    residues = []
    for pattern in ENGLISH_RESIDUE_PATTERNS:
        if any(pattern in value for value in zh_values):
            residues.append(pattern)
    return residues


def collect_zh_values(record: dict) -> list[str]:
    values = []
    for field in REQUIRED_RECORD_FIELDS:
        value = record.get(field)
        if isinstance(value, dict):
            values.extend(str(item) for items in value.values() for item in items)
        elif isinstance(value, list):
            values.extend(str(item) for item in value)
        elif value:
            values.append(str(value))
    for driver in record.get("keyDrivers", []):
        values.append(str(driver.get("nameZh", "")))
        values.append(str(driver.get("explanationZh", "")))
    for sector in record.get("subSectors", []):
        values.append(str(sector.get("nameZh", "")))
    return values


def build_alias_groups() -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for record in industryTrendData:
        terms = [
            record.get("id", ""),
            record.get("name", ""),
            record.get("chineseName", ""),
            *record.get("aliases", []),
        ]
        for term in terms:
            normalized = normalize_industry_query(term)
            if normalized:
                groups.setdefault(normalized, set()).add(record["id"])
    return groups


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
