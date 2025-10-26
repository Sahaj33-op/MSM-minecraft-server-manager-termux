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

# Global variables for CLI mode
logger = None
db = None
monitor = None
server_mgr = None
world_mgr = None
tunnel_mgr = None
plugin_mgr = None
scheduler = None

def init_cli_system():
    """Initialize the CLI system components."""
    global logger, db, monitor, server_mgr, world_mgr, tunnel_mgr, plugin_mgr, scheduler
    
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

def list_servers():
    """List all configured servers."""
    servers = server_mgr.list_servers()
    if servers:
        print("Configured servers:")
        for server in servers:
            print(f"  - {server}")
    else:
        print("No servers configured.")

def create_server(name):
    """Create a new server."""
    if server_mgr.create_server(name):
        print(f"Server '{name}' created successfully.")
    else:
        print(f"Failed to create server '{name}'.")
        sys.exit(1)

def delete_server(name):
    """Delete a server."""
    # Note: This is a simplified implementation
    # In a real implementation, you would need to:
    # 1. Stop the server if running
    # 2. Remove the server directory
    # 3. Remove the server from the configuration
    print(f"Server deletion not fully implemented in this CLI version.")
    sys.exit(1)

def start_server(name):
    """Start a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if server_mgr.start_server():
        print(f"Server '{name}' started successfully.")
    else:
        print(f"Failed to start server '{name}'.")
        sys.exit(1)

def stop_server(name):
    """Stop a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if server_mgr.stop_server():
        print(f"Server '{name}' stopped successfully.")
    else:
        print(f"Failed to stop server '{name}'.")
        sys.exit(1)

def install_server(name, server_type, version=None):
    """Install a server."""
    # This is a simplified implementation
    # In a real implementation, you would need to:
    # 1. Set the current server
    # 2. Call the appropriate installation method
    print(f"Server installation not fully implemented in this CLI version.")
    sys.exit(1)

def backup_world(name):
    """Create a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    server_path = Path(os.path.expanduser(f"~/.config/msm/servers/{name}"))
    if world_mgr.create_backup(name, server_path):
        print(f"Backup created for server '{name}'.")
    else:
        print(f"Failed to create backup for server '{name}'.")
        sys.exit(1)

def list_backups(name):
    """List world backups."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    server_path = Path(os.path.expanduser(f"~/.config/msm/servers/{name}"))
    backups = world_mgr.list_backups(server_path)
    if backups:
        print(f"Backups for server '{name}':")
        for backup in backups:
            print(f"  - {backup.name}")
    else:
        print(f"No backups found for server '{name}'.")

def restore_backup(name, backup_name):
    """Restore a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    server_path = Path(os.path.expanduser(f"~/.config/msm/servers/{name}"))
    backup_path = server_path / "backups" / backup_name
    
    if world_mgr.restore_backup(name, server_path, backup_path):
        print(f"Backup '{backup_name}' restored for server '{name}'.")
    else:
        print(f"Failed to restore backup '{backup_name}' for server '{name}'.")
        sys.exit(1)

def delete_backup(name, backup_name):
    """Delete a world backup."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    server_path = Path(os.path.expanduser(f"~/.config/msm/servers/{name}"))
    backup_path = server_path / "backups" / backup_name
    
    if world_mgr.delete_backup(server_path, backup_path):
        print(f"Backup '{backup_name}' deleted for server '{name}'.")
    else:
        print(f"Failed to delete backup '{backup_name}' for server '{name}'.")
        sys.exit(1)

def list_plugins(name):
    """List plugins for a server."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    plugins = plugin_mgr.list_plugins(name)
    if plugins:
        print(f"Plugins for server '{name}':")
        for plugin_name, enabled in plugins:
            status = "enabled" if enabled else "disabled"
            print(f"  - {plugin_name} ({status})")
    else:
        print(f"No plugins found for server '{name}'.")

def install_plugin(name, source):
    """Install a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if plugin_mgr.install_plugin(name, source):
        print(f"Plugin installed from '{source}' for server '{name}'.")
    else:
        print(f"Failed to install plugin from '{source}' for server '{name}'.")
        sys.exit(1)

