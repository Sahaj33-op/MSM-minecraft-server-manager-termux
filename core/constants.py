#!/usr/bin/env python3
"""
Constants - Application-wide constants and configuration values
"""
from typing import Dict, Set

# Server Configuration Constants
class ServerConfig:
    """Server-related configuration constants"""
    MIN_RAM_MB = 512
    MAX_RAM_MB = 8192
    DEFAULT_RAM_MB = 1024
    RAM_ALLOCATION_RATIO = 0.6  # Use 60% of available RAM
    
    MIN_PORT = 1
    MAX_PORT = 65535
    DEFAULT_PORT = 25565
    
    MIN_MAX_PLAYERS = 1
    MAX_MAX_PLAYERS = 1000
    DEFAULT_MAX_PLAYERS = 20

# Monitoring Constants
class MonitoringConfig:
    """Performance monitoring configuration"""
    MONITORING_INTERVAL = 60  # seconds
    PERFORMANCE_DASHBOARD_REFRESH = 5  # seconds
    THREAD_JOIN_TIMEOUT = 5  # seconds
    MAX_MONITORING_THREADS = 10
    HEALTH_CHECK_INTERVAL = 30  # seconds
    MEMORY_WARNING_THRESHOLD = 90  # percentage
    DISK_WARNING_THRESHOLD = 90  # percentage

# Scheduler Constants
class SchedulerConfig:
    """Scheduler configuration constants"""
    CHECK_INTERVAL = 60  # seconds between task checks
    TASK_TIMEOUT = 300  # seconds before a task is considered timed out
    MAX_CONCURRENT_TASKS = 3
    RETRY_ON_FAILURE = True
    MAX_TASK_RETRIES = 2

# Database Constants
class DatabaseConfig:
    """Database configuration constants"""
    MAX_BACKUP_DISPLAY = 10
    MAX_SESSION_HISTORY = 1000
    CONNECTION_TIMEOUT = 30  # seconds
    QUERY_TIMEOUT = 10  # seconds

# Security Constants
class SecurityConfig:
    """Security-related constants"""
    MAX_INPUT_LENGTH = 255
    MAX_FILENAME_LENGTH = 100
    MAX_PATH_DEPTH = 10
    
    # Dangerous commands that should be blocked
    DANGEROUS_COMMANDS: Set[str] = {
        'rm', 'del', 'format', 'shutdown', 'reboot', 'halt', 'poweroff',
        'dd', 'mkfs', 'fdisk', 'parted', 'wipefs', 'sfdisk', 'sgdisk',
        'chmod', 'chown', 'chgrp', 'umount', 'mount', 'fuser', 'killall',
        'pkill', 'kill', 'killall5', 'xkill', 'skill', 'slay'
    }
    
    # Sensitive paths that should be protected
    SENSITIVE_PATHS: Set[str] = {
        '/system', '/proc', '/sys', '/dev', '/etc/passwd', '/etc/shadow',
        '/data/system', '/data/misc', '/data/local'
    }
    
    # Shell metacharacters that should be blocked
    SHELL_METACHARS: Set[str] = {
        '&', '|', ';', '&&', '||', '>', '<', '`', '$', '(', ')'
    }

# Termux-specific Constants
class TermuxConfig:
    """Termux-specific configuration and paths"""
    TERMUX_HOME = '/data/data/com.termux/files/home'
    TERMUX_PREFIX = '/data/data/com.termux/files/usr'
    TERMUX_BIN = '/data/data/com.termux/files/usr/bin'
    
    # Termux-specific commands that are safe
    SAFE_TERMUX_COMMANDS: Set[str] = {
        'python', 'python3', 'pip', 'pip3', 'apt', 'pkg', 'termux-setup-storage',
        'termux-open', 'termux-share', 'termux-notification', 'termux-toast',
        'screen', 'tmux', 'nano', 'vim', 'curl', 'wget', 'git', 'java', 'javac'
    }
    
    # Android-specific paths to avoid
    ANDROID_SYSTEM_PATHS: Set[str] = {
        '/system/bin', '/system/xbin', '/system/lib', '/system/lib64',
        '/vendor/bin', '/vendor/lib', '/vendor/lib64'
    }

# File and Directory Constants
class FileConfig:
    """File and directory configuration"""
    MAX_BACKUP_SIZE_MB = 1000
    MAX_LOG_SIZE_MB = 50
    MAX_LOG_FILES = 30
    BACKUP_COMPRESSION_LEVEL = 6
    BACKUP_RETENTION_COUNT = 7  # Number of backups to keep when rotating
    BACKUP_RETENTION_DAYS = 30  # Alternative: retention period in days

    # Allowed file extensions for server files
    ALLOWED_SERVER_EXTENSIONS: Set[str] = {
        '.jar', '.phar', '.zip', '.tar.gz', '.tgz'
    }

    # Allowed file extensions for configuration files
    ALLOWED_CONFIG_EXTENSIONS: Set[str] = {
        '.json', '.yml', '.yaml', '.properties', '.txt', '.conf'
    }

# Network Constants
class NetworkConfig:
    """Network-related constants"""
    DEFAULT_TIMEOUT = 30  # seconds
    CONNECTION_TIMEOUT = 15  # seconds
    READ_TIMEOUT = 45  # seconds
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds (base delay for exponential backoff)
    RETRY_BACKOFF = 2  # multiplier for exponential backoff
    MAX_RETRY_DELAY = 30.0  # Maximum delay between retries
    JITTER_FACTOR = 0.25  # Random jitter factor (0-25%) to prevent thundering herd

