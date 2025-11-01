#!/usr/bin/env python3
"""
Unified Config Manager
- Bridges main (single-file) config with v1.1.0 style
- Stores JSON at ~/.config/msm/config.json
"""
import json, os, time
from pathlib import Path

CONFIG_DIR = Path(os.path.expanduser("~/.config/msm"))
CONFIG_FILE = CONFIG_DIR / "config.json"
SERVERS_ROOT = Path(os.path.expanduser("~"))

class ConfigManager:
    """Manager for handling configuration files and settings."""
    
    @staticmethod
    def load():
        """Load the main configuration file.
        
        Returns:
            Dictionary containing the configuration data
        """
        if not CONFIG_FILE.exists():
            return {"servers": {}, "current_server": None}
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            backup = CONFIG_FILE.with_suffix(f".bak_{int(time.time())}")
            try: CONFIG_FILE.replace(backup)
            except Exception: pass
            return {"servers": {}, "current_server": None}

    @staticmethod
    def save(cfg):
        """Save the configuration to the main configuration file.
        
        Args:
            cfg: Dictionary containing the configuration data to save
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

    @staticmethod
    def load_server_config(name: str):
        """Load configuration for a specific server.
        
        Args:
            name: Name of the server
            
        Returns:
            Dictionary containing the server configuration
        """
        cfg = ConfigManager.load()
        return cfg.get("servers", {}).get(name, {})

    @staticmethod
    def save_server_config(name: str, server_cfg: dict):
        """Save configuration for a specific server.
        
        Args:
            name: Name of the server
            server_cfg: Dictionary containing the server configuration to save
        """
        cfg = ConfigManager.load()
        cfg.setdefault("servers", {})[name] = server_cfg
        if cfg.get("current_server") is None:
            cfg["current_server"] = name
        ConfigManager.save(cfg)

    @staticmethod
    def get_current_server():
        """Get the name of the currently selected server.
        
        Returns:
            Name of the current server or None if no server is selected
        """
        return ConfigManager.load().get("current_server")

    @staticmethod
    def set_current_server(name: str):
        """Set the currently selected server.
        
        Args:
            name: Name of the server to set as current
        """
        cfg = ConfigManager.load()
        cfg["current_server"] = name
        ConfigManager.save(cfg)


def get_config_root() -> Path:
    """Get the configuration root directory path.
    
    Returns:
        Path object for the configuration root directory
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def get_servers_root() -> Path:
    """Get the servers root directory path.
    
    Returns:
        Path object for the servers root directory
    """
    return SERVERS_ROOT