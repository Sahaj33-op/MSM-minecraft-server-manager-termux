#!/usr/bin/env python3

"""
Enhanced Minecraft Server Manager (MSM) v2.1 for Termux
Advanced Multi-Server, Multi-Flavor Manager with Enterprise Features

Supports: Paper, Purpur, Folia, Vanilla, PocketMine-MP, Fabric, Quilt
Features: Ngrok, Auto-restart, Backups, Monitoring, Java Auto-switching
"""

import os
import sys
import subprocess
import time
import requests
import json
import re
import hashlib
import psutil
import threading
import shlex
import uuid
import logging
import signal
import math
import shutil
import zipfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Tuple, Any

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================
VERSION = "5.2"
CONFIG_DIR = os.path.expanduser("~/.config/msm")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATABASE_FILE = os.path.join(CONFIG_DIR, "msm.db")
LOG_FILE = os.path.join(CONFIG_DIR, "msm.log")
VERSIONS_PER_PAGE = 15
JAVA_BASE_PATH = os.path.expanduser("~/../usr/lib/jvm")

# Enhanced timeout and retry configuration
REQUEST_TIMEOUT = (15, 45)  # (connect_timeout, read_timeout)
MAX_RETRIES = 5
RETRY_BACKOFF = 2
NGROK_TIMEOUT = 20
MAX_RAM_PERCENTAGE = 80
BACKUP_COMPRESSION_LEVEL = zipfile.ZIP_DEFLATED

# Performance monitoring
MONITOR_INTERVAL = 60  # seconds
MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB
LOG_RETENTION_DAYS = 30

# Security settings
MAX_FILENAME_LENGTH = 255
ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9_.-]+$')

# ============================================================================
# SERVER FLAVORS CONFIGURATION - ENHANCED
# ============================================================================
SERVER_FLAVORS = {
    "paper": {
        "name": "PaperMC",
        "description": "High-performance server with optimizations and plugin support",
        "api_base": "https://api.papermc.io/v2/projects/paper",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "paper-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ“‹",
        "min_ram": 512
    },
    "purpur": {
        "name": "Purpur",
        "description": "Paper fork with extensive configurability and extra features",
        "api_base": "https://api.purpurmc.org/v2/purpur",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "purpur-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ’œ",
        "min_ram": 512
    },
    "folia": {
        "name": "Folia",
        "description": "Regionized multi-threaded Paper fork for massive servers",
        "api_base": "https://api.papermc.io/v2/projects/folia",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "folia-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸŒ¿",
        "min_ram": 1024
    },
    "vanilla": {
        "name": "Vanilla Minecraft",
        "description": "Official unmodified Minecraft server from Mojang",
        "api_base": "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "server.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ¦",
        "min_ram": 512
    },
    "fabric": {
        "name": "Fabric",
        "description": "Lightweight modding platform with excellent performance",
        "api_base": "https://meta.fabricmc.net/v2/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "fabric-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ§µ",
        "min_ram": 768
    },
    "quilt": {
        "name": "Quilt",
        "description": "Modern Fabric fork with enhanced features and compatibility",
        "api_base": "https://meta.quiltmc.org/v3/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "quilt-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ§¶",
        "min_ram": 768
    },
    "pocketmine": {
        "name": "PocketMine-MP",
        "description": "High-performance Bedrock Edition server software",
        "api_base": "https://api.github.com/repos/pmmp/PocketMine-MP/releases",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "PocketMine-MP.phar",
        "default_port": 19132,
        "type": "php",
        "icon": "ðŸ“±",
        "min_ram": 256
    }
}

# ============================================================================
# COLOR SYSTEM - ENHANCED
# ============================================================================
class ColorScheme:
    """Enhanced color system with themes and accessibility"""
    # Base colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

    # Status colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    DEBUG = DIM

    @classmethod
    def disable_colors(cls):
        """Disable all colors for compatibility"""
        for attr in dir(cls):
            if not attr.startswith('_') and not callable(getattr(cls, attr)):
                setattr(cls, attr, '')

C = ColorScheme()

# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================
class DatabaseManager:
    """Enhanced database management for server statistics and history"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database with comprehensive schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS server_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, flavor TEXT NOT NULL,
                    version TEXT NOT NULL, start_time TIMESTAMP NOT NULL, end_time TIMESTAMP,
                    duration INTEGER, peak_players INTEGER DEFAULT 0, crash_count INTEGER DEFAULT 0,
                    restart_count INTEGER DEFAULT 0, ram_usage_avg REAL, cpu_usage_avg REAL
                );
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, timestamp TIMESTAMP NOT NULL,
                    ram_usage REAL NOT NULL, cpu_usage REAL NOT NULL, player_count INTEGER DEFAULT 0,
                    tps REAL DEFAULT 20.0, mspt REAL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, backup_path TEXT NOT NULL,
                    backup_size INTEGER NOT NULL, created_at TIMESTAMP NOT NULL, backup_type TEXT DEFAULT 'manual',
                    compressed_size INTEGER
                );
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT, error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL, stack_trace TEXT, timestamp TIMESTAMP NOT NULL,
                    severity TEXT DEFAULT 'ERROR'
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_server ON server_sessions(server_name);
                CREATE INDEX IF NOT EXISTS idx_metrics_server_time ON performance_metrics(server_name, timestamp);
                CREATE INDEX IF NOT EXISTS idx_backups_server ON backup_history(server_name);
                CREATE INDEX IF NOT EXISTS idx_errors_time ON error_log(timestamp);
            ''')

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def log_session_start(self, server_name: str, flavor: str, version: str) -> int:
        """Log server session start"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO server_sessions (server_name, flavor, version, start_time) VALUES (?, ?, ?, ?)",
                (server_name, flavor, version, datetime.now())
            )
            conn.commit()
            return cursor.lastrowid

    def log_session_end(self, session_id: int):
        """Log server session end with statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time FROM server_sessions WHERE id = ?", (session_id,))
            start_time_row = cursor.fetchone()
            if start_time_row:
                start_time_str = start_time_row[0]
                start_time = datetime.fromisoformat(start_time_str)
                duration = int((datetime.now() - start_time).total_seconds())

                cursor.execute(
                    "UPDATE server_sessions SET end_time = ?, duration = ? WHERE id = ?",
                    (datetime.now(), duration, session_id)
                )
                conn.commit()

    def log_performance_metric(self, server_name: str, ram_usage: float, cpu_usage: float, player_count: int = 0):
        """Log performance metrics"""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO performance_metrics (server_name, timestamp, ram_usage, cpu_usage, player_count) VALUES (?, ?, ?, ?, ?)",
                (server_name, datetime.now(), ram_usage, cpu_usage, player_count)
            )
            conn.commit()

    def get_server_statistics(self, server_name: str) -> Dict[str, Any]:
        """Get comprehensive server statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total_sessions, AVG(duration) as avg_duration, SUM(duration) as total_uptime, "
                "SUM(crash_count) as total_crashes, SUM(restart_count) as total_restarts "
                "FROM server_sessions WHERE server_name = ? AND end_time IS NOT NULL", (server_name,)
            )
            session_stats = cursor.fetchone()
            cursor.execute(
                "SELECT AVG(ram_usage), AVG(cpu_usage), MAX(player_count) FROM performance_metrics "
                "WHERE server_name = ? AND timestamp > datetime('now', '-24 hours')", (server_name,)
            )
            perf_stats = cursor.fetchone()
            return {
                'total_sessions': session_stats['total_sessions'] if session_stats else 0,
                'avg_duration': session_stats['avg_duration'] if session_stats else 0,
                'total_uptime': session_stats['total_uptime'] if session_stats else 0,
                'total_crashes': session_stats['total_crashes'] if session_stats else 0,
                'total_restarts': session_stats['total_restarts'] if session_stats else 0,
                'avg_ram_usage_24h': perf_stats[0] if perf_stats and perf_stats[0] else 0,
                'avg_cpu_usage_24h': perf_stats[1] if perf_stats and perf_stats[1] else 0,
                'peak_players_24h': perf_stats[2] if perf_stats and perf_stats[2] else 0
            }

# ============================================================================
# LOGGING SYSTEM - ENHANCED
# ============================================================================
class EnhancedLogger:
    """Enhanced logging system with rotation and structured logging"""
    def __init__(self, log_file: str, max_size: int = MAX_LOG_SIZE):
        self.log_file = log_file
        self.max_size = max_size
        self._setup_logging()

    def _setup_logging(self):
        """Setup comprehensive logging configuration"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._rotate_log_if_needed()
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[logging.FileHandler(self.log_file, encoding='utf-8')]
        )
        self.logger = logging.getLogger('MSM')

    def _rotate_log_if_needed(self):
        """Rotate log file if it exceeds max size"""
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_size:
                backup_file = f"{self.log_file}.{int(time.time())}"
                os.rename(self.log_file, backup_file)
                log_dir = os.path.dirname(self.log_file)
                cutoff_time = time.time() - (LOG_RETENTION_DAYS * 24 * 3600)
                for file in os.listdir(log_dir):
                    if file.startswith(Path(self.log_file).name + '.') and \
                       os.path.getctime(os.path.join(log_dir, file)) < cutoff_time:
                        os.remove(os.path.join(log_dir, file))
        except Exception:
            pass  # Fail silently for logging rotation

    def log(self, level: str, message: str, **kwargs):
        """Enhanced logging with structured data and console output"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color_map = {
            'DEBUG': C.DIM, 'INFO': C.BLUE, 'SUCCESS': C.GREEN,
            'WARNING': C.YELLOW, 'ERROR': C.RED, 'CRITICAL': C.BG_RED + C.WHITE
        }
        color = color_map.get(level.upper(), C.RESET)
        
        console_msg = f"{C.DIM}[{timestamp}]{C.RESET} {color}[{level:>7s}]{C.RESET} {message}"
        if kwargs:
            console_msg += f" {C.DIM}{kwargs}{C.RESET}"
        print(console_msg)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        extra_data = f" | {kwargs}" if kwargs else ""
        self.logger.log(log_level, f"{message}{extra_data}")

# ============================================================================
# GLOBAL INSTANCES & STATE
# ============================================================================
logger = EnhancedLogger(LOG_FILE)
db_manager = DatabaseManager(DATABASE_FILE)

# Global state
monitor_thread_stop_event = threading.Event()
auto_restart_stop_event = threading.Event()
current_session_id = None
server_process = None

# ============================================================================
# UTILITY FUNCTIONS - ENHANCED
# ============================================================================
def sanitize_input(value: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Enhanced input sanitization with length limits"""
    if not value or not isinstance(value, str):
        return str(uuid.uuid4())[:8]
    value = os.path.basename(value)
    if len(value) > max_length:
        value = value[:max_length]
    if not ALLOWED_FILENAME_CHARS.match(value):
        value = re.sub(r'[^a-zA-Z0-9_.-]', '_', value)
    value = re.sub(r'\.{2,}', '.', value).strip('.-')
    return value if value else str(uuid.uuid4())[:8]

def check_disk_space(path: str, required_mb: int = 1000) -> bool:
    """Enhanced disk space checking with detailed reporting"""
    try:
        stat = shutil.disk_usage(path)
        free_mb = stat.free // (1024 * 1024)
        if free_mb < required_mb:
            logger.log('ERROR', f"Insufficient disk space: {free_mb}MB free, {required_mb}MB required")
            return False
        return True
    except Exception as e:
        logger.log('ERROR', f"Failed to check disk space: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    """Enhanced system information gathering with fallbacks"""
    try:
        mem = psutil.virtual_memory()
        total_ram_mb = mem.total // (1024 * 1024)
        available_ram_mb = mem.available // (1024 * 1024)
        cpu_count = psutil.cpu_count(logical=True) or os.cpu_count() or 2
        cpu_usage = psutil.cpu_percent(interval=1)
        max_safe_ram_mb = min(
            int(total_ram_mb * MAX_RAM_PERCENTAGE / 100),
            available_ram_mb - 512 if available_ram_mb > 1024 else available_ram_mb - 256
        )
        return {
            'total_ram_mb': total_ram_mb, 'available_ram_mb': available_ram_mb,
            'max_safe_ram_mb': max(max_safe_ram_mb, 512), 'cpu_count': cpu_count,
            'cpu_usage': cpu_usage, 'platform': sys.platform
        }
    except Exception as e:
        logger.log('WARNING', f"Could not detect full system info: {e}")
        return {
            'total_ram_mb': 4096, 'available_ram_mb': 2048, 'max_safe_ram_mb': 3072,
            'cpu_count': 2, 'cpu_usage': 0.0, 'platform': 'unknown'
        }

def create_robust_session() -> requests.Session:
    """Create enhanced HTTP session with comprehensive retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES, status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=RETRY_BACKOFF, raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': f'MSM-Enhanced/{VERSION} (https://github.com/YourRepo/MSM)',
        'Accept': 'application/json'
    })
    return session

