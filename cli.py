#!/usr/bin/env python3
"""
Command-line interface for MSM (Minecraft Server Manager).
Provides direct command-line access to MSM functions.
"""

import argparse
import sys
from pathlib import Path

# Add msm directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from environment import EnvironmentManager
from config import ConfigManager, DatabaseManager, get_config_root, get_servers_root
from server_manager import ServerManager
from world_manager import WorldManager
from tunnel_manager import TunnelManager
from logger import log, log_info, log_error
from utils import self_update


def setup_environment():
    """Ensure proper environment setup."""
    try:
        # Initialize infrastructure
        log_info("MSM CLI starting up")
        DatabaseManager.init()
        
        # Create necessary directories
        get_config_root().mkdir(parents=True, exist_ok=True)
        get_servers_root().mkdir(parents=True, exist_ok=True)
        
        return True
    except Exception as e:
        log_error("Failed to setup environment", e)
        return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MSM - Minecraft Server Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Server commands
    server_parser = subparsers.add_parser("server", help="Server management commands")
    server_subparsers = server_parser.add_subparsers(dest="server_command")
    
    # Create server
    create_parser = server_subparsers.add_parser("create", help="Create a new server")
    create_parser.add_argument("name", help="Server name")
    
    # Start server
    start_parser = server_subparsers.add_parser("start", help="Start a server")
    start_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Stop server
    stop_parser = server_subparsers.add_parser("stop", help="Stop a server")
    stop_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Install/Update server
    install_parser = server_subparsers.add_parser("install", help="Install or update server software")
    install_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Configure server
    config_parser = server_subparsers.add_parser("configure", help="Configure server settings")
    config_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Server console
    console_parser = server_subparsers.add_parser("console", help="Attach to server console")
    console_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Performance monitor
    monitor_parser = server_subparsers.add_parser("monitor", help="Monitor server performance")
    monitor_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # List servers
    server_subparsers.add_parser("list", help="List all servers")
    
    # Switch server
    switch_parser = server_subparsers.add_parser("switch", help="Switch current server")
    switch_parser.add_argument("name", help="Server name")
    
    # World commands
    world_parser = subparsers.add_parser("world", help="World management commands")
    world_subparsers = world_parser.add_subparsers(dest="world_command")
    
    # Backup world
    backup_parser = world_subparsers.add_parser("backup", help="Create world backup")
    backup_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # List backups
    list_backup_parser = world_subparsers.add_parser("list-backups", help="List world backups")
    list_backup_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Restore backup
    restore_parser = world_subparsers.add_parser("restore", help="Restore world from backup")
    restore_parser.add_argument("name", nargs="?", help="Server name (uses current if not specified)")
    
    # Tunnel commands
    tunnel_parser = subparsers.add_parser("tunnel", help="Tunnel management commands")
    tunnel_subparsers = tunnel_parser.add_subparsers(dest="tunnel_command")
    
    # Setup tunnel
    setup_tunnel_parser = tunnel_subparsers.add_parser("setup", help="Setup tunneling service")
    setup_tunnel_parser.add_argument("service", choices=["playit", "ngrok", "cloudflared"], help="Tunneling service")
    
    # Statistics commands
    stats_parser = subparsers.add_parser("stats", help="Server statistics")
    stats_subparsers = stats_parser.add_subparsers(dest="stats_command")
    
    # Show statistics
    stats_subparsers.add_parser("show", help="Show server statistics")
    
    # Environment commands
    env_parser = subparsers.add_parser("environment", help="Environment management commands")
    env_subparsers = env_parser.add_subparsers(dest="env_command")
    
    # Check environment
    env_subparsers.add_parser("check", help="Check environment status")
    
    # Update command
    subparsers.add_parser("update", help="Update MSM to latest version")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup environment
    if not setup_environment():
        print("Failed to setup environment")
        sys.exit(1)
    
    # Initialize managers
    server_mgr = ServerManager()
    world_mgr = WorldManager()
    tunnel_mgr = TunnelManager()
    
    # Handle commands
    if args.command == "server":
        handle_server_commands(args, server_mgr)
    elif args.command == "world":
        handle_world_commands(args, server_mgr, world_mgr)
    elif args.command == "tunnel":
        handle_tunnel_commands(args, tunnel_mgr)
    elif args.command == "stats":
        handle_stats_commands(args, server_mgr)
    elif args.command == "environment":
        handle_environment_commands(args)
    elif args.command == "update":
        handle_update_command()
    else:
        parser.print_help()


