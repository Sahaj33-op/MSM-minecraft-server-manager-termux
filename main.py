# ============================================================================
# main.py - Entry point (OPTIMIZED - managers initialized once)
# ============================================================================
#!/usr/bin/env python3
"""
MSM - Enhanced Minecraft Server Manager for Termux with Debian (proot-distro)
Version: 1.1.0 (Modular, Optimized)
Author: Sahaj33-op
License: MIT
Repository: https://github.com/Sahaj33-op/MSM-minecraft-server-manager-termux
"""

import sys
import argparse
from pathlib import Path

# Add msm directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from environment import EnvironmentManager
from config import ConfigManager, DatabaseManager, get_config_root, get_servers_root
from server_manager import ServerManager
from world_manager import WorldManager
from tunnel_manager import TunnelManager
from ui import UI, print_header, print_info, print_error
from logger import log
from utils import self_update

VERSION = "1.1.0"


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MSM - Minecraft Server Manager for Termux (Debian)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--install-debian-only",
        action="store_true",
        help="Only install Debian via proot-distro and exit"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"MSM v{VERSION}"
    )
    return parser.parse_args()


def main_menu(config_mgr, server_mgr, world_mgr, tunnel_mgr, ui):
    """
    Display and handle main menu.
    Managers are passed in to avoid re-initialization.
    """
    # Check for updates on startup
    from utils import run_command, self_update
    returncode, stdout, stderr = run_command(["git", "rev-parse", "HEAD"])
    if returncode == 0:
        current_commit = stdout.strip()
        returncode, stdout, stderr = run_command(["git", "ls-remote", "origin", "HEAD"])
        if returncode == 0:
            latest_commit = stdout.split()[0]
            if current_commit != latest_commit:
                print()
                ui.print_warning("New version available!")
                print(f"Current: {current_commit[:8]}")
                print(f"Latest:  {latest_commit[:8]}")
                update_choice = input(f"\n{ui.colors.YELLOW}Update now? (y/N): {ui.colors.RESET}").strip().lower()
                if update_choice == 'y':
                    self_update()
                    input("\nPress Enter to continue...")
    
    while True:
        print_header(VERSION)
        
        # Show current server
        current = server_mgr.get_current_server()
        if current:
            ui.print_success(f"Current Server: {current}")
        else:
            ui.print_warning("No server selected")
        
        print()
        ui.print_menu_options([
            ("1", "Start Server"),
            ("2", "Stop Server"),
            ("3", "Install/Update Server"),
            ("4", "Configure Server"),
            ("5", "Server Console"),
            ("6", "World Manager (backup/restore)"),
            ("7", "Statistics"),
            ("8", "Tunneling Manager"),
            ("9", "Environment Manager"),
            ("10", "Performance Monitor"),
            ("11", "Create New Server"),
            ("12", "Switch Server"),
            ("13", "Connection Info"),
            ("14", "Self-update"),
            ("0", "Exit")
        ])
        
        choice = input(f"\n{ui.colors.YELLOW}Select option (0-14): {ui.colors.RESET}").strip()
        
        if choice == "1":
            server_mgr.start_server_menu()
        elif choice == "2":
            server_mgr.stop_server_menu()
        elif choice == "3":
            server_mgr.install_update_menu()
        elif choice == "4":
            server_mgr.configure_server_menu()
        elif choice == "5":
            server_mgr.console_menu()
        elif choice == "6":
            world_mgr.world_manager_menu()
        elif choice == "7":
            server_mgr.statistics_menu()
        elif choice == "8":
            tunnel_mgr.tunneling_menu()
        elif choice == "9":
            EnvironmentManager.environment_menu()
        elif choice == "10":
            server_mgr.monitor_performance_menu()
        elif choice == "11":
            server_mgr.create_server_menu()
        elif choice == "12":
            server_mgr.switch_server_menu()
        elif choice == "13":
            server_mgr.show_connection_info()
        elif choice == "14":
            self_update()
            input("\nPress Enter to continue...")
        elif choice == "0":
            print_info("Exiting MSM. Goodbye!")
            log("MSM exited by user")
            sys.exit(0)
        else:
            print_error("Invalid option. Please try again.")
            import time
            time.sleep(1)


def main():
    """Main entry point."""
    try:
        args = parse_arguments()
        
        # Handle --install-debian-only flag
        if args.install_debian_only:
            log("Starting Debian-only installation mode")
            EnvironmentManager.install_debian_only()
            sys.exit(0)
        
        # Ensure running inside Debian
        EnvironmentManager.ensure_debian_environment()
        
        # Initialize infrastructure
        log("MSM starting up")
        DatabaseManager.init()
        
        # Create necessary directories
        get_config_root().mkdir(parents=True, exist_ok=True)
        get_servers_root().mkdir(parents=True, exist_ok=True)
        
        # Initialize managers ONCE (performance optimization)
        config_mgr = ConfigManager()
        server_mgr = ServerManager()
        world_mgr = WorldManager()
        tunnel_mgr = TunnelManager()
        ui = UI()
        
        # Show main menu with initialized managers
        main_menu(config_mgr, server_mgr, world_mgr, tunnel_mgr, ui)
        
    except KeyboardInterrupt:
        print()
        print_info("MSM interrupted by user")
        log("MSM interrupted by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