def run_command(command, check=True, capture_output=False, timeout=None, cwd=None) -> Optional[subprocess.CompletedProcess]:
    """Enhanced command execution with comprehensive error handling"""
    try:
        if isinstance(command, str):
            command = shlex.split(command)
        logger.log('DEBUG', f"Executing: {' '.join(command)} in {cwd or os.getcwd()}")
        result = subprocess.run(
            command, check=check, shell=False, capture_output=capture_output,
            text=True, timeout=timeout, cwd=cwd, env=os.environ.copy()
        )
        return result
    except subprocess.TimeoutExpired:
        logger.log('ERROR', f"Command timed out: {command}")
    except subprocess.CalledProcessError as e:
        logger.log('ERROR', f"Command failed (exit {e.returncode}): {command}")
        if e.stderr: logger.log('ERROR', f"stderr: {e.stderr.strip()}")
    except FileNotFoundError:
        logger.log('ERROR', f"Command not found: {command[0]}")
    except Exception as e:
        logger.log('CRITICAL', f"Unexpected error executing command: {e}")
    return None

def is_snapshot_version(version: str) -> bool:
    """Enhanced snapshot version detection"""
    snapshot_patterns = ['pre', 'rc', 'snapshot', 'alpha', 'beta', 'dev', r'\d+w\d+[a-z]']
    return any(re.search(p, version.lower()) for p in snapshot_patterns)

