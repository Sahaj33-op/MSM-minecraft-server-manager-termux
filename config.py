# ============================================================================
# config.py - Manages config.json, database, and server settings
# ============================================================================
"""
Configuration management, credentials, and database operations.
"""

import os
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from environment import is_inside_proot
from utils import log


def get_config_root() -> Path:
    """Get config root path (Debian: /root/msm, Host: temp)."""
    if is_inside_proot():
        return Path("/root/msm")
    return Path(tempfile.gettempdir()) / "msm_temp"


def get_servers_root() -> Path:
    """Get servers storage root."""
    if is_inside_proot():
        return Path("/root/mc_servers")
    return Path.home() / "mc_servers_temp"


def get_credentials_file() -> Path:
    return get_config_root() / "credentials.json"


def get_log_file() -> Path:
    return get_config_root() / "msm.log"


def get_db_file() -> Path:
    return get_config_root() / "servers.db"


class ConfigManager:
    """Manages server configurations."""
    
    @staticmethod
    def load_server_config(server_name: str) -> Dict[str, Any]:
        """Load configuration for a specific server."""
        config_file = get_config_root() / "servers" / server_name / "config.json"
        
        if not config_file.exists():
            return {}
        
        try:
            with open(config_file, "r") as f:
                return json.load(f)
        except Exception as e:
            log(f"Failed to load config for {server_name}: {e}", "ERROR")
            return {}
    
    @staticmethod
    def save_server_config(server_name: str, config: Dict[str, Any]):
        """Save configuration for a specific server."""
        config_dir = get_config_root() / "servers" / server_name
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "config.json"
        
        try:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            log(f"Config saved for {server_name}")
        except Exception as e:
            log(f"Failed to save config for {server_name}: {e}", "ERROR")


class CredentialsManager:
    """Manages stored credentials."""
    
    @staticmethod
    def load() -> Dict[str, Any]:
        """Load credentials from file."""
        try:
            cred_file = get_credentials_file()
            if cred_file.exists():
                with open(cred_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            log(f"Failed to load credentials: {e}", "ERROR")
        return {}
    
    @staticmethod
    def save(credentials: Dict[str, Any]):
        """Save credentials with restricted permissions."""
        try:
            cred_file = get_credentials_file()
            cred_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cred_file, "w") as f:
                json.dump(credentials, f, indent=2)
            
            os.chmod(cred_file, 0o600)
            log("Credentials saved")
        except Exception as e:
            log(f"Failed to save credentials: {e}", "ERROR")
    
    @staticmethod
    def get(key: str) -> Optional[str]:
        """Get a specific credential."""
        return CredentialsManager.load().get(key)
    
    @staticmethod
    def set(key: str, value: str):
        """Set a specific credential."""
        creds = CredentialsManager.load()
        creds[key] = value
        CredentialsManager.save(creds)


class DatabaseManager:
    """Manages SQLite database for server statistics."""
    
    @staticmethod
    def init():
        """Initialize database with required tables."""
        try:
            db_file = get_db_file()
            db_file.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS servers (
                    name TEXT PRIMARY KEY,
                    created_at INTEGER,
                    last_started INTEGER,
                    total_uptime INTEGER DEFAULT 0,
                    crash_count INTEGER DEFAULT 0,
                    session_count INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_name TEXT,
                    start_time INTEGER,
                    end_time INTEGER,
                    duration INTEGER,
                    crash BOOLEAN,
                    FOREIGN KEY(server_name) REFERENCES servers(name)
                )
            """)
            
            conn.commit()
            conn.close()
            
            log("Database initialized")
        except Exception as e:
            log(f"Database init error: {e}", "ERROR")
    
    @staticmethod
    def add_server(name: str, created_at: int):
        """Add a server to database."""
        try:
            db_file = get_db_file()
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO servers (name, created_at) VALUES (?, ?)",
                (name, created_at)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            log(f"Failed to add server to DB: {e}", "ERROR")
