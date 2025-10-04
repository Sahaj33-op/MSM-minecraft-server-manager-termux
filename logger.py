# ============================================================================
# logger.py - Centralized logging utility (NEW FILE - breaks circular dependency)
# ============================================================================
"""
Standalone logging module with zero dependencies on other MSM modules.
"""

import time
import traceback
from pathlib import Path
from typing import Optional

# Log buffer for host operations before entering proot
_log_buffer = []


def get_log_file_path() -> Path:
    """
    Get log file path without importing config.py (to avoid circular deps).
    """
    # Simple proot detection
    if Path("/.proot").exists():
        log_dir = Path("/root/msm")
    else:
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "msm_temp"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "msm.log"


def log(message: str, level: str = "INFO"):
    """
    Write logs to file with timestamp.
    Buffers on host, writes immediately inside proot.
    """
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    # Simple proot check without importing environment module
    if not Path("/.proot").exists():
        _log_buffer.append(log_entry)
        return
    
    try:
        log_file = get_log_file_path()
        with open(log_file, "a") as f:
            # Flush buffer if present
            if _log_buffer:
                f.writelines(_log_buffer)
                _log_buffer.clear()
            f.write(log_entry)
    except Exception:
        # Silent fail for logging errors
        pass


def log_error(message: str, exception: Optional[Exception] = None):
    """
    Log an error with optional exception details.
    """
    log(f"ERROR: {message}", "ERROR")
    if exception:
        log(f"Exception: {str(exception)}", "ERROR")
        log(f"Traceback: {traceback.format_exc()}", "ERROR")


def log_warning(message: str):
    """
    Log a warning message.
    """
    log(f"WARNING: {message}", "WARNING")


def log_info(message: str):
    """
    Log an info message.
    """
    log(f"INFO: {message}", "INFO")


def log_debug(message: str):
    """
    Log a debug message.
    """
    log(f"DEBUG: {message}", "DEBUG")