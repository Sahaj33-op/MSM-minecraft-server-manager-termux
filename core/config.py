#!/usr/bin/env python3
"""
Unified Config Manager
- Bridges main (single-file) config with v1.1.0 style
- Stores JSON at ~/.config/msm/config.json
- Includes schema validation and file locking
"""
import json
import os
import time
import tempfile
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from utils.helpers import get_config_dir, get_home_dir

# Handle platform-specific file locking
if sys.platform != 'win32':
    import fcntl
    HAS_FCNTL = True
else:
    HAS_FCNTL = False

CONFIG_DIR = get_config_dir()
CONFIG_FILE = CONFIG_DIR / "config.json"
SERVERS_ROOT = get_home_dir()

# Configuration schema for validation
CONFIG_SCHEMA = {
    "servers": dict,
    "current_server": (str, type(None)),
}

SERVER_SCHEMA = {
    "server_flavor": (str, type(None)),
    "server_version": (str, type(None)),
    "ram_mb": int,
    "auto_restart": bool,
    "eula_accepted": bool,
    "server_settings": dict,
}

SERVER_SETTINGS_SCHEMA = {
    "motd": str,
    "port": int,
    "max-players": int,
    "gamemode": str,
    "difficulty": str,
    "pvp": bool,
    "white-list": bool,
    "view-distance": int,
    "online-mode": bool,
}


class ConfigError(Exception):
    """Configuration-related errors."""
    pass


class ConfigManager:
    """Manager for handling configuration files and settings."""

    # Lock timeout in seconds
    LOCK_TIMEOUT = 10

    @staticmethod
    @contextmanager
    def _file_lock(file_path: Path, mode: str = 'r'):
        """Context manager for file locking to prevent corruption.

        Args:
            file_path: Path to the file to lock
            mode: File open mode ('r' for read, 'w' for write)

        Yields:
            File handle with exclusive lock
        """
        # Ensure directory exists for write mode
        if 'w' in mode:
            file_path.parent.mkdir(parents=True, exist_ok=True)

        # On Windows, use a simple approach without fcntl
        if not HAS_FCNTL:
            # Simple fallback for Windows - no file locking
            if 'w' not in mode and not file_path.exists():
                yield None
                return
            with open(file_path, mode, encoding='utf-8') as f:
                yield f
            return

        # Unix file locking using fcntl
        # Use a separate lock file to avoid issues with file truncation
        lock_file = file_path.with_suffix('.lock')

        try:
            # Create lock file if it doesn't exist
            lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)

            try:
                # Try to acquire lock with timeout
                start_time = time.time()
                while True:
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except (IOError, OSError):
                        if time.time() - start_time > ConfigManager.LOCK_TIMEOUT:
                            raise ConfigError(
                                f"Could not acquire lock on {file_path} after {ConfigManager.LOCK_TIMEOUT}s. "
                                "Another process may be using the file."
                            )
                        time.sleep(0.1)

                # Open the actual file
                if 'w' in mode or not file_path.exists():
                    if 'w' not in mode and not file_path.exists():
                        yield None
                        return
                    with open(file_path, mode, encoding='utf-8') as f:
                        yield f
                else:
                    with open(file_path, mode, encoding='utf-8') as f:
                        yield f

            finally:
                # Release lock
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                os.close(lock_fd)

        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"File operation failed: {e}") from e

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> List[str]:
        """Validate configuration against schema.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Validate top-level keys
        for key, expected_type in CONFIG_SCHEMA.items():
            if key in config:
                if isinstance(expected_type, tuple):
                    if not isinstance(config[key], expected_type):
                        errors.append(f"'{key}' must be one of types {expected_type}, got {type(config[key])}")
                elif not isinstance(config[key], expected_type):
                    errors.append(f"'{key}' must be {expected_type.__name__}, got {type(config[key]).__name__}")

        # Validate servers
        servers = config.get("servers", {})
        if isinstance(servers, dict):
            for server_name, server_config in servers.items():
                if not isinstance(server_config, dict):
                    errors.append(f"Server '{server_name}' config must be a dictionary")
                    continue

                # Validate server settings if present
                server_settings = server_config.get("server_settings", {})
                if server_settings and isinstance(server_settings, dict):
                    port = server_settings.get("port")
                    if port is not None and (not isinstance(port, int) or port < 1 or port > 65535):
                        errors.append(f"Server '{server_name}': port must be 1-65535")

                    max_players = server_settings.get("max-players")
                    if max_players is not None and (not isinstance(max_players, int) or max_players < 1):
                        errors.append(f"Server '{server_name}': max-players must be positive integer")

                # Validate RAM
                ram_mb = server_config.get("ram_mb")
                if ram_mb is not None and (not isinstance(ram_mb, int) or ram_mb < 256):
                    errors.append(f"Server '{server_name}': ram_mb must be at least 256 MB")

        return errors

    @staticmethod
    def load() -> Dict[str, Any]:
        """Load the main configuration file with locking and validation.

        Returns:
            Dictionary containing the configuration data
        """
        default_config = {"servers": {}, "current_server": None}

        if not CONFIG_FILE.exists():
            return default_config

        try:
            # Try to use file locking (Unix-like systems)
            try:
                with ConfigManager._file_lock(CONFIG_FILE, 'r') as f:
                    if f is None:
                        return default_config
                    content = f.read()
            except (AttributeError, ImportError, OSError):
                # Fallback for systems without fcntl (Windows)
                content = CONFIG_FILE.read_text(encoding='utf-8')

            if not content.strip():
                return default_config

            config = json.loads(content)

            # Validate configuration
            errors = ConfigManager._validate_config(config)
            if errors:
                # Log validation errors but don't fail
                import sys
                print(f"Config validation warnings: {errors}", file=sys.stderr)

            return config

        except json.JSONDecodeError as e:
            # Backup corrupted file
            backup = CONFIG_FILE.with_suffix(f".corrupted_{int(time.time())}")
            try:
                CONFIG_FILE.replace(backup)
            except Exception:
                pass
            return default_config

        except Exception:
            # Backup problematic file
            backup = CONFIG_FILE.with_suffix(f".bak_{int(time.time())}")
            try:
                CONFIG_FILE.replace(backup)
            except Exception:
                pass
            return default_config

    @staticmethod
    def save(cfg: Dict[str, Any]) -> None:
        """Save the configuration to the main configuration file with locking.

        Args:
            cfg: Dictionary containing the configuration data to save

        Raises:
            ConfigError: If save fails
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Validate before saving
        errors = ConfigManager._validate_config(cfg)
        if errors:
            import sys
            print(f"Config validation warnings before save: {errors}", file=sys.stderr)

        try:
            # Write to temp file first, then atomic rename
            temp_file = CONFIG_FILE.with_suffix('.tmp')

            try:
                with ConfigManager._file_lock(temp_file, 'w') as f:
                    json.dump(cfg, f, indent=2)
            except (AttributeError, ImportError, OSError):
                # Fallback for systems without fcntl
                temp_file.write_text(json.dumps(cfg, indent=2), encoding='utf-8')

            # Atomic rename
            temp_file.replace(CONFIG_FILE)

        except Exception as e:
            # Fallback: direct write
            try:
                CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
            except Exception as write_error:
                raise ConfigError(f"Failed to save config: {write_error}") from e

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