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
    (
        r"(?P<url>"
        r"https?://"
        r"(?:[a-z0-9-]+\.)*playit\.gg"
        r"/claim/"
        r"[A-Za-z0-9_-]+"
        r"/?"
        r")"
    ),
    re.IGNORECASE,
)


ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:\[[0-9;]*[a-zA-Z]|\(B|\)0|#\d|[=>]|7|8)")


def extract_last_non_empty_line(text: str) -> str | None:
    text = ANSI_ESCAPE_PATTERN.sub("", text)
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def get_playit_version(binary_path: str | Path) -> str | None:
    import subprocess

    version = None
    flags = ["--version", "-v", "version"]
    binary_name = Path(binary_path).name

    # First, try inferring from binary name for common cases
    if binary_name in ("playit-cli", "playitd"):
        return "1.0.0"
    if binary_name == "playit":
        # Last resort for Termux's default package
        return "1.0.0"

    # Try running version flags
    for flag in flags:
        try:
            result = subprocess.run(
                [str(binary_path), flag],
                capture_output=True,
                text=True,
                timeout=5,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            all_output = (result.stdout + "\n" + result.stderr).strip()
            if all_output:
                import re

                for line in all_output.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    # Look for any numeric version pattern
                    match = re.search(r"(\d+\.\d+\.\d+|\d+\.\d+)", line)
                    if match:
                        version = match.group(1)
                        break
            if version:
                break
        except Exception:
            continue

    # If we didn't get a version, check --help output for known flags
    if not version:
        try:
            help_result = subprocess.run(
                [str(binary_path), "--help"],
                capture_output=True,
                text=True,
                timeout=3,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            help_output = help_result.stdout + help_result.stderr
            if "--secret-path" in help_output:
                version = "1.0.0"
            elif "--secret_path" in help_output:
                version = "0.15.0"
            else:
                version = None
        except Exception:
            version = None

    return version


def build_playit_claim_generate_command(
    binary_path: str | Path, socket_path: str | Path | None = None
) -> list[str]:
    cmd = [str(binary_path)]
    binary_name = Path(binary_path).name
    if socket_path and binary_name in ("playit-cli", "playitd", "playit"):
        cmd.extend(["--socket-path", str(socket_path)])
    cmd.extend(["claim", "generate"])
    return cmd


def build_playit_claim_url_command(
    binary_path: str | Path, claim_code: str, socket_path: str | Path | None = None
) -> list[str]:
    cmd = [str(binary_path)]
    binary_name = Path(binary_path).name
    if socket_path and binary_name in ("playit-cli", "playitd", "playit"):
        cmd.extend(["--socket-path", str(socket_path)])
    cmd.extend(["claim", "url", claim_code])
    return cmd


def build_playit_claim_exchange_command(
    binary_path: str | Path,
    claim_code: str,
    secret_path: str | Path | None = None,
    socket_path: str | Path | None = None,
    playit_version: str | None = None,
) -> list[str]:
    command = [str(binary_path)]
    binary_name = Path(binary_path).name
    is_new_version = playit_version and playit_version.startswith("1.")

    if socket_path and binary_name in ("playit-cli", "playitd", "playit"):
        # For newer versions (v1.x) that use a daemon via socket: NO secret_path
        command.extend(["--socket-path", str(socket_path)])
    elif secret_path and not is_new_version:
        # For older v0.x versions or when version is unknown, use secret_path
        command.extend(["--secret_path", str(secret_path)])

    command.extend(["claim", "exchange", claim_code])
    return command


def build_playit_setup_command(
    binary_path: str | Path,
    socket_path: str | Path | None = None,
) -> list[str]:
    command = [str(binary_path)]
    binary_name = Path(binary_path).name
    if socket_path and binary_name in ("playit-cli", "playitd", "playit"):
        command.extend(["--socket-path", str(socket_path)])
    command.append("setup")
    return command


def build_playit_start_command(
    binary_path: str | Path,
    secret_path: str | Path | None = None,
    socket_path: str | Path | None = None,
    playit_version: str | None = None,
) -> list[str]:
    binary_name = Path(binary_path).name
    is_new_version = playit_version and playit_version.startswith("1.")

    if binary_name == "playitd":
        command = [str(binary_path)]
        if is_new_version:
            # Newer daemon versions use only socket_path
            if socket_path:
                command.extend(["--socket-path", str(socket_path)])
        else:
            # For older versions or when version is unknown
            if secret_path:
                command.extend(["--secret-path", str(secret_path)])
            if socket_path:
                command.extend(["--socket-path", str(socket_path)])
        return command

    command = [str(binary_path), "--stdout"]
    if is_new_version:
        # Newer versions use only socket_path
        if socket_path:
            command.extend(["--socket-path", str(socket_path)])
    else:
        # For older versions or when version is unknown
        if secret_path:
            command.extend(["--secret_path", str(secret_path)])
        if socket_path:
            command.extend(["--socket-path", str(socket_path)])
    command.append("start")
    return command


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
            return match.group("url")
    return None