def handle_server_commands(args, server_mgr):
    """Handle server-related commands."""
    if args.server_command == "create":
        # For CLI, we need to simulate the menu behavior
        # This is a simplified version - in a real implementation, 
        # you would want to add parameters for server type, version, etc.
        try:
            server_path = get_servers_root() / args.name
            
            if server_path.exists():
                print(f"Server '{args.name}' already exists")
                sys.exit(1)
            
            print(f"Creating server: {args.name}")
            
            import time
            from utils import suggest_ram_allocation
            
            server_path.mkdir(parents=True, exist_ok=True)
            
            config = {
                "name": args.name,
                "created": int(time.time()),
                "ram_mb": suggest_ram_allocation(),
                "port": 25565,
                "version": "latest"
            }
            
            ConfigManager.save_server_config(args.name, config)
            DatabaseManager.add_server(args.name, int(time.time()))
            
            server_mgr.set_current_server(args.name)
            
            print(f"Server '{args.name}' created successfully")
            log_info(f"Server created: {args.name}")
            
        except Exception as e:
            print(f"Failed to create server: {e}")
            log_error(f"Server creation failed: {e}")
            sys.exit(1)
            
    elif args.server_command == "start":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
        
        # Call the start server method
        server_mgr.start_server_menu()
        
    elif args.server_command == "stop":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
            
        # Call the stop server method
        server_mgr.stop_server_menu()
        
    elif args.server_command == "install":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
            
        # Call the install update method
        server_mgr.install_update_menu()
        
    elif args.server_command == "configure":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
            
        # Call the configure server method
        server_mgr.configure_server_menu()
        
    elif args.server_command == "console":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
            
        # Call the console method
        server_mgr.console_menu()
        
    elif args.server_command == "monitor":
        # Set current server if specified
        if args.name:
            server_mgr.set_current_server(args.name)
            
        # Call the monitor performance method
        server_mgr.monitor_performance_menu()
        
    elif args.server_command == "list":
        servers = server_mgr.list_servers()
        if servers:
            print("Available servers:")
            for server in servers:
                marker = " (current)" if server == server_mgr.get_current_server() else ""
                print(f"  {server}{marker}")
        else:
            print("No servers found")
            
    elif args.server_command == "switch":
        servers = server_mgr.list_servers()
        if args.name in servers:
            server_mgr.set_current_server(args.name)
            print(f"Switched to server: {args.name}")
        else:
            print(f"Server '{args.name}' not found")
            sys.exit(1)


def handle_world_commands(args, server_mgr, world_mgr):
    """Handle world-related commands."""
    # Set current server if specified
    if args.name:
        server_mgr.set_current_server(args.name)
    
    if args.world_command == "backup":
        world_mgr.create_backup(server_mgr.get_current_server() or args.name)
    elif args.world_command == "list-backups":
        world_mgr.list_backups(server_mgr.get_current_server() or args.name)
    elif args.world_command == "restore":
        world_mgr.restore_backup(server_mgr.get_current_server() or args.name)


def handle_tunnel_commands(args, tunnel_mgr):
    """Handle tunnel-related commands."""
    if args.tunnel_command == "setup":
        if args.service == "playit":
            tunnel_mgr.setup_playit()
        elif args.service == "ngrok":
            tunnel_mgr.setup_ngrok()
        elif args.service == "cloudflared":
            tunnel_mgr.setup_cloudflared()


def handle_stats_commands(args, server_mgr):
    """Handle statistics commands."""
    if args.stats_command == "show":
        server_mgr.statistics_menu()


def handle_environment_commands(args):
    """Handle environment-related commands."""
    if args.env_command == "check":
        EnvironmentManager.environment_menu()


def handle_update_command():
    """Handle update command."""
    self_update()


if __name__ == "__main__":
    main()