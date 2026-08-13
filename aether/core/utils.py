"""Utility functions for hashing, headers, date formatting, and Range parsing."""

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, Tuple


def calculate_md5(data: bytes) -> str:
    """Return MD5 hex string for given bytes."""
    return hashlib.md5(data).hexdigest()


def calculate_sha256(data: bytes) -> str:
    """Return SHA256 hex string for given bytes."""
    return hashlib.sha256(data).hexdigest()


def format_s3_date(dt: Optional[datetime] = None) -> str:
    """Format datetime object as HTTP RFC 1123 date string (e.g. 'Tue, 11 Aug 2026 20:23:00 GMT')."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


def format_iso8601(dt: Optional[datetime] = None) -> str:
    """Format datetime object as ISO 8601 string (e.g. '2026-08-11T20:23:00.000Z')."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def parse_range_header(range_header: str, file_size: int) -> Tuple[Optional[int], Optional[int]]:
    """Parse HTTP Range header string (e.g. 'bytes=0-499' or 'bytes=500-') into (start, end).

    Args:
        range_header: Raw 'Range' HTTP header string.
        file_size: Total size of the target object in bytes.

    Returns:
        Tuple of (start_byte, end_byte) inclusive.
    """
    if not range_header or not range_header.startswith("bytes="):
        return None, None

    match = re.match(r"^bytes=(\d*)-(\d*)$", range_header.strip())
    if not match:
        return None, None

    start_str, end_str = match.groups()

    if start_str and end_str:
        start = int(start_str)
        end = int(end_str)
    elif start_str and not end_str:
        start = int(start_str)
        end = file_size - 1
    elif not start_str and end_str:
        # Suffix byte range, e.g. bytes=-500 (last 500 bytes)
        length = int(end_str)
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        return None, None

    if start >= file_size or start > end:
        return None, None

    end = min(end, file_size - 1)
    return start, end


def sanitize_filename(filename: str) -> str:
    """Sanitize path component to prevent path traversal attack vectors."""
    clean = filename.replace("\\", "/").strip("/")
    # Filter out empty paths or relative dots
    parts = [p for p in clean.split("/") if p and p != "." and p != ".."]
    return "/".join(parts)
