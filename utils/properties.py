"""Helpers for Minecraft-style key=value property files."""

from __future__ import annotations

from pathlib import Path


def load_properties(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    properties: dict[str, str] = {}
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        properties[key.strip()] = value.strip()
    return properties


def write_properties(
    path: str | Path,
    properties: dict[str, object],
    header_comment: str | None = None,
) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    if header_comment:
        lines.append(f"# {header_comment}")
    for key, value in properties.items():
        lines.append(f"{key}={value}")
    file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
