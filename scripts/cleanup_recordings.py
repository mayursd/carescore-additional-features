"""
Cleanup old Daily.co recordings based on a retention policy.

Default retention: 7 days.

Features:
- Dry-run mode (default) prints candidates without deleting.
- Confirmed delete mode with --yes flag.
- Protect specific recordings by ID via --keep-file.
- Protect recordings by substring match in room name via --keep-substrings.
- Structured logging to console (and optional file).

Environment:
- DAILY_API_KEY must be set (or passed with --api-key).

Note: This script talks directly to the Daily REST API to avoid Streamlit dependencies.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import json
import logging
import os
import sys
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import requests


DAILY_API_BASE = "https://api.daily.co/v1"


logging.basicConfig(level=logging.INFO)


def _read_keep_ids(path: str) -> Set[str]:
    keep: Set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            keep.add(s)
    return keep


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Delete Daily.co recordings older than retention.")
    p.add_argument("--retention-days", type=int, default=7, help="Days to keep. Older recordings are deleted (default: 7)")
    p.add_argument("--dry-run", action="store_true", help="List candidates only; do not delete (default if --yes not provided)")
    p.add_argument("--yes", action="store_true", help="Actually perform deletions (confirmation flag)")
    p.add_argument("--keep-file", type=str, default=None, help="Path to a file with recording IDs to keep (one per line)")
    p.add_argument(
        "--keep-substrings",
        type=str,
        default=None,
        help="Comma-separated substrings; if present in room name, recording is kept",
    )
    p.add_argument("--api-key", type=str, default=None, help="Daily API key (falls back to env DAILY_API_KEY)")
    p.add_argument("--log-file", type=str, default=None, help="Optional path to write a log file")
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    return p.parse_args(argv)


def _setup_logging(verbose: bool, log_file: Optional[str]) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )


def _auth_headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def list_recordings_all(api_key: str) -> List[Dict[str, Any]]:
    """Fetch all recordings with best-effort pagination.

    Daily API typically returns { data: [...], ... }. Some APIs include pagination
    tokens or next links. We'll support a few common patterns gracefully.
    """
    url = f"{DAILY_API_BASE}/recordings"
    headers = _auth_headers(api_key)
    all_items: List[Dict[str, Any]] = []

    # Try to page until no more. We support these patterns:
    # - next_page_token
    # - next (absolute URL)
    # - has_more + starting_after
    params: Dict[str, Any] = {"limit": 100}
    next_url: Optional[str] = None
    starting_after: Optional[str] = None

    while True:
        req_url = next_url or url
        use_params = dict(params)
        if starting_after:
            use_params["starting_after"] = starting_after

        resp = requests.get(req_url, headers=headers, params=use_params if req_url == url else None, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Daily API error listing recordings: {resp.text}")
        data = resp.json()
        items = data.get("data") or data.get("items") or []
        if not isinstance(items, list):
            raise RuntimeError(f"Unexpected response format: {json.dumps(data)[:500]}")
        all_items.extend(items)

        # Determine pagination
        next_page_token = data.get("next_page_token") or data.get("nextToken")
        next_link = data.get("next") or data.get("next_link")
        has_more = bool(data.get("has_more"))

        if next_page_token:
            # Some APIs accept page_token
            params["page_token"] = next_page_token
            next_url = url
        elif next_link:
            next_url = next_link
        elif has_more and items:
            # Try starting_after = last id
            last_id = items[-1].get("id")
            if last_id:
                starting_after = last_id
                next_url = url
            else:
                break
        else:
            break

    return all_items


def _epoch_to_dt(sec: float) -> dt.datetime:
    # Handle ms epoch too
    if sec > 1_000_000_000_000:  # very large -> likely ms
        sec = sec / 1000.0
    return dt.datetime.utcfromtimestamp(sec).replace(tzinfo=dt.timezone.utc)


def _parse_any_datetime(val: Any) -> Optional[dt.datetime]:
    if val is None:
        return None
    # Numeric epoch
    if isinstance(val, (int, float)):
        try:
            return _epoch_to_dt(float(val))
        except Exception:
            return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        if s.isdigit():
            try:
                return _epoch_to_dt(float(s))
            except Exception:
                pass
        # ISO-8601 like strings
        iso = s.replace("Z", "+00:00")
        try:
            dtv = dt.datetime.fromisoformat(iso)
            if dtv.tzinfo is None:
                dtv = dtv.replace(tzinfo=dt.timezone.utc)
            return dtv.astimezone(dt.timezone.utc)
        except Exception:
            pass
        # Try common patterns
        for pat in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return dt.datetime.strptime(s, pat).replace(tzinfo=dt.timezone.utc)
            except Exception:
                continue
    return None


def _extract_ts_from_room_name(rn: str) -> Optional[dt.datetime]:
    if not rn:
        return None
    # 1) Look for pattern YYYY-MM-DD_HH-MM-SS
    m = re.search(r"(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", rn)
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M-%S").replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass
    # 2) Look for pattern YYYYMMDD_HHMMSS
    m = re.search(r"(\d{8}_\d{6})", rn)
    if m:
        compact = m.group(1).replace("_", "")
        try:
            return dt.datetime.strptime(compact, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass
    # 3) Look for compact 14-digit timestamp anywhere
    m = re.search(r"(?<!\d)(\d{14})(?!\d)", rn)
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
        except Exception:
            pass
    # 4) Fallback to prior double-underscore token logic
    parts = rn.split("__")
    ts_token = ""
    if len(parts) >= 4:
        ts_token = parts[3]
    elif len(parts) >= 3:
        ts_token = parts[2]
    ts = (ts_token or "").strip()
    if ts:
        if len(ts) == 19 and ts[4] == "-" and ts[7] == "-" and ts[10] == "_" and ts[13] == "-" and ts[16] == "-":
            try:
                return dt.datetime.strptime(ts, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=dt.timezone.utc)
            except Exception:
                pass
        compact = ts.replace("_", "")
        if compact.isdigit() and len(compact) == 14:
            try:
                return dt.datetime.strptime(compact, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
            except Exception:
                pass
    return None


def _parse_recording_time(rec: Dict[str, Any]) -> Optional[dt.datetime]:
    """Return a timezone-aware UTC datetime for the recording start/creation time.

    Tries fields in order: start_time, created_at/date_created/created..., then timestamp embedded in room_name.
    """
    # 1) try start_time
    dtv = _parse_any_datetime(rec.get("start_time"))
    if dtv:
        return dtv
    # 2) try other common fields
    for key in ("created_at", "date_created", "createdAt", "dateCreated", "created", "start_ts", "started_at", "startAt", "start"):
        dtv = _parse_any_datetime(rec.get(key))
        if dtv:
            return dtv
    # 3) parse from room_name (supports multiple formats)
    rn = rec.get("room_name") or ""
    return _extract_ts_from_room_name(rn)


def _should_keep(rec: Dict[str, Any], keep_ids: Set[str], keep_substrings: List[str]) -> bool:
    rid = str(rec.get("id", ""))
    if rid and rid in keep_ids:
        return True
    rn = (rec.get("room_name") or "").lower()
    for sub in keep_substrings:
        if sub and sub.lower() in rn:
            return True
    return False


def delete_recording(api_key: str, recording_id: str) -> Tuple[bool, Optional[str]]:
    url = f"{DAILY_API_BASE}/recordings/{recording_id}"
    resp = requests.delete(url, headers=_auth_headers(api_key), timeout=60)
    if resp.status_code in (200, 202, 204):
        return True, None
    try:
        data = resp.json()
        return False, data.get("error") or resp.text
    except Exception:
        return False, resp.text


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    _setup_logging(args.verbose, args.log_file)

    api_key = args.api_key or os.environ.get("DAILY_API_KEY")
    if not api_key:
        logging.error("DAILY_API_KEY is required (pass --api-key or set env var)")
        return 2

    keep_ids: Set[str] = set()
    if args.keep_file:
        try:
            keep_ids = _read_keep_ids(args.keep_file)
            logging.info("Loaded %d protected recording IDs from %s", len(keep_ids), args.keep_file)
        except Exception as e:
            logging.error("Failed to read keep-file: %s", e)
            return 2

    keep_substrings: List[str] = []
    if args.keep_substrings:
        keep_substrings = [s.strip() for s in args.keep_substrings.split(",") if s.strip()]
        if keep_substrings:
            logging.info("Protecting recordings containing substrings: %s", ", ".join(keep_substrings))

    try:
        recordings = list_recordings_all(api_key)
    except Exception as e:
        logging.error("Error listing recordings: %s", e)
        return 2

    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=max(0, args.retention_days))
    logging.info("Retention days: %d | Cutoff (UTC): %s", args.retention_days, cutoff.strftime("%Y-%m-%d %H:%M:%S"))
    logging.info("Retrieved %d total recording(s)", len(recordings))

    candidates: List[Tuple[Dict[str, Any], Optional[dt.datetime]]] = []
    for rec in recordings:
        rtime = _parse_recording_time(rec)
        if not rtime:
            # If we cannot determine time, skip deletion for safety
            continue
        if rtime < cutoff and not _should_keep(rec, keep_ids, keep_substrings):
            candidates.append((rec, rtime))

    if not candidates:
        logging.info("No recordings older than retention (and not protected). Nothing to do.")
        return 0

    logging.info("Found %d candidate(s) for deletion:", len(candidates))
    for rec, rtime in candidates:
        rid = rec.get("id")
        rn = rec.get("room_name")
        dur = rec.get("duration")
        size = rec.get("size") or rec.get("size_bytes")
        logging.info("- id=%s | room=%s | start=%s | duration=%s | size=%s", rid, rn, (rtime.isoformat() if rtime else "?"), dur, size)

    if args.dry_run or not args.yes:
        logging.info("Dry-run mode or missing --yes. No deletions performed.")
        logging.info("To delete, run again with --yes (optionally remove --dry-run).")
        return 0

    # Perform deletions
    failures = 0
    for rec, rtime in candidates:
        rid = rec.get("id")
        ok, err = delete_recording(api_key, rid)
        if ok:
            logging.info("Deleted recording id=%s | room=%s", rid, rec.get("room_name"))
        else:
            failures += 1
            logging.error("Failed to delete id=%s: %s", rid, err)

    if failures:
        logging.warning("Completed with %d failure(s).", failures)
        return 1
    logging.info("Deletion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
