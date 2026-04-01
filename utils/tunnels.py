"""Tunnel log parsing helpers."""

from __future__ import annotations

import re
from pathlib import Path

PLAYIT_TUNNEL_ADDRESS_PATTERN = re.compile(
    r"tunnel_address=(?P<endpoint>[^\s,]+)",
    re.IGNORECASE,
)
PLAYIT_ENDPOINT_PATTERN = re.compile(
    (
        r"\b(?P<endpoint>"
        r"(?:[a-z0-9-]+\.)+(?:playit\.gg|ply\.gg)(?::\d+)?"
        r"|(?:\d{1,3}\.){3}\d{1,3}:\d+"
        r")\b"
    ),
    re.IGNORECASE,
)
PLAYIT_CLAIM_URL_PATTERN = re.compile(
    r"https?://[^\s]*playit\.gg[^\s]*claim[^\s]*",
    re.IGNORECASE,
)


def build_playit_claim_command(binary_path: str | Path) -> list[str]:
    return [str(binary_path), "--stdout", "claim"]


def build_playit_start_command(binary_path: str | Path) -> list[str]:
    return [str(binary_path), "--stdout", "start"]


def extract_playit_public_endpoint(log_text: str) -> str | None:
    for line in reversed(log_text.splitlines()):
        tunnel_match = PLAYIT_TUNNEL_ADDRESS_PATTERN.search(line)
        if tunnel_match:
            return tunnel_match.group("endpoint")
        endpoint_match = PLAYIT_ENDPOINT_PATTERN.search(line)
        if endpoint_match:
            return endpoint_match.group("endpoint")
    return None


def extract_playit_claim_url(log_text: str) -> str | None:
    for line in reversed(log_text.splitlines()):
        match = PLAYIT_CLAIM_URL_PATTERN.search(line)
        if match:
            return match.group(0)
    return None
