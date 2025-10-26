#!/usr/bin/env python3
"""
MSM Unified - Complete modular implementation
"""
import os
import sys
import signal
import time
import argparse
import psutil  # For getting live metrics
import re      # For finding PID
from pathlib import Path  # Import Path
from utils.helpers import is_screen_session_running, get_screen_session_name, check_dependencies, get_server_directory, run_command  # To find log file

# Add imports for custom exceptions
from core.exceptions import MSMError, APIError, DownloadError, ConfigError
from core.logger import EnhancedLogger
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from core.config import ConfigManager
from core import scheduler  # Import scheduler
from managers.server_manager import ServerManager
from managers.world_manager import WorldManager
from managers.tunnel_manager import TunnelManager
from managers.plugin_manager import PluginManager  # Import PluginManager
from ui.interface import UI

VERSION = "Unified"

# Default locations
CONFIG_DIR = os.path.expanduser("~/.config/msm")
LOG_FILE = os.path.join(CONFIG_DIR, "msm.log")
DB_FILE = os.path.join(CONFIG_DIR, "msm.db")

# Globals
logger = None
db = None
monitor = None
ui = None
server_mgr = None
world_mgr = None
tunnel_mgr = None
plugin_mgr = None  # Plugin Manager
global_scheduler = None  # Scheduler

def graceful_shutdown(signum=None, frame=None):
    """Gracefully shutdown the application, stopping all services."""
    try:
        if server_mgr is not None:
            cur = server_mgr.get_current_server()
            if cur and monitor is not None:
                # Best-effort stop monitor threads before exit
                monitor.stop_monitoring(cur)
        # Stop the scheduler
        if global_scheduler is not None:
            global_scheduler.stop()
    except Exception:
        pass
    if logger is not None:
        logger.log('INFO', "MSM shutting down.")
    sys.exit(0)

