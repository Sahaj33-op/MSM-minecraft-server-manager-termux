#!/usr/bin/env python3
"""
Shared mixins for common component behavior.
"""


class LogMixin:
    """Provide a consistent instance-level logging fallback."""

    logger = None

    def _log(self, level: str, message: str, **kwargs):
        if self.logger:
            self.logger.log(level, message, **kwargs)
        else:
            print(f"[{level}] {message}")


class ClassLogMixin:
    """Provide a consistent class-level logging fallback."""

    logger = None

    @classmethod
    def _log(cls, message: str, level: str = "INFO", **kwargs):
        if cls.logger:
            cls.logger.log(level, message, **kwargs)
        else:
            print(f"[{level}] {message}")
