#!/usr/bin/env python3
"""
Server Manager (unified scaffold):
- Uses ConfigManager
- Leaves actual process handling to msm.py for now
"""
import os
from core.config import ConfigManager

class ServerManager:
    def list_servers(self):
        cfg = ConfigManager.load()
        return sorted(list(cfg.get('servers', {}).keys()))

    def get_current_server(self):
        return ConfigManager.get_current_server()

    def set_current_server(self, name: str):
        ConfigManager.set_current_server(name)

    # TODO: wire to msm.py start/stop during extraction
