"""
Shared utilities for recording components.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Tuple, Optional, Union


def clean_segment(seg: str) -> str:
    """Normalize a string for safe inclusion in IDs (lowercase, dash-separated)."""
    return re.sub(r"[^a-z0-9-_]", "-", str(seg or "").lower()).strip("-_") or "x"


def parse_room_tokens(room_name: str) -> Tuple[str, str, str, str]:
    """Parse room name into (base, case, user, ts) for old and new formats."""
    room_name = room_name or ""
    parts = room_name.split("__")
    base = parts[0] if len(parts) > 0 else ""
    if len(parts) >= 4:
        case = parts[1]
        user = parts[2]
        ts = parts[3]
    else:
        case = ""
        user = parts[1] if len(parts) > 1 else ""
        ts = parts[2] if len(parts) > 2 else ""
    return base, case, user, ts


def normalize_token(s: str) -> str:
    """Normalize a token for fuzzy matching (alphanumeric lowercase)."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def build_room_name(base_room: str, case_name: Optional[str], user_id: str, ts: Optional[str] = None) -> str:
    """Compose the canonical room name using the agreed convention.

    Format:
    - With case: base__case__user__YYYY-MM-DD_HH-MM-SS
    - Without case: base__user__YYYY-MM-DD_HH-MM-SS
    """
    base = clean_segment(base_room)
    case_seg = clean_segment(case_name) if case_name else ""
    uid = clean_segment(user_id)
    timestamp = ts or datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    if case_seg:
        return f"{base}__{case_seg}__{uid}__{timestamp}"
    return f"{base}__{uid}__{timestamp}"


def format_created_str(ts_raw: str, start_time: Optional[Union[int, float, str]]) -> str:
    """Return a human-readable created string from a timestamp token or start_time fallback."""
    try:
        if ts_raw:
            # New format: YYYY-MM-DD_HH-MM-SS
            if (
                len(ts_raw) == 19
                and ts_raw[4] == "-"
                and ts_raw[7] == "-"
                and ts_raw[10] == "_"
                and ts_raw[13] == "-"
                and ts_raw[16] == "-"
            ):
                return datetime.strptime(ts_raw, "%Y-%m-%d_%H-%M-%S").strftime("%Y-%m-%d %H:%M:%S")
            # Old formats: YYYYMMDDHHMMSS or YYYYMMDD_HHMMSS
            compact = ts_raw.replace("_", "")
            if compact.isdigit() and len(compact) == 14:
                return datetime.strptime(compact, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        # Fallbacks using start_time
        if isinstance(start_time, (int, float)):
            return datetime.fromtimestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(start_time, str):
            s = start_time.strip()
            if s.isdigit():
                return datetime.fromtimestamp(int(s)).strftime("%Y-%m-%d %H:%M:%S")
            return s or "Unknown"
    except Exception:
        pass
    return "Unknown"
