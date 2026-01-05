#!/usr/bin/env python3
"""
Utils - Helper functions and system utilities
From both branches with enhanced system detection
"""
import os
import re
import shutil
import subprocess
import psutil
import time
from pathlib import Path
from typing import Optional, Tuple

from core.constants import (
    ServerConfig, SecurityConfig, TermuxConfig,
    ErrorMessages, SuccessMessages
)
from utils.termux_utils import is_termux_environment

def sanitize_input(value: str, max_length: int = SecurityConfig.MAX_INPUT_LENGTH) -> str:
    """Enhanced input sanitization with length limits and path traversal protection.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum length of the sanitized string (default: 255)
        
    Returns:
        Sanitized string
    """
    if not value or not isinstance(value, str):
        return f"server_{int(time.time())}"
    
    # Security: Remove any path traversal attempts
    value = value.replace('..', '').replace('/', '').replace('\\', '')
    value = os.path.basename(value)
    
    if len(value) > max_length:
        value = value[:max_length]
    
    # Allow only safe characters
    if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
        value = re.sub(r'[^a-zA-Z0-9_.-]', '_', value)
    
    value = re.sub(r'\.{2,}', '.', value).strip('.-')
    return value if value else f"server_{int(time.time())}"

def get_config_dir() -> Path:
    """Get MSM configuration directory (Termux-aware).

    Returns Termux-specific path when running in Termux environment,
    otherwise returns standard ~/.config/msm path.

    Returns:
        Path object pointing to MSM config directory
    """
    if is_termux_environment():
        return Path(TermuxConfig.TERMUX_HOME) / ".config/msm"
    return Path.home() / ".config/msm"

def get_home_dir() -> Path:
    """Get user home directory (Termux-aware).

    Returns Termux-specific home when running in Termux environment,
    otherwise returns standard home directory.

    Returns:
        Path object pointing to home directory
    """
    if is_termux_environment():
        return Path(TermuxConfig.TERMUX_HOME)
    return Path.home()

def validate_port(port: int) -> bool:
    """Validate that a port number is in the valid range.

    Args:
        port: Port number to validate

    Returns:
        True if port is valid

    Raises:
        ValueError: If port is not an integer or out of range
    """
    if not isinstance(port, int):
        raise ValueError(f"Port must be an integer, got {type(port).__name__}")

    if not 1 <= port <= 65535:
        raise ValueError(f"Port must be between 1-65535, got {port}")

    return True


def validate_ram_allocation(ram_mb: int, warn_threshold: float = 0.8) -> Tuple[bool, str]:
    """Validate RAM allocation against available system memory.

    Args:
        ram_mb: Requested RAM allocation in MB
        warn_threshold: Percentage of available RAM that triggers a warning (default: 0.8)

    Returns:
        Tuple of (is_valid, message) where message contains warning/error info

    Raises:
        ValueError: If ram_mb is not a positive integer
    """
    if not isinstance(ram_mb, int) or ram_mb <= 0:
        raise ValueError(f"RAM must be a positive integer, got {ram_mb}")

    # Check minimum RAM requirement
    if ram_mb < ServerConfig.MIN_RAM_MB:
        return False, f"RAM allocation too low. Minimum: {ServerConfig.MIN_RAM_MB} MB"

    # Check maximum RAM limit
    if ram_mb > ServerConfig.MAX_RAM_MB:
        return False, f"RAM allocation too high. Maximum: {ServerConfig.MAX_RAM_MB} MB"

    # Check against available system RAM
    try:
        mem = psutil.virtual_memory()
        available_mb = mem.available // (1024 * 1024)
        total_mb = mem.total // (1024 * 1024)

        # Error if requesting more than total RAM
        if ram_mb > total_mb:
            return False, f"Requested {ram_mb} MB but system only has {total_mb} MB total"

        # Warning if requesting more than available RAM
        if ram_mb > available_mb:
            return True, f"Warning: Requesting {ram_mb} MB but only {available_mb} MB available"

        # Warning if requesting more than threshold of available RAM
        if ram_mb > available_mb * warn_threshold:
            return True, f"Warning: {ram_mb} MB is over {int(warn_threshold * 100)}% of available RAM ({available_mb} MB)"

        return True, ""

    except Exception:
        # If we can't check, allow it with a warning
        return True, "Warning: Could not verify available system memory"


