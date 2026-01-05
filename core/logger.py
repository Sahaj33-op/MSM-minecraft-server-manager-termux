#!/usr/bin/env python3
"""
Enhanced Logger - Extracted from main branch msm.py
Professional logging with rotation, compression, levels, and dual output
"""
import os
import time
import gzip
import shutil
import logging
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


class CompressedRotatingFileHandler(RotatingFileHandler):
    """Rotating file handler that compresses old log files with gzip."""

    def doRollover(self):
        """Do a rollover, compressing the old log file."""
        if self.stream:
            self.stream.close()
            self.stream = None

        if self.backupCount > 0:
            # Shift existing compressed files
            for i in range(self.backupCount - 1, 0, -1):
                sfn = self.rotation_filename(f"{self.baseFilename}.{i}.gz")
                dfn = self.rotation_filename(f"{self.baseFilename}.{i + 1}.gz")
                if os.path.exists(sfn):
                    if os.path.exists(dfn):
                        os.remove(dfn)
                    os.rename(sfn, dfn)

            # Compress the current log file
            dfn = self.rotation_filename(f"{self.baseFilename}.1.gz")
            if os.path.exists(dfn):
                os.remove(dfn)

            if os.path.exists(self.baseFilename):
                try:
                    with open(self.baseFilename, 'rb') as f_in:
                        with gzip.open(dfn, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    os.remove(self.baseFilename)
                except Exception:
                    # If compression fails, fallback to regular rotation
                    if os.path.exists(self.baseFilename):
                        backup_name = f"{self.baseFilename}.1"
                        if os.path.exists(backup_name):
                            os.remove(backup_name)
                        os.rename(self.baseFilename, backup_name)

        if not self.delay:
            self.stream = self._open()


class EnhancedLogger:
    """Enhanced logging system with rotation and structured logging"""

    def __init__(self, log_file: str, max_size: int = 50 * 1024 * 1024, backup_count: int = 5,
                 compress_backups: bool = True):
        """Initialize the EnhancedLogger.

        Args:
            log_file: Path to the log file
            max_size: Maximum size of log file before rotation (default: 50MB)
            backup_count: Number of backup files to keep (default: 5)
            compress_backups: Whether to compress old log files (default: True)
        """
        self.log_file = log_file
        self.max_size = max_size
        self.backup_count = backup_count
        self.compress_backups = compress_backups
        self._setup_logging()

    def _setup_logging(self):
        """Setup comprehensive logging configuration using named logger."""
        # Ensure log directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Create named logger (not root logger)
        self.logger = logging.getLogger('MSM')
        self.logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers if logger already configured
        if self.logger.handlers:
            return

        # Prevent propagation to root logger
        self.logger.propagate = False

        # Create rotating file handler (with or without compression)
        if self.compress_backups:
            file_handler = CompressedRotatingFileHandler(
                self.log_file,
                maxBytes=self.max_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_size,
                backupCount=self.backup_count,
                encoding='utf-8'
            )
        file_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)8s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)

        # Clean up old log files (from previous rotation method)
        self._cleanup_old_logs()

    def _cleanup_old_logs(self):
        """Clean up old log files from previous rotation method."""
        try:
            log_dir = os.path.dirname(self.log_file)
            if not log_dir or not os.path.exists(log_dir):
                return

            log_basename = Path(self.log_file).name
            cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days

            for file in os.listdir(log_dir):
                # Match old-style rotated logs (timestamp suffix)
                if file.startswith(log_basename + '.') and file != log_basename:
                    file_path = os.path.join(log_dir, file)
                    try:
                        if os.path.getctime(file_path) < cutoff_time:
                            os.remove(file_path)
                    except (OSError, IOError):
                        pass  # Skip files we can't access
        except Exception:
            pass  # Fail silently for cleanup

    def _rotate_log_if_needed(self):
        """Legacy method - rotation now handled by RotatingFileHandler."""
        pass  # Kept for backward compatibility

    def log(self, level: str, message: str, **kwargs):
        """Enhanced logging with structured data and console output.
        
        Args:
            level: Log level (DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL)
            message: Message to log
            **kwargs: Additional key-value pairs to include in the log
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        color_map = {
            'DEBUG': '\033[2m', 'INFO': '\033[94m', 'SUCCESS': '\033[92m',
            'WARNING': '\033[93m', 'ERROR': '\033[91m', 'CRITICAL': '\033[101m\033[97m'
        }
        color = color_map.get(level.upper(), '\033[0m')
        reset = '\033[0m'
        
        console_msg = f"\033[2m[{timestamp}]{reset} {color}[{level:>7s}]{reset} {message}"
        if kwargs:
            console_msg += f" \033[2m{kwargs}{reset}"
        print(console_msg)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        extra_data = f" | {kwargs}" if kwargs else ""
        self.logger.log(log_level, f"{message}{extra_data}")