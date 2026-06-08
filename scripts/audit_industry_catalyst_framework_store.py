"""Audit V4.13 updatable catalyst framework store without network access."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = types.SimpleNamespace(cache_data=lambda *args, **kwargs: (lambda func: func))

from src.industry_catalyst_framework_store import (  # noqa: E402
    FRAMEWORK_REQUIRED_FIELDS,
    apply_snapshot_as_framework_override,
    ensure_framework_store,
    get_base_catalyst_framework,
    get_effective_catalyst_framework,
    load_framework_overrides,
    remove_framework_override,
    save_framework_overrides,
    write_framework_override,
)


def main() -> int:
    issues = []
    path = ensure_framework_store()
    if not path.exists():
        issues.append("framework override file was not created")
    overrides = load_framework_overrides()
    if not isinstance(overrides, dict):
        issues.append("framework overrides payload should be a dict")

    base = get_base_catalyst_framework("semiconductor")
    if not base:
        issues.append("base semiconductor framework was not readable")
    else:
        for field in ["summary", "summaryZh", "events", "base_framework_dates", "is_override"]:
            if field not in base:
                issues.append(f"base framework missing field: {field}")

    effective = get_effective_catalyst_framework("semiconductor")
    if not effective:
        issues.append("effective framework fallback failed")
    elif effective.get("is_override") not in {True, False}:
        issues.append("effective framework missing is_override boolean")

    audit_id = "__audit_framework__"
    try:
        remove_framework_override(audit_id)
        mock_override = {
            "updated_at": "2026-06-08T11:06:15",
            "source": "audit",
            "base_framework_dates": ["2026-05-27"],
            "summary": "Audit override summary",
            "summaryZh": "审计覆盖摘要",
            "heat_score": 6.0,
            "heat_level": "Medium",
            "heat_direction": "Stable",
            "events": [
                {
                    "date": "2026-06-08",
                    "title": "Audit event",
                    "titleZh": "审计事件",
                    "event_type": "technology",
                    "event_typeZh": "技术",
                    "impact": "neutral",
                    "impactZh": "中性",
                    "confidence": "medium",
                    "confidenceZh": "中",
                    "description": "Audit description",
                    "descriptionZh": "审计说明",
                }
            ],
        }
        write_framework_override(audit_id, mock_override)
        loaded = load_framework_overrides().get(audit_id)
        if not loaded or loaded.get("summary") != "Audit override summary":
            issues.append("mock override write/read failed")
        remove_framework_override(audit_id)
    except Exception as exc:
        issues.append(f"mock override write/read raised: {exc}")

    original_overrides = load_framework_overrides()
    original_semiconductor = original_overrides.get("semiconductor")
    snapshot = {
        "review_status": "stable",
        "evidence_level": "medium",
        "active_catalysts": ["AI chip"],
        "emerging_catalysts": ["DRAM", "SK Hynix"],
        "active_catalyst_themes": [
            {
                "theme": "AI chip-chain diffusion",
                "theme_zh": "AI 芯片链条扩散",
                "matched_terms": ["AI chip"],
                "reason": "audit",
                "reason_zh": "审计",
            }
        ],
        "emerging_catalyst_themes": [
            {
                "theme": "HBM / DRAM memory-chain reinforcement",
                "theme_zh": "HBM / DRAM 存储链强化",
                "matched_terms": ["DRAM", "SK Hynix"],
                "reason": "audit",
                "reason_zh": "审计",
            }
        ],
        "one_line_snapshot": "Audit snapshot",
        "one_line_snapshot_zh": "审计快照",
        "coverage_note": "Audit coverage",
        "coverage_note_zh": "审计覆盖说明",
    }
    review = {"evidence_level": "medium"}
    try:
        generated = apply_snapshot_as_framework_override("semiconductor", base, snapshot, review, {"items": []})
        for field in FRAMEWORK_REQUIRED_FIELDS:
            if field not in generated:
                issues.append(f"generated effective framework missing field: {field}")
        if not generated.get("is_override"):
            issues.append("generated effective framework should be override")
        if not generated.get("events"):
            issues.append("generated override should include events")
        titles_zh = [event.get("titleZh", "") for event in generated.get("events", [])]
        if not any("HBM / DRAM 存储链强化" in title for title in titles_zh):
            issues.append("generated override event title should use normalized catalyst theme")
    except Exception as exc:
        issues.append(f"apply snapshot as override raised: {exc}")
    finally:
        restored = load_framework_overrides()
        if original_semiconductor is None:
            restored.pop("semiconductor", None)
        else:
            restored["semiconductor"] = original_semiconductor
        save_framework_overrides(restored)

    print_report("FRAMEWORK STORE PATH", str(path))
    print_report("FRAMEWORK STORE ISSUES", issues)
    return 1 if issues else 0


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