def validate_max_players(max_players: int) -> bool:
    """Validate max players setting.

    Args:
        max_players: Maximum number of players

    Returns:
        True if valid

    Raises:
        ValueError: If max_players is out of range
    """
    if not isinstance(max_players, int):
        raise ValueError(f"Max players must be an integer, got {type(max_players).__name__}")

    if not 1 <= max_players <= 1000:
        raise ValueError(f"Max players must be between 1-1000, got {max_players}")

    return True

def is_port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a port is already in use.

    Args:
        port: Port number to check
        host: Host address to check (default: localhost)

    Returns:
        True if port is in use, False if available
    """
    import socket

    # Validate port first
    try:
        validate_port(port)
    except ValueError:
        return False  # Invalid port is considered "not in use"

    # Try to bind to the port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False  # Port is available
        except OSError:
            return True  # Port is in use

def validate_path(path: str, base_path: str = None) -> bool:
    """Validate that a path is safe and within allowed boundaries.

    Args:
        path: Path to validate
        base_path: Base path to check against (optional)

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(path)

        # Check for path traversal
        if '..' in path or path.startswith('/') or '\\' in path:
            return False

        # If base_path is provided, ensure path is within it
        if base_path:
            base_abs = os.path.abspath(base_path)
            return abs_path.startswith(base_abs)

        return True
    except Exception:
        return False


