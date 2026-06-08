"""Local snapshot and watchlist helpers for the industry radar."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


RADAR_DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "industry_radar"
WATCHLIST_PATH = RADAR_DATA_DIR / "watchlist.json"
LATEST_RADAR_PATH = RADAR_DATA_DIR / "latest_radar.csv"
DEFAULT_WATCHLIST = [
    "semiconductor",
    "cpo_optical_module",
    "ai_compute",
    "cpu",
    "gold",
    "sic",
]


def ensure_radar_data_dir() -> Path:
    """Create and return the local radar data directory."""

    RADAR_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return RADAR_DATA_DIR


def load_watchlist() -> list[str]:
    """Load watchlist ids, creating the default config if needed."""

    ensure_radar_data_dir()
    if not WATCHLIST_PATH.exists():
        save_watchlist(DEFAULT_WATCHLIST)
        return list(DEFAULT_WATCHLIST)
    try:
        payload = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            values = payload.get("industry_ids", DEFAULT_WATCHLIST)
        else:
            values = payload
        if not isinstance(values, list):
            return list(DEFAULT_WATCHLIST)
        return [str(item) for item in values]
    except Exception:
        return list(DEFAULT_WATCHLIST)


def save_watchlist(industry_ids: list[str]) -> None:
    """Persist watchlist ids as local JSON."""

    ensure_radar_data_dir()
    WATCHLIST_PATH.write_text(
        json.dumps({"industry_ids": industry_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_snapshot(snapshot_rows: list[dict[str, Any]], snapshot_date: date | None = None) -> Path:
    """Save the current radar snapshot to a dated CSV file."""

    ensure_radar_data_dir()
    current_date = snapshot_date or date.today()
    path = RADAR_DATA_DIR / f"radar_snapshot_{current_date:%Y-%m-%d}.csv"
    pd.DataFrame(snapshot_rows).to_csv(path, index=False, encoding="utf-8-sig")
    return path


def save_latest_radar(snapshot_rows: list[dict[str, Any]]) -> Path:
    """Save the latest radar cache used for fast default page loads."""

    ensure_radar_data_dir()
    frame = pd.DataFrame(snapshot_rows)
    temp_path = LATEST_RADAR_PATH.with_suffix(".tmp.csv")
    frame.to_csv(temp_path, index=False, encoding="utf-8-sig")
    temp_path.replace(LATEST_RADAR_PATH)
    return LATEST_RADAR_PATH


def load_latest_radar_frame() -> pd.DataFrame:
    """Load the latest radar cache without creating network work."""

    ensure_radar_data_dir()
    if not LATEST_RADAR_PATH.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(LATEST_RADAR_PATH)
    except Exception:
        return pd.DataFrame()


def latest_radar_updated_at() -> str:
    """Return the latest radar cache file mtime as a readable timestamp."""

    if not LATEST_RADAR_PATH.exists():
        return ""
    try:
        return datetime.fromtimestamp(LATEST_RADAR_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def list_snapshot_files() -> list[Path]:
    """Return snapshot CSV files sorted by date descending."""

    ensure_radar_data_dir()
    return sorted(RADAR_DATA_DIR.glob("radar_snapshot_*.csv"), reverse=True)


def snapshot_date_from_path(path: Path) -> str:
    """Extract YYYY-MM-DD from a snapshot filename."""

    return path.stem.replace("radar_snapshot_", "")


def latest_snapshot_path(before: date | None = None) -> Path | None:
    """Return the latest snapshot, preferring one before the supplied date."""

    files = list_snapshot_files()
    if not files:
        return None
    if before is None:
        return files[0]
    before_text = f"{before:%Y-%m-%d}"
    older_files = [path for path in files if snapshot_date_from_path(path) < before_text]
    return older_files[0] if older_files else files[0]


def load_latest_snapshot_lookup(before: date | None = None) -> dict[str, dict[str, Any]]:
    """Load the latest snapshot as an industry_id keyed lookup."""

    path = latest_snapshot_path(before=before)
    if path is None:
        return {}
    try:
        frame = pd.read_csv(path)
    except Exception:
        return {}
    if "industry_id" not in frame.columns:
        return {}
    return {
        str(row["industry_id"]): row.to_dict()
        for _, row in frame.iterrows()
        if pd.notna(row.get("industry_id"))
    }


def snapshot_summary() -> dict[str, Any]:
    """Return a small summary of local snapshot files."""

    files = list_snapshot_files()
    latest = snapshot_date_from_path(files[0]) if files else None
    return {
        "count": len(files),
        "latest": latest,
        "files": [path.name for path in files],
        "directory": str(ensure_radar_data_dir()),
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_snapshot_history() -> pd.DataFrame:
    """Load all local radar snapshots into one dataframe."""

    frames = []
    for path in list_snapshot_files():
        try:
            frame = pd.read_csv(path)
        except Exception:
            continue
        if frame.empty:
            continue
        if "snapshot_date" not in frame.columns:
            frame["snapshot_date"] = snapshot_date_from_path(path)
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
