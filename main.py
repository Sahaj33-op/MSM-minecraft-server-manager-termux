#!/usr/bin/env python3
"""
Unified entrypoint (Phase 1): use modular managers when available
Falls back to msm.py monolith during extraction
"""
from core.logger import EnhancedLogger
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from core.config import ConfigManager
from managers.server_manager import ServerManager
from managers.tunnel_manager import TunnelManager

logger = EnhancedLogger
_db = DatabaseManager
_mon = PerformanceMonitor
_cfg = ConfigManager
_srv = ServerManager
_tun = TunnelManager

# For now, just expose main() from msm.py so we keep full functionality
from msm import main

if __name__ == "__main__":
    main()
