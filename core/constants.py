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
    RETRY_DELAY = 1  # seconds
    RETRY_BACKOFF = 2  # multiplier

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
    """Standardized error messages"""
    NO_SERVER_SELECTED = "No server selected"
    SERVER_NOT_FOUND = "Server not found"
    INVALID_INPUT = "Invalid input provided"
    PERMISSION_DENIED = "Permission denied"
    COMMAND_NOT_FOUND = "Command not found"
    TIMEOUT_ERROR = "Operation timed out"
    NETWORK_ERROR = "Network error occurred"
    DATABASE_ERROR = "Database error occurred"
    FILE_NOT_FOUND = "File not found"
    INVALID_CONFIG = "Invalid configuration"

# Success Messages
class SuccessMessages:
    """Standardized success messages"""
    SERVER_STARTED = "Server started successfully"
    SERVER_STOPPED = "Server stopped successfully"
    CONFIG_SAVED = "Configuration saved successfully"
    BACKUP_CREATED = "Backup created successfully"
    BACKUP_RESTORED = "Backup restored successfully"
    INSTALLATION_COMPLETE = "Installation completed successfully"
