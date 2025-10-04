# ============================================================================
# utils.py - Shared utilities (FIXED - no circular dependency)
# ============================================================================
"""
Utility functions: RAM detection, self-update, command execution.
Clean imports only from logger.
"""

import os
import shutil
import hashlib
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from logger import log  # Clean import
# No imports from ui.py here!


def detect_total_ram_mb() -> int:
    """Detect total system RAM in MB."""
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except:
        pass
    return 2048


def suggest_ram_allocation() -> int:
    """
    Suggest RAM allocation (75% of total).
    Cap removed for future-proofing - let users on high-end devices use more.
    """
    total_mb = detect_total_ram_mb()
    suggested = int(total_mb * 0.75)
    return max(1024, suggested)  # No upper cap


def run_command(cmd: list, timeout: int = 60) -> tuple:
    """
    Run command and return (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        log(f"Command timed out: {' '.join(cmd)}", "ERROR")
        return (1, "", "Timeout")
    except Exception as e:
        log(f"Command failed: {e}", "ERROR")
        return (1, "", str(e))


def self_update():
    """
    Update script from GitHub with atomic write.
    Import UI functions locally to avoid circular dependency.
    """
    from ui import print_info, print_success, print_error, Colors
    
    SCRIPT_URL = "https://raw.githubusercontent.com/Sahaj33-op/MSM-minecraft-server-manager-termux/main/msm.py"
    
    print_info("Checking for updates...")
    log("Starting self-update check")
    
    try:
        with urllib.request.urlopen(SCRIPT_URL, timeout=30) as response:
            new_script = response.read().decode('utf-8')
        
        current_file = Path(__file__).parent / "main.py"
        current_script = current_file.read_text()
        current_hash = hashlib.sha256(current_script.encode()).hexdigest()
        new_hash = hashlib.sha256(new_script.encode()).hexdigest()
        
        if current_hash == new_hash:
            print_success("Already running latest version")
            log("No update available")
            return
        
        print_success("Update available!")
        print_info(f"Current: {current_hash[:8]}")
        print_info(f"New:     {new_hash[:8]}")
        
        confirm = input(f"\n{Colors.YELLOW}Install update? (y/N): {Colors.RESET}").strip().lower()
        
        if confirm == 'y':
            backup_path = current_file.with_suffix('.py.backup')
            shutil.copy2(current_file, backup_path)
            print_info(f"Backup: {backup_path}")
            
            # Atomic write with temp file
            temp_path = current_file.with_suffix('.py.tmp')
            temp_path.write_text(new_script, encoding='utf-8')
            os.chmod(temp_path, 0o755)
            
            # Atomic replace
            os.replace(str(temp_path), current_file)
            
            print_success("Update installed successfully")
            print_info("Restarting...")
            log("Update completed, restarting")
            
            import sys
            os.execv(sys.executable, [sys.executable, str(current_file)] + sys.argv[1:])
        else:
            print_info("Update cancelled")
            log("Update cancelled by user")
    
    except urllib.error.URLError as e:
        print_error(f"Download failed: {e}")
        log(f"Update download failed: {e}", "ERROR")
    except Exception as e:
        print_error(f"Update failed: {e}")
        log(f"Update error: {e}", "ERROR")


def is_screen_session_running(session_name: str) -> bool:
    """Check if a screen session is running."""
    returncode, stdout, stderr = run_command(["screen", "-ls"], timeout=5)
    return session_name in stdout
