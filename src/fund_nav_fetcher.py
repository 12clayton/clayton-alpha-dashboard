"""Compatibility wrapper for the real fund NAV provider."""

from __future__ import annotations

from src.fund_nav_provider import (  # noqa: F401
    NAV_COLUMNS,
    get_latest_fund_nav,
    get_latest_fund_navs_for_funds,
    load_fund_nav_cache,
    normalize_fund_code,
    update_fund_nav_cache,
)
