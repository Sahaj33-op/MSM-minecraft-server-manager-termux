#!/usr/bin/env python3
"""
Enhanced Logger - Extracted from main branch msm.py
Professional logging with rotation, levels, and dual output
"""
import os
import time
import logging
from datetime import datetime
from pathlib import Path

class EnhancedLogger:
    """Enhanced logging system with rotation and structured logging"""
    def __init__(self, log_file: str, max_size: int = 50 * 1024 * 1024):
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
                cutoff_time = time.time() - (30 * 24 * 3600)  # 30 days
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