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
import urllib.error  # Add this import
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

# Add imports for custom exceptions
from core.exceptions import DownloadError, ConfigError
from core.config import ConfigManager
from core.database import DatabaseManager
from core.monitoring import PerformanceMonitor
from managers.api_client import (
    PaperMCAPI, PurpurAPI, FoliaAPI, VanillaAPI, FabricAPI, QuiltAPI, PocketMineAPI
)
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
        "6": ("Vanilla", VanillaAPI, "vanilla"),
        "7": ("PocketMine-MP", PocketMineAPI, "pocketmine")
    }
    
    # Complete server.properties settings
    SERVER_PROPERTIES_SETTINGS = [
        'gamemode', 'difficulty', 'pvp', 'white-list', 'view-distance',
        'max-players', 'motd', 'port', 'online-mode', 'allow-flight',
        'spawn-animals', 'spawn-monsters', 'spawn-npcs', 'enable-command-block',
        'max-world-size', 'player-idle-timeout', 'level-type', 'level-name'
    ]
    
    def __init__(self, db_manager: DatabaseManager, logger, monitor: PerformanceMonitor):
        """Initialize the ServerManager with required dependencies.
        
        Args:
            db_manager: Database manager instance for storing server data
            logger: Logger instance for logging messages
            monitor: Performance monitor instance for tracking server metrics
        """
        self.db = db_manager
        self.logger = logger
        self.monitor = monitor
        self.ui = UI()
        self.current_session_id = None
        
        # Set the logger for all API clients
        from managers.api_client import BaseAPI
        BaseAPI.set_logger(logger)
    
    def list_servers(self) -> List[str]:
        """List all configured servers.
        
        Returns:
            List of server names
        """
        config = ConfigManager.load()
        return list(config.get('servers', {}).keys())
    
    def get_current_server(self) -> Optional[str]:
        """Get currently selected server.
        
        Returns:
            Name of the current server or None if no server is selected
        """
        return ConfigManager.get_current_server()
    
    def set_current_server(self, name: str):
        """Set current server.
        
        Args:
            name: Name of the server to set as current
        """
        ConfigManager.set_current_server(name)
        self.logger.log('INFO', f'Switched to server: {name}')
    
    def create_server(self, name: str) -> bool:
        """Create new server configuration.
        
        Args:
            name: Name of the server to create
            
        Returns:
            True if server was created successfully, False otherwise
        """
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
                    'max-players': 20,
                    'gamemode': 'survival',
                    'difficulty': 'normal',
                    'pvp': True,
                    'white-list': False,
                    'view-distance': 10,
                    'online-mode': True,
                    'allow-flight': False,
                    'spawn-animals': True,
                    'spawn-monsters': True,
                    'spawn-npcs': True,
                    'enable-command-block': False,
                    'max-world-size': 29999984,
                    'player-idle-timeout': 0,
                    'level-type': 'default',
                    'level-name': 'world'
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
        """Start the current server with monitoring.
        
        Returns:
            True if server was started successfully, False otherwise
        """
        current_server = self.get_current_server()
        if not current_server:
            self.logger.log('ERROR', 'No server selected')
            return False
        
        server_config = ConfigManager.load_server_config(current_server)
        flavor = server_config.get('server_flavor')
        version = server_config.get('server_version')
        
        if not flavor or not version:
            self.logger.log('ERROR', 'Server not installed or configured. Please install first.')
            return False
        
        server_dir = get_server_directory(current_server)
        screen_name = get_screen_session_name(current_server)
        
        if is_screen_session_running(screen_name):
            self.logger.log('WARNING', 'Server is already running')
            return False
        
        # --- Determine startup command based on flavor ---
        startup_command = []
        ram_mb = server_config.get('ram_mb', 1024) # Default RAM

        if flavor == "pocketmine":
            # Find .phar file
            phar_files = list(server_dir.glob('*.phar'))
            if not phar_files:
                self.logger.log('ERROR', 'PocketMine PHAR file not found')
                return False
            phar_file = phar_files[0]
            # Check if PHP is available
            if not shutil.which('php'):
                 self.logger.log('ERROR', 'PHP not found. Install with: pkg install php')
                 return False
            startup_command = ['php', str(phar_file)] 
            # Note: PocketMine doesn't use RAM args like Java
            # Ensure eula.txt is NOT created for PocketMine
            eula_file = server_dir / 'eula.txt'
            if eula_file.exists(): eula_file.unlink() # Remove if it exists by mistake

        else: # Assume Java-based server (Paper, Purpur, Vanilla, etc.)
            # Find server JAR
            jar_files = list(server_dir.glob('*.jar'))
            if not jar_files:
                # Special check for Fabric/Quilt that might use different names initially
                potential_launchers = list(server_dir.glob('fabric-server-launch.jar')) + \
                                      list(server_dir.glob('quilt-server-launch.jar'))
                if potential_launchers:
                    jar_files = potential_launchers
                
            if not jar_files:
                self.logger.log('ERROR', 'No server JAR found')
                return False
            
            jar_file = jar_files[0] # Use the first one found
            java_path = get_java_path(version) 
            
            if not java_path:
                self.logger.log('ERROR', f'Required Java version for {version} not found.')
                return False

            # Accept EULA if needed
            eula_file = server_dir / 'eula.txt'
            try:
                if not eula_file.exists() or 'eula=false' in eula_file.read_text(errors='ignore'):
                    eula_file.write_text('eula=true\n')
                    self.logger.log('INFO', 'EULA accepted')
            except Exception as e:
                 self.logger.log('WARNING', f'Could not handle EULA file: {e}')
                 # Proceed anyway, server might handle it

            # Create or update server.properties
            self._update_server_properties(current_server, server_config.get('server_settings', {}))

            # Build command
            java_args = [
                java_path, f'-Xmx{ram_mb}M', f'-Xms{ram_mb}M',
                '-XX:+UseG1GC', # Add other recommended flags if desired
                '-jar', str(jar_file), 'nogui'
            ]
            startup_command = java_args

        # --- End of command determination ---

        if not startup_command:
             self.logger.log('ERROR', 'Could not determine startup command.')
             return False

        screen_cmd = ['screen', '-dmS', screen_name] + startup_command
        
        try:
            # Pass cwd=str(server_dir) to run command inside the server directory
            returncode, stdout, stderr = run_command(screen_cmd, cwd=str(server_dir)) 
            if returncode == 0:
                self.logger.log('SUCCESS', f'Server {current_server} started')
                
                # Log session start
                self.current_session_id = self.db.log_session_start(current_server, flavor, version)
                
                # Start monitoring
                time.sleep(3) # Give server time to start
                
                pid = 0
                try:
                    # More robust PID finding for screen
                    result = run_command(['screen', '-ls'], capture_output=True)
                    if result[0] == 0:
                        match = re.search(rf'(\d+)\.{screen_name}\s', result[1])
                        if match:
                            pid = int(match.group(1))
                except Exception as e:
                     self.logger.log('WARNING', f'Could not reliably get PID for monitoring: {e}')

                if pid > 0:
                    self.monitor.start_monitoring(current_server, pid)
                else:
                     self.logger.log('WARNING', 'Could not find server process PID for monitoring.')

                return True
            else:
                self.logger.log('ERROR', f'Failed to start server in screen: {stderr}')
                return False
        except Exception as e:
            self.logger.log('ERROR', f'Error starting server: {e}')
            return False
    
    def _update_server_properties(self, server_name: str, settings: dict):
        """Update server.properties file with given settings.
        
        Args:
            server_name: Name of the server
            settings: Dictionary of settings to update
        """
        server_dir = get_server_directory(server_name)
        properties_file = server_dir / 'server.properties'
        
        # Read existing properties or create new ones
        properties = {}
        if properties_file.exists():
            with open(properties_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        properties[key] = value
        
        # Update with new settings
        properties.update(settings)
        
        # Write back to file
        with open(properties_file, 'w') as f:
            f.write('# Minecraft server properties\n')
            f.write(f'# Updated {time.strftime("%a %b %d %H:%M:%S %Z %Y")}\n')
            for key, value in properties.items():
                if isinstance(value, bool):
                    f.write(f'{key}={str(value).lower()}\n')
                else:
                    f.write(f'{key}={value}\n')
    
    def stop_server(self) -> bool:
        """Stop the current server gracefully.
        
        Returns:
            True if server was stopped successfully, False otherwise
        """
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
        
        choice = input(f"\n{self.ui.colors.YELLOW}Select server type (1-7): {self.ui.colors.RESET}").strip()
        
        if choice not in self.SERVER_TYPES:
            self.ui.print_error('Invalid selection')
            input('Press Enter to continue...')
            return
        
        server_type_name, api_class, flavor_key = self.SERVER_TYPES[choice]
        
        # Get versions with error handling
        self.ui.print_info(f'Fetching {server_type_name} versions...')
        try:
            versions = api_class.get_versions()
        except Exception as e:
            self.ui.print_error(f'Failed to fetch {server_type_name} versions: {e}')
            input('Press Enter to continue...')
            return
        
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
        
        # Download server with error handling
        try:
            if self._download_server(current_server, server_type_name, api_class, selected_version, flavor_key):
                self.ui.print_success(f'{server_type_name} {selected_version} installed successfully!')
            else:
                self.ui.print_error('Installation failed')
        except Exception as e:
            self.ui.print_error(f'Installation failed: {e}')
        
        input('Press Enter to continue...')
    
    def _download_server(self, server_name: str, server_type: str, api_class, version: str, flavor_key: str) -> bool:
        """Download and install server JAR or PHAR"""
        server_dir = get_server_directory(server_name)
        jar_path = None  # Initialize jar_path
        
        try:
            download_url = None
            build_info = None # Store build info
            target_filename = "server.jar" # Default for Java

            if hasattr(api_class, 'get_latest_build'):
                # Paper-like and PocketMine APIs
                build_info = api_class.get_latest_build(version)
                if build_info:
                    if flavor_key == "pocketmine":
                        download_url = api_class.get_download_url(version, build_info)
                        target_filename = build_info.get("filename", "PocketMine-MP.phar") # Use actual filename
                    else: # Paper, Purpur, Folia
                         build_num = build_info.get('build')
                         download_url = api_class.get_download_url(version, build_num)
            elif hasattr(api_class, 'get_loader_versions'):
                # Fabric/Quilt APIs
                loaders = api_class.get_loader_versions()
                if loaders:
                    download_url = api_class.get_download_url(version, loaders[0])
                    target_filename = "server.jar" # Default for Fabric/Quilt
            else:
                # Vanilla API
                download_url = api_class.get_download_url(version)
                target_filename = "server.jar" # Default for Vanilla
            
            if not download_url:
                self.logger.log('ERROR', f'Could not get download URL for {server_type} {version}')
                return False

            jar_path = server_dir / target_filename # Use the determined filename
            
            self.ui.print_info(f'Downloading {server_type} {version} to {jar_path}...')
            
            # Download with progress
            def progress_hook(block_num, block_size, total_size):
                if total_size > 0:
                    percent = min(100, (block_num * block_size * 100) // total_size)
                    print(f'\rProgress: {percent}%', end='', flush=True)
            
            urllib.request.urlretrieve(download_url, jar_path, progress_hook) # Ensure progress_hook is defined as before
            print() # New line after progress

            # Verify download
            if not jar_path.exists() or jar_path.stat().st_size == 0:
                # Raise specific exception
                raise DownloadError("Download verification failed (file missing or empty)")

            # Update server config
            server_config = ConfigManager.load_server_config(server_name)
            server_config['server_flavor'] = flavor_key
            server_config['server_version'] = version
            # Add build info if available (useful for Paper/Purpur/Folia/PocketMine)
            if build_info and build_info.get('build'):
                 server_config['server_build'] = build_info.get('build')
            # Set default port based on type
            server_config.setdefault('server_settings', {})['port'] = 19132 if flavor_key == "pocketmine" else 25565

            ConfigManager.save_server_config(server_name, server_config)
            
            self.logger.log('SUCCESS', f'Installed {server_type} {version} for {server_name}')
            return True
            
        except urllib.error.URLError as e:
             raise DownloadError(f"Network error during download: {e}") from e
        except ConfigError as e: # If save_server_config raises it
             raise ConfigError(f"Failed to save config after download: {e}") from e
        except DownloadError as e: # Catch specific verification error
             self.logger.log('ERROR', str(e))
             # Clean up empty file if possible
             if jar_path and jar_path.exists():
                 try:
                     jar_path.unlink()
                 except OSError:
                     pass # Ignore cleanup errors
             return False # Return bool for flow control
        except Exception as e:
            # Catch broader exceptions but raise a specific DownloadError
            raise DownloadError(f"Unexpected download failure: {e}") from e
    
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
    
    def configure_server_menu(self):
        """Complete configuration menu with 16+ server.properties settings"""
        current_server = self.get_current_server()
        if not current_server:
            self.ui.print_error('No server selected')
            input('Press Enter to continue...')
            return
        
        server_config = ConfigManager.load_server_config(current_server)
        settings = server_config.get('server_settings', {})
        
        self.ui.clear_screen()
        self.ui.print_header()
        print(f"{self.ui.colors.BOLD}Configure Server: {current_server}{self.ui.colors.RESET}\n")
        
        # Display current settings
        print("Current Settings:")
        for setting in self.SERVER_PROPERTIES_SETTINGS:
            current_value = settings.get(setting, 'Not set')
            print(f"  {setting}: {current_value}")
        
        print("\nOptions:")
        print(" 1. Edit setting")
        print(" 2. Reset to defaults")
        print(" 0. Back")
        
        choice = input(f"\n{self.ui.colors.YELLOW}Select option: {self.ui.colors.RESET}").strip()
        
        if choice == "1":
            self._edit_server_setting(current_server, settings)
        elif choice == "2":
            self._reset_server_settings(current_server)
        
        input('Press Enter to continue...')
    
    def _edit_server_setting(self, server_name: str, settings: dict):
        """Edit a specific server setting"""
        print("\nAvailable settings to edit:")
        for i, setting in enumerate(self.SERVER_PROPERTIES_SETTINGS, 1):
            print(f" {i}. {setting}")
        
        try:
            selection = int(input(f"\n{self.ui.colors.YELLOW}Select setting to edit (1-{len(self.SERVER_PROPERTIES_SETTINGS)}): {self.ui.colors.RESET}").strip())
            if 1 <= selection <= len(self.SERVER_PROPERTIES_SETTINGS):
                setting_name = self.SERVER_PROPERTIES_SETTINGS[selection - 1]
                current_value = settings.get(setting_name, '')
                new_value = input(f"Enter new value for {setting_name} [{current_value}]: ").strip()
                
                if new_value:
                    # Convert to appropriate type
                    if setting_name in ['port', 'max-players', 'view-distance', 'max-world-size', 'player-idle-timeout']:
                        try:
                            new_value = int(new_value)
                        except ValueError:
                            self.ui.print_error('Invalid number')
                            return
                    elif setting_name in ['pvp', 'white-list', 'online-mode', 'allow-flight', 'spawn-animals', 'spawn-monsters', 'spawn-npcs', 'enable-command-block']:
                        new_value = new_value.lower() in ['true', '1', 'yes', 'on']
                    
                    settings[setting_name] = new_value
                    server_config = ConfigManager.load_server_config(server_name)
                    server_config['server_settings'] = settings
                    ConfigManager.save_server_config(server_name, server_config)
                    self.ui.print_success(f'Updated {setting_name} to {new_value}')
            else:
                self.ui.print_error('Invalid selection')
        except ValueError:
            self.ui.print_error('Invalid input')
    
    def _reset_server_settings(self, server_name: str):
        """Reset server settings to defaults"""
        confirm = input(f"{self.ui.colors.YELLOW}Are you sure you want to reset all settings to defaults? (y/N): {self.ui.colors.RESET}").strip().lower()
        if confirm == 'y':
            server_config = ConfigManager.load_server_config(server_name)
            server_config['server_settings'] = {
                'motd': f'{server_name} Server',
                'port': 25565,
                'max-players': 20,
                'gamemode': 'survival',
                'difficulty': 'normal',
                'pvp': True,
                'white-list': False,
                'view-distance': 10,
                'online-mode': True,
                'allow-flight': False,
                'spawn-animals': True,
                'spawn-monsters': True,
                'spawn-npcs': True,
                'enable-command-block': False,
                'max-world-size': 29999984,
                'player-idle-timeout': 0,
                'level-type': 'default',
                'level-name': 'world'
            }
            ConfigManager.save_server_config(server_name, server_config)
            self.ui.print_success('Settings reset to defaults')