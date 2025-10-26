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
import psutil  # Add missing psutil import
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Union

# Add imports for custom exceptions
from core.exceptions import DownloadError, ConfigError, APIError
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
                try:
                    self.current_session_id = self.db.log_session_start(current_server, flavor, version)
                except Exception as db_error:
                    self.logger.log('ERROR', f'Failed to log session start: {db_error}')
                    # Continue despite database error
                
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
                    try:
                        self.monitor.start_monitoring(current_server, pid)
                    except Exception as monitor_error:
                        self.logger.log('ERROR', f'Failed to start monitoring: {monitor_error}')
                        # Continue despite monitoring error
                else:
                     self.logger.log('WARNING', 'Could not find server process PID for monitoring.')

                return True
            else:
                self.logger.log('ERROR', f'Failed to start server in screen: {stderr}')
                return False
        except subprocess.SubprocessError as e:
            self.logger.log('ERROR', f'Subprocess error starting server: {e}')
            return False
        except OSError as e:
            self.logger.log('ERROR', f'OS error starting server: {e}')
            return False
        except Exception as e:
            self.logger.log('ERROR', f'Unexpected error starting server: {e}')
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
        
        try:
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
                    self.logger.log('WARNING', 'Server did not stop gracefully, forcing quit')
                    force_cmd = ['screen', '-S', screen_name, '-X', 'quit']
                    run_command(force_cmd)
                
                # Stop monitoring
                try:
                    self.monitor.stop_monitoring(current_server)
                except Exception as monitor_error:
                    self.logger.log('ERROR', f'Failed to stop monitoring: {monitor_error}')
                
                # Log session end
                if self.current_session_id:
                    try:
                        self.db.log_session_end(self.current_session_id)
                    except Exception as db_error:
                        self.logger.log('ERROR', f'Failed to log session end: {db_error}')
                    finally:
                        self.current_session_id = None
                
                self.logger.log('SUCCESS', f'Server {current_server} stopped')
                return True
            else:
                self.logger.log('ERROR', f'Failed to stop server: {stderr}')
                return False
        except subprocess.SubprocessError as e:
            self.logger.log('ERROR', f'Subprocess error stopping server: {e}')
            return False
        except Exception as e:
            self.logger.log('ERROR', f'Unexpected error stopping server: {e}')
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
        except APIError as e:
            self.ui.print_error(f'Failed to fetch {server_type_name} versions: {e}')
            input('Press Enter to continue...')
            return
        except Exception as e:
            self.ui.print_error(f'Unexpected error fetching {server_type_name} versions: {e}')
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
            self._download_server(current_server, server_type_name, api_class, selected_version, flavor_key)
            self.ui.print_success(f'{server_type_name} {selected_version} installed successfully!')
        except DownloadError as e:
            self.ui.print_error(f'Installation failed: {e}')
        except APIError as e:
            self.ui.print_error(f'API error during installation: {e}')
        except Exception as e:
            self.ui.print_error(f'Unexpected error during installation: {e}')
        
        input('Press Enter to continue...')
    
    def _download_server(self, server_name: str, server_type: str, api_class, version: str, flavor_key: str) -> bool:
        """Download and install server JAR or PHAR
        
        Args:
            server_name: Name of the server
            server_type: Type of server (PaperMC, Purpur, etc.)
            api_class: API class to use for downloading
            version: Version to download
            flavor_key: Flavor key for the server
            
        Returns:
            True if download was successful, False otherwise
            
        Raises:
            DownloadError: If download fails
            APIError: If API call fails
        """
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
                    if hasattr(api_class, 'get_download_url'):
                        if server_type == "PocketMine-MP":
                            download_url = api_class.get_download_url(version)
                            target_filename = "PocketMine-MP.phar"
                        else:
                            build_number = build_info.get('build')
                            if build_number:
                                download_url = api_class.get_download_url(version, build_number)
                else:
                    raise DownloadError(f"Failed to get build info for {server_type} {version}")
            elif hasattr(api_class, 'get_download_url'):
                # Vanilla API
                download_url = api_class.get_download_url(version)
                target_filename = "server.jar"

            if not download_url:
                raise DownloadError(f"Could not generate download URL for {server_type} {version}")

            # Download the file
            jar_path = server_dir / target_filename
            
            self.logger.log('INFO', f'Downloading {server_type} {version} from {download_url}')
            
            # Use a request with a user agent
            req = urllib.request.Request(
                download_url, 
                headers={'User-Agent': 'MSM-Server-Manager'}
            )
            
            with urllib.request.urlopen(req, timeout=300) as response:  # 5 minute timeout
                with open(jar_path, 'wb') as f:
                    shutil.copyfileobj(response, f)
            
            # Verify download
            if not jar_path.exists() or jar_path.stat().st_size == 0:
                raise DownloadError(f"Download failed or resulted in empty file for {server_type} {version}")

            # Save server configuration
            server_config = ConfigManager.load_server_config(server_name)
            server_config.update({
                'server_flavor': flavor_key,
                'server_version': version,
                'server_build': build_info.get('build') if build_info else None,
                'server_settings': server_config.get('server_settings', {})
            })
            
            # Set default port based on server type
            if 'server_settings' in server_config:
                if server_type == "PocketMine-MP":
                    server_config['server_settings']['port'] = 19132  # Default Bedrock port
                else:
                    server_config['server_settings']['port'] = 25565  # Default Java port
            
            ConfigManager.save_server_config(server_name, server_config)
            
            self.logger.log('SUCCESS', f'Downloaded {server_type} {version} successfully')
            return True
            
        except urllib.error.URLError as e:
            # Clean up partial download
            if jar_path and jar_path.exists():
                jar_path.unlink()
            raise DownloadError(f"Network error downloading {server_type} {version}: {e}") from e
        except Exception as e:
            # Clean up partial download
            if jar_path and jar_path.exists():
                jar_path.unlink()
            # Re-raise specific exceptions or wrap generic ones
            if isinstance(e, (DownloadError, APIError)):
                raise
            else:
                raise DownloadError(f"Failed to download {server_type} {version}: {e}") from e

    def show_console(self):
        """Show server console by attaching to the screen session."""
        current_server = self.get_current_server()
        if not current_server:
            self.logger.log('ERROR', 'No server selected')
            return False
        
        screen_name = get_screen_session_name(current_server)
        
        if not is_screen_session_running(screen_name):
            self.logger.log('ERROR', f'Server {current_server} is not running')
            return False
        
        # Attach to the screen session
        try:
            # This will attach to the screen session and give control to the user
            # When they detach (Ctrl+A, D), control will return to our program
            attach_cmd = ['screen', '-r', screen_name]
            self.logger.log('INFO', f'Attaching to server console for {current_server}. Press Ctrl+A then D to detach.')
            subprocess.run(attach_cmd)
            return True
        except Exception as e:
            self.logger.log('ERROR', f'Failed to attach to server console: {e}')
            return False

    def show_performance_dashboard(self):
        """Display live performance metrics for the current server."""
        current_server = self.get_current_server()
        if not current_server:
            self.logger.log('ERROR', 'No server selected')
            return False

        screen_name = get_screen_session_name(current_server)

        if not is_screen_session_running(screen_name):
            self.logger.log('WARNING', f"Server '{current_server}' is not running.")
            return False

        self.logger.log('INFO', f"Starting performance dashboard for {current_server}")
        print(f"Starting Performance Dashboard for '{current_server}'... Press Ctrl+C to exit.")
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
                    self.logger.log('WARNING', "Could not find server process PID. Displaying limited info.")

            except Exception as e:
                self.logger.log('WARNING', f'Could not reliably get PID for monitoring: {e}')
                self.logger.log('WARNING', "Could not find server process PID. Displaying limited info.")

            while True:
                print(f"Performance Dashboard: {current_server} (Press Ctrl+C to exit)\n")

                cpu_percent = "N/A"
                mem_percent = "N/A"
                
                # Get actual process data if available
                if server_process and server_process.is_running():
                    try:
                        with server_process.oneshot():
                            cpu_percent = f"{server_process.cpu_percent():.1f}%"
                            mem_info = server_process.memory_info()
                            mem_percent = f"{mem_info.rss / (1024 * 1024):.1f} MB"
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
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
                            self.logger.log('WARNING', "Server process stopped running.")
                            break  # Exit dashboard loop
                    except psutil.NoSuchProcess:
                        self.logger.log('WARNING', "Server process disappeared.")
                        break  # Exit dashboard loop
                    except Exception as e:
                        self.logger.log('ERROR', f"Error getting process stats: {e}")
                        cpu_percent = "Error"
                        mem_rss_mb = "Error"

                print(f"  CPU Usage:  {cpu_percent}")
                print(f"  RAM Usage:  {mem_rss_mb}")
                # print(f"  RAM Percent: {mem_percent}")  # Optional

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
                    self.logger.log('DEBUG', f"Failed to parse log for TPS/Players: {e}")
                    tps_info = "Error parsing log"
                    player_count = "Error parsing log"

                print(f"  TPS (est.): {tps_info}")
                print(f"  Players:    {player_count}")
                # --- End Optional Parsing ---

                time.sleep(5)  # Refresh interval

        except KeyboardInterrupt:
            self.logger.log('INFO', "Performance dashboard stopped by user.")
            print("\nExiting dashboard...")
            # Stop monitoring if it was started
            try:
                if current_server:
                    self.monitor.stop_monitoring(current_server)
            except Exception as e:
                self.logger.log('WARNING', f'Error stopping monitoring: {e}')
            time.sleep(1)
            return True
        except Exception as e:
            self.logger.log('ERROR', f"Error in performance dashboard: {e}")
            print(f"Dashboard error: {e}")
            return False

    def show_statistics(self):
        """Display server statistics from the database."""
        try:
            current_server = self.get_current_server()
            if not current_server:
                print(f"{UI.colors.RED}No server selected.{UI.colors.RESET}")
                input("\nPress Enter to continue...")
                return

            if not self.db:
                print(f"{UI.colors.RED}Database not available.{UI.colors.RESET}")
                input("\nPress Enter to continue...")
                return

            # Get server statistics from database
            stats = self.db.get_server_statistics(current_server)
            
            def format_duration(seconds):
                if not seconds:
                    return "N/A"
                seconds = int(seconds)
                days, rem = divmod(seconds, 86400)
                hours, rem = divmod(rem, 3600)
                minutes, _ = divmod(rem, 60)
                return f"{days}d {hours}h {minutes}m"

            print(f"\n{UI.colors.BOLD}Statistics for: {current_server}{UI.colors.RESET}")
            print(f"  - Total Sessions:    {UI.colors.CYAN}{stats.get('total_sessions', 'N/A')}{UI.colors.RESET}")
            print(f"  - Total Uptime:      {UI.colors.CYAN}{format_duration(stats.get('total_uptime'))}{UI.colors.RESET}")
            print(f"  - Average Session:   {UI.colors.CYAN}{format_duration(stats.get('avg_duration'))}{UI.colors.RESET}")
            print(f"  - Total Crashes:     {UI.colors.YELLOW}{stats.get('total_crashes', 'N/A')}{UI.colors.RESET}")
            print(f"  - Total Restarts:    {UI.colors.YELLOW}{stats.get('total_restarts', 'N/A')}{UI.colors.RESET}")
            print("\n  --- 24-Hour Performance ---")
            print(f"  - Avg RAM Usage:     {UI.colors.CYAN}{stats.get('avg_ram_usage_24h', 0):.2f}%{UI.colors.RESET}")
            print(f"  - Avg CPU Usage:     {UI.colors.CYAN}{stats.get('avg_cpu_usage_24h', 0):.2f}%{UI.colors.RESET}")
            print(f"  - Peak Players:      {UI.colors.CYAN}{stats.get('peak_players_24h', 'N/A')}{UI.colors.RESET}")
            
        except Exception as e:
            if self.logger:
                self.logger.log('ERROR', f'Failed to show statistics: {e}')
            print(f"{UI.colors.RED}Failed to load statistics: {e}{UI.colors.RESET}")
        finally:
            input("\nPress Enter to continue...")

    def configure_server_menu(self):
        """Interactive configuration menu for server settings."""
        try:
            current_server = self.get_current_server()
            if not current_server:
                print(f"{UI.colors.RED}No server selected.{UI.colors.RESET}")
                input("\nPress Enter to continue...")
                return

            config = ConfigManager.load()
            server_config = config.get("servers", {}).get(current_server, {})
            settings = server_config.get("server_settings", {})

            while True:
                print(f"\n{UI.colors.BOLD}Configure Server: {current_server}{UI.colors.RESET}")
                print(f" 1. RAM Allocation: {UI.colors.CYAN}{server_config.get('ram_mb', 1024)} MB{UI.colors.RESET}")
                print(f" 2. Port: {UI.colors.CYAN}{settings.get('port', 25565)}{UI.colors.RESET}")
                print(f" 3. Auto Restart: {UI.colors.CYAN}{'Yes' if server_config.get('auto_restart') else 'No'}{UI.colors.RESET}")
                print(f" 4. MOTD: {UI.colors.CYAN}{settings.get('motd', 'A Minecraft Server')}{UI.colors.RESET}")
                print(f" 5. Max Players: {UI.colors.CYAN}{settings.get('max-players', 20)}{UI.colors.RESET}")
                print(f" 0. Back to Main Menu")
                
                choice = input(f"\n{UI.colors.YELLOW}Select option to change: {UI.colors.RESET}").strip()
                
                try:
                    if choice == '1':
                        new_ram = input("Enter new RAM allocation (MB): ").strip()
                        if new_ram.isdigit():
                            server_config['ram_mb'] = int(new_ram)
                            print(f"{UI.colors.GREEN}RAM allocation updated to {new_ram} MB{UI.colors.RESET}")
                        else:
                            print(f"{UI.colors.RED}Invalid input. Please enter a number.{UI.colors.RESET}")
                    elif choice == '2':
                        new_port = input("Enter new port: ").strip()
                        if new_port.isdigit() and 1 <= int(new_port) <= 65535:
                            settings['port'] = int(new_port)
                            print(f"{UI.colors.GREEN}Port updated to {new_port}{UI.colors.RESET}")
                        else:
                            print(f"{UI.colors.RED}Invalid port. Please enter a number between 1-65535.{UI.colors.RESET}")
                    elif choice == '3':
                        server_config['auto_restart'] = not server_config.get('auto_restart', False)
                        status = "enabled" if server_config['auto_restart'] else "disabled"
                        print(f"{UI.colors.GREEN}Auto restart {status}{UI.colors.RESET}")
                    elif choice == '4':
                        new_motd = input("Enter new MOTD: ").strip()
                        if new_motd:
                            settings['motd'] = new_motd
                            print(f"{UI.colors.GREEN}MOTD updated{UI.colors.RESET}")
                        else:
                            print(f"{UI.colors.RED}MOTD cannot be empty{UI.colors.RESET}")
                    elif choice == '5':
                        new_max_players = input("Enter max players: ").strip()
                        if new_max_players.isdigit() and 1 <= int(new_max_players) <= 1000:
                            settings['max-players'] = int(new_max_players)
                            print(f"{UI.colors.GREEN}Max players updated to {new_max_players}{UI.colors.RESET}")
                        else:
                            print(f"{UI.colors.RED}Invalid input. Please enter a number between 1-1000.{UI.colors.RESET}")
                    elif choice == '0':
                        break
                    else:
                        print(f"{UI.colors.RED}Invalid choice.{UI.colors.RESET}")
                        continue
                    
                    # Update the configuration
                    server_config['server_settings'] = settings
                    config['servers'][current_server] = server_config
                    ConfigManager.save(config)
                    
                except ValueError:
                    print(f"{UI.colors.RED}Invalid input, please enter a number where required.{UI.colors.RESET}")
                except Exception as e:
                    if self.logger:
                        self.logger.log('ERROR', f'Error updating configuration: {e}')
                    print(f"{UI.colors.RED}Error updating configuration: {e}{UI.colors.RESET}")
                    
        except Exception as e:
            if self.logger:
                self.logger.log('ERROR', f'Failed to configure server: {e}')
            print(f"{UI.colors.RED}Failed to configure server: {e}{UI.colors.RESET}")
            input("\nPress Enter to continue...")