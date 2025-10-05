# ============================================================================
# ui.py - Handles printing headers, menus, and progress bars (FIXED)
# ============================================================================
"""
UI components: headers, menus, colors, and formatting.
NO circular dependencies - only imports logger.
"""

import os
from logger import log  # Clean import from logger


class Colors:
    """Terminal color codes."""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GRAY = "\033[90m"


class Icons:
    """UI icons."""
    CHECK = "✓"
    CROSS = "✗"
    ARROW = "→"
    WARNING = "⚠"
    INFO = "ℹ"
    GEAR = "⚙"


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def print_header(version: str):
    """Print application header."""
    clear_screen()
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("=" * 60)
    print(" MSM - Minecraft Server Manager for Termux (Debian)")
    print(f" Version {version}")
    print("=" * 60)
    print(f"{Colors.RESET}")


def print_msg(message: str, color: str = Colors.RESET, icon: str = ""):
    """Print colored message."""
    if icon:
        print(f"{color}{icon} {message}{Colors.RESET}")
    else:
        print(f"{color}{message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print_msg(message, Colors.RED, Icons.CROSS)
    log(message, "ERROR")


def print_success(message: str):
    """Print success message."""
    print_msg(message, Colors.GREEN, Icons.CHECK)
    log(message, "INFO")


def print_warning(message: str):
    """Print warning message."""
    print_msg(message, Colors.YELLOW, Icons.WARNING)
    log(message, "WARNING")


def print_info(message: str):
    """Print info message."""
    print_msg(message, Colors.CYAN, Icons.INFO)
    log(message, "INFO")


class UI:
    """UI helper class with color/icon access."""
    colors = Colors
    icons = Icons
    
    @staticmethod
    def print_menu_options(options):
        """Print menu options in standard format."""
        print(f"{Colors.BOLD}Main Menu:{Colors.RESET}")
        print()
        for num, label in options:
            print(f" {Colors.CYAN}{num}.{Colors.RESET} {label}")
    
    @staticmethod
    def print_success(message: str):
        """Print success without logging (for status display)."""
        print_msg(message, Colors.GREEN, Icons.CHECK)
    
    @staticmethod
    def print_warning(message: str):
        """Print warning without logging (for status display)."""
        print_msg(message, Colors.YELLOW, Icons.WARNING)
    
    @staticmethod
    def print_info(message: str):
        """Print info without logging (for status display)."""
        print_msg(message, Colors.CYAN, Icons.INFO)