# Logging Constants
class LoggingConfig:
    """Logging configuration constants"""
    LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'SUCCESS']
    DEFAULT_LOG_LEVEL = 'INFO'
    MAX_LOG_MESSAGE_LENGTH = 1000
    
    # Log rotation settings
    MAX_LOG_SIZE = 50 * 1024 * 1024  # 50MB
    BACKUP_COUNT = 5
    ROTATION_INTERVAL = 'midnight'

# UI Constants
class UIConfig:
    """User interface constants"""
    MAX_MENU_ITEMS = 20
    MAX_DISPLAY_LENGTH = 80
    REFRESH_INTERVAL = 1  # seconds
    
    # Color codes for different message types
    COLORS = {
        'RED': '\033[91m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'BLUE': '\033[94m',
        'MAGENTA': '\033[95m',
        'CYAN': '\033[96m',
        'WHITE': '\033[97m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
        'RESET': '\033[0m'
    }

# Error Messages
class ErrorMessages:
    """Standardized error messages with actionable information."""

    # Server-related errors
    NO_SERVER_SELECTED = "No server selected. Use 'msm server list' to see available servers or 'msm server create <name>' to create one."
    SERVER_NOT_FOUND = "Server not found. Check spelling or use 'msm server list' to see available servers."
    SERVER_ALREADY_RUNNING = "Server is already running. Use 'msm server stop' first if you want to restart."
    SERVER_NOT_RUNNING = "Server is not running. Use 'msm server start' to start it."
    SERVER_START_FAILED = "Failed to start server. Check logs at ~/.config/msm/msm.log for details."
    EULA_NOT_ACCEPTED = "Minecraft EULA must be accepted before starting the server. Run the start command again to accept."

    # Input validation errors
    INVALID_INPUT = "Invalid input provided. Please check the value and try again."
    INVALID_PORT = "Invalid port number. Port must be between 1-65535."
    INVALID_RAM = "Invalid RAM allocation. Must be between 512-8192 MB and not exceed available system memory."
    INVALID_SERVER_NAME = "Invalid server name. Use only letters, numbers, underscores, dots, and hyphens."

    # Permission and access errors
    PERMISSION_DENIED = "Permission denied. Check file permissions or try running with appropriate privileges."
    COMMAND_NOT_FOUND = "Required command not found. Install missing dependencies with 'pkg install <package>'."

    # Timeout and network errors
    TIMEOUT_ERROR = "Operation timed out. Check network connection and try again."
    NETWORK_ERROR = "Network error occurred. Check internet connection or try again later."
    API_ERROR = "Failed to fetch data from API. Server may be temporarily unavailable."
    DOWNLOAD_FAILED = "Download failed. Check internet connection and available disk space."

    # Database errors
    DATABASE_ERROR = "Database error occurred. Try restarting the application. If problem persists, check ~/.config/msm/msm.db"
    DATABASE_LOCKED = "Database is locked. Another process may be using it. Close other MSM instances."
    DATABASE_CORRUPTED = "Database appears corrupted. A backup has been created. Restart application."

    # File system errors
    FILE_NOT_FOUND = "File not found. Check the path and verify the file exists."
    DISK_FULL = "Insufficient disk space. Free up space and try again."
    BACKUP_FAILED = "Backup failed. Check available disk space and write permissions."

    # Configuration errors
    INVALID_CONFIG = "Invalid configuration. Check config file syntax and values."
    CONFIG_LOCKED = "Configuration file is locked. Another process may be using it."

    # Tunnel errors
    TUNNEL_NOT_AVAILABLE = "Tunnel service not available. Install required tool: {tool_name}"
    TUNNEL_ALREADY_RUNNING = "Tunnel is already running. Stop it first before starting a new one."

    # Screen session errors
    SCREEN_NOT_INSTALLED = "Screen is not installed. Install with 'pkg install screen'."

    # Java errors
    JAVA_NOT_FOUND = "Java not found. Install with 'pkg install openjdk-17' or 'pkg install openjdk-21'."

# Success Messages
class SuccessMessages:
    """Standardized success messages with context."""

    # Server operations
    SERVER_CREATED = "Server '{name}' created successfully. Use 'msm server install' to install server software."
    SERVER_STARTED = "Server started successfully. Connect at localhost:{port}"
    SERVER_STOPPED = "Server stopped successfully."
    SERVER_RESTARTED = "Server restarted successfully."
    SERVER_INSTALLED = "Server software installed successfully. Use 'msm server start' to run."

    # Configuration
    CONFIG_SAVED = "Configuration saved successfully."
    SETTINGS_UPDATED = "Settings updated. Restart the server for changes to take effect."

    # Backup operations
    BACKUP_CREATED = "Backup created successfully: {filename}"
    BACKUP_RESTORED = "Backup restored successfully. Start the server to verify."
    BACKUP_DELETED = "Backup deleted successfully."

    # Installation
    INSTALLATION_COMPLETE = "Installation completed successfully."

    # Tunnel operations
    TUNNEL_STARTED = "Tunnel started. Share this URL with players: {url}"
    TUNNEL_STOPPED = "Tunnel stopped successfully."

    # Scheduler
    TASK_SCHEDULED = "Task scheduled successfully. It will run at the configured time."
    TASK_REMOVED = "Scheduled task removed successfully."
