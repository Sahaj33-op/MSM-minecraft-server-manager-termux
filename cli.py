<<<<<<< HEAD
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
=======
#!/usr/bin/env python3
"""
MSM CLI - Command Line Interface for Minecraft Server Manager
Provides automation capabilities for server management tasks.
"""
import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import EnhancedLogger
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from core.config import ConfigManager
from managers.server_manager import ServerManager
from managers.world_manager import WorldManager
from managers.tunnel_manager import TunnelManager
from managers.plugin_manager import PluginManager
from core.scheduler import Scheduler

def init_cli_system():
    """Initialize the CLI system components."""
    # Set up paths
    config_dir = Path(os.path.expanduser("~/.config/msm"))
    config_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = config_dir / "msm.log"
    db_file = config_dir / "msm.db"
    
    # Initialize core components
    logger = EnhancedLogger(str(log_file))
    db = DatabaseManager(str(db_file))
    monitor = PerformanceMonitor(db, logger)
    
    # Initialize managers
    server_mgr = ServerManager(db, logger, monitor)
    world_mgr = WorldManager(logger)
    tunnel_mgr = TunnelManager(logger)
    plugin_mgr = PluginManager(logger)
    scheduler = Scheduler(config_dir, logger, server_mgr, world_mgr)
    
    return logger, db, monitor, server_mgr, world_mgr, tunnel_mgr, plugin_mgr, scheduler

def list_servers(server_mgr):
    """List all configured servers."""
    servers = server_mgr.list_servers()
    if servers:
        print("Configured servers:")
        for server in servers:
            print(f"  - {server}")
    else:
        print("No servers configured.")

def create_server(server_mgr, name):
    """Create a new server."""
    if server_mgr.create_server(name):
        print(f"Server '{name}' created successfully.")
    else:
        print(f"Failed to create server '{name}'.")
        sys.exit(1)

def delete_server(server_mgr, name):
    """Delete a server."""
    # Get server path
    from utils.helpers import get_server_directory
    server_path = get_server_directory(name)
    
    # Stop server if running
    current_server = server_mgr.get_current_server()
    if current_server == name:
        if server_mgr.stop_server():
            print(f"Server '{name}' stopped.")
        else:
            print(f"Warning: Could not stop server '{name}'.")
    
    # Remove server directory
    if server_path.exists():
        import shutil
        try:
            shutil.rmtree(server_path)
            print(f"Server directory for '{name}' removed.")
        except Exception as e:
            print(f"Warning: Could not remove server directory: {e}")
    
    # Remove from configuration
    config = ConfigManager.load()
    if 'servers' in config and name in config['servers']:
        del config['servers'][name]
        if config.get('current_server') == name:
            config['current_server'] = None
            # Set a new current server if available
            if config['servers']:
                config['current_server'] = list(config['servers'].keys())[0]
        ConfigManager.save(config)
        print(f"Server '{name}' removed from configuration.")
    else:
        print(f"Server '{name}' not found in configuration.")
    
    print(f"Server '{name}' deleted successfully.")

def start_server(server_mgr, name):
    """Start a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if server_mgr.start_server():
        print(f"Server '{name}' started successfully.")
    else:
        print(f"Failed to start server '{name}'.")
        sys.exit(1)

def stop_server(server_mgr, name):
    """Stop a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if server_mgr.stop_server():
        print(f"Server '{name}' stopped successfully.")
    else:
        print(f"Failed to stop server '{name}'.")
        sys.exit(1)

