"""Lightweight data models for tunnel status and diagnostics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TunnelStatus:
    """Snapshot of a tunnel provider's current state."""

    provider: str
    state: str
    message: str
    endpoint: str | None = None
    claim_url: str | None = None
    pid: int | None = None


@dataclass
class TunnelCheck:
    """One item in a diagnostic checklist."""

    name: str
    ok: bool
    detail: str
