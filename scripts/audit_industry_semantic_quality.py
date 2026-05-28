"""Audit semantic quality of industry trend and catalyst framework data.

This script looks for fields that are structurally complete but semantically
misaligned with an industry's category, especially generic technology or
manufacturing template residue in consumer, financial, healthcare, and
industrial themes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.industry_catalyst_data import INDUSTRY_CATALYST_DATA  # noqa: E402
from src.industry_trend_data import industryTrendData  # noqa: E402


TEMPLATE_POLLUTION_TERMS = {
    "组件供应商": "generic technology supplier layer",
    "基础设施提供商": "generic infrastructure layer",
    "应用层": "generic application layer",
    "原始投入": "generic raw-input layer",
    "核心设备": "generic equipment layer",
    "专用材料": "generic specialized-material layer",
    "设计工具": "generic design-tool layer",
    "平台运营商": "generic platform-operator layer",
    "集成环节": "generic integration layer",
    "公共项目": "generic public-project demand layer",
    "全球渠道": "generic global-channel layer",
    "Component Suppliers": "generic technology supplier layer",
    "Infrastructure Providers": "generic infrastructure layer",
    "Application Layer": "generic application layer",
    "Raw inputs": "generic raw-input layer",
    "Core equipment": "generic equipment layer",
    "Specialized materials": "generic specialized-material layer",
    "Design tools": "generic design-tool layer",
    "Platform operators": "generic platform-operator layer",
    "Integration": "generic integration layer",
    "Public projects": "generic public-project demand layer",
    "Global channels": "generic global-channel layer",
}

FOCUS_CATEGORIES = {
    "Consumer",
    "Financial & Real Estate",
    "Healthcare",
    "Cyclical & Industrial",
}

FIELD_PATHS = {
    "keyDrivers": ["name", "nameZh", "explanation", "explanationZh"],
    "subSectors": ["name", "nameZh", "status"],
    "industryChain": ["upstream", "midstream", "downstream"],
    "industryChainZh": ["upstream", "midstream", "downstream"],
    "catalysts": [],
    "catalystsZh": [],
    "riskSignals": [],
    "riskSignalsZh": [],
}


def main() -> int:
    issues: list[dict[str, str]] = []
    for industry in industryTrendData:
        issues.extend(audit_industry(industry))
        catalyst = INDUSTRY_CATALYST_DATA.get(str(industry.get("id", "")))
        if catalyst:
            issues.extend(audit_catalyst(industry, catalyst))

    print("## SEMANTIC QUALITY ISSUES")
    if not issues:
        print("None")
        return 0
    for issue in issues:
        print(f"- industry_id: {issue['industry_id']}")
        print(f"  field: {issue['field']}")
        print(f"  suspicious_value: {issue['suspicious_value']}")
        print(f"  reason: {issue['reason']}")
        print(f"  suggested_fix: {issue['suggested_fix']}")
    return 1


def audit_industry(industry: dict[str, Any]) -> list[dict[str, str]]:
    category = str(industry.get("category", ""))
    if category not in FOCUS_CATEGORIES:
        return []
    issues: list[dict[str, str]] = []
    industry_id = str(industry.get("id", ""))
    for field, subfields in FIELD_PATHS.items():
        value = industry.get(field)
        values = flatten_field_values(value, subfields)
        for item in values:
            reason = suspicious_reason(item)
            if reason:
                issues.append(
                    build_issue(
                        industry_id=industry_id,
                        field=field,
                        value=item,
                        reason=reason,
                        suggested_fix=f"Replace {field} with category-specific {category} wording.",
                    )
                )
    return issues


def audit_catalyst(industry: dict[str, Any], catalyst: dict[str, Any]) -> list[dict[str, str]]:
    category = str(industry.get("category", ""))
    if category not in FOCUS_CATEGORIES:
        return []
    issues: list[dict[str, str]] = []
    industry_id = str(industry.get("id", ""))
    for field in ("summary", "summaryZh"):
        reason = suspicious_reason(str(catalyst.get(field, "")))
        if reason:
            issues.append(
                build_issue(
                    industry_id=industry_id,
                    field=f"catalyst.{field}",
                    value=str(catalyst.get(field, "")),
                    reason=reason,
                    suggested_fix="Replace catalyst summary with category-specific event language.",
                )
            )
    for index, event in enumerate(catalyst.get("events", []) or []):
        for field in ("title", "titleZh", "description", "descriptionZh"):
            reason = suspicious_reason(str(event.get(field, "")))
            if reason:
                issues.append(
                    build_issue(
                        industry_id=industry_id,
                        field=f"catalyst.events[{index}].{field}",
                        value=str(event.get(field, "")),
                        reason=reason,
                        suggested_fix="Replace event wording with category-specific catalyst language.",
                    )
                )
    return issues


def flatten_field_values(value: Any, subfields: list[str]) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            if isinstance(item, dict):
                output.extend(str(item.get(key, "")) for key in subfields if item.get(key))
            else:
                output.append(str(item))
        return output
    if isinstance(value, dict):
        output = []
        for item in value.values():
            output.extend(flatten_field_values(item, subfields))
        return output
    return [str(value)]


def suspicious_reason(value: str) -> str:
    for term, reason in TEMPLATE_POLLUTION_TERMS.items():
        if term in value:
            return reason
    return ""


def build_issue(
    *,
    industry_id: str,
    field: str,
    value: str,
    reason: str,
    suggested_fix: str,
) -> dict[str, str]:
    return {
        "industry_id": industry_id,
        "field": field,
        "suspicious_value": value,
        "reason": reason,
        "suggested_fix": suggested_fix,
    }


if __name__ == "__main__":
    raise SystemExit(main())