def install_server(server_mgr, name, server_type, version=None):
    """Install a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # Map server type to number
    server_type_map = {
        'paper': '1',
        'purpur': '2',
        'folia': '3',
        'fabric': '4',
        'quilt': '5',
        'vanilla': '6',
        'pocketmine': '7'
    }
    
    if server_type.lower() not in server_type_map:
        print(f"Invalid server type: {server_type}")
        print("Valid types: paper, purpur, folia, fabric, quilt, vanilla, pocketmine")
        sys.exit(1)
    
    choice = server_type_map[server_type.lower()]
    
    # Get the API class
    server_type_name, api_class, flavor_key = ServerManager.SERVER_TYPES[choice]
    
    # If no version specified, get the latest
    if not version:
        try:
            versions = api_class.get_versions()
            if versions:
                version = versions[-1]
            else:
                print(f"Could not fetch versions for {server_type_name}")
                sys.exit(1)
        except Exception as e:
            print(f"Error fetching versions for {server_type_name}: {e}")
            sys.exit(1)
    
    # Download the server
    try:
        if server_mgr._download_server(name, server_type_name, api_class, version, flavor_key):
            print(f"{server_type_name} {version} installed successfully for server '{name}'.")
        else:
            print(f"Failed to install {server_type_name} {version} for server '{name}'.")
            sys.exit(1)
    except Exception as e:
        print(f"Error installing {server_type_name} {version}: {e}")
        sys.exit(1)

def backup_world(world_mgr, name):
    """Create a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    from utils.helpers import get_server_directory
    server_path = get_server_directory(name)
    if world_mgr.create_backup(name, server_path):
        print(f"Backup created for server '{name}'.")
    else:
        print(f"Failed to create backup for server '{name}'.")
        sys.exit(1)

def list_backups(world_mgr, name):
    """List world backups."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    from utils.helpers import get_server_directory
    server_path = get_server_directory(name)
    backups = world_mgr.list_backups(server_path)
    if backups:
        print(f"Backups for server '{name}':")
        for backup in backups:
            print(f"  - {backup.name}")
    else:
        print(f"No backups found for server '{name}'.")

def restore_backup(world_mgr, server_mgr, name, backup_name):
    """Restore a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    from utils.helpers import get_server_directory
    server_path = get_server_directory(name)
    backup_path = server_path / "backups" / backup_name
    
    # Stop server if running
    if server_mgr.get_current_server() == name:
        server_mgr.stop_server()
    
    if world_mgr.restore_backup(name, server_path, backup_path):
        print(f"Backup '{backup_name}' restored for server '{name}'.")
    else:
        print(f"Failed to restore backup '{backup_name}' for server '{name}'.")
        sys.exit(1)

def delete_backup(world_mgr, name, backup_name):
    """Delete a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    from utils.helpers import get_server_directory
    server_path = get_server_directory(name)
    backup_path = server_path / "backups" / backup_name
    
    if world_mgr.delete_backup(server_path, backup_path):
        print(f"Backup '{backup_name}' deleted for server '{name}'.")
    else:
        print(f"Failed to delete backup '{backup_name}' for server '{name}'.")
        sys.exit(1)

def list_plugins(plugin_mgr, name):
    """List plugins for a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    try:
        plugins = plugin_mgr.list_plugins(name)
        if plugins:
            print(f"Plugins for server '{name}':")
            for plugin_name, enabled in plugins:
                status = "enabled" if enabled else "disabled"
                print(f"  - {plugin_name} ({status})")
        else:
            print(f"No plugins found for server '{name}'.")
    except Exception as e:
        print(f"Error listing plugins: {e}")
        sys.exit(1)

def install_plugin(plugin_mgr, name, source):
    """Install a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    try:
        plugin_mgr.install_plugin(name, source)
        print(f"Plugin installed from '{source}' for server '{name}'.")
    except Exception as e:
        print(f"Error installing plugin: {e}")
        sys.exit(1)

def enable_plugin(plugin_mgr, name, plugin_name):
    """Enable a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    try:
        plugin_mgr.enable_plugin(name, plugin_name)
        print(f"Plugin '{plugin_name}' enabled for server '{name}'.")
    except Exception as e:
        print(f"Error enabling plugin: {e}")
        sys.exit(1)

