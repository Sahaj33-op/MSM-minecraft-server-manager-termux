"""Application-wide constants."""

from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

VERSION = "6.0"

CONFIG_DIR = Path(os.path.expanduser("~/.config/msm"))
CONFIG_FILE = CONFIG_DIR / "config.json"
DATABASE_FILE = CONFIG_DIR / "msm.db"
LOG_FILE = CONFIG_DIR / "msm.log"

VERSIONS_PER_PAGE = 15
PAPER_VERSION_LOOKBACK = 20
REQUEST_TIMEOUT = (15, 45)
MAX_RETRIES = 5
RETRY_BACKOFF = 2
NGROK_TIMEOUT = 20
DOWNLOAD_CHUNK_SIZE = 1024 * 1024

MAX_RAM_PERCENTAGE = 80
MONITOR_INTERVAL = 60
AUTO_RESTART_POLL_INTERVAL = 15
AUTO_RESTART_DELAY_SECONDS = 5
BACKUP_POLL_INTERVAL = 30
DEFAULT_BACKUP_INTERVAL_HOURS = 6
MAX_LOG_SIZE = 50 * 1024 * 1024
LOG_RETENTION_DAYS = 30

MAX_FILENAME_LENGTH = 255
ALLOWED_FILENAME_CHARS = re.compile(r"^[a-zA-Z0-9_.-]+$")
INVALID_FILENAME_CHARS = re.compile(r"[^a-zA-Z0-9_.-]")
COLLAPSE_DOTS_PATTERN = re.compile(r"\.{2,}")
WORLD_SUFFIX_PATTERN = re.compile(r"^world(?:[_.-].+)?$", re.IGNORECASE)

BACKUP_COMPRESSION = zipfile.ZIP_DEFLATED
BACKUP_COMPRESSION_LEVEL = 6

PID_FILE_NAME = ".msm.pid"
SESSION_FILE_NAME = ".msm.session"
TUNNEL_PID_FILE_NAME = ".msm.tunnel.pid"
PLAYIT_SECRET_FILE_NAME = ".msm.playit.secret"
SERVER_PROPERTIES_FILE = "server.properties"
EULA_FILE = "eula.txt"

SUPPORTED_TUNNEL_PROVIDERS = ("ngrok", "playit")
DEFAULT_TUNNEL_BINARIES = {
    "ngrok": "ngrok",
    "playit": "playit-cli",
}

_java_home = os.environ.get("JAVA_HOME")
COMMON_JAVA_HOME_BASES = [
    *([Path(_java_home)] if _java_home else []),
    Path(os.path.expanduser("~/../usr/lib/jvm")),
    Path("/usr/lib/jvm"),
    Path("/usr/lib64/jvm"),
]

SERVER_FLAVORS = {
    "paper": {
        "name": "PaperMC",
        "description": "High-performance server with plugin support",
        "api_base": "https://api.papermc.io/v2/projects/paper",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "paper-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 512,
    },
    "purpur": {
        "name": "Purpur",
        "description": "Paper fork with extra gameplay controls",
        "api_base": "https://api.purpurmc.org/v2/purpur",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "purpur-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 512,
    },
    "folia": {
        "name": "Folia",
        "description": "Regionized multi-threaded Paper fork",
        "api_base": "https://api.papermc.io/v2/projects/folia",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "folia-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 1024,
    },
    "vanilla": {
        "name": "Vanilla Minecraft",
        "description": "Official Mojang server",
        "api_base": "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "server.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 512,
    },
    "fabric": {
        "name": "Fabric",
        "description": "Lightweight modding platform",
        "api_base": "https://meta.fabricmc.net/v2/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "fabric-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 768,
    },
    "quilt": {
        "name": "Quilt",
        "description": "Fabric-compatible modern fork",
        "api_base": "https://meta.quiltmc.org/v3/versions",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "quilt-server-launch.jar",
        "default_port": 25565,
        "type": "java",
        "min_ram": 768,
    },
    "pocketmine": {
        "name": "PocketMine-MP",
        "description": "Bedrock Edition server software",
        "api_base": "https://api.github.com/repos/pmmp/PocketMine-MP/releases",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "PocketMine-MP.phar",
        "default_port": 19132,
        "type": "php",
        "min_ram": 256,
    },
}
