#!/usr/bin/env python3
"""
Environment detection with optional proot (Debian) support.
- Default: native Termux (no proot required)
- Optional: ensure Debian via proot-distro when playit.gg chosen
"""
import os, shutil, subprocess

class EnvironmentManager:
    @staticmethod
    def is_termux():
        return 'com.termux' in (os.environ.get('PREFIX','')) or os.path.exists('/data/data/com.termux')

    @staticmethod
    def has_proot_distro():
        return shutil.which('proot-distro') is not None

    @staticmethod
    def ensure_debian_if_needed(reason: str = ""):
        """Only require Debian when a feature needs it (e.g., playit.gg)."""
        if reason != 'playit':
            return True
        if EnvironmentManager.in_debian():
            return True
        if not EnvironmentManager.has_proot_distro():
            print("proot-distro not found. Install with: pkg install proot-distro")
            return False
        print("Launching Debian (proot-distro) for playit.gg...")
        # Caller should re-exec inside debian environment.
        return True

    @staticmethod
    def in_debian():
        # naive heuristic: presence of /etc/debian_version
        return os.path.exists('/etc/debian_version')