def disable_plugin(plugin_mgr, name, plugin_name):
    """Disable a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    try:
        plugin_mgr.disable_plugin(name, plugin_name)
        print(f"Plugin '{plugin_name}' disabled for server '{name}'.")
    except Exception as e:
        print(f"Error disabling plugin: {e}")
        sys.exit(1)

def delete_plugin(plugin_mgr, name, plugin_name):
    """Delete a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    try:
        plugin_mgr.delete_plugin(name, plugin_name)
        print(f"Plugin '{plugin_name}' deleted for server '{name}'.")
    except Exception as e:
        print(f"Error deleting plugin: {e}")
        sys.exit(1)

def list_scheduled_tasks(scheduler):
    """List all scheduled tasks."""
    tasks = scheduler.list_tasks()
    if tasks:
        print("Scheduled tasks:")
        print(f"{'ID':<6} {'Server':<15} {'Type':<10} {'Frequency':<15} {'Time':<6} {'Enabled':<8} {'Last Run'}")
        print("-" * 80)
        for task in tasks:
            last_run = task.get('last_run_dt')
            last_run_str = last_run.strftime('%Y-%m-%d %H:%M') if last_run else 'Never'
            enabled = "enabled" if task.get('enabled', True) else "disabled"
            print(f"{task.get('id', 'N/A'):<6} {task.get('server', 'N/A'):<15} {task.get('type', 'N/A'):<10} {task.get('frequency', 'N/A'):<15} {task.get('time', '--'):<6} {enabled:<8} {last_run_str}")
    else:
        print("No scheduled tasks found.")

def add_scheduled_task(scheduler, server_name, task_type, frequency, time_str=None):
    """Add a scheduled task."""
    scheduler.add_task(task_type, server_name, frequency, time_str)
    print(f"Scheduled task added for server '{server_name}'.")

def remove_scheduled_task(scheduler, task_id):
    """Remove a scheduled task."""
    if scheduler.remove_task(task_id):
        print(f"Scheduled task {task_id} removed.")
    else:
        print(f"Failed to remove scheduled task {task_id}.")
        sys.exit(1)

def toggle_scheduled_task(scheduler, task_id):
    """Toggle a scheduled task."""
    if scheduler.toggle_task(task_id):
        print(f"Scheduled task {task_id} toggled.")
    else:
        print(f"Failed to toggle scheduled task {task_id}.")
        sys.exit(1)

def show_statistics(db, name):
    """Show server statistics."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # Get statistics from database
    stats = db.get_server_statistics(name)
    
    print(f"Statistics for server '{name}':")
    print(f"  Total sessions: {stats.get('total_sessions', 0)}")
    print(f"  Average session duration: {stats.get('avg_duration', 0):.0f} seconds")
    print(f"  Total uptime: {stats.get('total_uptime', 0)} seconds")
    print(f"  Total crashes: {stats.get('total_crashes', 0)}")
    print(f"  Total restarts: {stats.get('total_restarts', 0)}")
    print(f"  Average RAM usage (24h): {stats.get('avg_ram_usage_24h', 0):.1f}%")
    print(f"  Average CPU usage (24h): {stats.get('avg_cpu_usage_24h', 0):.1f}%")
    print(f"  Peak players (24h): {stats.get('peak_players_24h', 0)}")

def configure_server(name, setting, value):
    """Configure a server setting."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # Load current config
    server_config = ConfigManager.load_server_config(name)
    
    # Update the setting
    if 'server_settings' not in server_config:
        server_config['server_settings'] = {}
    
    server_config['server_settings'][setting] = value
    
    # Save config
    ConfigManager.save_server_config(name, server_config)
    
    print(f"Setting '{setting}' updated to '{value}' for server '{name}'.")