def safe_request(session: requests.Session, method: str, url: str, **kwargs) -> Optional[requests.Response]:
    """Enhanced HTTP request with detailed error handling"""
    try:
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        response = session.request(method, url, **kwargs)
        if 200 <= response.status_code < 300:
            return response
        logger.log('WARNING', f"HTTP {response.status_code} for {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.log('ERROR', f"Request failed for {url}: {e}")
        return None

# ============================================================================
# VERSION MANAGEMENT - ENHANCED
# ============================================================================
def get_versions_for_flavor(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    """Unified version fetcher for all server flavors."""
    fetcher_map = {
        "paper": get_paper_like_versions, "purpur": get_purpur_versions,
        "folia": get_paper_like_versions, "vanilla": get_vanilla_versions,
        "fabric": get_fabric_versions, "quilt": get_quilt_versions,
        "pocketmine": get_pocketmine_versions
    }
    if flavor in fetcher_map:
        return fetcher_map[flavor](flavor, include_snapshots)
    return {}

def get_paper_like_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    """Fetches versions for Paper and Folia."""
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', f"Fetching {flavor.capitalize()} versions...")
        proj_resp = safe_request(session, 'GET', api_base)
        if not proj_resp: return {}
        
        versions = proj_resp.json().get("versions", [])
        if not include_snapshots:
            versions = [v for v in versions if not is_snapshot_version(v)]

        version_info = {}
        for version in reversed(versions[-20:]): # Get latest 20 versions
            builds_resp = safe_request(session, 'GET', f"{api_base}/versions/{version}/builds")
            if builds_resp:
                builds = builds_resp.json().get("builds", [])
                if builds:
                    latest = builds[-1]
                    app = latest.get("downloads", {}).get("application", {})
                    version_info[version] = {
                        'latest_build': latest.get("build"),
                        'download_name': app.get("name"),
                        'sha256': app.get("sha256"),
                        'is_snapshot': is_snapshot_version(version)
                    }
        return version_info
    except Exception as e:
        logger.log('ERROR', f"Failed to fetch {flavor.capitalize()} versions: {e}")
        return {}
    finally:
        session.close()

def get_purpur_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Purpur versions...")
        proj_resp = safe_request(session, 'GET', api_base)
        if not proj_resp: return {}
        
        versions = proj_resp.json().get("versions", [])
        version_info = {}
        for version in reversed(versions[-20:]):
            build_resp = safe_request(session, 'GET', f"{api_base}/{version}")
            if build_resp:
                latest = build_resp.json().get("builds", {}).get("latest")
                if latest:
                    version_info[version] = {
                        'latest_build': latest,
                        'download_url': f"{api_base}/{version}/{latest}/download",
                        'is_snapshot': is_snapshot_version(version)
                    }
        return version_info
    finally:
        session.close()

def get_vanilla_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Vanilla versions...")
        resp = safe_request(session, 'GET', api_base)
        if not resp: return {}
        
        version_info = {}
        for v_data in resp.json().get("versions", []):
            version = v_data["id"]
            is_snap = v_data["type"] != "release"
            if include_snapshots or not is_snap:
                version_info[version] = {
                    'url': v_data["url"], 'is_snapshot': is_snap
                }
        return version_info
    finally:
        session.close()

def get_fabric_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Fabric versions...")
        game_resp = safe_request(session, 'GET', f"{api_base}/game")
        loader_resp = safe_request(session, 'GET', f"{api_base}/loader")
        installer_resp = safe_request(session, 'GET', f"{api_base}/installer")
        
        if not all([game_resp, loader_resp, installer_resp]): return {}
        
        latest_loader = loader_resp.json()[0]['version']
        latest_installer = installer_resp.json()[0]['version']
        
        version_info = {}
        for game in game_resp.json():
            version = game['version']
            is_snap = not game['stable']
            if include_snapshots or not is_snap:
                version_info[version] = {
                    'loader': latest_loader, 'installer': latest_installer, 'is_snapshot': is_snap
                }
        return version_info
    finally:
        session.close()

def get_quilt_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    # Quilt's API is similar to Fabric's
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Quilt versions...")
        game_resp = safe_request(session, 'GET', f"{api_base}/game")
        loader_resp = safe_request(session, 'GET', f"{api_base}/loader")
        
        if not all([game_resp, loader_resp]): return {}
        
        latest_loader = loader_resp.json()[0]['version']
        
        version_info = {}
        for game in game_resp.json():
            version = game['version']
            is_snap = 'snapshot' in version.lower() or 'pre' in version.lower()
            if include_snapshots or not is_snap:
                 version_info[version] = {'loader': latest_loader, 'is_snapshot': is_snap}
        return version_info
    finally:
        session.close()

def get_pocketmine_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching PocketMine versions...")
        resp = safe_request(session, 'GET', api_base)
        if not resp: return {}
        
        version_info = {}
        for release in resp.json():
            if release['draft']: continue
            is_snap = release['prerelease']
            if include_snapshots or not is_snap:
                for asset in release.get("assets", []):
                    if asset['name'].endswith(".phar"):
                        version_info[release['tag_name']] = {
                            'download_url': asset['browser_download_url'],
                            'filename': asset['name'], 'is_snapshot': is_snap
                        }
                        break
        return version_info
    finally:
        session.close()

# ============================================================================
# CORE APPLICATION LOGIC
# ============================================================================
def load_config() -> Dict[str, Any]:
    """Load configuration with multi-server support and defaults."""
    default_config = {"servers": {}, "current_server": None}
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Basic validation/migration
        if 'servers' not in config:
            return default_config
        return config
    except json.JSONDecodeError:
        logger.log('ERROR', f"Config file {CONFIG_FILE} is corrupted. Backing up and starting fresh.")
        shutil.move(CONFIG_FILE, f"{CONFIG_FILE}.bak_{int(time.time())}")
        return default_config

def save_config(config: Dict[str, Any]):
    """Save configuration with backup."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.log('ERROR', f"Failed to save config: {e}")

def get_server_dir(server_name: str) -> str:
    return os.path.expanduser(f"~/minecraft-{sanitize_input(server_name)}")

def get_screen_name(server_name: str) -> str:
    return f"mc_{sanitize_input(server_name)}"

def is_server_running(screen_name: str) -> bool:
    """Check if a screen session exists."""
    result = run_command(f"screen -ls {screen_name}", check=False, capture_output=True)
    return result is not None and screen_name in result.stdout

def get_required_java(version: str) -> str:
    """Determine required Java version based on Minecraft version."""
    if not version: return '17'
    match = re.match(r'1\.(\d+)', version)
    if not match: return '17' # Default for modern versions
    minor = int(match.group(1))
    if minor >= 21: return '21'
    if minor >= 17: return '17'
    return '8' # For 1.16 and below

def get_java_path(mc_version: str) -> Optional[str]:
    """Find the path to the required Java executable."""
    required_ver = get_required_java(mc_version)
    java_home = os.path.join(JAVA_BASE_PATH, f"openjdk-{required_ver}")
    java_exe = os.path.join(java_home, "bin", "java")
    if os.path.exists(java_exe):
        return java_exe
    
    # Fallback to checking PATH
    result = run_command(f"java -version", capture_output=True, check=False)
    if result and result.stderr:
        if f'version "{required_ver}' in result.stderr:
            return 'java'
    
    logger.log('ERROR', f"Java {required_ver} not found at {java_home}. Please install openjdk-{required_ver}.")
    return None

def check_dependencies():
    """Check for essential command-line tools."""
    logger.log('INFO', "Checking system dependencies...")
    deps = {'wget': False, 'screen': False, 'java': False, 'php': False}
    for dep in deps:
        if shutil.which(dep):
            deps[dep] = True
    
    missing = [d for d, found in deps.items() if not found]
    if missing:
        logger.log('WARNING', f"Missing dependencies: {', '.join(missing)}")
        if input("Attempt to install missing dependencies with 'pkg'? (y/N): ").lower() == 'y':
            run_command(f"pkg install {' '.join(missing)} -y")
            return all(shutil.which(d) for d in missing)
        return False
    logger.log('SUCCESS', "All essential dependencies are installed.")
    return True

def server_monitor_thread(server_name: str, pid: int, stop_event: threading.Event):
    """Monitors a running server process for performance metrics."""
    try:
        process = psutil.Process(pid)
        logger.log('INFO', f"Monitoring thread started for {server_name} (PID: {pid}).")
        while not stop_event.wait(MONITOR_INTERVAL):
            if process.is_running():
                with process.oneshot():
                    cpu = process.cpu_percent()
                    mem = process.memory_percent()
                    db_manager.log_performance_metric(server_name, mem, cpu)
            else:
                logger.log('WARNING', f"Monitoring target process (PID: {pid}) for {server_name} is no longer running.")
                break
    except psutil.NoSuchProcess:
        logger.log('WARNING', f"Monitoring failed: Process with PID {pid} for {server_name} not found.")
    except Exception as e:
        logger.log('ERROR', f"Error in monitoring thread for {server_name}: {e}")
    logger.log('INFO', f"Monitoring thread stopped for {server_name}.")

def auto_restart_monitor(server_name: str, command: List[str], cwd: str, stop_event: threading.Event):
    """Monitors server and restarts it on crash."""
    screen_name = get_screen_name(server_name)
    logger.log('INFO', f"Auto-restart enabled for {server_name}.")
    while not stop_event.wait(15): # Check every 15 seconds
        if not is_server_running(screen_name):
            logger.log('WARNING', f"Server {server_name} is down. Restarting in 5 seconds...")
            time.sleep(5)
            # Check again in case it was a manual stop
            if stop_event.is_set():
                break
            run_command(command, cwd=cwd)
    logger.log('INFO', f"Auto-restart disabled for {server_name}.")

def start_server():
    """Enhanced server startup with monitoring and auto-restart."""
    global current_session_id, monitor_thread_stop_event, auto_restart_stop_event
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    server_config = config['servers'][current_server]
    server_dir = get_server_dir(current_server)
    screen_name = get_screen_name(current_server)
    
    if is_server_running(screen_name):
        logger.log('WARNING', "Server is already running!"); return
        
    flavor = server_config.get('server_flavor')
    version = server_config.get('server_version')
    ram_mb = server_config.get('ram_mb', 1024)
    flavor_info = SERVER_FLAVORS.get(flavor, {})

    if not all([flavor, version, flavor_info]):
        logger.log('ERROR', "Server is not configured or installed. Please run install first."); return

    startup_command = []
    if flavor_info['type'] == 'java':
        java_path = get_java_path(version)
        if not java_path: return
        
        jar_file = "server.jar"
        if not os.path.exists(os.path.join(server_dir, jar_file)):
            # Fallback for fabric/quilt style installers
            potential_jars = [f for f in os.listdir(server_dir) if f.endswith(".jar")]
            if potential_jars:
                jar_file = potential_jars[0]
            else:
                 logger.log('ERROR', "No server JAR file found!"); return

        java_args = f"-Xmx{ram_mb}M -Xms{ram_mb}M -XX:+UseG1GC -jar"
        startup_command = [java_path] + shlex.split(java_args) + [jar_file, "nogui"]
    elif flavor_info['type'] == 'php':
        phar_files = [f for f in os.listdir(server_dir) if f.endswith('.phar')]
        if not phar_files:
            logger.log('ERROR', "PocketMine PHAR not found!"); return
        startup_command = ["php", phar_files[0]]
    
    if not startup_command:
        logger.log('ERROR', "Could not determine startup command."); return

    logger.log('INFO', f"Starting {flavor} server '{current_server}'...")
    screen_cmd = ["screen", "-dmS", screen_name] + startup_command
    
    if run_command(screen_cmd, cwd=server_dir):
        logger.log('SUCCESS', "Server process started in screen session.")
        current_session_id = db_manager.log_session_start(current_server, flavor, version)
        
        time.sleep(5) # Give server time to start and get a PID
        result = run_command(f"screen -ls {screen_name}", capture_output=True, check=False)
        if result and result.stdout:
            pid_match = re.search(r'(\d+)\.', result.stdout)
            if pid_match:
                pid = int(pid_match.group(1))
                monitor_thread_stop_event = threading.Event()
                monitor = threading.Thread(target=server_monitor_thread, args=(current_server, pid, monitor_thread_stop_event))
                monitor.daemon = True
                monitor.start()

        if server_config.get('auto_restart'):
            auto_restart_stop_event = threading.Event()
            auto_restarter = threading.Thread(target=auto_restart_monitor, args=(current_server, screen_cmd, server_dir, auto_restart_stop_event))
            auto_restarter.daemon = True
            auto_restarter.start()

    else:
        logger.log('ERROR', "Failed to start server in screen.")
    input("\nPress Enter to continue...")

def stop_server(force=False):
    """Stops the current server gracefully or forcefully."""
    global current_session_id
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    screen_name = get_screen_name(current_server)
    if not is_server_running(screen_name):
        logger.log('INFO', "Server is not running."); return
    
    # Signal monitoring threads to stop
    monitor_thread_stop_event.set()
    auto_restart_stop_event.set()
    
    if force:
        logger.log('WARNING', f"Forcefully stopping server {current_server}...")
        run_command(f"screen -S {screen_name} -X quit")
    else:
        logger.log('INFO', f"Stopping server {current_server} gracefully...")
        run_command(f"screen -S {screen_name} -p 0 -X stuff 'stop\n'")
        
        # Wait for shutdown
        for _ in range(20): # Wait up to 20 seconds
            if not is_server_running(screen_name):
                break
            time.sleep(1)
        else:
            logger.log('WARNING', "Server did not stop gracefully. Forcing shutdown.")
            run_command(f"screen -S {screen_name} -X quit")
            
    logger.log('SUCCESS', "Server stopped.")
    if current_session_id:
        db_manager.log_session_end(current_session_id)
        current_session_id = None
    input("\nPress Enter to continue...")

def install_server():
    """Complete server installation wizard."""
    config = load_config()
    current_server = config['current_server']
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    server_dir = get_server_dir(current_server)
    os.makedirs(server_dir, exist_ok=True)

    flavor = select_server_flavor()
    if not flavor: return

    selected_version, version_info = select_server_version(flavor)
    if not selected_version or not version_info: return

    # Download
    if download_server_jar(flavor, selected_version, version_info, server_dir):
        # EULA for Java
        if SERVER_FLAVORS[flavor]['type'] == 'java':
            with open(os.path.join(server_dir, 'eula.txt'), 'w') as f:
                f.write("eula=true\n")
            logger.log('SUCCESS', "EULA accepted.")

        # Update config
        config['servers'][current_server]['server_flavor'] = flavor
        config['servers'][current_server]['server_version'] = selected_version
        config['servers'][current_server]['server_settings']['port'] = SERVER_FLAVORS[flavor]['default_port']
        save_config(config)
        logger.log('SUCCESS', f"Installation of {flavor} {selected_version} complete!")
    else:
        logger.log('ERROR', "Installation failed during download.")
    input("\nPress Enter to continue...")
    
def download_server_jar(flavor, version, version_info, server_dir):
    """Download the selected server jar file."""
    if not check_disk_space(server_dir, 500): return False
    
    session = create_robust_session()
    download_url = None
    target_filename = "server.jar"
    
    try:
        if flavor in ["paper", "folia"]:
            build = version_info['latest_build']
            jar_name = version_info['download_name']
            api_base = SERVER_FLAVORS[flavor]['api_base']
            download_url = f"{api_base}/versions/{version}/builds/{build}/downloads/{jar_name}"
        elif flavor == "purpur":
            download_url = version_info['download_url']
        elif flavor == "vanilla":
            manifest_resp = safe_request(session, 'GET', version_info['url'])
            if manifest_resp:
                download_url = manifest_resp.json()['downloads']['server']['url']
        elif flavor == "fabric":
            loader, installer = version_info['loader'], version_info['installer']
            download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader}/{installer}/server/jar"
        elif flavor == "quilt":
            loader = version_info['loader']
            download_url = f"https://meta.quiltmc.org/v3/versions/loader/{version}/{loader}/0.0.0/server/jar" # Installer version seems unused for now
        elif flavor == "pocketmine":
            download_url = version_info['download_url']
            target_filename = version_info['filename']
        
        if not download_url:
            logger.log('ERROR', "Could not determine download URL.")
            return False
            
        target_path = os.path.join(server_dir, target_filename)
        logger.log('INFO', f"Downloading {flavor} {version} to {target_path}...")
        
        download_cmd = f"wget -O \"{target_path}\" \"{download_url}\" --progress=bar:force:noscroll"
        if run_command(download_cmd, cwd=server_dir, timeout=900):
            logger.log('SUCCESS', "Download complete.")
            return True
        else:
            logger.log('ERROR', "Download failed via wget.")
            return False

    except Exception as e:
        logger.log('ERROR', f"Download process failed: {e}")
        return False
    finally:
        session.close()

def select_server_flavor() -> Optional[str]:
    """Interactive menu to select a server flavor."""
    print_header()
    print(f"{C.BOLD}Select Server Flavor:{C.RESET}")
    flavors = list(SERVER_FLAVORS.keys())
    for i, key in enumerate(flavors, 1):
        flavor = SERVER_FLAVORS[key]
        print(f"  {C.BOLD}{i}.{C.RESET} {flavor['icon']} {flavor['name']} - {C.DIM}{flavor['description']}{C.RESET}")
    
    while True:
        try:
            choice = input(f"\n{C.BOLD}Choose flavor (1-{len(flavors)}): {C.RESET}").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(flavors):
                return flavors[idx]
        except (ValueError, IndexError):
            logger.log('ERROR', "Invalid selection.")

def select_server_version(flavor: str) -> Tuple[Optional[str], Optional[Dict]]:
    """Interactive version selection with pagination."""
    include_snapshots = False
    current_page = 1
    
    while True:
        versions_data = get_versions_for_flavor(flavor, include_snapshots)
        if not versions_data:
            logger.log('ERROR', f"Could not retrieve versions for {flavor}.")
            return None, None

        versions_list = list(versions_data.keys())
        if flavor != 'vanilla':
            versions_list.reverse() # Most APIs list oldest first
        
        total_pages = math.ceil(len(versions_list) / VERSIONS_PER_PAGE)
        start = (current_page - 1) * VERSIONS_PER_PAGE
        end = start + VERSIONS_PER_PAGE
        page_versions = versions_list[start:end]
        
        print_header()
        snap_status = "ON" if include_snapshots else "OFF"
        print(f"{C.BOLD}Select {SERVER_FLAVORS[flavor]['name']} Version (Page {current_page}/{total_pages}) | Snapshots: {snap_status}{C.RESET}\n")
        
        for i, version in enumerate(page_versions, 1):
            print(f" {C.BOLD}{i:2}.{C.RESET} {version}")
        
        print(f"\n{C.DIM}Commands: [p]rev, [n]ext, [s]napshots, [q]uit, or number to select{C.RESET}")
        choice = input(f"{C.BOLD}Selection: {C.RESET}").strip().lower()

        if choice in ['p', 'prev'] and current_page > 1: current_page -= 1
        elif choice in ['n', 'next'] and current_page < total_pages: current_page += 1
        elif choice in ['s', 'snap']: include_snapshots = not include_snapshots; current_page = 1
        elif choice in ['q', 'quit']: return None, None
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(page_versions):
                    selected_ver = page_versions[idx]
                    return selected_ver, versions_data[selected_ver]
            except ValueError:
                logger.log('ERROR', "Invalid input.")
                time.sleep(1)

def configure_server():
    """Interactive configuration wizard."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server: logger.log('ERROR', "No server selected."); return

    server_config = config['servers'][current_server]
    settings = server_config.get('server_settings', {})

    while True:
        print_header()
        print(f"{C.BOLD}Configure Server: {current_server}{C.RESET}")
        options = {
            "1": ("RAM Allocation", server_config.get('ram_mb', 1024), "MB"),
            "2": ("Port", settings.get('port', 25565), ""),
            "3": ("Auto Restart", "Yes" if server_config.get('auto_restart') else "No", "(Toggle)"),
            "4": ("MOTD", settings.get('motd', "A Minecraft Server"), ""),
            "5": ("Max Players", settings.get('max-players', 20), ""),
            "0": ("Back to Main Menu", "", "")
        }
        for k, (label, val, unit) in options.items():
            print(f" {C.BOLD}{k}.{C.RESET} {label}: {C.CYAN}{val}{C.RESET} {C.DIM}{unit}{C.RESET}")
        
        choice = input(f"\n{C.BOLD}Select option to change: {C.RESET}").strip()
        
        try:
            if choice == '1': server_config['ram_mb'] = int(input("Enter new RAM (MB): "))
            elif choice == '2': settings['port'] = int(input("Enter new port: "))
            elif choice == '3': server_config['auto_restart'] = not server_config.get('auto_restart')
            elif choice == '4': settings['motd'] = input("Enter new MOTD: ")
            elif choice == '5': settings['max-players'] = int(input("Enter max players: "))
            elif choice == '0': break
            else: logger.log('ERROR', "Invalid choice.")
        except ValueError:
            logger.log('ERROR', "Invalid input, please enter a number where required.")
        
        server_config['server_settings'] = settings
        save_config(config)

def world_manager():
    """Menu for managing server worlds, including backups and restores."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    server_dir = get_server_dir(current_server)
    backup_dir = os.path.join(server_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    while True:
        print_header()
        print(f"{C.BOLD}World Manager: {current_server}{C.RESET}")
        menu = {
            "1": "Create Backup",
            "2": "List Backups",
            "3": "Restore from Backup",
            "4": "Delete a Backup",
            "0": "Back to Main Menu"
        }
        for k, v in menu.items():
            print(f" {C.BOLD}{k}.{C.RESET} {v}")
        
        choice = input(f"\n{C.BOLD}Choose option: {C.RESET}").strip()

        if choice == '1':
            backup_name = f"world_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(backup_dir, backup_name)
            world_folders = [d for d in os.listdir(server_dir) if 'world' in d and os.path.isdir(os.path.join(server_dir, d))]
            
            if not world_folders:
                logger.log('ERROR', "No world folders found to back up.")
                time.sleep(2)
                continue
            
            logger.log('INFO', f"Creating backup: {backup_name}...")
            try:
                with zipfile.ZipFile(backup_path, 'w', BACKUP_COMPRESSION_LEVEL) as zf:
                    for folder in world_folders:
                        folder_path = os.path.join(server_dir, folder)
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                zf.write(os.path.join(root, file), 
                                         os.path.relpath(os.path.join(root, file), server_dir))
                logger.log('SUCCESS', f"Backup created successfully at {backup_path}")
            except Exception as e:
                logger.log('ERROR', f"Failed to create backup: {e}")
            input("\nPress Enter to continue...")

        elif choice == '2' or choice == '3' or choice == '4':
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.zip')], reverse=True)
            if not backups:
                logger.log('INFO', "No backups found.")
                time.sleep(2)
                continue

            print("\nAvailable Backups:")
            for i, backup in enumerate(backups, 1):
                print(f"  {C.BOLD}{i}.{C.RESET} {backup}")
            
            if choice == '2':
                input("\nPress Enter to continue...")
                continue
            
            try:
                idx_choice = int(input(f"\n{C.BOLD}Select a backup number: {C.RESET}")) - 1
                if not (0 <= idx_choice < len(backups)):
                    logger.log('ERROR', "Invalid selection.")
                    continue
                selected_backup = backups[idx_choice]
                backup_path = os.path.join(backup_dir, selected_backup)

                if choice == '3': # Restore
                    if input(f"{C.YELLOW}This will overwrite current world data. Are you sure? (y/N): {C.RESET}").lower() != 'y':
                        continue
                    
                    logger.log('INFO', f"Restoring from {selected_backup}...")
                    try:
                        with zipfile.ZipFile(backup_path, 'r') as zf:
                            zf.extractall(server_dir)
                        logger.log('SUCCESS', "Restore complete.")
                    except Exception as e:
                        logger.log('ERROR', f"Failed to restore: {e}")
                    input("\nPress Enter to continue...")

                elif choice == '4': # Delete
                    if input(f"{C.RED}Confirm deletion of '{selected_backup}' by typing 'DELETE': {C.RESET}") == 'DELETE':
                        os.remove(backup_path)
                        logger.log('SUCCESS', f"Deleted backup: {selected_backup}")
                    else:
                        logger.log('INFO', "Deletion cancelled.")
                    input("\nPress Enter to continue...")

            except ValueError:
                logger.log('ERROR', "Invalid input.")
        
        elif choice == '0':
            break

def show_statistics():
    """Displays server statistics from the database."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    stats = db_manager.get_server_statistics(current_server)
    
    def format_duration(seconds):
        if not seconds: return "N/A"
        seconds = int(seconds)
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        return f"{days}d {hours}h {minutes}m"

    print_header()
    print(f"{C.BOLD}Statistics for: {current_server}{C.RESET}")
    print(f"  - Total Sessions:    {C.CYAN}{stats.get('total_sessions', 'N/A')}{C.RESET}")
    print(f"  - Total Uptime:      {C.CYAN}{format_duration(stats.get('total_uptime'))}{C.RESET}")
    print(f"  - Average Session:   {C.CYAN}{format_duration(stats.get('avg_duration'))}{C.RESET}")
    print(f"  - Total Crashes:     {C.YELLOW}{stats.get('total_crashes', 'N/A')}{C.RESET}")
    print(f"  - Total Restarts:    {C.YELLOW}{stats.get('total_restarts', 'N/A')}{C.RESET}")
    print("\n  --- 24-Hour Performance ---")
    print(f"  - Avg RAM Usage:     {C.CYAN}{stats.get('avg_ram_usage_24h', 0):.2f}%{C.RESET}")
    print(f"  - Avg CPU Usage:     {C.CYAN}{stats.get('avg_cpu_usage_24h', 0):.2f}%{C.RESET}")
    print(f"  - Peak Players:      {C.CYAN}{stats.get('peak_players_24h', 'N/A')}{C.RESET}")
    
    input("\nPress Enter to continue...")

# ============================================================================
# UI & MAIN LOOP
# ============================================================================
def print_header():
    """Enhanced header with system information"""
    os.system('cls' if os.name == 'nt' else 'clear')
    system_info = get_system_info()
    ram_usage = f"{system_info['available_ram_mb']}MB/{system_info['total_ram_mb']}MB"
    cpu_info = f"{system_info['cpu_count']} cores @ {system_info['cpu_usage']:.1f}%"
    print(f"{C.BOLD}{C.CYAN}{'=' * 80}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':>25} Enhanced Minecraft Server Manager v{VERSION} {'':>25}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':>15} Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine {'':>15}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 80}{C.RESET}")
    print(f"{C.DIM}System: {ram_usage} RAM Free | {cpu_info} CPU | Platform: {system_info['platform']}{C.RESET}\n")

def show_console():
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    screen_name = get_screen_name(current_server)
    if is_server_running(screen_name):
        print(f"{C.CYAN}Attaching to console for '{current_server}'. Press Ctrl+A, then D to detach.{C.RESET}")
        time.sleep(2)
        os.system(f"screen -r {screen_name}")
    else:
        logger.log('ERROR', "Server is not running.")
        input("Press Enter to continue...")

def graceful_shutdown(signum, frame):
    """Handle signals for a clean exit."""
    logger.log('WARNING', "Shutdown signal received. Stopping server if running...")
    config = load_config()
    if config.get('current_server'):
        stop_server()
    logger.log('INFO', "MSM is shutting down.")
    sys.exit(0)
    
def main():
    """Main application loop."""
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    if not check_dependencies():
        sys.exit(1)

    while True:
        config = load_config()
        current_server = config.get('current_server')

        if not current_server and config.get('servers'):
            current_server = list(config['servers'].keys())[0]
            config['current_server'] = current_server
            save_config(config)
        elif not config.get('servers'):
            print_header()
            logger.log('INFO', "No servers found. Let's create your first one.")
            create_new_server()
            continue

        server_config = config['servers'][current_server]
        flavor = server_config.get('server_flavor', 'N/A')
        version = server_config.get('server_version', 'N/A')
        screen_name = get_screen_name(current_server)
        
        print_header()
        
        status = f"{C.GREEN}â—ONLINE{C.RESET}" if is_server_running(screen_name) else f"{C.RED}â—OFFLINE{C.RESET}"
        flavor_icon = SERVER_FLAVORS.get(flavor, {}).get('icon', 'â“')
        flavor_name = SERVER_FLAVORS.get(flavor, {}).get('name', 'Unknown')
        
        print(f"ðŸ“‹ Server: {C.CYAN}{current_server}{C.RESET} | Status: {status}")
        print(f"   {flavor_icon} {flavor_name} {version}")
        
        menu_options = [
            ("1", "ðŸš€", "Start Server"), ("2", "â¹ï¸", "Stop Server"), 
            ("3", "ðŸ“¦", "Install/Update Server"), ("4", "âš™ï¸", "Configure Server"),
            ("5", "ðŸ’»", "Server Console"), ("6", "ðŸ—„ï¸", "World Manager"),
            ("7", "ðŸ“Š", "Statistics"), ("8", "âž•", "Create New Server"),
            ("9", "ðŸ”„", "Switch Server"), ("0", "ðŸšª", "Exit")
        ]
        
        print(f"\n{C.BOLD}Main Menu:{C.RESET}")
        for key, icon, label in menu_options:
            print(f" {C.BOLD}{key}.{C.RESET} {icon} {label}")
        
        try:
            choice = input(f"\n{C.BOLD}Choose option: {C.RESET}").strip()
            
            if choice == '1': start_server()
            elif choice == '2': stop_server()
            elif choice == '3': install_server()
            elif choice == '4': configure_server()
            elif choice == '5': show_console()
            elif choice == '6': world_manager()
            elif choice == '7': show_statistics()
            elif choice == '8': create_new_server()
            elif choice == '9': select_current_server()
            elif choice == '0':
                if is_server_running(screen_name) and input(f"{C.YELLOW}Server is running. Stop it before exiting? (y/N): {C.RESET}").lower() == 'y':
                    stop_server()
                raise SystemExit
            else:
                logger.log('ERROR', "Invalid option.")
                time.sleep(1)

        except (KeyboardInterrupt, SystemExit):
            logger.log('INFO', "Exiting MSM. Goodbye!")
            sys.exit(0)
        except Exception as e:
            logger.log('CRITICAL', f"An unexpected error occurred in the main loop: {e}")
            time.sleep(3)

def create_new_server():
    """Wizard to create a new server configuration."""
    name = input(f"{C.BOLD}Enter new server name (e.g., 'survival' or 'creative'): {C.RESET}").strip()
    if not name:
        logger.log('ERROR', "Name cannot be empty."); return
    
    sanitized_name = sanitize_input(name)
    config = load_config()
    if sanitized_name in config['servers']:
        logger.log('ERROR', f"A server named '{sanitized_name}' already exists."); return
    
    config['servers'][sanitized_name] = {
        "server_flavor": None, "server_version": None, "ram_mb": 2048,
        "auto_restart": False, "server_settings": {
            "motd": f"{name} Server", "port": 25565, "max-players": 20
        }
    }
    config['current_server'] = sanitized_name
    save_config(config)
    os.makedirs(get_server_dir(sanitized_name), exist_ok=True)
    logger.log('SUCCESS', f"Created new server '{sanitized_name}'. Please use 'Install/Update' to set it up.")
    input("\nPress Enter to continue...")

def select_current_server():
    """Menu to switch between configured servers."""
    config = load_config()
    servers = list(config.get('servers', {}).keys())
    if not servers:
        logger.log('ERROR', "No servers configured."); return

    print_header()
    print(f"{C.BOLD}Select a Server to Manage:{C.RESET}")
    for i, name in enumerate(servers, 1):
        print(f"  {C.BOLD}{i}.{C.RESET} {name}")
    
    try:
        choice = int(input(f"\n{C.BOLD}Choose server: {C.RESET}")) - 1
        if 0 <= choice < len(servers):
            config['current_server'] = servers[choice]
            save_config(config)
            logger.log('SUCCESS', f"Switched to server '{servers[choice]}'.")
        else:
            logger.log('ERROR', "Invalid selection.")
    except ValueError:
        logger.log('ERROR', "Invalid input.")
    time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.log('CRITICAL', f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)#!/usr/bin/env python3

"""
Enhanced Minecraft Server Manager (MSM) v5.2 for Termux
Advanced Multi-Server, Multi-Flavor Manager with Enterprise Features

Supports: Paper, Purpur, Folia, Vanilla, PocketMine-MP, Fabric, Quilt
Features: Ngrok, Auto-restart, Backups, Monitoring, Java Auto-switching
"""

import os
import sys
import subprocess
import time
import requests
import json
import re
import hashlib
import psutil
import threading
import shlex
import uuid
import logging
import signal
import math
import shutil
import zipfile
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional, Tuple, Any

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================
VERSION = "5.2"
CONFIG_DIR = os.path.expanduser("~/.config/msm")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DATABASE_FILE = os.path.join(CONFIG_DIR, "msm.db")
LOG_FILE = os.path.join(CONFIG_DIR, "msm.log")
VERSIONS_PER_PAGE = 15
JAVA_BASE_PATH = os.path.expanduser("~/../usr/lib/jvm")

# Enhanced timeout and retry configuration
REQUEST_TIMEOUT = (15, 45)  # (connect_timeout, read_timeout)
MAX_RETRIES = 5
RETRY_BACKOFF = 2
NGROK_TIMEOUT = 20
MAX_RAM_PERCENTAGE = 80
BACKUP_COMPRESSION_LEVEL = zipfile.ZIP_DEFLATED

# Performance monitoring
MONITOR_INTERVAL = 60  # seconds
MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB
LOG_RETENTION_DAYS = 30

# Security settings
MAX_FILENAME_LENGTH = 255
ALLOWED_FILENAME_CHARS = re.compile(r'^[a-zA-Z0-9_.-]+$')

# ============================================================================
# SERVER FLAVORS CONFIGURATION - ENHANCED
# ============================================================================
SERVER_FLAVORS = {
    "paper": {
        "name": "PaperMC",
        "description": "High-performance server with optimizations and plugin support",
        "api_base": "https://api.papermc.io/v2/projects/paper",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "paper-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ“‹",
        "min_ram": 512
    },
    "purpur": {
        "name": "Purpur",
        "description": "Paper fork with extensive configurability and extra features",
        "api_base": "https://api.purpurmc.org/v2/purpur",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "purpur-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ’œ",
        "min_ram": 512
    },
    "folia": {
        "name": "Folia",
        "description": "Regionized multi-threaded Paper fork for massive servers",
        "api_base": "https://api.papermc.io/v2/projects/folia",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "folia-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸŒ¿",
        "min_ram": 1024
    },
    "vanilla": {
        "name": "Vanilla Minecraft",
        "description": "Official unmodified Minecraft server from Mojang",
        "api_base": "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "server.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ¦",
        "min_ram": 512
    },
    "fabric": {
        "name": "Fabric",
        "description": "Lightweight modding platform with excellent performance",
        "api_base": "https://meta.fabricmc.net/v2/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "fabric-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ§µ",
        "min_ram": 768
    },
    "quilt": {
        "name": "Quilt",
        "description": "Modern Fabric fork with enhanced features and compatibility",
        "api_base": "https://meta.quiltmc.org/v3/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "quilt-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "icon": "ðŸ§¶",
        "min_ram": 768
    },
    "pocketmine": {
        "name": "PocketMine-MP",
        "description": "High-performance Bedrock Edition server software",
        "api_base": "https://api.github.com/repos/pmmp/PocketMine-MP/releases",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "PocketMine-MP.phar",
        "default_port": 19132,
        "type": "php",
        "icon": "ðŸ“±",
        "min_ram": 256
    }
}

# ============================================================================
# COLOR SYSTEM - ENHANCED
# ============================================================================
class ColorScheme:
    """Enhanced color system with themes and accessibility"""
    # Base colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'

    # Standard colors
    BLACK = '\033[30m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'
    BG_BLUE = '\033[104m'

    # Status colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    DEBUG = DIM

    @classmethod
    def disable_colors(cls):
        """Disable all colors for compatibility"""
        for attr in dir(cls):
            if not attr.startswith('_') and not callable(getattr(cls, attr)):
                setattr(cls, attr, '')

C = ColorScheme()

# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================
class DatabaseManager:
    """Enhanced database management for server statistics and history"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database with comprehensive schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS server_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, flavor TEXT NOT NULL,
                    version TEXT NOT NULL, start_time TIMESTAMP NOT NULL, end_time TIMESTAMP,
                    duration INTEGER, peak_players INTEGER DEFAULT 0, crash_count INTEGER DEFAULT 0,
                    restart_count INTEGER DEFAULT 0, ram_usage_avg REAL, cpu_usage_avg REAL
                );
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, timestamp TIMESTAMP NOT NULL,
                    ram_usage REAL NOT NULL, cpu_usage REAL NOT NULL, player_count INTEGER DEFAULT 0,
                    tps REAL DEFAULT 20.0, mspt REAL DEFAULT 0.0
                );
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, backup_path TEXT NOT NULL,
                    backup_size INTEGER NOT NULL, created_at TIMESTAMP NOT NULL, backup_type TEXT DEFAULT 'manual',
                    compressed_size INTEGER
                );
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT, error_type TEXT NOT NULL,
                    error_message TEXT NOT NULL, stack_trace TEXT, timestamp TIMESTAMP NOT NULL,
                    severity TEXT DEFAULT 'ERROR'
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_server ON server_sessions(server_name);
                CREATE INDEX IF NOT EXISTS idx_metrics_server_time ON performance_metrics(server_name, timestamp);
                CREATE INDEX IF NOT EXISTS idx_backups_server ON backup_history(server_name);
                CREATE INDEX IF NOT EXISTS idx_errors_time ON error_log(timestamp);
            ''')

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

    def log_session_start(self, server_name: str, flavor: str, version: str) -> int:
        """Log server session start"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO server_sessions (server_name, flavor, version, start_time) VALUES (?, ?, ?, ?)",
                (server_name, flavor, version, datetime.now())
            )
            conn.commit()
            return cursor.lastrowid

    def log_session_end(self, session_id: int):
        """Log server session end with statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time FROM server_sessions WHERE id = ?", (session_id,))
            start_time_row = cursor.fetchone()
            if start_time_row:
                start_time_str = start_time_row[0]
                start_time = datetime.fromisoformat(start_time_str)
                duration = int((datetime.now() - start_time).total_seconds())

                cursor.execute(
                    "UPDATE server_sessions SET end_time = ?, duration = ? WHERE id = ?",
                    (datetime.now(), duration, session_id)
                )
                conn.commit()

    def log_performance_metric(self, server_name: str, ram_usage: float, cpu_usage: float, player_count: int = 0):
        """Log performance metrics"""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO performance_metrics (server_name, timestamp, ram_usage, cpu_usage, player_count) VALUES (?, ?, ?, ?, ?)",
                (server_name, datetime.now(), ram_usage, cpu_usage, player_count)
            )
            conn.commit()

    def get_server_statistics(self, server_name: str) -> Dict[str, Any]:
        """Get comprehensive server statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total_sessions, AVG(duration) as avg_duration, SUM(duration) as total_uptime, "
                "SUM(crash_count) as total_crashes, SUM(restart_count) as total_restarts "
                "FROM server_sessions WHERE server_name = ? AND end_time IS NOT NULL", (server_name,)
            )
            session_stats = cursor.fetchone()
            cursor.execute(
                "SELECT AVG(ram_usage), AVG(cpu_usage), MAX(player_count) FROM performance_metrics "
                "WHERE server_name = ? AND timestamp > datetime('now', '-24 hours')", (server_name,)
            )
            perf_stats = cursor.fetchone()
            return {
                'total_sessions': session_stats['total_sessions'] if session_stats else 0,
                'avg_duration': session_stats['avg_duration'] if session_stats else 0,
                'total_uptime': session_stats['total_uptime'] if session_stats else 0,
                'total_crashes': session_stats['total_crashes'] if session_stats else 0,
                'total_restarts': session_stats['total_restarts'] if session_stats else 0,
                'avg_ram_usage_24h': perf_stats[0] if perf_stats and perf_stats[0] else 0,
                'avg_cpu_usage_24h': perf_stats[1] if perf_stats and perf_stats[1] else 0,
                'peak_players_24h': perf_stats[2] if perf_stats and perf_stats[2] else 0
            }

