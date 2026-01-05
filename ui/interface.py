#!/usr/bin/env python3
"""
UI Components - From v1.1.0 branch
Color system, header display, and user interface utilities
"""
import os
import sys
import time
import threading
from typing import Optional, Callable, Any
from contextlib import contextmanager

class ColorScheme:
    """Enhanced color system for terminal output"""
    # Base colors
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Standard colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Status colors
    SUCCESS = GREEN
    ERROR = RED
    WARNING = YELLOW
    INFO = BLUE
    DEBUG = DIM

class UI:
    """User interface utilities"""
    colors = ColorScheme()
    
    @staticmethod
    def clear_screen():
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def print_header(version="2.0", system_info=None):
        """Print enhanced header with system info.
        
        Args:
            version: Version string to display
            system_info: Dictionary containing system information
        """
        UI.clear_screen()
        print(f"{UI.colors.BOLD}{UI.colors.CYAN}{'=' * 80}{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}{UI.colors.CYAN}{'':>25} Enhanced Minecraft Server Manager v{version} {'':>25}{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}{UI.colors.CYAN}{'':>15} Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine {'':>15}{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}{UI.colors.CYAN}{'=' * 80}{UI.colors.RESET}")
        
        if system_info:
            ram_info = f"{system_info.get('available_ram_mb', 0)}MB/{system_info.get('total_ram_mb', 0)}MB"
            cpu_info = f"{system_info.get('cpu_count', 0)} cores @ {system_info.get('cpu_usage', 0):.1f}%"
            print(f"{UI.colors.DIM}System: {ram_info} RAM | {cpu_info} CPU{UI.colors.RESET}\n")
    
    @staticmethod
    def print_menu_options(options):
        """Print menu options in a formatted way.
        
        Args:
            options: List of tuples containing (key, label) for menu options
        """
        for key, label in options:
            print(f" {UI.colors.BOLD}{key}.{UI.colors.RESET} {label}")
    
    @staticmethod
    def print_info(message: str):
        """Print info message.
        
        Args:
            message: Message to print
        """
        print(f"{UI.colors.INFO}[INFO]{UI.colors.RESET} {message}")
    
    @staticmethod
    def print_success(message: str):
        """Print success message.
        
        Args:
            message: Message to print
        """
        print(f"{UI.colors.SUCCESS}[SUCCESS]{UI.colors.RESET} {message}")
    
    @staticmethod
    def print_warning(message: str):
        """Print warning message.
        
        Args:
            message: Message to print
        """
        print(f"{UI.colors.WARNING}[WARNING]{UI.colors.RESET} {message}")
    
    @staticmethod
    def print_error(message: str):
        """Print error message.

        Args:
            message: Message to print
        """
        print(f"{UI.colors.ERROR}[ERROR]{UI.colors.RESET} {message}")

    @staticmethod
    def print_progress(current: int, total: int, prefix: str = "", suffix: str = "", bar_length: int = 40):
        """Print a progress bar.

        Args:
            current: Current progress value
            total: Total/maximum value
            prefix: Text to display before the bar
            suffix: Text to display after the bar
            bar_length: Length of the progress bar in characters
        """
        if total <= 0:
            percent = 0.0
            filled = 0
        else:
            percent = current / total
            filled = int(bar_length * percent)

        bar = "█" * filled + "░" * (bar_length - filled)
        percent_str = f"{percent * 100:.1f}%"

        # Use \r to overwrite the line
        sys.stdout.write(f"\r{prefix} |{bar}| {percent_str} {suffix}")
        sys.stdout.flush()

        # Print newline when complete
        if current >= total:
            print()

    @staticmethod
    @contextmanager
    def spinner(message: str = "Working..."):
        """Context manager that shows a spinner animation.

        Args:
            message: Message to display alongside the spinner

        Usage:
            with UI.spinner("Loading"):
                do_long_operation()
        """
        spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        stop_event = threading.Event()

        def spin():
            idx = 0
            while not stop_event.is_set():
                char = spinner_chars[idx % len(spinner_chars)]
                sys.stdout.write(f"\r{UI.colors.CYAN}{char}{UI.colors.RESET} {message}")
                sys.stdout.flush()
                idx += 1
                time.sleep(0.1)
            # Clear the spinner line
            sys.stdout.write("\r" + " " * (len(message) + 4) + "\r")
            sys.stdout.flush()

        spinner_thread = threading.Thread(target=spin, daemon=True)
        spinner_thread.start()

        try:
            yield
        finally:
            stop_event.set()
            spinner_thread.join(timeout=1.0)

    @staticmethod
    def print_step(current: int, total: int, message: str):
        """Print a step indicator (e.g., "Step 2/5: Installing...").

        Args:
            current: Current step number
            total: Total number of steps
            message: Description of the current step
        """
        print(f"{UI.colors.CYAN}[{current}/{total}]{UI.colors.RESET} {message}")


class ProgressTracker:
    """Track progress for multi-step operations.

    Usage:
        tracker = ProgressTracker(total_steps=5, description="Installing server")
        tracker.start()
        for i in range(5):
            tracker.update(i + 1, f"Step {i + 1}")
        tracker.complete("Installation complete!")
    """

    def __init__(self, total_steps: int, description: str = "Processing"):
        """Initialize the progress tracker.

        Args:
            total_steps: Total number of steps in the operation
            description: Description of the overall operation
        """
        self.total_steps = total_steps
        self.description = description
        self.current_step = 0
        self.start_time = None

    def start(self):
        """Start tracking progress."""
        self.start_time = time.time()
        print(f"{UI.colors.CYAN}Starting: {self.description}{UI.colors.RESET}")

    def update(self, step: int, message: str = ""):
        """Update progress to a specific step.

        Args:
            step: Current step number
            message: Description of the current step
        """
        self.current_step = step
        UI.print_step(step, self.total_steps, message)

    def complete(self, message: str = "Complete!"):
        """Mark the operation as complete.

        Args:
            message: Completion message
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"{UI.colors.SUCCESS}✓ {message}{UI.colors.RESET} ({elapsed:.1f}s)")

    def fail(self, message: str = "Failed!"):
        """Mark the operation as failed.

        Args:
            message: Failure message
        """
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"{UI.colors.ERROR}✗ {message}{UI.colors.RESET} ({elapsed:.1f}s)")

# Legacy functions for compatibility
def clear_screen():
    """Clear terminal screen (legacy function)."""
    UI.clear_screen()

def print_header(version="2.0"):
    """Print enhanced header with system info (legacy function).
    
    Args:
        version: Version string to display
    """
    UI.print_header(version)

def print_info(message: str):
    """Print info message (legacy function).
    
    Args:
        message: Message to print
    """
    UI.print_info(message)

def print_success(message: str):
    """Print success message (legacy function).
    
    Args:
        message: Message to print
    """
    UI.print_success(message)

def print_warning(message: str):
    """Print warning message (legacy function).
    
    Args:
        message: Message to print
    """
    UI.print_warning(message)

def print_error(message: str):
    """Print error message (legacy function).
    
    Args:
        message: Message to print
    """
    UI.print_error(message)