def validate_server_name(name: str) -> Tuple[bool, str]:
    """Validate a server name for use in MSM.

    Server names must be:
    - Between 1-64 characters
    - Alphanumeric with underscores, dots, and hyphens only
    - Not start with a dot or hyphen
    - Not contain path separators or traversal patterns

    Args:
        name: Server name to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        If valid, error_message is empty string
    """
    if not name:
        return False, "Server name cannot be empty"

    if not isinstance(name, str):
        return False, f"Server name must be a string, got {type(name).__name__}"

    if len(name) > 64:
        return False, f"Server name too long ({len(name)} chars). Maximum is 64 characters"

    # Check for path traversal or dangerous characters
    if '..' in name or '/' in name or '\\' in name:
        return False, "Server name cannot contain path separators or '..' patterns"

    # Check for shell metacharacters
    dangerous_chars = ['&', '|', ';', '$', '`', '(', ')', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        if char in name:
            return False, f"Server name cannot contain shell metacharacter '{char}'"

    # Must match safe pattern
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$', name):
        return False, "Server name must start with alphanumeric and contain only letters, numbers, underscores, dots, and hyphens"

    # Reserved names (Windows compatibility)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                      'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                      'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    if name.upper() in reserved_names:
        return False, f"'{name}' is a reserved name and cannot be used"

    return True, ""


def validate_minecraft_version(version: str) -> Tuple[bool, str]:
    """Validate a Minecraft version string format.

    Args:
        version: Version string to validate (e.g., "1.20.4", "1.19.2")

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not version:
        return False, "Version cannot be empty"

    if not isinstance(version, str):
        return False, f"Version must be a string, got {type(version).__name__}"

    # Standard Minecraft version pattern (e.g., 1.20.4, 1.19, 24w10a)
    standard_pattern = r'^(\d+\.\d+(\.\d+)?|(\d{2}w\d{2}[a-z]?))$'
    if re.match(standard_pattern, version):
        return True, ""

    # Also accept snapshot patterns and other formats
    if re.match(r'^[a-zA-Z0-9._-]+$', version):
        return True, ""

    return False, f"Invalid version format: '{version}'. Expected format like '1.20.4' or '24w10a'"


def detect_total_ram_mb() -> int:
    """Detect total system RAM in MB.
    
    Returns:
        Total system RAM in MB
    """
    try:
        mem = psutil.virtual_memory()
        return mem.total // (1024 * 1024)
    except Exception:
        return 2048  # Default fallback

def suggest_ram_allocation() -> int:
    """Suggest optimal RAM allocation.
    
    Returns:
        Suggested RAM allocation in MB
    """
    try:
        mem = psutil.virtual_memory()
        total_mb = mem.total // (1024 * 1024)
        available_mb = mem.available // (1024 * 1024)
        
        # Use configured ratio of available RAM, but cap at reasonable limits
        suggested = min(int(available_mb * ServerConfig.RAM_ALLOCATION_RATIO), total_mb // 2)
        
        # Ensure minimums and maximums
        if suggested < ServerConfig.MIN_RAM_MB:
            return ServerConfig.MIN_RAM_MB
        elif suggested > ServerConfig.MAX_RAM_MB:
            return ServerConfig.MAX_RAM_MB
        
        return suggested
    except Exception:
        return ServerConfig.DEFAULT_RAM_MB  # Safe default

def is_screen_session_running(session_name: str) -> bool:
    """Check if a screen session exists and is running.
    
    Args:
        session_name: Name of the screen session to check
        
    Returns:
        True if session is running, False otherwise
    """
    try:
        result = subprocess.run(
            ["screen", "-ls", session_name],
            capture_output=True,
            text=True,
            check=False
        )
        return session_name in result.stdout
    except Exception:
        return False

def run_command(command, cwd=None, timeout=None, capture_output=False) -> Tuple[int, str, str]:
    """Run command with comprehensive error handling and security measures.
    
    Args:
        command: Command to run (string or list)
        cwd: Working directory (default: None)
        timeout: Timeout in seconds (default: None)
        capture_output: Whether to capture output (default: False)
        
    Returns:
        Tuple containing (returncode, stdout, stderr)
    """
    try:
        if isinstance(command, str):
            # Security: Use shlex.split to properly handle quoted arguments
            import shlex
            command = shlex.split(command)
        
        # Security: Validate command is not empty
        if not command:
            return -1, "", "Empty command provided"
        
        # Security: Block dangerous commands that could harm the system
        if command[0].lower() in SecurityConfig.DANGEROUS_COMMANDS:
            return -1, "", f"Command '{command[0]}' is not allowed for security reasons"
        
        # Security: Validate first argument is not a shell metacharacter
        if command[0] in SecurityConfig.SHELL_METACHARS:
            return -1, "", f"Invalid command: {command[0]}"
        
        # Security: Block commands that try to access sensitive paths
        for arg in command:
            if any(sensitive_path in arg for sensitive_path in SecurityConfig.SENSITIVE_PATHS):
                return -1, "", f"Access to sensitive path not allowed: {arg}"
        
        # Security: Use subprocess.run with shell=False to prevent injection
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            check=False,
            shell=False  # Critical: Never use shell=True
        )
        
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {command[0] if command else 'unknown'}"
    except PermissionError:
        return -1, "", f"Permission denied: {command[0] if command else 'unknown'}"
    except Exception as e:
        return -1, "", f"Command execution error: {str(e)}"

def get_java_path(minecraft_version: str) -> Optional[str]:
    """Find appropriate Java executable for Minecraft version.
    
    Args:
        minecraft_version: Minecraft version string
        
    Returns:
        Path to Java executable or None if not found
    """
    # Determine required Java version
    if not minecraft_version:
        java_version = "17"
    else:
        match = re.match(r'1\.(\d+)', minecraft_version)
        if match:
            minor = int(match.group(1))
            if minor >= 17:
                java_version = "17"
            elif minor >= 8:
                java_version = "8"
            else:
                java_version = "8"
        else:
            # Modern versions (1.20+)
            java_version = "17"
    
    # Check Termux Java installations first, then system Java
    if is_termux_environment():
        java_paths = [
            f"{TermuxConfig.TERMUX_PREFIX}/lib/jvm/openjdk-{java_version}/bin/java",
            f"{TermuxConfig.TERMUX_BIN}/java",
            "java"  # System PATH fallback
        ]
    else:
        java_paths = ["java"]  # Use system Java on non-Termux systems
    
    for java_path in java_paths:
        if shutil.which(java_path) or os.path.exists(java_path):
            return java_path
    
    return None

def check_dependencies() -> bool:
    """Check for required system dependencies.
    
    Returns:
        True if all dependencies are available, False otherwise
    """
    required = ['python3', 'wget', 'screen']
    missing = []
    
    for dep in required:
        if not shutil.which(dep):
            missing.append(dep)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        return False
    
    return True

def get_server_directory(server_name: str) -> Path:
    """Get server directory path (Termux-aware).

    Args:
        server_name: Name of the server

    Returns:
        Path to the server directory
    """
    safe_name = sanitize_input(server_name)
    return get_home_dir() / f"minecraft-{safe_name}"

def get_screen_session_name(server_name: str) -> str:
    """Get screen session name for server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Screen session name
    """
    safe_name = sanitize_input(server_name)
    return f"msm-{safe_name}"