def ensure_infra():
    """Ensure the infrastructure directories exist."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def init_system():
    """Initialize all system components including managers, database, logger, etc."""
    global logger, db, monitor, ui, server_mgr, world_mgr, tunnel_mgr, plugin_mgr, global_scheduler

    ensure_infra()
    logger = EnhancedLogger(LOG_FILE)
    db = DatabaseManager(DB_FILE)
    monitor = PerformanceMonitor(db, logger)
    ui = UI()

    server_mgr = ServerManager(db, logger, monitor)
    world_mgr = WorldManager(logger)
    tunnel_mgr = TunnelManager(logger)
    plugin_mgr = PluginManager(logger, ui)  # Initialize PluginManager
    global_scheduler = scheduler.Scheduler(Path(CONFIG_DIR), logger, server_mgr, world_mgr)  # Initialize Scheduler
    global_scheduler.start()  # Start the scheduler

    # Select a default server if none set
    cfg = ConfigManager.load()
    if not cfg.get("current_server") and cfg.get("servers"):
        first = list(cfg["servers"].keys())[0]
        ConfigManager.set_current_server(first)

def configure_menu():
    """Configuration menu for server settings"""
    if server_mgr is None or ui is None or logger is None:
        print("Error: System not initialized properly")
        return
        
    # Use the enhanced configuration menu
    server_mgr.configure_server_menu()

def world_menu():
    """World management menu"""
    if server_mgr is None or ui is None or world_mgr is None:
        print("Error: System not initialized properly")
        return
        
    cur = server_mgr.get_current_server()
    if not cur:
        ui.print_error("No server selected")
        input("\nPress Enter to continue...")
        return
    from utils.helpers import get_server_directory
    server_path = get_server_directory(cur)
    print("\nWorld Manager:")
    print(" 1. Create Backup")
    print(" 2. List Backups")
    print(" 3. Restore Backup")
    print(" 4. Delete Backup")
    print(" 0. Back")
    sub = input("\nSelect (0-4): ").strip()
    if sub == "1":
        world_mgr.create_backup(cur, server_path)
        input("\nPress Enter to continue...")
    elif sub == "2":
        backups = world_mgr.list_backups(server_path)
        print("\nBackups:")
        for b in backups:
            print(f" - {b}")
        input("\nPress Enter to continue...")
    elif sub == "3":
        backups = world_mgr.list_backups(server_path)
        if not backups:
            ui.print_info("No backups found")
            input("\nPress Enter to continue...")
            return
        print("\nAvailable Backups:")
        for i, b in enumerate(backups, 1):
            print(f" {i}. {b}")
        pick = input("\nSelect backup #: ").strip()
        try:
            idx = int(pick) - 1
            if 0 <= idx < len(backups):
                world_mgr.restore_backup(cur, server_path, backups[idx])
        except Exception:
            ui.print_error("Invalid selection")
        input("\nPress Enter to continue...")
    elif sub == "4":
        backups = world_mgr.list_backups(server_path)
        if not backups:
            ui.print_info("No backups found")
            input("\nPress Enter to continue...")
            return
        print("\nAvailable Backups:")
        for i, b in enumerate(backups, 1):
            print(f" {i}. {b}")
        pick = input("\nSelect backup #: ").strip()
        try:
            idx = int(pick) - 1
            if 0 <= idx < len(backups):
                world_mgr.delete_backup(server_path, backups[idx])
        except Exception:
            ui.print_error("Invalid selection")
        input("\nPress Enter to continue...")

def tunnel_menu():
    """Tunneling menu"""
    if server_mgr is None or ui is None or tunnel_mgr is None or logger is None:
        print("Error: System not initialized properly")
        return
        
    cur = server_mgr.get_current_server()
    if not cur:
        ui.print_error("No server selected")
        input("\nPress Enter to continue...")
        return
    cfg = ConfigManager.load_server_config(cur)
    port = cfg.get('server_settings', {}).get('port', 25565)
    print("\nTunneling:")
    print(" 1. ngrok (Termux-native)")
    print(" 2. cloudflared (Termux-native)")
    print(" 3. pinggy (Termux-native)")
    print(" 4. playit.gg (requires proot Debian)")
    print(" 5. Show tunnel status")
    print(" 0. Back")
    sub = input("\nSelect (0-5): ").strip()
    ok = False
    if sub == "1":
        ok = tunnel_mgr.start_ngrok(port)
    elif sub == "2":
        ok = tunnel_mgr.start_cloudflared(port)
    elif sub == "3":
        ok = tunnel_mgr.start_pinggy(port)
    elif sub == "4":
        ok = tunnel_mgr.start_playit(port)  # will prompt for proot if needed
    elif sub == "5":
        # Show tunnel status
        tunnels = tunnel_mgr.list_tunnels()
        print("\nTunnel Status:")
        for name, info in tunnels.items():
            print(f"  {name}: {info['status']} - {info['url']}")
        input("\nPress Enter to continue...")
        return
    if ok:
        logger.log('SUCCESS', "Tunnel start requested")
    input("\nPress Enter to continue...")

def server_switch_menu():
    """Create or switch server menu"""
    if server_mgr is None or ui is None:
        print("Error: System not initialized properly")
        return
        
    print("\nServers:")
    servers = server_mgr.list_servers()
    for i, s in enumerate(servers, 1):
        print(f" {i}. {s}")
    print(" n. Create new")
    sel = input("\nSelect #: ").strip().lower()
    if sel == "n":
        name = input("Enter new server name: ").strip()
        if name:
            server_mgr.create_server(name)
    else:
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(servers):
                server_mgr.set_current_server(servers[idx])
        except Exception:
            ui.print_error("Invalid selection")

def show_performance_dashboard():
    """Display live performance metrics for the current server."""
    if server_mgr is None or ui is None or logger is None:
        print("Error: System not initialized properly")
        input("\nPress Enter to continue...")
        return

    current_server = server_mgr.get_current_server()
    if not current_server:
        ui.print_error("No server selected")
        input("\nPress Enter to continue...")
        return

    screen_name = get_screen_session_name(current_server)

    if not is_screen_session_running(screen_name):
        ui.print_warning(f"Server '{current_server}' is not running.")
        input("\nPress Enter to continue...")
        return

    logger.log('INFO', f"Starting performance dashboard for {current_server}")
    print(f"{ui.colors.CYAN}Starting Performance Dashboard for '{current_server}'... Press Ctrl+C to exit.{ui.colors.RESET}")
    time.sleep(2)

    try:
        pid = 0
        server_process = None

        # Find the screen process PID more reliably
        try:
            result = run_command(['screen', '-ls'], capture_output=True)
            if result[0] == 0:
                match = re.search(rf'(\d+)\.{screen_name}\s', result[1])
                if match:
                    pid = int(match.group(1))
                    # Find the actual Java/PHP child process if possible (more accurate)
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    # Look for java or php process among children
                    for child in children:
                        if child.name().lower() in ['java', 'php']:
                            server_process = child
                            break
                    if not server_process:  # Fallback to screen process if child not found
                        server_process = parent
            if not server_process:
                ui.print_warning("Could not find server process PID. Displaying limited info.")

        except Exception as e:
            logger.log('WARNING', f'Could not reliably get PID for monitoring: {e}')
            ui.print_warning("Could not find server process PID. Displaying limited info.")

        while True:
            # Refresh system info for header
            sys_info = monitor.get_system_info() if monitor else None
            ui.print_header(version=VERSION, system_info=sys_info)
            print(f"{ui.colors.BOLD}Performance Dashboard: {current_server}{ui.colors.RESET} (Press Ctrl+C to exit)\n")

            cpu_percent = "N/A"
            mem_percent = "N/A"
            mem_rss_mb = "N/A"

            # Get metrics if process found
            if server_process:
                try:
                    if server_process.is_running():
                        with server_process.oneshot():
                            cpu_percent = f"{server_process.cpu_percent():.1f}%"
                            mem_info = server_process.memory_info()
                            mem_rss_mb = f"{mem_info.rss / (1024 * 1024):.1f} MB"
                            # psutil memory_percent can be misleading in containers/proot, RSS is often better
                            # mem_percent = f"{server_process.memory_percent():.1f}%"
                    else:
                        ui.print_warning("Server process stopped running.")
                        break  # Exit dashboard loop
                except psutil.NoSuchProcess:
                    ui.print_warning("Server process disappeared.")
                    break  # Exit dashboard loop
                except Exception as e:
                    logger.log('ERROR', f"Error getting process stats: {e}")
                    cpu_percent = "Error"
                    mem_rss_mb = "Error"

            print(f"  {ui.colors.CYAN}CPU Usage:{ui.colors.RESET}  {cpu_percent}")
            print(f"  {ui.colors.CYAN}RAM Usage:{ui.colors.RESET}  {mem_rss_mb}")
            # print(f"  {ui.colors.CYAN}RAM Percent:{ui.colors.RESET} {mem_percent}")  # Optional

            # --- Optional: Attempt to parse TPS and Players from log ---
            # Note: This is less reliable than RCON or server plugins
            tps_info = "N/A (Log parsing)"
            player_count = "N/A (Log parsing)"
            try:
                server_path = get_server_directory(current_server)
                log_file = server_path / "logs" / "latest.log"
                if log_file.exists():
                    with open(log_file, "r", errors='ignore') as f:
                        # Read last ~200 lines for recent info
                        lines = f.readlines()[-200:]

                    # Simple TPS parsing (adjust regex based on server type/plugins)
                    tps_found = False
                    for line in reversed(lines):
                        # Example regex for Paper/Spigot TPS:
                        tps_match = re.search(r'TPS from last 1m, 5m, 15m:\s*\*([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)', line)
                        if tps_match:
                            tps_info = f"{float(tps_match.group(1)):.1f} (1m)"
                            tps_found = True
                            break
                    if not tps_found:
                        # Fallback for simpler messages if needed
                        pass

                    # Simple Player count parsing (very basic)
                    players = set()
                    for line in lines:
                        join_match = re.search(r'\]:\s*(\w+)\[.*logged in', line)
                        quit_match = re.search(r'\]:\s*(\w+)\s*left the game', line)
                        disc_match = re.search(r'\]:\s*(\w+)\s*lost connection', line)
                        if join_match:
                            players.add(join_match.group(1))
                        elif quit_match:
                            players.discard(quit_match.group(1))
                        elif disc_match:
                            players.discard(disc_match.group(1))
                    player_count = str(len(players))

            except Exception as e:
                logger.log('DEBUG', f"Failed to parse log for TPS/Players: {e}")
                tps_info = "Error parsing log"
                player_count = "Error parsing log"

            print(f"  {ui.colors.CYAN}TPS (est.):{ui.colors.RESET} {tps_info}")
            print(f"  {ui.colors.CYAN}Players:{ui.colors.RESET}    {player_count}")
            # --- End Optional Parsing ---

            time.sleep(5)  # Refresh interval

    except KeyboardInterrupt:
        logger.log('INFO', "Performance dashboard stopped by user.")
        print("\nExiting dashboard...")
        time.sleep(1)
    except Exception as e:
        logger.log('ERROR', f"Error in performance dashboard: {e}")
        ui.print_error(f"Dashboard error: {e}")
        input("\nPress Enter to continue...")

def plugin_menu():
    """Plugin management menu."""
    if server_mgr is None or ui is None or plugin_mgr is None or logger is None:
        print("Error: System not initialized properly")
        input("\nPress Enter to continue...")
        return

    current_server = server_mgr.get_current_server()
    if not current_server:
        ui.print_error("No server selected")
        input("\nPress Enter to continue...")
        return

    # Check if plugins are supported for this server type
    plugins_dir = plugin_mgr._get_plugins_dir(current_server)
    if not plugins_dir:
         input("\nPress Enter to continue...")
         return # Error message already printed by _get_plugins_dir

    while True:
        ui.clear_screen()
        ui.print_header(version=VERSION)
        print(f"{ui.colors.BOLD}Plugin Manager: {current_server}{ui.colors.RESET}\n")

        plugins = plugin_mgr.list_plugins(current_server)
        if plugins:
            print("Installed Plugins:")
            for i, (name, enabled) in enumerate(plugins, 1):
                status = f"{ui.colors.GREEN}Enabled{ui.colors.RESET}" if enabled else f"{ui.colors.YELLOW}Disabled{ui.colors.RESET}"
                print(f" {i}. {name} ({status})")
        else:
            print("No plugins found.")

        print("\nOptions:")
        print(" i. Install Plugin (URL or Path)")
        print(" e. Enable Plugin")
        print(" d. Disable Plugin")
        print(" x. Delete Plugin")
        print(" 0. Back to Main Menu")

        choice = input(f"\n{ui.colors.YELLOW}Select option: {ui.colors.RESET}").strip().lower()

        selected_plugin_name = None
        if choice in ['e', 'd', 'x'] and plugins:
             try:
                 num = int(input("Enter plugin number: ").strip())
                 if 1 <= num <= len(plugins):
                      selected_plugin_name = plugins[num-1][0]
                 else:
                      ui.print_error("Invalid number.")
             except ValueError:
                  ui.print_error("Invalid input.")

        if choice == 'i':
            source = input("Enter Plugin URL or local .jar path: ").strip()
            if source:
                plugin_mgr.install_plugin(current_server, source)
            else:
                ui.print_warning("No source provided.")
        elif choice == 'e' and selected_plugin_name:
            plugin_mgr.enable_plugin(current_server, selected_plugin_name)
        elif choice == 'd' and selected_plugin_name:
            plugin_mgr.disable_plugin(current_server, selected_plugin_name)
        elif choice == 'x' and selected_plugin_name:
             plugin_mgr.delete_plugin(current_server, selected_plugin_name)
        elif choice == '0':
            break
        elif choice not in ['i', 'e', 'd', 'x']:
             ui.print_error("Invalid option.")

        if choice != '0':
             input("\nPress Enter to continue...")

def scheduler_menu():
    """Scheduled tasks menu."""
    if global_scheduler is None or ui is None or logger is None:
         print("Error: System not initialized properly")
         input("\nPress Enter to continue...")
         return

    while True:
        ui.clear_screen()
        ui.print_header(version=VERSION)
        print(f"{ui.colors.BOLD}Scheduled Tasks{ui.colors.RESET}\n")

        tasks = global_scheduler.list_tasks()
        if tasks:
            print("Current Schedule:")
            print(f"{'ID':<6} {'Server':<15} {'Type':<10} {'Frequency':<15} {'Time':<6} {'Enabled':<8} {'Last Run'}")
            print("-" * 80)
            for task in tasks:
                last_run_dt = task.get('last_run_dt')
                if last_run_dt is not None:
                    last_run_str = last_run_dt.strftime('%Y-%m-%d %H:%M')
                else:
                    last_run_str = 'Never'
                enabled_str = str(task.get('enabled', True))
                print(f"{task.get('id', 'N/A'):<6} {task.get('server', 'N/A'):<15} {task.get('type', 'N/A'):<10} {task.get('frequency', 'N/A'):<15} {task.get('time', '--'):<6} {enabled_str:<8} {last_run_str}")
        else:
            print("No scheduled tasks found.")

        print("\nOptions:")
        print(" a. Add Task")
        print(" t. Toggle Task (Enable/Disable)")
        print(" r. Remove Task")
        print(" 0. Back to Main Menu")

        choice = input(f"\n{ui.colors.YELLOW}Select option: {ui.colors.RESET}").strip().lower()

        if choice == 'a':
             # --- Add Task Wizard ---
             task_type = input("Task Type (backup / restart): ").strip().lower()
             if task_type not in ['backup', 'restart']:
                  ui.print_error("Invalid task type.")
                  continue

             # Server Selection (reuse server_switch_menu logic if possible)
             if server_mgr is None:
                 ui.print_error("Server manager not initialized.")
                 continue
             servers = server_mgr.list_servers()
             if not servers: 
                 ui.print_error("No servers exist.")
                 continue
             print("Select server:")
             for i, s in enumerate(servers, 1): 
                 print(f" {i}. {s}")
             try:
                 idx = int(input("Server number: ").strip()) - 1
                 if not (0 <= idx < len(servers)): 
                     raise ValueError
                 server_name = servers[idx]
             except (ValueError, IndexError): 
                 ui.print_error("Invalid server selection.")
                 continue

             frequency = input("Frequency (hourly / daily / weekly@day e.g., weekly@sun): ").strip().lower()
             # Add validation for frequency format here

             time_str = None
             if frequency.startswith("daily") or frequency.startswith("weekly"):
                  time_str = input("Time (HH:MM, 24-hour format, e.g., 03:00): ").strip()
                  # Add validation for time format here

             global_scheduler.add_task(task_type, server_name, frequency, time_str)
             # --- End Add Task Wizard ---

        elif choice == 't':
             try:
                  task_id = int(input("Enter Task ID to toggle: ").strip())
                  global_scheduler.toggle_task(task_id)
             except ValueError: 
                 ui.print_error("Invalid ID.")
        elif choice == 'r':
             try:
                  task_id = int(input("Enter Task ID to remove: ").strip())
                  confirm = input(f"Remove task {task_id}? (y/N): ").strip().lower()
                  if confirm == 'y':
                       global_scheduler.remove_task(task_id)
             except ValueError: 
                 ui.print_error("Invalid ID.")
        elif choice == '0':
            break
        else:
            ui.print_error("Invalid option.")

        if choice != '0':
             input("\nPress Enter to continue...")

def menu_loop():
    """Main menu loop."""
    # Check dependencies before starting
    if not check_dependencies():
        sys.exit(1)
        
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    while True:
        # Header with system info
        if monitor is not None and ui is not None:
            sys_info = monitor.get_system_info()
            ui.print_header(version=VERSION, system_info=sys_info)

        if server_mgr is not None and ui is not None:
            current = server_mgr.get_current_server()
            if current:
                ui.print_success(f"Current Server: {current}")
                # Show if running
                if ui is not None:
                    screen_name = get_screen_session_name(current)
                    if is_screen_session_running(screen_name):
                        ui.print_info("Status: RUNNING")
                    else:
                        ui.print_warning("Status: STOPPED")
            else:
                ui.print_warning("No server selected")

        print()
        if ui is not None:
            print(f"{ui.colors.BOLD}Main Menu:{ui.colors.RESET}")
            options = [
                ("1", "🚀 Start Server"),
                ("2", "⏹️  Stop Server"),
                ("3", "📦 Install/Update Server"),
                ("4", "⚙️  Configure Server"),
                ("5", "💻 Server Console"),
                ("6", "🗄️  World Manager"),
                ("7", "📊 Statistics"),
                ("8", "🌐 Tunneling"),
                ("9", "📈 Performance Dashboard"),
                ("P", "🔌 Plugin Manager"),
                ("S", "⏰ Scheduler"),
                ("10", "➕ Create/Switch Server"),
                ("0", "🚪 Exit")
            ]

            for key, label in options:
                print(f" {ui.colors.BOLD}{key}.{ui.colors.RESET} {label}")
        
        choice = input(f"\n{ui.colors.YELLOW if ui is not None else ''}Choose option: {ui.colors.RESET if ui is not None else ''}").strip()

        try:
            if choice == "1" and server_mgr is not None:
                server_mgr.start_server()
            elif choice == "2" and server_mgr is not None:
                server_mgr.stop_server()
            elif choice == "3" and server_mgr is not None:
                server_mgr.install_server_menu()
            elif choice == "4":
                configure_menu()
            elif choice == "5" and server_mgr is not None:
                server_mgr.show_console()
            elif choice == "6":
                world_menu()
            elif choice == "7" and server_mgr is not None:
                server_mgr.show_statistics()
            elif choice == "8":
                tunnel_menu()
            elif choice == "9":
                show_performance_dashboard()
            elif choice.upper() == "P":
                plugin_menu()
            elif choice.upper() == "S":
                scheduler_menu()
            elif choice == "10":
                server_switch_menu()
            elif choice == "0":
                graceful_shutdown()
            else:
                if ui is not None:
                    ui.print_error("Invalid option")
                time.sleep(1)

        except APIError as e: # Catch specific errors for tailored feedback
            if ui is not None:
                ui.print_error(f"API Error: {e}")
            if logger is not None:
                logger.log('ERROR', f"API Error encountered: {e}")
        except DownloadError as e:
            if ui is not None:
                ui.print_error(f"Download Error: {e}")
            if logger is not None:
                logger.log('ERROR', f"Download Error encountered: {e}")
        except ConfigError as e:
            if ui is not None:
                ui.print_error(f"Configuration Error: {e}")
            if logger is not None:
                logger.log('ERROR', f"Configuration Error encountered: {e}")
        except MSMError as e: # Catch other known MSM errors
            if ui is not None:
                ui.print_error(f"Error: {e}")
            if logger is not None:
                logger.log('ERROR', f"MSM Error encountered: {e}")
        except KeyboardInterrupt: # Keep handling Ctrl+C
             graceful_shutdown()
        except Exception as e: # Catch truly unexpected errors
            if logger is not None:
                logger.log('CRITICAL', f"Unhandled error in main loop: {e}", exc_info=True)
            if ui is not None:
                ui.print_error(f"An critical unexpected error occurred: {e}")

            # Add input pause after handling errors
            input("\nPress Enter to continue...")

def main():
    """Main entry point for the application."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Minecraft Server Manager - Unified")
    parser.add_argument('--version', action='version', version=f'MSM {VERSION}')
    parser.add_argument('--help', action='help', help='Show this help message and exit')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize and run
    init_system()
    menu_loop()

if __name__ == "__main__":
    main()