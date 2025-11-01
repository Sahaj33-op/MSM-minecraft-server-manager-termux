#!/usr/bin/env python3
"""
UI Components - From v1.1.0 branch
Color system, header display, and user interface utilities
"""
import os

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