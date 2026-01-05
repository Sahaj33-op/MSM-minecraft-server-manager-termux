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

def show_health_check(monitor, name=None):
    """Show system and server health check."""
    health = monitor.get_health_check(name)

    # Print overall status with color
    status = health['status']
    status_colors = {'healthy': '\033[92m', 'degraded': '\033[93m', 'unhealthy': '\033[91m'}
    color = status_colors.get(status, '\033[0m')
    reset = '\033[0m'

    print(f"\n{'='*60}")
    print(f"Health Check - {health['timestamp']}")
    print(f"{'='*60}")
    print(f"Overall Status: {color}{status.upper()}{reset}")

    # System info
    if health.get('system'):
        sys_info = health['system']
        print(f"\nSystem:")
        print(f"  CPU Usage:        {sys_info.get('cpu_percent', 'N/A')}%")
        print(f"  Memory Usage:     {sys_info.get('memory_percent', 'N/A')}%")
        print(f"  Memory Available: {sys_info.get('memory_available_mb', 'N/A')} MB")
        print(f"  Disk Usage:       {sys_info.get('disk_percent', 'N/A')}%")
        print(f"  Disk Free:        {sys_info.get('disk_free_gb', 'N/A')} GB")

    # Server info if requested
    if name and health.get('server'):
        srv_info = health['server']
        print(f"\nServer '{name}':")
        print(f"  Status:           {srv_info.get('status', 'unknown')}")
        print(f"  Process Running:  {srv_info.get('process_running', False)}")
        print(f"  Monitoring:       {srv_info.get('monitoring_active', False)}")

    # Warnings
    if health.get('warnings'):
        print(f"\n\033[93mWarnings:{reset}")
        for warning in health['warnings']:
            print(f"  - {warning}")

    # Errors
    if health.get('errors'):
        print(f"\n\033[91mErrors:{reset}")
        for error in health['errors']:
            print(f"  - {error}")

    print()

def show_database_info(db):
    """Show database information and statistics."""
    info = db.get_database_info()

    print(f"\n{'='*60}")
    print("Database Information")
    print(f"{'='*60}")
    print(f"Path:            {info.get('db_path', 'N/A')}")
    print(f"Size:            {info.get('db_size_mb', 0):.2f} MB")
    print(f"Schema Version:  {info.get('schema_version', 'N/A')}")
    print(f"Target Version:  {info.get('target_version', 'N/A')}")

    needs_migration = info.get('needs_migration', False)
    if needs_migration:
        print(f"\033[93mMigration Required: Yes\033[0m")
    else:
        print(f"Migration Status: Up to date")

    # Row counts
    if info.get('row_counts'):
        print(f"\nTable Statistics:")
        for table, count in info['row_counts'].items():
            print(f"  {table}: {count} rows")

    print()

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

    # Health check command
    health_parser = subparsers.add_parser('health', help='Show system and server health check')
    health_parser.add_argument('--server', help='Optional server name for server-specific health')

    # Database info command
    subparsers.add_parser('db-info', help='Show database information and statistics')

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

        elif args.command == 'health':
            show_health_check(monitor, args.server)

        elif args.command == 'db-info':
            show_database_info(db)

        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()