def enable_plugin(name, plugin_name):
    """Enable a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if plugin_mgr.enable_plugin(name, plugin_name):
        print(f"Plugin '{plugin_name}' enabled for server '{name}'.")
    else:
        print(f"Failed to enable plugin '{plugin_name}' for server '{name}'.")
        sys.exit(1)

def disable_plugin(name, plugin_name):
    """Disable a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if plugin_mgr.disable_plugin(name, plugin_name):
        print(f"Plugin '{plugin_name}' disabled for server '{name}'.")
    else:
        print(f"Failed to disable plugin '{plugin_name}' for server '{name}'.")
        sys.exit(1)

def delete_plugin(name, plugin_name):
    """Delete a plugin."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    if plugin_mgr.delete_plugin(name, plugin_name):
        print(f"Plugin '{plugin_name}' deleted for server '{name}'.")
    else:
        print(f"Failed to delete plugin '{plugin_name}' for server '{name}'.")
        sys.exit(1)

def list_scheduled_tasks():
    """List all scheduled tasks."""
    tasks = scheduler.list_tasks()
    if tasks:
        print("Scheduled tasks:")
        for task in tasks:
            last_run = task.get('last_run_dt')
            last_run_str = last_run.strftime('%Y-%m-%d %H:%M') if last_run else 'Never'
            enabled = "enabled" if task.get('enabled', True) else "disabled"
            print(f"  - ID: {task.get('id')}, Server: {task.get('server')}, Type: {task.get('type')}, "
                  f"Frequency: {task.get('frequency')}, Time: {task.get('time')}, {enabled}, Last run: {last_run_str}")
    else:
        print("No scheduled tasks found.")

def add_scheduled_task(server_name, task_type, frequency, time_str=None):
    """Add a scheduled task."""
    scheduler.add_task(task_type, server_name, frequency, time_str)
    print(f"Scheduled task added for server '{server_name}'.")

def remove_scheduled_task(task_id):
    """Remove a scheduled task."""
    if scheduler.remove_task(task_id):
        print(f"Scheduled task {task_id} removed.")
    else:
        print(f"Failed to remove scheduled task {task_id}.")
        sys.exit(1)

def toggle_scheduled_task(task_id):
    """Toggle a scheduled task."""
    if scheduler.toggle_task(task_id):
        print(f"Scheduled task {task_id} toggled.")
    else:
        print(f"Failed to toggle scheduled task {task_id}.")
        sys.exit(1)

def show_statistics(name):
    """Show server statistics."""
    # Set the current server
    ConfigManager.set_current_server(name)
    
    # This is a simplified implementation
    # In a real implementation, you would need to get actual statistics
    print(f"Statistics for server '{name}' not fully implemented in this CLI version.")
    sys.exit(1)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Minecraft Server Manager CLI")
    parser.add_argument('--version', action='version', version='MSM CLI 1.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
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
    init_cli_system()
    
    # Execute the appropriate command
    try:
        if args.command == 'server':
            if args.server_command == 'list':
                list_servers()
            elif args.server_command == 'create':
                create_server(args.name)
            elif args.server_command == 'delete':
                delete_server(args.name)
            elif args.server_command == 'start':
                start_server(args.name)
            elif args.server_command == 'stop':
                stop_server(args.name)
            elif args.server_command == 'install':
                install_server(args.name, args.type, args.version)
            else:
                parser.print_help()
        
        elif args.command == 'world':
            if args.world_command == 'backup':
                backup_world(args.name)
            elif args.world_command == 'list-backups':
                list_backups(args.name)
            elif args.world_command == 'restore':
                restore_backup(args.name, args.backup)
            elif args.world_command == 'delete-backup':
                delete_backup(args.name, args.backup)
            else:
                parser.print_help()
        
        elif args.command == 'plugin':
            if args.plugin_command == 'list':
                list_plugins(args.name)
            elif args.plugin_command == 'install':
                install_plugin(args.name, args.source)
            elif args.plugin_command == 'enable':
                enable_plugin(args.name, args.plugin)
            elif args.plugin_command == 'disable':
                disable_plugin(args.name, args.plugin)
            elif args.plugin_command == 'delete':
                delete_plugin(args.name, args.plugin)
            else:
                parser.print_help()
        
        elif args.command == 'schedule':
            if args.scheduler_command == 'list':
                list_scheduled_tasks()
            elif args.scheduler_command == 'add':
                add_scheduled_task(args.server, args.type, args.frequency, args.time)
            elif args.scheduler_command == 'remove':
                remove_scheduled_task(args.id)
            elif args.scheduler_command == 'toggle':
                toggle_scheduled_task(args.id)
            else:
                parser.print_help()
        
        elif args.command == 'stats':
            show_statistics(args.name)
        
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()