# ============================================================================
# LOGGING SYSTEM - ENHANCED
# ============================================================================
class EnhancedLogger:
    """Enhanced logging system with rotation and structured logging"""
    def __init__(self, log_file: str, max_size: int = MAX_LOG_SIZE):
        self.log_file = log_file
        self.max_size = max_size
        self._setup_logging()

    def _setup_logging(self):
        """Setup comprehensive logging configuration"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._rotate_log_if_needed()
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[logging.FileHandler(self.log_file, encoding='utf-8')]
        )
        self.logger = logging.getLogger('MSM')

    def _rotate_log_if_needed(self):
        """Rotate log file if it exceeds max size"""
        try:
            if os.path.exists(self.log_file) and os.path.getsize(self.log_file) > self.max_size:
                backup_file = f"{self.log_file}.{int(time.time())}"
                os.rename(self.log_file, backup_file)
                log_dir = os.path.dirname(self.log_file)
                cutoff_time = time.time() - (LOG_RETENTION_DAYS * 24 * 3600)
                for file in os.listdir(log_dir):
                    if file.startswith(Path(self.log_file).name + '.') and \
                       os.path.getctime(os.path.join(log_dir, file)) < cutoff_time:
                        os.remove(os.path.join(log_dir, file))
        except Exception:
            pass  # Fail silently for logging rotation

    def log(self, level: str, message: str, **kwargs):
        """Enhanced logging with structured data and console output"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color_map = {
            'DEBUG': C.DIM, 'INFO': C.BLUE, 'SUCCESS': C.GREEN,
            'WARNING': C.YELLOW, 'ERROR': C.RED, 'CRITICAL': C.BG_RED + C.WHITE
        }
        color = color_map.get(level.upper(), C.RESET)
        
        console_msg = f"{C.DIM}[{timestamp}]{C.RESET} {color}[{level:>7s}]{C.RESET} {message}"
        if kwargs:
            console_msg += f" {C.DIM}{kwargs}{C.RESET}"
        print(console_msg)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        extra_data = f" | {kwargs}" if kwargs else ""
        self.logger.log(log_level, f"{message}{extra_data}")

