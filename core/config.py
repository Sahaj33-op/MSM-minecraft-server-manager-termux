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
    @staticmethod
    def load():
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
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

    @staticmethod
    def load_server_config(name: str):
        cfg = ConfigManager.load()
        return cfg.get("servers", {}).get(name, {})

    @staticmethod
    def save_server_config(name: str, server_cfg: dict):
        cfg = ConfigManager.load()
        cfg.setdefault("servers", {})[name] = server_cfg
        if cfg.get("current_server") is None:
            cfg["current_server"] = name
        ConfigManager.save(cfg)

    @staticmethod
    def get_current_server():
        return ConfigManager.load().get("current_server")

    @staticmethod
    def set_current_server(name: str):
        cfg = ConfigManager.load()
        cfg["current_server"] = name
        ConfigManager.save(cfg)


def get_config_root() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR

def get_servers_root() -> Path:
    return SERVERS_ROOT
