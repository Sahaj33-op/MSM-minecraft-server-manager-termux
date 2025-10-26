#!/usr/bin/env python3
"""
Unified entrypoint (Phase 2): run modular managers directly
- Initializes core subsystems (logger, db, monitoring)
- Wires managers (server/world/tunnel)
- Presents a minimal, familiar main menu
"""

import os
import sys
import signal
import time

from core.logger import EnhancedLogger
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from core.config import ConfigManager, get_config_root
from managers.server_manager import ServerManager
from managers.world_manager import WorldManager
from managers.tunnel_manager import TunnelManager
from ui.interface import UI
from utils.helpers import detect_total_ram_mb

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

def graceful_shutdown(signum=None, frame=None):
    try:
        cur = server_mgr.get_current_server()
        if cur:
            # Best-effort stop monitor threads before exit
            monitor.stop_monitoring(cur)
    except Exception:
        pass
    if logger:
        logger.log('INFO', "MSM shutting down.")
    sys.exit(0)

def ensure_infra():
    os.makedirs(CONFIG_DIR, exist_ok=True)

def init_system():
    global logger, db, monitor, ui, server_mgr, world_mgr, tunnel_mgr

    ensure_infra()
    logger = EnhancedLogger(LOG_FILE)
    db = DatabaseManager(DB_FILE)
    monitor = PerformanceMonitor(db, logger)
    ui = UI()

    server_mgr = ServerManager(db, logger, monitor)
    world_mgr = WorldManager(logger)
    tunnel_mgr = TunnelManager(logger)

    # Select a default server if none set
    cfg = ConfigManager.load()
    if not cfg.get("current_server") and cfg.get("servers"):
        first = list(cfg["servers"].keys())[0]
        ConfigManager.set_current_server(first)

def menu_loop():
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)

    while True:
        # Header with system info
        sys_info = monitor.get_system_info()
        ui.print_header(version=VERSION, system_info=sys_info)

        current = server_mgr.get_current_server()
        if current:
            ui.print_success(f"Current Server: {current}")
        else:
            ui.print_warning("No server selected")

        print()
        options = [
            ("1", "Start Server"),
            ("2", "Stop Server"),
            ("3", "Install/Update Server"),
            ("4", "Configure Server (basic)"),
            ("5", "Server Console"),
            ("6", "World Manager (backup/restore)"),
            ("7", "Statistics"),
            ("8", "Tunneling"),
            ("9", "Create/Switch Server"),
            ("0", "Exit"),
        ]
        ui.print_menu_options([(k, v) for k, v in options])

        choice = input(f"\n{ui.colors.YELLOW}Choose option (0-9): {ui.colors.RESET}").strip()

        try:
            if choice == "1":
                server_mgr.start_server()

            elif choice == "2":
                server_mgr.stop_server()

            elif choice == "3":
                server_mgr.install_server_menu()

            elif choice == "4":
                # Minimal config: RAM, port, motd, max-players
                cur = server_mgr.get_current_server()
                if not cur:
                    ui.print_error("No server selected")
                    input("\nPress Enter to continue...")
                    continue
                cfg = ConfigManager.load_server_config(cur)
                print("\nBasic Settings:")
                ram = input(f"RAM MB [{cfg.get('ram_mb', 2048)}]: ").strip()
                if ram:
                    cfg['ram_mb'] = int(ram)
                port = input(f"Port [{cfg.get('server_settings', {}).get('port', 25565)}]: ").strip()
                if port:
                    cfg.setdefault('server_settings', {})['port'] = int(port)
                motd = input(f"MOTD [{cfg.get('server_settings', {}).get('motd', 'A Minecraft Server')}]: ").strip()
                if motd:
                    cfg['server_settings']['motd'] = motd
                maxp = input(f"Max Players [{cfg.get('server_settings', {}).get('max-players', 20)}]: ").strip()
                if maxp:
                    cfg['server_settings']['max-players'] = int(maxp)
                ConfigManager.save_server_config(cur, cfg)
                logger.log('SUCCESS', "Configuration updated")
                input("\nPress Enter to continue...")

            elif choice == "5":
                server_mgr.show_console()

            elif choice == "6":
                cur = server_mgr.get_current_server()
                if not cur:
                    ui.print_error("No server selected")
                    input("\nPress Enter to continue...")
                    continue
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
                        continue
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
                        continue
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

            elif choice == "7":
                server_mgr.show_statistics()

            elif choice == "8":
                # Tunneling menu
                cur = server_mgr.get_current_server()
                if not cur:
                    ui.print_error("No server selected")
                    input("\nPress Enter to continue...")
                    continue
                cfg = ConfigManager.load_server_config(cur)
                port = cfg.get('server_settings', {}).get('port', 25565)
                print("\nTunneling:")
                print(" 1. ngrok (Termux-native)")
                print(" 2. cloudflared (Termux-native)")
                print(" 3. pinggy (Termux-native)")
                print(" 4. playit.gg (requires proot Debian)")
                print(" 0. Back")
                sub = input("\nSelect (0-4): ").strip()
                ok = False
                if sub == "1":
                    ok = tunnel_mgr.start_ngrok(port)
                elif sub == "2":
                    ok = tunnel_mgr.start_cloudflared(port)
                elif sub == "3":
                    ok = tunnel_mgr.start_pinggy(port)
                elif sub == "4":
                    ok = tunnel_mgr.start_playit(port)  # will prompt for proot if needed
                if ok:
                    logger.log('SUCCESS', "Tunnel start requested")
                input("\nPress Enter to continue...")

            elif choice == "9":
                # Create or switch server
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

            elif choice == "0":
                # Attempt clean shutdown of monitor
                graceful_shutdown()

            else:
                ui.print_error("Invalid option")
                time.sleep(1)

        except Exception as e:
            if logger:
                logger.log('ERROR', f"Unexpected error: {e}")
            time.sleep(1)

def main():
    init_system()
    menu_loop()

if __name__ == "__main__":
    main()