def show_performance_dashboard(server_mgr, name):
    """Show performance dashboard for a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # Use the server manager's dashboard method
    server_mgr.show_performance_dashboard()

def show_server_console(server_mgr, name):
    """Show server console for a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # Use the server manager's console method
    server_mgr.show_console()

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Minecraft Server Manager CLI")
    parser.add_argument('--version', action='version', version='MSM CLI 1.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add performance dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Show performance dashboard for a server')
    dashboard_parser.add_argument('name', help='Server name')
    
    # Add server console command
    console_parser = subparsers.add_parser('console', help='Show server console')
    console_parser.add_argument('name', help='Server name')
    
    # Server commands
    server_parser = subparsers.add_parser('server', help='Server management commands')
    server_subparsers = server_parser.add_subparsers(dest='server_command')
    
    server_subparsers.add_parser('list', help='List all servers')
    
    create_parser = server_subparsers.add_parser('create', help='Create a new server')
    create_parser.add_argument('name', help='Server name')
    
    delete_parser = server_subparsers.add_parser('delete', help='Delete a server')
    delete_parser.add_argument('name', help='Server name')
    
    start_parser = server_subparsers.add_parser('start', help='Start a server')
    start_parser.add_argument('name', help='Server name')
    
    stop_parser = server_subparsers.add_parser('stop', help='Stop a server')
    stop_parser.add_argument('name', help='Server name')
    
    install_parser = server_subparsers.add_parser('install', help='Install a server')
    install_parser.add_argument('name', help='Server name')
    install_parser.add_argument('type', help='Server type (paper, purpur, etc.)')
    install_parser.add_argument('--version', help='Server version')
    
    configure_parser = server_subparsers.add_parser('configure', help='Configure server settings')
    configure_parser.add_argument('name', help='Server name')
    configure_parser.add_argument('setting', help='Setting name')
    configure_parser.add_argument('value', help='Setting value')
    
    # World commands
    world_parser = subparsers.add_parser('world', help='World management commands')
    world_subparsers = world_parser.add_subparsers(dest='world_command')
    
    backup_parser = world_subparsers.add_parser('backup', help='Create a world backup')
    backup_parser.add_argument('name', help='Server name')
    
    list_backups_parser = world_subparsers.add_parser('list-backups', help='List world backups')
    list_backups_parser.add_argument('name', help='Server name')
    
    restore_parser = world_subparsers.add_parser('restore', help='Restore a world backup')
    restore_parser.add_argument('name', help='Server name')
    restore_parser.add_argument('backup', help='Backup name')
    
    delete_backup_parser = world_subparsers.add_parser('delete-backup', help='Delete a world backup')
    delete_backup_parser.add_argument('name', help='Server name')
    delete_backup_parser.add_argument('backup', help='Backup name')
    
    # Plugin commands
    plugin_parser = subparsers.add_parser('plugin', help='Plugin management commands')
    plugin_subparsers = plugin_parser.add_subparsers(dest='plugin_command')
    
    list_plugins_parser = plugin_subparsers.add_parser('list', help='List plugins')
    list_plugins_parser.add_argument('name', help='Server name')
    
    install_plugin_parser = plugin_subparsers.add_parser('install', help='Install a plugin')
    install_plugin_parser.add_argument('name', help='Server name')
    install_plugin_parser.add_argument('source', help='Plugin source (URL or file path)')
    
    enable_plugin_parser = plugin_subparsers.add_parser('enable', help='Enable a plugin')
    enable_plugin_parser.add_argument('name', help='Server name')
    enable_plugin_parser.add_argument('plugin', help='Plugin name')
    
    disable_plugin_parser = plugin_subparsers.add_parser('disable', help='Disable a plugin')
    disable_plugin_parser.add_argument('name', help='Server name')
    disable_plugin_parser.add_argument('plugin', help='Plugin name')
    
    delete_plugin_parser = plugin_subparsers.add_parser('delete', help='Delete a plugin')
    delete_plugin_parser.add_argument('name', help='Server name')
    delete_plugin_parser.add_argument('plugin', help='Plugin name')
    
    # Scheduler commands
    scheduler_parser = subparsers.add_parser('schedule', help='Scheduler commands')
    scheduler_subparsers = scheduler_parser.add_subparsers(dest='scheduler_command')
    
    scheduler_subparsers.add_parser('list', help='List scheduled tasks')
    
    add_task_parser = scheduler_subparsers.add_parser('add', help='Add a scheduled task')
    add_task_parser.add_argument('server', help='Server name')
    add_task_parser.add_argument('type', choices=['backup', 'restart'], help='Task type')
    add_task_parser.add_argument('frequency', help='Task frequency (hourly, daily, weekly@day)')
    add_task_parser.add_argument('--time', help='Time for daily/weekly tasks (HH:MM)')
    
    remove_task_parser = scheduler_subparsers.add_parser('remove', help='Remove a scheduled task')
    remove_task_parser.add_argument('id', type=int, help='Task ID')
    
    toggle_task_parser = scheduler_subparsers.add_parser('toggle', help='Toggle a scheduled task')
    toggle_task_parser.add_argument('id', type=int, help='Task ID')
    
    # Statistics command
    stats_parser = subparsers.add_parser('stats', help='Show server statistics')
    stats_parser.add_argument('name', help='Server name')
    
    args = parser.parse_args()
    
    # Initialize the system
    logger, db, monitor, server_mgr, world_mgr, tunnel_mgr, plugin_mgr, scheduler = init_cli_system()
    
    # Execute the appropriate command
    try:
        if args.command == 'server':
            if args.server_command == 'list':
                list_servers(server_mgr)
            elif args.server_command == 'create':
                create_server(server_mgr, args.name)
            elif args.server_command == 'delete':
                delete_server(server_mgr, args.name)
            elif args.server_command == 'start':
                start_server(server_mgr, args.name)
            elif args.server_command == 'stop':
                stop_server(server_mgr, args.name)
            elif args.server_command == 'install':
                install_server(server_mgr, args.name, args.type, args.version)
            elif args.server_command == 'configure':
                configure_server(args.name, args.setting, args.value)
            else:
                parser.print_help()
        
        elif args.command == 'world':
            if args.world_command == 'backup':
                backup_world(world_mgr, args.name)
            elif args.world_command == 'list-backups':
                list_backups(world_mgr, args.name)
            elif args.world_command == 'restore':
                restore_backup(world_mgr, server_mgr, args.name, args.backup)
            elif args.world_command == 'delete-backup':
                delete_backup(world_mgr, args.name, args.backup)
            else:
                parser.print_help()
        
        elif args.command == 'plugin':
            if args.plugin_command == 'list':
                list_plugins(plugin_mgr, args.name)
            elif args.plugin_command == 'install':
                install_plugin(plugin_mgr, args.name, args.source)
            elif args.plugin_command == 'enable':
                enable_plugin(plugin_mgr, args.name, args.plugin)
            elif args.plugin_command == 'disable':
                disable_plugin(plugin_mgr, args.name, args.plugin)
            elif args.plugin_command == 'delete':
                delete_plugin(plugin_mgr, args.name, args.plugin)
            else:
                parser.print_help()
        
        elif args.command == 'schedule':
            if args.scheduler_command == 'list':
                list_scheduled_tasks(scheduler)
            elif args.scheduler_command == 'add':
                add_scheduled_task(scheduler, args.server, args.type, args.frequency, args.time)
            elif args.scheduler_command == 'remove':
                remove_scheduled_task(scheduler, args.id)
            elif args.scheduler_command == 'toggle':
                toggle_scheduled_task(scheduler, args.id)
            else:
                parser.print_help()
        
        elif args.command == 'stats':
            show_statistics(db, args.name)
        
        elif args.command == 'dashboard':
            show_performance_dashboard(server_mgr, args.name)
        
        elif args.command == 'console':
            show_server_console(server_mgr, args.name)
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
>>>>>>> unify-merge-for-release
    main()