# ============================================================================
# GLOBAL INSTANCES & STATE
# ============================================================================
logger = EnhancedLogger(LOG_FILE)
db_manager = DatabaseManager(DATABASE_FILE)

# Global state
monitor_thread_stop_event = threading.Event()
auto_restart_stop_event = threading.Event()
current_session_id = None
server_process = None

# ============================================================================
# UTILITY FUNCTIONS - ENHANCED
# ============================================================================
def sanitize_input(value: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """Enhanced input sanitization with length limits"""
    if not value or not isinstance(value, str):
        return str(uuid.uuid4())[:8]
    value = os.path.basename(value)
    if len(value) > max_length:
        value = value[:max_length]
    if not ALLOWED_FILENAME_CHARS.match(value):
        value = re.sub(r'[^a-zA-Z0-9_.-]', '_', value)
    value = re.sub(r'\.{2,}', '.', value).strip('.-')
    return value if value else str(uuid.uuid4())[:8]

def check_disk_space(path: str, required_mb: int = 1000) -> bool:
    """Enhanced disk space checking with detailed reporting"""
    try:
        stat = shutil.disk_usage(path)
        free_mb = stat.free // (1024 * 1024)
        if free_mb < required_mb:
            logger.log('ERROR', f"Insufficient disk space: {free_mb}MB free, {required_mb}MB required")
            return False
        return True
    except Exception as e:
        logger.log('ERROR', f"Failed to check disk space: {e}")
        return False

def get_system_info() -> Dict[str, Any]:
    """Enhanced system information gathering with fallbacks"""
    try:
        mem = psutil.virtual_memory()
        total_ram_mb = mem.total // (1024 * 1024)
        available_ram_mb = mem.available // (1024 * 1024)
        cpu_count = psutil.cpu_count(logical=True) or os.cpu_count() or 2
        cpu_usage = psutil.cpu_percent(interval=1)
        max_safe_ram_mb = min(
            int(total_ram_mb * MAX_RAM_PERCENTAGE / 100),
            available_ram_mb - 512 if available_ram_mb > 1024 else available_ram_mb - 256
        )
        return {
            'total_ram_mb': total_ram_mb, 'available_ram_mb': available_ram_mb,
            'max_safe_ram_mb': max(max_safe_ram_mb, 512), 'cpu_count': cpu_count,
            'cpu_usage': cpu_usage, 'platform': sys.platform
        }
    except Exception as e:
        logger.log('WARNING', f"Could not detect full system info: {e}")
        return {
            'total_ram_mb': 4096, 'available_ram_mb': 2048, 'max_safe_ram_mb': 3072,
            'cpu_count': 2, 'cpu_usage': 0.0, 'platform': 'unknown'
        }

def create_robust_session() -> requests.Session:
    """Create enhanced HTTP session with comprehensive retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=MAX_RETRIES, status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=RETRY_BACKOFF, raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': f'MSM-Enhanced/{VERSION} (https://github.com/YourRepo/MSM)',
        'Accept': 'application/json'
    })
    return session

def run_command(command, check=True, capture_output=False, timeout=None, cwd=None) -> Optional[subprocess.CompletedProcess]:
    """Enhanced command execution with comprehensive error handling"""
    try:
        if isinstance(command, str):
            command = shlex.split(command)
        logger.log('DEBUG', f"Executing: {' '.join(command)} in {cwd or os.getcwd()}")
        result = subprocess.run(
            command, check=check, shell=False, capture_output=capture_output,
            text=True, timeout=timeout, cwd=cwd, env=os.environ.copy()
        )
        return result
    except subprocess.TimeoutExpired:
        logger.log('ERROR', f"Command timed out: {command}")
    except subprocess.CalledProcessError as e:
        logger.log('ERROR', f"Command failed (exit {e.returncode}): {command}")
        if e.stderr: logger.log('ERROR', f"stderr: {e.stderr.strip()}")
    except FileNotFoundError:
        logger.log('ERROR', f"Command not found: {command[0]}")
    except Exception as e:
        logger.log('CRITICAL', f"Unexpected error executing command: {e}")
    return None

def is_snapshot_version(version: str) -> bool:
    """Enhanced snapshot version detection"""
    snapshot_patterns = ['pre', 'rc', 'snapshot', 'alpha', 'beta', 'dev', r'\d+w\d+[a-z]']
    return any(re.search(p, version.lower()) for p in snapshot_patterns)

def safe_request(session: requests.Session, method: str, url: str, **kwargs) -> Optional[requests.Response]:
    """Enhanced HTTP request with detailed error handling"""
    try:
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        response = session.request(method, url, **kwargs)
        if 200 <= response.status_code < 300:
            return response
        logger.log('WARNING', f"HTTP {response.status_code} for {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.log('ERROR', f"Request failed for {url}: {e}")
        return None

# ============================================================================
# VERSION MANAGEMENT - ENHANCED
# ============================================================================
def get_versions_for_flavor(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    """Unified version fetcher for all server flavors."""
    fetcher_map = {
        "paper": get_paper_like_versions, "purpur": get_purpur_versions,
        "folia": get_paper_like_versions, "vanilla": get_vanilla_versions,
        "fabric": get_fabric_versions, "quilt": get_quilt_versions,
        "pocketmine": get_pocketmine_versions
    }
    if flavor in fetcher_map:
        return fetcher_map[flavor](flavor, include_snapshots)
    return {}

def get_paper_like_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    """Fetches versions for Paper and Folia."""
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', f"Fetching {flavor.capitalize()} versions...")
        proj_resp = safe_request(session, 'GET', api_base)
        if not proj_resp: return {}
        
        versions = proj_resp.json().get("versions", [])
        if not include_snapshots:
            versions = [v for v in versions if not is_snapshot_version(v)]

        version_info = {}
        for version in reversed(versions[-20:]): # Get latest 20 versions
            builds_resp = safe_request(session, 'GET', f"{api_base}/versions/{version}/builds")
            if builds_resp:
                builds = builds_resp.json().get("builds", [])
                if builds:
                    latest = builds[-1]
                    app = latest.get("downloads", {}).get("application", {})
                    version_info[version] = {
                        'latest_build': latest.get("build"),
                        'download_name': app.get("name"),
                        'sha256': app.get("sha256"),
                        'is_snapshot': is_snapshot_version(version)
                    }
        return version_info
    except Exception as e:
        logger.log('ERROR', f"Failed to fetch {flavor.capitalize()} versions: {e}")
        return {}
    finally:
        session.close()

def get_purpur_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Purpur versions...")
        proj_resp = safe_request(session, 'GET', api_base)
        if not proj_resp: return {}
        
        versions = proj_resp.json().get("versions", [])
        version_info = {}
        for version in reversed(versions[-20:]):
            build_resp = safe_request(session, 'GET', f"{api_base}/{version}")
            if build_resp:
                latest = build_resp.json().get("builds", {}).get("latest")
                if latest:
                    version_info[version] = {
                        'latest_build': latest,
                        'download_url': f"{api_base}/{version}/{latest}/download",
                        'is_snapshot': is_snapshot_version(version)
                    }
        return version_info
    finally:
        session.close()

def get_vanilla_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Vanilla versions...")
        resp = safe_request(session, 'GET', api_base)
        if not resp: return {}
        
        version_info = {}
        for v_data in resp.json().get("versions", []):
            version = v_data["id"]
            is_snap = v_data["type"] != "release"
            if include_snapshots or not is_snap:
                version_info[version] = {
                    'url': v_data["url"], 'is_snapshot': is_snap
                }
        return version_info
    finally:
        session.close()

def get_fabric_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Fabric versions...")
        game_resp = safe_request(session, 'GET', f"{api_base}/game")
        loader_resp = safe_request(session, 'GET', f"{api_base}/loader")
        installer_resp = safe_request(session, 'GET', f"{api_base}/installer")
        
        if not all([game_resp, loader_resp, installer_resp]): return {}
        
        latest_loader = loader_resp.json()[0]['version']
        latest_installer = installer_resp.json()[0]['version']
        
        version_info = {}
        for game in game_resp.json():
            version = game['version']
            is_snap = not game['stable']
            if include_snapshots or not is_snap:
                version_info[version] = {
                    'loader': latest_loader, 'installer': latest_installer, 'is_snapshot': is_snap
                }
        return version_info
    finally:
        session.close()

def get_quilt_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    # Quilt's API is similar to Fabric's
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching Quilt versions...")
        game_resp = safe_request(session, 'GET', f"{api_base}/game")
        loader_resp = safe_request(session, 'GET', f"{api_base}/loader")
        
        if not all([game_resp, loader_resp]): return {}
        
        latest_loader = loader_resp.json()[0]['version']
        
        version_info = {}
        for game in game_resp.json():
            version = game['version']
            is_snap = 'snapshot' in version.lower() or 'pre' in version.lower()
            if include_snapshots or not is_snap:
                 version_info[version] = {'loader': latest_loader, 'is_snapshot': is_snap}
        return version_info
    finally:
        session.close()

def get_pocketmine_versions(flavor: str, include_snapshots=False) -> Dict[str, Any]:
    api_base = SERVER_FLAVORS[flavor]['api_base']
    session = create_robust_session()
    try:
        logger.log('INFO', "Fetching PocketMine versions...")
        resp = safe_request(session, 'GET', api_base)
        if not resp: return {}
        
        version_info = {}
        for release in resp.json():
            if release['draft']: continue
            is_snap = release['prerelease']
            if include_snapshots or not is_snap:
                for asset in release.get("assets", []):
                    if asset['name'].endswith(".phar"):
                        version_info[release['tag_name']] = {
                            'download_url': asset['browser_download_url'],
                            'filename': asset['name'], 'is_snapshot': is_snap
                        }
                        break
        return version_info
    finally:
        session.close()

# ============================================================================
# CORE APPLICATION LOGIC
# ============================================================================
def load_config() -> Dict[str, Any]:
    """Load configuration with multi-server support and defaults."""
    default_config = {"servers": {}, "current_server": None}
    if not os.path.exists(CONFIG_FILE):
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Basic validation/migration
        if 'servers' not in config:
            return default_config
        return config
    except json.JSONDecodeError:
        logger.log('ERROR', f"Config file {CONFIG_FILE} is corrupted. Backing up and starting fresh.")
        shutil.move(CONFIG_FILE, f"{CONFIG_FILE}.bak_{int(time.time())}")
        return default_config

def save_config(config: Dict[str, Any]):
    """Save configuration with backup."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.log('ERROR', f"Failed to save config: {e}")

def get_server_dir(server_name: str) -> str:
    return os.path.expanduser(f"~/minecraft-{sanitize_input(server_name)}")

def get_screen_name(server_name: str) -> str:
    return f"mc_{sanitize_input(server_name)}"

def is_server_running(screen_name: str) -> bool:
    """Check if a screen session exists."""
    result = run_command(f"screen -ls {screen_name}", check=False, capture_output=True)
    return result is not None and screen_name in result.stdout

def get_required_java(version: str) -> str:
    """Determine required Java version based on Minecraft version."""
    if not version: return '17'
    match = re.match(r'1\.(\d+)', version)
    if not match: return '17' # Default for modern versions
    minor = int(match.group(1))
    if minor >= 21: return '21'
    if minor >= 17: return '17'
    return '8' # For 1.16 and below

def get_java_path(mc_version: str) -> Optional[str]:
    """Find the path to the required Java executable."""
    required_ver = get_required_java(mc_version)
    java_home = os.path.join(JAVA_BASE_PATH, f"openjdk-{required_ver}")
    java_exe = os.path.join(java_home, "bin", "java")
    if os.path.exists(java_exe):
        return java_exe
    
    # Fallback to checking PATH
    result = run_command(f"java -version", capture_output=True, check=False)
    if result and result.stderr:
        if f'version "{required_ver}' in result.stderr:
            return 'java'
    
    logger.log('ERROR', f"Java {required_ver} not found at {java_home}. Please install openjdk-{required_ver}.")
    return None

def check_dependencies():
    """Check for essential command-line tools."""
    logger.log('INFO', "Checking system dependencies...")
    deps = {'wget': False, 'screen': False, 'java': False, 'php': False}
    for dep in deps:
        if shutil.which(dep):
            deps[dep] = True
    
    missing = [d for d, found in deps.items() if not found]
    if missing:
        logger.log('WARNING', f"Missing dependencies: {', '.join(missing)}")
        if input("Attempt to install missing dependencies with 'pkg'? (y/N): ").lower() == 'y':
            run_command(f"pkg install {' '.join(missing)} -y")
            return all(shutil.which(d) for d in missing)
        return False
    logger.log('SUCCESS', "All essential dependencies are installed.")
    return True

def server_monitor_thread(server_name: str, pid: int, stop_event: threading.Event):
    """Monitors a running server process for performance metrics."""
    try:
        process = psutil.Process(pid)
        logger.log('INFO', f"Monitoring thread started for {server_name} (PID: {pid}).")
        while not stop_event.wait(MONITOR_INTERVAL):
            if process.is_running():
                with process.oneshot():
                    cpu = process.cpu_percent()
                    mem = process.memory_percent()
                    db_manager.log_performance_metric(server_name, mem, cpu)
            else:
                logger.log('WARNING', f"Monitoring target process (PID: {pid}) for {server_name} is no longer running.")
                break
    except psutil.NoSuchProcess:
        logger.log('WARNING', f"Monitoring failed: Process with PID {pid} for {server_name} not found.")
    except Exception as e:
        logger.log('ERROR', f"Error in monitoring thread for {server_name}: {e}")
    logger.log('INFO', f"Monitoring thread stopped for {server_name}.")

def auto_restart_monitor(server_name: str, command: List[str], cwd: str, stop_event: threading.Event):
    """Monitors server and restarts it on crash."""
    screen_name = get_screen_name(server_name)
    logger.log('INFO', f"Auto-restart enabled for {server_name}.")
    while not stop_event.wait(15): # Check every 15 seconds
        if not is_server_running(screen_name):
            logger.log('WARNING', f"Server {server_name} is down. Restarting in 5 seconds...")
            time.sleep(5)
            # Check again in case it was a manual stop
            if stop_event.is_set():
                break
            run_command(command, cwd=cwd)
    logger.log('INFO', f"Auto-restart disabled for {server_name}.")

def start_server():
    """Enhanced server startup with monitoring and auto-restart."""
    global current_session_id, monitor_thread_stop_event, auto_restart_stop_event
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    server_config = config['servers'][current_server]
    server_dir = get_server_dir(current_server)
    screen_name = get_screen_name(current_server)
    
    if is_server_running(screen_name):
        logger.log('WARNING', "Server is already running!"); return
        
    flavor = server_config.get('server_flavor')
    version = server_config.get('server_version')
    ram_mb = server_config.get('ram_mb', 1024)
    flavor_info = SERVER_FLAVORS.get(flavor, {})

    if not all([flavor, version, flavor_info]):
        logger.log('ERROR', "Server is not configured or installed. Please run install first."); return

    startup_command = []
    if flavor_info['type'] == 'java':
        java_path = get_java_path(version)
        if not java_path: return
        
        jar_file = "server.jar"
        if not os.path.exists(os.path.join(server_dir, jar_file)):
            # Fallback for fabric/quilt style installers
            potential_jars = [f for f in os.listdir(server_dir) if f.endswith(".jar")]
            if potential_jars:
                jar_file = potential_jars[0]
            else:
                 logger.log('ERROR', "No server JAR file found!"); return

        java_args = f"-Xmx{ram_mb}M -Xms{ram_mb}M -XX:+UseG1GC -jar"
        startup_command = [java_path] + shlex.split(java_args) + [jar_file, "nogui"]
    elif flavor_info['type'] == 'php':
        phar_files = [f for f in os.listdir(server_dir) if f.endswith('.phar')]
        if not phar_files:
            logger.log('ERROR', "PocketMine PHAR not found!"); return
        startup_command = ["php", phar_files[0]]
    
    if not startup_command:
        logger.log('ERROR', "Could not determine startup command."); return

    logger.log('INFO', f"Starting {flavor} server '{current_server}'...")
    screen_cmd = ["screen", "-dmS", screen_name] + startup_command
    
    if run_command(screen_cmd, cwd=server_dir):
        logger.log('SUCCESS', "Server process started in screen session.")
        current_session_id = db_manager.log_session_start(current_server, flavor, version)
        
        time.sleep(5) # Give server time to start and get a PID
        result = run_command(f"screen -ls {screen_name}", capture_output=True, check=False)
        if result and result.stdout:
            pid_match = re.search(r'(\d+)\.', result.stdout)
            if pid_match:
                pid = int(pid_match.group(1))
                monitor_thread_stop_event = threading.Event()
                monitor = threading.Thread(target=server_monitor_thread, args=(current_server, pid, monitor_thread_stop_event))
                monitor.daemon = True
                monitor.start()

        if server_config.get('auto_restart'):
            auto_restart_stop_event = threading.Event()
            auto_restarter = threading.Thread(target=auto_restart_monitor, args=(current_server, screen_cmd, server_dir, auto_restart_stop_event))
            auto_restarter.daemon = True
            auto_restarter.start()

    else:
        logger.log('ERROR', "Failed to start server in screen.")
    input("\nPress Enter to continue...")

def stop_server(force=False):
    """Stops the current server gracefully or forcefully."""
    global current_session_id
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    screen_name = get_screen_name(current_server)
    if not is_server_running(screen_name):
        logger.log('INFO', "Server is not running."); return
    
    # Signal monitoring threads to stop
    monitor_thread_stop_event.set()
    auto_restart_stop_event.set()
    
    if force:
        logger.log('WARNING', f"Forcefully stopping server {current_server}...")
        run_command(f"screen -S {screen_name} -X quit")
    else:
        logger.log('INFO', f"Stopping server {current_server} gracefully...")
        run_command(f"screen -S {screen_name} -p 0 -X stuff 'stop\n'")
        
        # Wait for shutdown
        for _ in range(20): # Wait up to 20 seconds
            if not is_server_running(screen_name):
                break
            time.sleep(1)
        else:
            logger.log('WARNING', "Server did not stop gracefully. Forcing shutdown.")
            run_command(f"screen -S {screen_name} -X quit")
            
    logger.log('SUCCESS', "Server stopped.")
    if current_session_id:
        db_manager.log_session_end(current_session_id)
        current_session_id = None
    input("\nPress Enter to continue...")

def install_server():
    """Complete server installation wizard."""
    config = load_config()
    current_server = config['current_server']
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    server_dir = get_server_dir(current_server)
    os.makedirs(server_dir, exist_ok=True)

    flavor = select_server_flavor()
    if not flavor: return

    selected_version, version_info = select_server_version(flavor)
    if not selected_version or not version_info: return

    # Download
    if download_server_jar(flavor, selected_version, version_info, server_dir):
        # EULA for Java
        if SERVER_FLAVORS[flavor]['type'] == 'java':
            with open(os.path.join(server_dir, 'eula.txt'), 'w') as f:
                f.write("eula=true\n")
            logger.log('SUCCESS', "EULA accepted.")

        # Update config
        config['servers'][current_server]['server_flavor'] = flavor
        config['servers'][current_server]['server_version'] = selected_version
        config['servers'][current_server]['server_settings']['port'] = SERVER_FLAVORS[flavor]['default_port']
        save_config(config)
        logger.log('SUCCESS', f"Installation of {flavor} {selected_version} complete!")
    else:
        logger.log('ERROR', "Installation failed during download.")
    input("\nPress Enter to continue...")
    
def download_server_jar(flavor, version, version_info, server_dir):
    """Download the selected server jar file."""
    if not check_disk_space(server_dir, 500): return False
    
    session = create_robust_session()
    download_url = None
    target_filename = "server.jar"
    
    try:
        if flavor in ["paper", "folia"]:
            build = version_info['latest_build']
            jar_name = version_info['download_name']
            api_base = SERVER_FLAVORS[flavor]['api_base']
            download_url = f"{api_base}/versions/{version}/builds/{build}/downloads/{jar_name}"
        elif flavor == "purpur":
            download_url = version_info['download_url']
        elif flavor == "vanilla":
            manifest_resp = safe_request(session, 'GET', version_info['url'])
            if manifest_resp:
                download_url = manifest_resp.json()['downloads']['server']['url']
        elif flavor == "fabric":
            loader, installer = version_info['loader'], version_info['installer']
            download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader}/{installer}/server/jar"
        elif flavor == "quilt":
            loader = version_info['loader']
            download_url = f"https://meta.quiltmc.org/v3/versions/loader/{version}/{loader}/0.0.0/server/jar" # Installer version seems unused for now
        elif flavor == "pocketmine":
            download_url = version_info['download_url']
            target_filename = version_info['filename']
        
        if not download_url:
            logger.log('ERROR', "Could not determine download URL.")
            return False
            
        target_path = os.path.join(server_dir, target_filename)
        logger.log('INFO', f"Downloading {flavor} {version} to {target_path}...")
        
        download_cmd = f"wget -O \"{target_path}\" \"{download_url}\" --progress=bar:force:noscroll"
        if run_command(download_cmd, cwd=server_dir, timeout=900):
            logger.log('SUCCESS', "Download complete.")
            return True
        else:
            logger.log('ERROR', "Download failed via wget.")
            return False

    except Exception as e:
        logger.log('ERROR', f"Download process failed: {e}")
        return False
    finally:
        session.close()

