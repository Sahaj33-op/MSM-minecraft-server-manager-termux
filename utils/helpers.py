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

def sanitize_input(value: str, max_length: int = 255) -> str:
    """Enhanced input sanitization with length limits.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum length of the sanitized string (default: 255)
        
    Returns:
        Sanitized string
    """
    if not value or not isinstance(value, str):
        return f"server_{int(time.time())}"
    
    value = os.path.basename(value)
    if len(value) > max_length:
        value = value[:max_length]
    
    # Allow only safe characters
    if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
        value = re.sub(r'[^a-zA-Z0-9_.-]', '_', value)
    
    value = re.sub(r'\.{2,}', '.', value).strip('.-')
    return value if value else f"server_{int(time.time())}"

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
        
        # Use 60% of available RAM, but cap at reasonable limits
        suggested = min(int(available_mb * 0.6), total_mb // 2)
        
        # Ensure minimums and maximums
        if suggested < 512:
            return 512
        elif suggested > 8192:
            return 8192
        
        return suggested
    except Exception:
        return 1024  # Safe default

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
    """Run command with comprehensive error handling.
    
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
            command = command.split()
        
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture_output,
            text=True,
            check=False
        )
        
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {command[0] if command else 'unknown'}"
    except Exception as e:
        return -1, "", str(e)

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
    
    # Check Termux Java installations
    java_paths = [
        f"/data/data/com.termux/files/usr/lib/jvm/openjdk-{java_version}/bin/java",
        f"/data/data/com.termux/files/usr/bin/java",
        "java"  # System PATH
    ]
    
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
    """Get server directory path.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Path to the server directory
    """
    safe_name = sanitize_input(server_name)
    return Path.home() / f"minecraft-{safe_name}"

def get_screen_session_name(server_name: str) -> str:
    """Get screen session name for server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Screen session name
    """
    safe_name = sanitize_input(server_name)
    return f"msm-{safe_name}"