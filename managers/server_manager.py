#!/usr/bin/env python3
"""
Server Manager - Unified from both branches
Combines v1.1.0 modular design with main branch enterprise features
"""
import os
import re
import time
import shutil
import urllib.request
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

from core.config import ConfigManager
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from managers.api_client import PaperMCAPI, PurpurAPI, FoliaAPI, VanillaAPI, FabricAPI, QuiltAPI
from utils.helpers import (
    sanitize_input, get_java_path, is_screen_session_running, 
    run_command, get_server_directory, get_screen_session_name
)
from ui.interface import UI

class ServerManager:
    """Unified server management combining both branch features"""
    
    SERVER_TYPES = {
        "1": ("PaperMC", PaperMCAPI, "paper"),
        "2": ("Purpur", PurpurAPI, "purpur"),
        "3": ("Folia", FoliaAPI, "folia"),
        "4": ("Fabric", FabricAPI, "fabric"),
        "5": ("Quilt", QuiltAPI, "quilt"),
        "6": ("Vanilla", VanillaAPI, "vanilla")
    }
    
    def __init__(self, db_manager: DatabaseManager, logger, monitor: PerformanceMonitor):
        self.db = db_manager
        self.logger = logger
        self.monitor = monitor
        self.ui = UI()
        self.current_session_id = None
    
    def list_servers(self) -> List[str]:
        """List all configured servers"""
        config = ConfigManager.load()
        return list(config.get('servers', {}).keys())
    
    def get_current_server(self) -> Optional[str]:
        """Get currently selected server"""
        return ConfigManager.get_current_server()
    
    def set_current_server(self, name: str):
        """Set current server"""
        ConfigManager.set_current_server(name)
        self.logger.log('INFO', f'Switched to server: {name}')
    
    def create_server(self, name: str) -> bool:
        """Create new server configuration"""
        safe_name = sanitize_input(name)
        server_dir = get_server_directory(safe_name)
        
        if server_dir.exists():
            self.logger.log('ERROR', f'Server {safe_name} already exists')
            return False
        
        try:
            server_dir.mkdir(parents=True, exist_ok=True)
            
            server_config = {
                'server_flavor': None,
                'server_version': None,
                'ram_mb': 2048,
                'auto_restart': False,
                'server_settings': {
                    'motd': f'{name} Server',
                    'port': 25565,
                    'max-players': 20
                }
            }
            
            ConfigManager.save_server_config(safe_name, server_config)
            self.set_current_server(safe_name)
            
            self.logger.log('SUCCESS', f'Created server: {safe_name}')
            return True
            
        except Exception as e:
            self.logger.log('ERROR', f'Failed to create server: {e}')
            return False
    
    def start_server(self) -> bool:
        """Start the current server with monitoring"""
        current_server = self.get_current_server()
        if not current_server:
            self.logger.log('ERROR', 'No server selected')
            return False
        
        server_config = ConfigManager.load_server_config(current_server)
        if not server_config.get('server_flavor'):
            self.logger.log('ERROR', 'Server not installed. Please install first.')
            return False
        
        server_dir = get_server_directory(current_server)
        screen_name = get_screen_session_name(current_server)
        
        if is_screen_session_running(screen_name):
            self.logger.log('WARNING', 'Server is already running')
            return False
        
        # Find server JAR
        jar_files = list(server_dir.glob('*.jar'))
        if not jar_files:
            self.logger.log('ERROR', 'No server JAR found')
            return False
        
        jar_file = jar_files[0]
        java_path = get_java_path(server_config.get('server_version', ''))
        
        if not java_path:
            self.logger.log('ERROR', 'Java not found. Install with: pkg install openjdk-17')
            return False
        
        # Accept EULA if needed
        eula_file = server_dir / 'eula.txt'
        if not eula_file.exists() or 'eula=false' in eula_file.read_text():
            eula_file.write_text('eula=true\n')
            self.logger.log('INFO', 'EULA accepted')
        
        # Build command
        ram_mb = server_config.get('ram_mb', 2048)
        java_args = [
            java_path, f'-Xmx{ram_mb}M', f'-Xms{ram_mb}M',
            '-XX:+UseG1GC', '-jar', str(jar_file), 'nogui'
        ]
        
        screen_cmd = ['screen', '-dmS', screen_name] + java_args
        
        try:
            returncode, stdout, stderr = run_command(screen_cmd, cwd=str(server_dir))
            if returncode == 0:
                self.logger.log('SUCCESS', f'Server {current_server} started')
                
                # Log session start
                flavor = server_config.get('server_flavor')
                version = server_config.get('server_version')
                self.current_session_id = self.db.log_session_start(current_server, flavor, version)
                
                # Start monitoring
                time.sleep(3)  # Give server time to start
                # Get PID from screen session (simplified)
                self.monitor.start_monitoring(current_server, 0)  # Will be enhanced
                
                return True
            else:
                self.logger.log('ERROR', f'Failed to start server: {stderr}')
                return False
        except Exception as e:
            self.logger.log('ERROR', f'Error starting server: {e}')
            return False
    
    def stop_server(self) -> bool:
        """Stop the current server gracefully"""
        current_server = self.get_current_server()
        if not current_server:
            self.logger.log('ERROR', 'No server selected')
            return False
        
        screen_name = get_screen_session_name(current_server)
        
        if not is_screen_session_running(screen_name):
            self.logger.log('INFO', 'Server is not running')
            return False
        
        # Send stop command
        stop_cmd = ['screen', '-S', screen_name, '-X', 'stuff', 'stop\n']
        returncode, stdout, stderr = run_command(stop_cmd)
        
        if returncode == 0:
            # Wait for graceful shutdown
            for _ in range(15):
                if not is_screen_session_running(screen_name):
                    break
                time.sleep(1)
            else:
                # Force quit if still running
                run_command(['screen', '-S', screen_name, '-X', 'quit'])
            
            # Stop monitoring
            self.monitor.stop_monitoring(current_server)
            
            # Log session end
            if self.current_session_id:
                self.db.log_session_end(self.current_session_id)
                self.current_session_id = None
            
            self.logger.log('SUCCESS', f'Server {current_server} stopped')
            return True
        else:
            self.logger.log('ERROR', f'Failed to stop server: {stderr}')
            return False
    
    def install_server_menu(self):
        """Interactive server installation menu"""
        current_server = self.get_current_server()
        if not current_server:
            self.ui.print_error('No server selected')
            return
        
        self.ui.clear_screen()
        self.ui.print_header()
        print(f"{self.ui.colors.BOLD}Install/Update Server: {current_server}{self.ui.colors.RESET}\n")
        
        # Show server types
        print("Select server type:")
        for key, (name, api_class, flavor_key) in self.SERVER_TYPES.items():
            print(f" {key}. {name}")
        
        choice = input(f"\n{self.ui.colors.YELLOW}Select server type (1-6): {self.ui.colors.RESET}").strip()
        
        if choice not in self.SERVER_TYPES:
            self.ui.print_error('Invalid selection')
            input('Press Enter to continue...')
            return
        
        server_type_name, api_class, flavor_key = self.SERVER_TYPES[choice]
        
        # Get versions
        self.ui.print_info(f'Fetching {server_type_name} versions...')
        versions = api_class.get_versions()
        
        if not versions:
            self.ui.print_error(f'Failed to fetch {server_type_name} versions')
            input('Press Enter to continue...')
            return
        
        # Show version selection
        print(f"\nAvailable {server_type_name} versions:")
        recent_versions = versions[-10:] if len(versions) > 10 else versions
        
        for i, version in enumerate(recent_versions, 1):
            print(f" {i}. {version}")
        
        print(f"\nLatest: {versions[-1]}")
        version_choice = input(f"Select version (1-{len(recent_versions)}) or Enter for latest: ").strip()
        
        if not version_choice:
            selected_version = versions[-1]
        else:
            try:
                idx = int(version_choice) - 1
                if 0 <= idx < len(recent_versions):
                    selected_version = recent_versions[idx]
                else:
                    self.ui.print_error('Invalid selection')
                    input('Press Enter to continue...')
                    return
            except ValueError:
                self.ui.print_error('Invalid input')
                input('Press Enter to continue...')
                return
        
        # Download server
        if self._download_server(current_server, server_type_name, api_class, selected_version, flavor_key):
            self.ui.print_success(f'{server_type_name} {selected_version} installed successfully!')
        else:
            self.ui.print_error('Installation failed')
        
        input('Press Enter to continue...')
    
    def _download_server(self, server_name: str, server_type: str, api_class, version: str, flavor_key: str) -> bool:
        """Download and install server JAR"""
        server_dir = get_server_directory(server_name)
        jar_path = server_dir / 'server.jar'
        
        try:
            download_url = None
            
            if hasattr(api_class, 'get_latest_build'):
                # Paper-like APIs
                build_info = api_class.get_latest_build(version)
                if build_info:
                    build_num = build_info.get('build')
                    download_url = api_class.get_download_url(version, build_num)
            elif hasattr(api_class, 'get_loader_versions'):
                # Fabric/Quilt APIs
                loaders = api_class.get_loader_versions()
                if loaders:
                    download_url = api_class.get_download_url(version, loaders[0])
            else:
                # Vanilla API
                download_url = api_class.get_download_url(version)
            
            if not download_url:
                self.logger.log('ERROR', f'Could not get download URL for {server_type} {version}')
                return False
            
            self.ui.print_info(f'Downloading {server_type} {version}...')
            
            # Download with progress
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    print(f'\rProgress: {percent}%', end='', flush=True)
            
            urllib.request.urlretrieve(download_url, jar_path, progress_hook)
            print()  # New line after progress
            
            # Verify download
            if not jar_path.exists() or jar_path.stat().st_size == 0:
                self.logger.log('ERROR', 'Download verification failed')
                return False
            
            # Update server config
            server_config = ConfigManager.load_server_config(server_name)
            server_config['server_flavor'] = flavor_key
            server_config['server_version'] = version
            ConfigManager.save_server_config(server_name, server_config)
            
            self.logger.log('SUCCESS', f'Installed {server_type} {version} for {server_name}')
            return True
            
        except Exception as e:
            self.logger.log('ERROR', f'Download failed: {e}')
            return False
    
    def show_statistics(self):
        """Display server statistics"""
        current_server = self.get_current_server()
        if not current_server:
            self.ui.print_error('No server selected')
            return
        
        stats = self.db.get_server_statistics(current_server)
        
        self.ui.clear_screen()
        self.ui.print_header()
        print(f"{self.ui.colors.BOLD}Statistics for: {current_server}{self.ui.colors.RESET}\n")
        
        def format_duration(seconds):
            if not seconds:
                return "N/A"
            seconds = int(seconds)
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{days}d {hours}h {minutes}m"
        
        print(f"  Total Sessions:    {self.ui.colors.CYAN}{stats.get('total_sessions', 0)}{self.ui.colors.RESET}")
        print(f"  Total Uptime:      {self.ui.colors.CYAN}{format_duration(stats.get('total_uptime'))}{self.ui.colors.RESET}")
        print(f"  Average Session:   {self.ui.colors.CYAN}{format_duration(stats.get('avg_duration'))}{self.ui.colors.RESET}")
        print(f"  Total Crashes:     {self.ui.colors.YELLOW}{stats.get('total_crashes', 0)}{self.ui.colors.RESET}")
        print(f"  Total Restarts:    {self.ui.colors.YELLOW}{stats.get('total_restarts', 0)}{self.ui.colors.RESET}")
        
        print("\n  --- 24-Hour Performance ---")
        print(f"  Avg RAM Usage:     {self.ui.colors.CYAN}{stats.get('avg_ram_usage_24h', 0):.2f}%{self.ui.colors.RESET}")
        print(f"  Avg CPU Usage:     {self.ui.colors.CYAN}{stats.get('avg_cpu_usage_24h', 0):.2f}%{self.ui.colors.RESET}")
        print(f"  Peak Players:      {self.ui.colors.CYAN}{stats.get('peak_players_24h', 0)}{self.ui.colors.RESET}")
        
        input('\nPress Enter to continue...')
    
    def show_console(self):
        """Attach to server console"""
        current_server = self.get_current_server()
        if not current_server:
            self.ui.print_error('No server selected')
            return
        
        screen_name = get_screen_session_name(current_server)
        
        if not is_screen_session_running(screen_name):
            self.ui.print_error('Server is not running')
            input('Press Enter to continue...')
            return
        
        self.ui.print_info(f'Attaching to {current_server} console...')
        self.ui.print_info('Press Ctrl+A, then D to detach')
        input('Press Enter to attach...')
        
        os.system(f'screen -r {screen_name}')