def select_server_flavor() -> Optional[str]:
    """Interactive menu to select a server flavor."""
    print_header()
    print(f"{C.BOLD}Select Server Flavor:{C.RESET}")
    flavors = list(SERVER_FLAVORS.keys())
    for i, key in enumerate(flavors, 1):
        flavor = SERVER_FLAVORS[key]
        print(f"  {C.BOLD}{i}.{C.RESET} {flavor['icon']} {flavor['name']} - {C.DIM}{flavor['description']}{C.RESET}")
    
    while True:
        try:
            choice = input(f"\n{C.BOLD}Choose flavor (1-{len(flavors)}): {C.RESET}").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(flavors):
                return flavors[idx]
        except (ValueError, IndexError):
            logger.log('ERROR', "Invalid selection.")

def select_server_version(flavor: str) -> Tuple[Optional[str], Optional[Dict]]:
    """Interactive version selection with pagination."""
    include_snapshots = False
    current_page = 1
    
    while True:
        versions_data = get_versions_for_flavor(flavor, include_snapshots)
        if not versions_data:
            logger.log('ERROR', f"Could not retrieve versions for {flavor}.")
            return None, None

        versions_list = list(versions_data.keys())
        if flavor != 'vanilla':
            versions_list.reverse() # Most APIs list oldest first
        
        total_pages = math.ceil(len(versions_list) / VERSIONS_PER_PAGE)
        start = (current_page - 1) * VERSIONS_PER_PAGE
        end = start + VERSIONS_PER_PAGE
        page_versions = versions_list[start:end]
        
        print_header()
        snap_status = "ON" if include_snapshots else "OFF"
        print(f"{C.BOLD}Select {SERVER_FLAVORS[flavor]['name']} Version (Page {current_page}/{total_pages}) | Snapshots: {snap_status}{C.RESET}\n")
        
        for i, version in enumerate(page_versions, 1):
            print(f" {C.BOLD}{i:2}.{C.RESET} {version}")
        
        print(f"\n{C.DIM}Commands: [p]rev, [n]ext, [s]napshots, [q]uit, or number to select{C.RESET}")
        choice = input(f"{C.BOLD}Selection: {C.RESET}").strip().lower()

        if choice in ['p', 'prev'] and current_page > 1: current_page -= 1
        elif choice in ['n', 'next'] and current_page < total_pages: current_page += 1
        elif choice in ['s', 'snap']: include_snapshots = not include_snapshots; current_page = 1
        elif choice in ['q', 'quit']: return None, None
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(page_versions):
                    selected_ver = page_versions[idx]
                    return selected_ver, versions_data[selected_ver]
            except ValueError:
                logger.log('ERROR', "Invalid input.")
                time.sleep(1)

def configure_server():
    """Interactive configuration wizard."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server: logger.log('ERROR', "No server selected."); return

    server_config = config['servers'][current_server]
    settings = server_config.get('server_settings', {})

    while True:
        print_header()
        print(f"{C.BOLD}Configure Server: {current_server}{C.RESET}")
        options = {
            "1": ("RAM Allocation", server_config.get('ram_mb', 1024), "MB"),
            "2": ("Port", settings.get('port', 25565), ""),
            "3": ("Auto Restart", "Yes" if server_config.get('auto_restart') else "No", "(Toggle)"),
            "4": ("MOTD", settings.get('motd', "A Minecraft Server"), ""),
            "5": ("Max Players", settings.get('max-players', 20), ""),
            "0": ("Back to Main Menu", "", "")
        }
        for k, (label, val, unit) in options.items():
            print(f" {C.BOLD}{k}.{C.RESET} {label}: {C.CYAN}{val}{C.RESET} {C.DIM}{unit}{C.RESET}")
        
        choice = input(f"\n{C.BOLD}Select option to change: {C.RESET}").strip()
        
        try:
            if choice == '1': server_config['ram_mb'] = int(input("Enter new RAM (MB): "))
            elif choice == '2': settings['port'] = int(input("Enter new port: "))
            elif choice == '3': server_config['auto_restart'] = not server_config.get('auto_restart')
            elif choice == '4': settings['motd'] = input("Enter new MOTD: ")
            elif choice == '5': settings['max-players'] = int(input("Enter max players: "))
            elif choice == '0': break
            else: logger.log('ERROR', "Invalid choice.")
        except ValueError:
            logger.log('ERROR', "Invalid input, please enter a number where required.")
        
        server_config['server_settings'] = settings
        save_config(config)

def world_manager():
    """Menu for managing server worlds, including backups and restores."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    server_dir = get_server_dir(current_server)
    backup_dir = os.path.join(server_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    while True:
        print_header()
        print(f"{C.BOLD}World Manager: {current_server}{C.RESET}")
        menu = {
            "1": "Create Backup",
            "2": "List Backups",
            "3": "Restore from Backup",
            "4": "Delete a Backup",
            "0": "Back to Main Menu"
        }
        for k, v in menu.items():
            print(f" {C.BOLD}{k}.{C.RESET} {v}")
        
        choice = input(f"\n{C.BOLD}Choose option: {C.RESET}").strip()

        if choice == '1':
            backup_name = f"world_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            backup_path = os.path.join(backup_dir, backup_name)
            world_folders = [d for d in os.listdir(server_dir) if 'world' in d and os.path.isdir(os.path.join(server_dir, d))]
            
            if not world_folders:
                logger.log('ERROR', "No world folders found to back up.")
                time.sleep(2)
                continue
            
            logger.log('INFO', f"Creating backup: {backup_name}...")
            try:
                with zipfile.ZipFile(backup_path, 'w', BACKUP_COMPRESSION_LEVEL) as zf:
                    for folder in world_folders:
                        folder_path = os.path.join(server_dir, folder)
                        for root, _, files in os.walk(folder_path):
                            for file in files:
                                zf.write(os.path.join(root, file), 
                                         os.path.relpath(os.path.join(root, file), server_dir))
                logger.log('SUCCESS', f"Backup created successfully at {backup_path}")
            except Exception as e:
                logger.log('ERROR', f"Failed to create backup: {e}")
            input("\nPress Enter to continue...")

        elif choice == '2' or choice == '3' or choice == '4':
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.zip')], reverse=True)
            if not backups:
                logger.log('INFO', "No backups found.")
                time.sleep(2)
                continue

            print("\nAvailable Backups:")
            for i, backup in enumerate(backups, 1):
                print(f"  {C.BOLD}{i}.{C.RESET} {backup}")
            
            if choice == '2':
                input("\nPress Enter to continue...")
                continue
            
            try:
                idx_choice = int(input(f"\n{C.BOLD}Select a backup number: {C.RESET}")) - 1
                if not (0 <= idx_choice < len(backups)):
                    logger.log('ERROR', "Invalid selection.")
                    continue
                selected_backup = backups[idx_choice]
                backup_path = os.path.join(backup_dir, selected_backup)

                if choice == '3': # Restore
                    if input(f"{C.YELLOW}This will overwrite current world data. Are you sure? (y/N): {C.RESET}").lower() != 'y':
                        continue
                    
                    logger.log('INFO', f"Restoring from {selected_backup}...")
                    try:
                        with zipfile.ZipFile(backup_path, 'r') as zf:
                            zf.extractall(server_dir)
                        logger.log('SUCCESS', "Restore complete.")
                    except Exception as e:
                        logger.log('ERROR', f"Failed to restore: {e}")
                    input("\nPress Enter to continue...")

                elif choice == '4': # Delete
                    if input(f"{C.RED}Confirm deletion of '{selected_backup}' by typing 'DELETE': {C.RESET}") == 'DELETE':
                        os.remove(backup_path)
                        logger.log('SUCCESS', f"Deleted backup: {selected_backup}")
                    else:
                        logger.log('INFO', "Deletion cancelled.")
                    input("\nPress Enter to continue...")

            except ValueError:
                logger.log('ERROR', "Invalid input.")
        
        elif choice == '0':
            break

def show_statistics():
    """Displays server statistics from the database."""
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return

    stats = db_manager.get_server_statistics(current_server)
    
    def format_duration(seconds):
        if not seconds: return "N/A"
        seconds = int(seconds)
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, _ = divmod(rem, 60)
        return f"{days}d {hours}h {minutes}m"

    print_header()
    print(f"{C.BOLD}Statistics for: {current_server}{C.RESET}")
    print(f"  - Total Sessions:    {C.CYAN}{stats.get('total_sessions', 'N/A')}{C.RESET}")
    print(f"  - Total Uptime:      {C.CYAN}{format_duration(stats.get('total_uptime'))}{C.RESET}")
    print(f"  - Average Session:   {C.CYAN}{format_duration(stats.get('avg_duration'))}{C.RESET}")
    print(f"  - Total Crashes:     {C.YELLOW}{stats.get('total_crashes', 'N/A')}{C.RESET}")
    print(f"  - Total Restarts:    {C.YELLOW}{stats.get('total_restarts', 'N/A')}{C.RESET}")
    print("\n  --- 24-Hour Performance ---")
    print(f"  - Avg RAM Usage:     {C.CYAN}{stats.get('avg_ram_usage_24h', 0):.2f}%{C.RESET}")
    print(f"  - Avg CPU Usage:     {C.CYAN}{stats.get('avg_cpu_usage_24h', 0):.2f}%{C.RESET}")
    print(f"  - Peak Players:      {C.CYAN}{stats.get('peak_players_24h', 'N/A')}{C.RESET}")
    
    input("\nPress Enter to continue...")

# ============================================================================
# UI & MAIN LOOP
# ============================================================================
def print_header():
    """Enhanced header with system information"""
    os.system('cls' if os.name == 'nt' else 'clear')
    system_info = get_system_info()
    ram_usage = f"{system_info['available_ram_mb']}MB/{system_info['total_ram_mb']}MB"
    cpu_info = f"{system_info['cpu_count']} cores @ {system_info['cpu_usage']:.1f}%"
    print(f"{C.BOLD}{C.CYAN}{'=' * 80}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':>25} Enhanced Minecraft Server Manager v{VERSION} {'':>25}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':>15} Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine {'':>15}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 80}{C.RESET}")
    print(f"{C.DIM}System: {ram_usage} RAM Free | {cpu_info} CPU | Platform: {system_info['platform']}{C.RESET}\n")

def show_console():
    config = load_config()
    current_server = config.get('current_server')
    if not current_server:
        logger.log('ERROR', "No server selected."); return
    
    screen_name = get_screen_name(current_server)
    if is_server_running(screen_name):
        print(f"{C.CYAN}Attaching to console for '{current_server}'. Press Ctrl+A, then D to detach.{C.RESET}")
        time.sleep(2)
        os.system(f"screen -r {screen_name}")
    else:
        logger.log('ERROR', "Server is not running.")
        input("Press Enter to continue...")

def graceful_shutdown(signum, frame):
    """Handle signals for a clean exit."""
    logger.log('WARNING', "Shutdown signal received. Stopping server if running...")
    config = load_config()
    if config.get('current_server'):
        stop_server()
    logger.log('INFO', "MSM is shutting down.")
    sys.exit(0)
    
def main():
    """Main application loop."""
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    
    if not check_dependencies():
        sys.exit(1)

    while True:
        config = load_config()
        current_server = config.get('current_server')

        if not current_server and config.get('servers'):
            current_server = list(config['servers'].keys())[0]
            config['current_server'] = current_server
            save_config(config)
        elif not config.get('servers'):
            print_header()
            logger.log('INFO', "No servers found. Let's create your first one.")
            create_new_server()
            continue

        server_config = config['servers'][current_server]
        flavor = server_config.get('server_flavor', 'N/A')
        version = server_config.get('server_version', 'N/A')
        screen_name = get_screen_name(current_server)
        
        print_header()
        
        status = f"{C.GREEN}â—ONLINE{C.RESET}" if is_server_running(screen_name) else f"{C.RED}â—OFFLINE{C.RESET}"
        flavor_icon = SERVER_FLAVORS.get(flavor, {}).get('icon', 'â“')
        flavor_name = SERVER_FLAVORS.get(flavor, {}).get('name', 'Unknown')
        
        print(f"ðŸ“‹ Server: {C.CYAN}{current_server}{C.RESET} | Status: {status}")
        print(f"   {flavor_icon} {flavor_name} {version}")
        
        menu_options = [
            ("1", "ðŸš€", "Start Server"), ("2", "â¹ï¸", "Stop Server"), 
            ("3", "ðŸ“¦", "Install/Update Server"), ("4", "âš™ï¸", "Configure Server"),
            ("5", "ðŸ’»", "Server Console"), ("6", "ðŸ—„ï¸", "World Manager"),
            ("7", "ðŸ“Š", "Statistics"), ("8", "âž•", "Create New Server"),
            ("9", "ðŸ”„", "Switch Server"), ("0", "ðŸšª", "Exit")
        ]
        
        print(f"\n{C.BOLD}Main Menu:{C.RESET}")
        for key, icon, label in menu_options:
            print(f" {C.BOLD}{key}.{C.RESET} {icon} {label}")
        
        try:
            choice = input(f"\n{C.BOLD}Choose option: {C.RESET}").strip()
            
            if choice == '1': start_server()
            elif choice == '2': stop_server()
            elif choice == '3': install_server()
            elif choice == '4': configure_server()
            elif choice == '5': show_console()
            elif choice == '6': world_manager()
            elif choice == '7': show_statistics()
            elif choice == '8': create_new_server()
            elif choice == '9': select_current_server()
            elif choice == '0':
                if is_server_running(screen_name) and input(f"{C.YELLOW}Server is running. Stop it before exiting? (y/N): {C.RESET}").lower() == 'y':
                    stop_server()
                raise SystemExit
            else:
                logger.log('ERROR', "Invalid option.")
                time.sleep(1)

        except (KeyboardInterrupt, SystemExit):
            logger.log('INFO', "Exiting MSM. Goodbye!")
            sys.exit(0)
        except Exception as e:
            logger.log('CRITICAL', f"An unexpected error occurred in the main loop: {e}")
            time.sleep(3)

def create_new_server():
    """Wizard to create a new server configuration."""
    name = input(f"{C.BOLD}Enter new server name (e.g., 'survival' or 'creative'): {C.RESET}").strip()
    if not name:
        logger.log('ERROR', "Name cannot be empty."); return
    
    sanitized_name = sanitize_input(name)
    config = load_config()
    if sanitized_name in config['servers']:
        logger.log('ERROR', f"A server named '{sanitized_name}' already exists."); return
    
    config['servers'][sanitized_name] = {
        "server_flavor": None, "server_version": None, "ram_mb": 2048,
        "auto_restart": False, "server_settings": {
            "motd": f"{name} Server", "port": 25565, "max-players": 20
        }
    }
    config['current_server'] = sanitized_name
    save_config(config)
    os.makedirs(get_server_dir(sanitized_name), exist_ok=True)
    logger.log('SUCCESS', f"Created new server '{sanitized_name}'. Please use 'Install/Update' to set it up.")
    input("\nPress Enter to continue...")

def select_current_server():
    """Menu to switch between configured servers."""
    config = load_config()
    servers = list(config.get('servers', {}).keys())
    if not servers:
        logger.log('ERROR', "No servers configured."); return

    print_header()
    print(f"{C.BOLD}Select a Server to Manage:{C.RESET}")
    for i, name in enumerate(servers, 1):
        print(f"  {C.BOLD}{i}.{C.RESET} {name}")
    
    try:
        choice = int(input(f"\n{C.BOLD}Choose server: {C.RESET}")) - 1
        if 0 <= choice < len(servers):
            config['current_server'] = servers[choice]
            save_config(config)
            logger.log('SUCCESS', f"Switched to server '{servers[choice]}'.")
        else:
            logger.log('ERROR', "Invalid selection.")
    except ValueError:
        logger.log('ERROR', "Invalid input.")
    time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.log('CRITICAL', f"Unhandled exception at top level: {e}", exc_info=True)
        sys.exit(1)
