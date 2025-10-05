# ============================================================================
# server_manager.py - Core logic: start, stop, install, configure servers
# ============================================================================

import time
import re
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional

from config import ConfigManager, DatabaseManager, get_config_root, get_servers_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log, detect_total_ram_mb, suggest_ram_allocation, is_screen_session_running, run_command
from api_client import PaperMCAPI, PurpurAPI, FoliaAPI, FabricAPI, QuiltAPI, VanillaAPI


class ServerManager:
    """Manages Minecraft servers."""
    
    def __init__(self):
        """Initialize ServerManager with NetworkHelper."""
        self.network_helper = NetworkHelper()
    
    @staticmethod
    def list_servers() -> List[str]:
        """List all created servers."""
        servers_root = get_servers_root()
        if not servers_root.exists():
            return []
        
        servers = [d.name for d in servers_root.iterdir() if d.is_dir()]
        return sorted(servers)
    
    @staticmethod
    def get_current_server() -> Optional[str]:
        """Get currently selected server."""
        config_file = get_config_root() / "current_server.txt"
        if config_file.exists():
            return config_file.read_text().strip()
        return None
    
    @staticmethod
    def set_current_server(name: str):
        """Set currently selected server."""
        config_file = get_config_root() / "current_server.txt"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(name)
        log(f"Current server set to: {name}")
    
    def start_server_menu(self):
        """Start the selected Minecraft server in a detached screen session."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Start Server{UI.colors.RESET}\n")
        
        current_server = self.get_current_server()
        if not current_server:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return

        session_name = f"msm-{current_server}"
        
        if is_screen_session_running(session_name):
            print_error(f"Server '{current_server}' is already running in screen session '{session_name}'.")
            print_info("Use 'Server Console' to attach.")
            input("\nPress Enter to continue...")
            return
        
        server_path = get_servers_root() / current_server
        
        # Find the first .jar file in the directory (robust JAR finding)
        try:
            jar_file = next(server_path.glob("*.jar"))
        except StopIteration:
            print_error(f"No .jar file found in {server_path}")
            print_info("Please install the server first using option 3.")
            input("\nPress Enter to continue...")
            return
            
        eula_file = server_path / "eula.txt"

        # EULA auto-acceptance logic
        if not eula_file.exists():
            print_warning("eula.txt not found. A brief first run is needed to generate it.")
            try:
                # Run once for a very short time to generate files, then kill it.
                # This is a common trick for server setup.
                temp_proc = subprocess.Popen(
                    ["java", "-jar", str(jar_file), "nogui"],
                    cwd=str(server_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(5) # Give it a few seconds to generate files
                temp_proc.kill()
                print_info("Initial files generated.")
            except Exception as e:
                print_error(f"Failed to generate initial server files: {e}")
                input("\nPress Enter to continue...")
                return

        if eula_file.exists():
            with open(eula_file, "r+") as f:
                content = f.read()
                if "eula=false" in content:
                    print_info("Accepting Minecraft EULA...")
                    f.seek(0)
                    f.write(content.replace("eula=false", "eula=true"))
                    f.truncate()
                    log(f"EULA accepted for {current_server}")

        # Load server-specific config
        config = ConfigManager.load_server_config(current_server)
        ram_alloc = config.get("ram_mb", suggest_ram_allocation())

        print_info(f"Starting server '{current_server}' with {ram_alloc}MB RAM...")
        
        # Command to run inside the server's directory
        start_cmd = [
            "screen", "-dmS", session_name,
            "java", f"-Xmx{ram_alloc}M", f"-Xms{ram_alloc}M",
            "-jar", str(jar_file), "nogui"
        ]

        # Use run_command from utils, but execute from the server's directory
        try:
            subprocess.run(start_cmd, check=True, cwd=str(server_path))
            print_success(f"Server '{current_server}' started successfully in session '{session_name}'.")
            log(f"Started server {current_server}")
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to start server: {e}")
            log(f"Failed to start server {current_server}: {e}", "ERROR")

        input("\nPress Enter to continue...")
    
    def stop_server_menu(self):
        """Stop the server by sending the 'stop' command to its screen session."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Stop Server{UI.colors.RESET}\n")
        
        current_server = self.get_current_server()
        if not current_server:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
        
        session_name = f"msm-{current_server}"

        if not is_screen_session_running(session_name):
            print_warning(f"Server '{current_server}' does not appear to be running.")
            input("\nPress Enter to continue...")
            return
        
        print_info(f"Sending 'stop' command to server '{current_server}'...")
        
        # The '\n' is crucial to simulate pressing Enter
        stop_cmd = ["screen", "-S", session_name, "-X", "stuff", "stop\n"]
        
        returncode, _, stderr = run_command(stop_cmd)
        
        if returncode == 0:
            print_success("Stop command sent. The server will shut down shortly.")
            log(f"Sent stop command to {current_server}")
        else:
            print_error(f"Failed to send stop command: {stderr}")
            log(f"Failed to stop {current_server}: {stderr}", "ERROR")
            
        input("\nPress Enter to continue...")
    
    def install_update_menu(self):
        """Install/update server menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Install/Update Server{UI.colors.RESET}\n")
        
        current_server = self.get_current_server()
        if not current_server:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
            
        server_path = get_servers_root() / current_server
        
        print_info("Select server type:")
        print(" 1. PaperMC (default)")
        print(" 2. Purpur")
        print(" 3. Folia")
        print(" 4. Fabric")
        print(" 5. Quilt")
        print(" 6. Vanilla Minecraft")
        print()
        
        server_type_choice = input(f"{UI.colors.YELLOW}Select server type (1-6, or 0 to cancel): {UI.colors.RESET}").strip()
        
        if server_type_choice == "0":
            return
            
        # Map choices to API classes
        api_map = {
            "1": ("PaperMC", PaperMCAPI),
            "2": ("Purpur", PurpurAPI),
            "3": ("Folia", FoliaAPI),
            "4": ("Fabric", FabricAPI),
            "5": ("Quilt", QuiltAPI),
            "6": ("Vanilla", VanillaAPI)
        }
        
        if server_type_choice not in api_map:
            print_error("Invalid selection.")
            input("\nPress Enter to continue...")
            return
            
        server_type_name, api_class = api_map[server_type_choice]
        print_info(f"Selected server type: {server_type_name}")
        
        # Initialize variables
        selected_version = None
        build_number = None
        selected_loader_version = None
        download_url = None
        
        # Special handling for Vanilla
        if server_type_name == "Vanilla":
            # Get game versions
            print_info("Fetching game versions...")
            versions = api_class.get_versions()
            if not versions:
                print_error(f"Failed to fetch {server_type_name} versions.")
                input("\nPress Enter to continue...")
                return
                
            # Display versions
            print_info(f"Available Minecraft versions:")
            for i, version in enumerate(versions[-10:], 1):  # Show last 10 versions
                print(f" {i}. {version}")
                
            print(f"\nLatest version is {versions[-1]}")
            choice = input(f"\nSelect version (1-{len(versions[-10:])}) or press Enter for latest: ").strip()
            
            if not choice:
                selected_version = versions[-1]
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(versions[-10:]):
                        selected_version = versions[-10:][index]
                    else:
                        print_error("Invalid selection.")
                        input("\nPress Enter to continue...")
                        return
                except ValueError:
                    print_error("Invalid input.")
                    input("\nPress Enter to continue...")
                    return
            
            print_info(f"Selected version: {selected_version}")
            
            # Get download URL
            download_url = api_class.get_download_url(selected_version)
            
            # Download the server jar
            if download_url:
                self._download_and_install_server(server_path, current_server, server_type_name, selected_version, selected_version, download_url)
        # Special handling for Fabric and Quilt (they need loader versions)
        elif server_type_name in ["Fabric", "Quilt"]:
            # Get game versions
            print_info("Fetching game versions...")
            versions = api_class.get_versions()
            if not versions:
                print_error(f"Failed to fetch {server_type_name} game versions.")
                input("\nPress Enter to continue...")
                return
                
            # Display versions
            print_info(f"Available Minecraft versions:")
            for i, version in enumerate(versions[-10:], 1):  # Show last 10 versions
                print(f" {i}. {version}")
                
            print(f"\nLatest version is {versions[-1]}")
            choice = input(f"\nSelect version (1-{len(versions[-10:])}) or press Enter for latest: ").strip()
            
            if not choice:
                selected_version = versions[-1]
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(versions[-10:]):
                        selected_version = versions[-10:][index]
                    else:
                        print_error("Invalid selection.")
                        input("\nPress Enter to continue...")
                        return
                except ValueError:
                    print_error("Invalid input.")
                    input("\nPress Enter to continue...")
                    return
            
            # Get loader versions
            print_info("Fetching loader versions...")
            loader_versions = api_class.get_loader_versions()
            if not loader_versions:
                print_error(f"Failed to fetch {server_type_name} loader versions.")
                input("\nPress Enter to continue...")
                return
                
            print_info(f"Available loader versions:")
            for i, version in enumerate(loader_versions[:5], 1):  # Show first 5 versions
                print(f" {i}. {version}")
                
            loader_choice = input(f"\nSelect loader version (1-{len(loader_versions[:5])}) or press Enter for latest: ").strip()
            
            if not loader_choice:
                selected_loader_version = loader_versions[0]
            else:
                try:
                    index = int(loader_choice) - 1
                    if 0 <= index < len(loader_versions[:5]):
                        selected_loader_version = loader_versions[:5][index]
                    else:
                        print_error("Invalid selection.")
                        input("\nPress Enter to continue...")
                        return
                except ValueError:
                    print_error("Invalid input.")
                    input("\nPress Enter to continue...")
                    return
                    
            print_info(f"Selected version: {selected_version}")
            print_info(f"Selected loader: {selected_loader_version}")
            
            # Get download URL
            download_url = api_class.get_download_url(selected_version, selected_loader_version)
            
            # Download the server jar
            if download_url:
                self._download_and_install_server(server_path, current_server, server_type_name, selected_version, selected_loader_version, download_url)
        else:
            # Standard handling for PaperMC, Purpur, Folia
            print_info("Fetching versions...")
            versions = api_class.get_versions()
            if not versions:
                print_error(f"Failed to fetch {server_type_name} versions.")
                input("\nPress Enter to continue...")
                return
                
            # Display versions
            print_info(f"Available Minecraft versions:")
            for i, version in enumerate(versions[-10:], 1):  # Show last 10 versions
                print(f" {i}. {version}")
                
            print(f"\nLatest version is {versions[-1]}")
            choice = input(f"\nSelect version (1-{len(versions[-10:])}) or press Enter for latest: ").strip()
            
            if not choice:
                selected_version = versions[-1]
            else:
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(versions[-10:]):
                        selected_version = versions[-10:][index]
                    else:
                        print_error("Invalid selection.")
                        input("\nPress Enter to continue...")
                        return
                except ValueError:
                    print_error("Invalid input.")
                    input("\nPress Enter to continue...")
                    return
            
            print_info(f"Selected version: {selected_version}")
            
            # Fetch latest build for selected version
            print_info("Fetching latest build...")
            build_info = api_class.get_latest_build(selected_version)
            if not build_info:
                print_error(f"Failed to fetch build information for {selected_version}.")
                input("\nPress Enter to continue...")
                return
                
            build_number = build_info.get("build")
            if not isinstance(build_number, int):
                print_error("Failed to extract build number from API response.")
                input("\nPress Enter to continue...")
                return
                
            print_info(f"Latest build: {build_number}")
            
            # Get download URL
            download_url = api_class.get_download_url(selected_version, build_number)
            
            # Download the server jar
            if download_url:
                self._download_and_install_server(server_path, current_server, server_type_name, selected_version, build_number, download_url)
    
    def _download_and_install_server(self, server_path, current_server, server_type_name, selected_version, build_identifier, download_url):
        """Download and install the server jar file."""
        jar_file = server_path / "server.jar"
        print_info(f"Downloading server.jar to {jar_file}...")
        
        try:
            # Simple download with progress reporting
            def report_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                if total_size > 0:
                    percent = min(100, (downloaded * 100) // total_size)
                    print(f"\rDownloading: {percent}% ({downloaded}/{total_size} bytes)", end="", flush=True)
                else:
                    # If total_size is unknown, show downloaded bytes
                    print(f"\rDownloading: {downloaded} bytes", end="", flush=True)
            
            urllib.request.urlretrieve(download_url, jar_file, reporthook=report_progress)
            print()  # New line after progress
            print_success("Server downloaded successfully!")
            
            # Verify the downloaded file exists and is not empty
            if not jar_file.exists():
                print_error("Download completed but server.jar file not found!")
                log(f"Download verification failed for {current_server}: server.jar not found", "ERROR")
                return
                
            if jar_file.stat().st_size == 0:
                print_error("Download completed but server.jar file is empty!")
                log(f"Download verification failed for {current_server}: server.jar is empty", "ERROR")
                return
            
            # Update server config with version info
            config = ConfigManager.load_server_config(current_server)
            config["version"] = selected_version
            config["server_type"] = server_type_name
            config["build"] = build_identifier
            ConfigManager.save_server_config(current_server, config)
            
            log(f"Installed {server_type_name} {selected_version} build {build_identifier} for server {current_server}")
            
        except urllib.error.HTTPError as e:
            # Handle HTTP-specific errors
            if e.code == 404:
                error_msg = f"Download failed: File not found (404). The server version may be unavailable."
            elif e.code == 403:
                error_msg = f"Download failed: Access denied (403). Check your credentials or try a different version."
            elif e.code >= 500:
                error_msg = f"Download failed: Server error ({e.code}). Try again later."
            else:
                error_msg = f"HTTP error during download: {e.code} {e.reason}"
            
            print_error(error_msg)
            log(f"HTTP error downloading server for {current_server}: {e.code} {e.reason}", "ERROR")
        except urllib.error.URLError as e:
            error_msg = f"Network error during download: {e}"
            if hasattr(e, 'reason'):
                if isinstance(e.reason, TimeoutError):
                    error_msg = f"Download timeout: Connection to server timed out. Try again later."
                elif isinstance(e.reason, OSError):
                    error_msg = f"DNS resolution failed: Could not resolve server address. Check your internet connection."
            
            print_error(error_msg)
            log(f"Network error downloading server for {current_server}: {e}", "ERROR")
        except PermissionError as e:
            print_error(f"Permission denied while writing to {jar_file}: Check directory permissions or run as administrator.")
            log(f"Permission error downloading server for {current_server}: {e}", "ERROR")
        except FileNotFoundError as e:
            print_error(f"Directory not found: {server_path}. Ensure the server directory exists.")
            log(f"File not found error downloading server for {current_server}: {e}", "ERROR")
        except Exception as e:
            print_error(f"Unexpected error during download: {str(e)}. Check logs for details.")
            log(f"Unexpected error downloading server for {current_server}: {e}", "ERROR")
    
    def configure_server_menu(self):
        """Configure server menu with Aternos-like interface."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Configure Server{UI.colors.RESET}\n")
        
        current = self.get_current_server()
        if not current:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
        
        server_path = get_servers_root() / current
        properties_file = server_path / "server.properties"
        
        # Load current configuration
        config = {}
        if properties_file.exists():
            try:
                with open(properties_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            config[key] = value
            except Exception as e:
                print_error(f"Failed to read server.properties: {e}")
                input("\nPress Enter to continue...")
                return
        else:
            print_warning("server.properties not found. Starting with default values.")
            print_info("Note: This file will be generated when the server is first started.")
            input("\nPress Enter to continue...")
            return
        
        print_info(f"Configuring: {current}")
        print()
        
        while True:
            clear_screen()
            print_header("1.1.0")
            print(f"\n{UI.colors.BOLD}Configure Server: {current}{UI.colors.RESET}\n")
            
            # Display categorized configuration options like Aternos
            print(f"{UI.colors.BOLD}Basic Settings:{UI.colors.RESET}")
            print(f" 1. Server Port          : {config.get('server-port', '25565')}")
            print(f" 2. Maximum Players      : {config.get('max-players', '20')}")
            print(f" 3. Message of the Day   : {config.get('motd', 'A Minecraft Server')}")
            print()
            
            print(f"{UI.colors.BOLD}Game Settings:{UI.colors.RESET}")
            print(f" 4. Game Mode            : {config.get('gamemode', 'survival')}")
            print(f" 5. Difficulty           : {config.get('difficulty', 'easy')}")
            print(f" 6. PVP                  : {config.get('pvp', 'true')}")
            print(f" 7. Whitelist            : {config.get('white-list', 'false')}")
            print(f" 8. Online Mode (Cracked): {config.get('online-mode', 'true')}")
            print(f" 9. Force Game Mode      : {config.get('force-gamemode', 'false')}")
            print()
            
            print(f"{UI.colors.BOLD}World Settings:{UI.colors.RESET}")
            print(f"10. Spawn Protection     : {config.get('spawn-protection', '16')}")
            print(f"11. Allow Nether         : {config.get('allow-nether', 'true')}")
            print(f"12. Spawn Monsters       : {config.get('spawn-monsters', 'true')}")
            print(f"13. View Distance        : {config.get('view-distance', '10')}")
            print()
            
            print(f"{UI.colors.BOLD}Advanced Settings:{UI.colors.RESET}")
            print(f"14. Enable Command Blocks: {config.get('enable-command-block', 'false')}")
            print(f"15. Allow Flight         : {config.get('allow-flight', 'false')}")
            print(f"16. Resource Pack        : {config.get('resource-pack', '')}")
            print()
            
            print("0. Back to main menu")
            print()
            
            choice = input(f"{UI.colors.YELLOW}Select option to edit (0-16): {UI.colors.RESET}").strip()
            
            if choice == "0":
                return
            
            # Handle each configuration option
            try:
                if choice == "1":
                    current_value = config.get('server-port', '25565')
                    new_value = input(f"Server Port [{current_value}]: ").strip()
                    if new_value:
                        config['server-port'] = new_value
                        self._save_server_properties(config, properties_file, current)
                
                elif choice == "2":
                    current_value = config.get('max-players', '20')
                    new_value = input(f"Maximum Players [{current_value}]: ").strip()
                    if new_value:
                        config['max-players'] = new_value
                        self._save_server_properties(config, properties_file, current)
                
                elif choice == "3":
                    current_value = config.get('motd', 'A Minecraft Server')
                    new_value = input(f"Message of the Day [{current_value}]: ").strip()
                    if new_value:
                        config['motd'] = new_value if new_value else current_value
                        self._save_server_properties(config, properties_file, current)
                
                elif choice == "4":
                    current_value = config.get('gamemode', 'survival')
                    print("Game Modes: survival, creative, adventure, spectator")
                    new_value = input(f"Game Mode [{current_value}]: ").strip()
                    if new_value and new_value in ['survival', 'creative', 'adventure', 'spectator']:
                        config['gamemode'] = new_value
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid game mode. Use: survival, creative, adventure, or spectator")
                        input("\nPress Enter to continue...")
                
                elif choice == "5":
                    current_value = config.get('difficulty', 'easy')
                    print("Difficulties: peaceful, easy, normal, hard")
                    new_value = input(f"Difficulty [{current_value}]: ").strip()
                    if new_value and new_value in ['peaceful', 'easy', 'normal', 'hard']:
                        config['difficulty'] = new_value
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid difficulty. Use: peaceful, easy, normal, or hard")
                        input("\nPress Enter to continue...")
                
                elif choice == "6":
                    current_value = config.get('pvp', 'true')
                    print("PVP: true or false")
                    new_value = input(f"Enable PVP [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['pvp'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "7":
                    current_value = config.get('white-list', 'false')
                    print("Whitelist: true or false")
                    new_value = input(f"Enable Whitelist [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['white-list'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "8":
                    current_value = config.get('online-mode', 'true')
                    print("Online Mode (Cracked): true or false")
                    new_value = input(f"Online Mode [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['online-mode'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "9":
                    current_value = config.get('force-gamemode', 'false')
                    print("Force Game Mode: true or false")
                    new_value = input(f"Force Game Mode [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['force-gamemode'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "10":
                    current_value = config.get('spawn-protection', '16')
                    new_value = input(f"Spawn Protection [{current_value}]: ").strip()
                    if new_value:
                        try:
                            int(new_value)  # Validate it's a number
                            config['spawn-protection'] = new_value
                            self._save_server_properties(config, properties_file, current)
                        except ValueError:
                            print_error("Invalid value. Must be a number.")
                            input("\nPress Enter to continue...")
                
                elif choice == "11":
                    current_value = config.get('allow-nether', 'true')
                    print("Allow Nether: true or false")
                    new_value = input(f"Allow Nether [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['allow-nether'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "12":
                    current_value = config.get('spawn-monsters', 'true')
                    print("Spawn Monsters: true or false")
                    new_value = input(f"Spawn Monsters [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['spawn-monsters'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "13":
                    current_value = config.get('view-distance', '10')
                    new_value = input(f"View Distance [{current_value}]: ").strip()
                    if new_value:
                        try:
                            int(new_value)  # Validate it's a number
                            config['view-distance'] = new_value
                            self._save_server_properties(config, properties_file, current)
                        except ValueError:
                            print_error("Invalid value. Must be a number.")
                            input("\nPress Enter to continue...")
                
                elif choice == "14":
                    current_value = config.get('enable-command-block', 'false')
                    print("Enable Command Blocks: true or false")
                    new_value = input(f"Enable Command Blocks [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['enable-command-block'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "15":
                    current_value = config.get('allow-flight', 'false')
                    print("Allow Flight: true or false")
                    new_value = input(f"Allow Flight [{current_value}]: ").strip()
                    if new_value and new_value.lower() in ['true', 'false']:
                        config['allow-flight'] = new_value.lower()
                        self._save_server_properties(config, properties_file, current)
                    elif new_value:
                        print_error("Invalid value. Use: true or false")
                        input("\nPress Enter to continue...")
                
                elif choice == "16":
                    current_value = config.get('resource-pack', '')
                    new_value = input(f"Resource Pack URL [{current_value}]: ").strip()
                    if new_value:
                        config['resource-pack'] = new_value
                        self._save_server_properties(config, properties_file, current)
                    elif new_value == "":  # Allow clearing the value
                        config['resource-pack'] = ""
                        self._save_server_properties(config, properties_file, current)
                
                else:
                    print_error("Invalid selection.")
                    input("\nPress Enter to continue...")
            
            except ValueError:
                print_error("Invalid input.")
                input("\nPress Enter to continue...")
    
    def _save_server_properties(self, config, properties_file, server_name):
        """Save server properties file."""
        try:
            with open(properties_file, "w") as f:
                f.write("# Minecraft server properties\n")
                f.write(f"# Updated by MSM on {time.strftime('%a %b %d %H:%M:%S %Z %Y')}\n\n")
                for k, v in config.items():
                    f.write(f"{k}={v}\n")
            
            print_success("Configuration saved successfully!")
            log(f"Updated server properties for {server_name}")
            
        except Exception as e:
            print_error(f"Failed to save server.properties: {e}")
            log(f"Failed to save server.properties for {server_name}: {e}", "ERROR")
        
        input("\nPress Enter to continue...")
    
    def console_menu(self):
        """Attach to the server's screen session."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Server Console{UI.colors.RESET}\n")
        
        current_server = self.get_current_server()
        if not current_server:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
        
        session_name = f"msm-{current_server}"
        if not is_screen_session_running(session_name):
            print_error(f"Server '{current_server}' is not running.")
            input("\nPress Enter to continue...")
            return
            
        print_info(f"Attaching to console for '{current_server}'.")
        print_info("To detach, press: Ctrl+A then D")
        input("\nPress Enter to attach...")
        
        # Use os.system for interactive attachment
        import os
        os.system(f"screen -r {session_name}")
    
    def statistics_menu(self):
        """Statistics menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Server Statistics{UI.colors.RESET}\n")
        
        current = self.get_current_server()
        if not current:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
        
        # Query database for server statistics
        try:
            from config import get_db_file
            import sqlite3
            
            db_file = get_db_file()
            if not db_file.exists():
                print_warning("No statistics database found.")
                input("\nPress Enter to continue...")
                return
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get server statistics
            cursor.execute("""
                SELECT created_at, last_started, total_uptime, crash_count, session_count
                FROM servers
                WHERE name = ?
            """, (current,))
            
            result = cursor.fetchone()
            if not result:
                print_warning("No statistics found for this server.")
                input("\nPress Enter to continue...")
                conn.close()
                return
            
            created_at, last_started, total_uptime, crash_count, session_count = result
            
            # Convert timestamps to readable format
            from datetime import datetime
            if created_at:
                created_date = datetime.fromtimestamp(created_at).strftime('%Y-%m-%d %H:%M')
            else:
                created_date = "Unknown"
                
            if last_started:
                last_started_date = datetime.fromtimestamp(last_started).strftime('%Y-%m-%d %H:%M')
            else:
                last_started_date = "Never"
            
            # Convert uptime to hours and minutes
            total_hours = total_uptime // 3600
            total_minutes = (total_uptime % 3600) // 60
            
            print_info(f"Statistics for: {current}")
            print()
            print(f"Created:        {created_date}")
            print(f"Last Started:   {last_started_date}")
            print(f"Total Uptime:   {total_hours}h {total_minutes}m")
            print(f"Sessions:       {session_count}")
            print(f"Crashes:        {crash_count}")
            
            # Get recent sessions
            print()
            print(f"{UI.colors.BOLD}Recent Sessions:{UI.colors.RESET}")
            cursor.execute("""
                SELECT start_time, end_time, duration, crash
                FROM sessions
                WHERE server_name = ?
                ORDER BY start_time DESC
                LIMIT 5
            """, (current,))
            
            sessions = cursor.fetchall()
            if sessions:
                print(f"{'Start Time':<20} {'Duration':<10} {'Status'}")
                print("-" * 40)
                for start_time, end_time, duration, crash in sessions:
                    if start_time:
                        start_date = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M')
                    else:
                        start_date = "Unknown"
                    duration_minutes = duration // 60 if duration else 0
                    status = "Crashed" if crash else "Completed"
                    print(f"{start_date:<20} {duration_minutes}m{'':<7} {status}")
            else:
                print("No session data available.")
            
            conn.close()
            
        except Exception as e:
            print_error(f"Failed to fetch statistics: {e}")
            log(f"Statistics fetch failed for {current}: {e}", "ERROR")
        
        print()
        input("Press Enter to continue...")
    
    def create_server_menu(self):
        """Create new server menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Create New Server{UI.colors.RESET}\n")
        
        name = input("Enter server name: ").strip()
        
        if not name:
            print_error("Server name cannot be empty")
            input("\nPress Enter to continue...")
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            print_error("Invalid characters in name")
            input("\nPress Enter to continue...")
            return
        
        server_path = get_servers_root() / name
        
        if server_path.exists():
            print_error(f"Server '{name}' already exists")
            input("\nPress Enter to continue...")
            return
        
        print_info(f"Creating server: {name}")
        
        try:
            server_path.mkdir(parents=True, exist_ok=True)
            
            config = {
                "name": name,
                "created": int(time.time()),
                "ram_mb": suggest_ram_allocation(),
                "port": 25565,
                "version": "latest"
            }
            
            ConfigManager.save_server_config(name, config)
            DatabaseManager.add_server(name, int(time.time()))
            
            self.set_current_server(name)
            
            print_success(f"Server '{name}' created")
            print_info(f"Directory: {server_path}")
            print_info(f"RAM: {config['ram_mb']}MB")
            
            log(f"Server created: {name}")
            
        except Exception as e:
            print_error(f"Failed to create server: {e}")
            log(f"Server creation failed: {e}", "ERROR")
        
        input("\nPress Enter to continue...")
    
    def switch_server_menu(self):
        """Switch server menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Switch Server{UI.colors.RESET}\n")
        
        servers = self.list_servers()
        
        if not servers:
            print_warning("No servers created yet")
            input("\nPress Enter to continue...")
            return
        
        current = self.get_current_server()
        
        print("Available servers:\n")
        for i, server in enumerate(servers, 1):
            marker = " (current)" if server == current else ""
            print(f" {i}. {server}{marker}")
        
        print()
        choice = input(f"Select server (1-{len(servers)}): ").strip()
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(servers):
                selected = servers[index]
                self.set_current_server(selected)
                print_success(f"Switched to: {selected}")
                log(f"Switched to: {selected}")
        except ValueError:
            print_error("Invalid input")
        
        input("\nPress Enter to continue...")
    
    def monitor_performance_menu(self):
        """Monitor server performance (TPS, RAM usage)."""
        while True:
            clear_screen()
            print_header("1.1.0")
            print(f"\n{UI.colors.BOLD}Performance Monitor{UI.colors.RESET}\n")
            
            current_server = self.get_current_server()
            if not current_server:
                print_error("No server selected.")
                input("\nPress Enter to continue...")
                return
                
            session_name = f"msm-{current_server}"
            
            if not is_screen_session_running(session_name):
                print_warning(f"Server '{current_server}' is not running.")
                input("\nPress Enter to continue...")
                return
                
            print_info(f"Monitoring performance for: {current_server}")
            print()
            print("Options:")
            print(" 1. View current TPS")
            print(" 2. View memory usage")
            print(" 3. View online players")
            print(" 4. Continuous monitoring")
            print(" 5. Stream console output")
            print(" 0. Back to main menu")
            print()
            
            choice = input(f"{UI.colors.YELLOW}Select option (0-5): {UI.colors.RESET}").strip()
            
            if choice == "1":
                self._get_tps(current_server, session_name)
            elif choice == "2":
                self._get_memory_usage(current_server, session_name)
            elif choice == "3":
                self._get_online_players(current_server)
            elif choice == "4":
                self._continuous_monitoring(current_server, session_name)
            elif choice == "5":
                self._stream_console_output(current_server)
            elif choice == "0":
                return
            else:
                print_error("Invalid option.")
                
            if choice != "0":
                input("\nPress Enter to continue...")

    def _get_tps(self, server_name, session_name):
        """Get current TPS (Ticks Per Second) of the server."""
        print_info("Fetching TPS...")
        
        # Send command to get TPS
        tps_cmd = ["screen", "-S", session_name, "-X", "stuff", "tps\n"]
        returncode, _, stderr = run_command(tps_cmd)
        
        if returncode == 0:
            print_info("TPS command sent. Checking latest log for output...")
        else:
            print_error(f"Failed to send TPS command: {stderr}")
            
        # Try to read latest.log for TPS info
        server_path = get_servers_root() / server_name
        log_file = server_path / "logs" / "latest.log"
        
        if log_file.exists():
            try:
                # Read last 100 lines of log file
                with open(log_file, "r") as f:
                    lines = f.readlines()[-100:]
                
                # Look for TPS information
                tps_lines = [line for line in lines if "TPS" in line.upper() and ("CURRENT" in line.upper() or "AVG" in line.upper() or "TICK" in line.upper())]
                
                if tps_lines:
                    print()
                    print(f"{UI.colors.BOLD}Recent TPS Information:{UI.colors.RESET}")
                    for line in tps_lines[-10:]:  # Show last 10 TPS lines
                        print(line.strip())
                else:
                    print_info("No recent TPS information found in logs.")
                    print_info("Note: TPS monitoring requires server software that reports TPS.")
            except Exception as e:
                print_error(f"Failed to read log file: {e}")
        else:
            print_info("Log file not found. Server may not have started yet.")

    def _get_memory_usage(self, server_name, session_name):
        """Get current memory usage of the server."""
        print_info("Fetching memory usage...")
        
        # Try to get memory usage from system
        try:
            # This is a simplified approach - in a real implementation, you might want to
            # parse the actual JVM memory usage from the server process
            import psutil
            
            # Find screen process
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'screen' and session_name in ' '.join(proc.info['cmdline']):
                        # Get memory info for this process
                        memory_info = proc.memory_info()
                        memory_mb = memory_info.rss / (1024 * 1024)
                        print_success(f"Memory usage: {memory_mb:.1f} MB")
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            print_warning("Server process not found or not running in screen.")
        except ImportError:
            print_info("psutil not available. Install with: pip install psutil")
        except Exception as e:
            print_error(f"Failed to get memory usage: {e}")

    def _get_online_players(self, server_name):
        """Get list of online players from server log."""
        print_info("Fetching online players...")
        
        server_path = get_servers_root() / server_name
        log_file = server_path / "logs" / "latest.log"
        
        if not log_file.exists():
            print_warning("Server log file not found.")
            return
            
        try:
            # Read the log file and look for player join/leave messages
            with open(log_file, "r") as f:
                lines = f.readlines()
            
            # Track connected players
            connected_players = set()
            
            # Process log lines from newest to oldest
            for line in reversed(lines):
                if "[Server thread/INFO]" in line:
                    # Check for player join messages
                    if "logged in with entity id" in line:
                        # Extract player name
                        import re
                        match = re.search(r": (.+?) joined the game", line)
                        if match:
                            player_name = match.group(1)
                            connected_players.add(player_name)
                    # Check for player leave messages
                    elif "lost connection:" in line or "left the game" in line:
                        # Extract player name
                        import re
                        match = re.search(r": (.+?) (lost connection|left the game)", line)
                        if match:
                            player_name = match.group(1)
                            connected_players.discard(player_name)
            
            if connected_players:
                print_success(f"Online players ({len(connected_players)}):")
                for player in sorted(connected_players):
                    print(f"  - {player}")
            else:
                print_info("No players online.")
                
        except Exception as e:
            print_error(f"Failed to read player information: {e}")

    def _continuous_monitoring(self, server_name, session_name):
        """Continuous monitoring of server performance."""
        print_info("Starting continuous monitoring...")
        print_info("Press Ctrl+C to stop")
        print()
        
        try:
            import time
            import psutil
            
            print(f"{'Time':<10} {'Status':<15} {'Memory (MB)':<15}")
            print("-" * 45)
            
            start_time = time.time()
            while time.time() - start_time < 60:  # Run for 60 seconds
                # Check if server is running
                running = is_screen_session_running(session_name)
                status = "RUNNING" if running else "STOPPED"
                
                # Get memory usage
                memory_mb = 0
                if running:
                    try:
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            try:
                                if proc.info['name'] == 'screen' and session_name in ' '.join(proc.info['cmdline']):
                                    memory_info = proc.memory_info()
                                    memory_mb = memory_info.rss / (1024 * 1024)
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                    except Exception:
                        pass
                
                # Get current time
                current_time = time.strftime("%H:%M:%S")
                
                print(f"{current_time:<10} {status:<15} {memory_mb:<15.1f}")
                
                time.sleep(5)  # Update every 5 seconds
                
        except KeyboardInterrupt:
            print_info("\nMonitoring stopped by user.")
        except Exception as e:
            print_error(f"Monitoring error: {e}")

    def _stream_console_output(self, server_name):
        """Stream console output from server log."""
        print_info("Streaming console output...")
        print_info("Press Ctrl+C to stop")
        print()
        
        server_path = get_servers_root() / server_name
        log_file = server_path / "logs" / "latest.log"
        
        if not log_file.exists():
            print_warning("Server log file not found.")
            return
            
        try:
            # Tail the log file
            import subprocess
            subprocess.run(["tail", "-f", str(log_file)])
        except KeyboardInterrupt:
            print_info("\nStopped streaming.")
        except Exception as e:
            print_error(f"Failed to stream console output: {e}")

    def show_connection_info(self):
        """Show LAN and multiplayer IP addresses for server connection."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Connection Information{UI.colors.RESET}\n")
        
        current_server = self.get_current_server()
        if not current_server:
            print_error("No server selected.")
            input("\nPress Enter to continue...")
            return
            
        # Get server configuration to determine port
        config = ConfigManager.load_server_config(current_server)
        server_port = config.get("port", 25565)  # Default Minecraft port
        
        # Try to get server properties for the actual port
        server_path = get_servers_root() / current_server
        properties_file = server_path / "server.properties"
        
        if properties_file.exists():
            try:
                with open(properties_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key == "server-port":
                                server_port = int(value)
                                break
            except Exception as e:
                print_warning(f"Could not read server port from properties: {e}")
        
        # Get LAN and public IP addresses using NetworkHelper
        lan_ip = self.network_helper.get_lan_ip()
        public_ip = self.network_helper.get_public_ip()
        nat_type = self.network_helper.detect_nat_type(lan_ip, public_ip)
        
        print_info(f"Server: {current_server}")
        print_info(f"Port: {server_port}")
        print()
        
        # Show LAN connection info
        if lan_ip:
            print(f"{UI.colors.BOLD}LAN Connection:{UI.colors.RESET}")
            print(f"  IP: {lan_ip}")
            print(f"  Port: {server_port}")
            print(f"  Connection String: {lan_ip}:{server_port}")
            print()
        
        # Show public connection info
        if public_ip and public_ip != lan_ip:
            print(f"{UI.colors.BOLD}Public Connection:{UI.colors.RESET}")
            print(f"  IP: {public_ip}")
            print(f"  Port: {server_port}")
            print(f"  Connection String: {public_ip}:{server_port}")
            
            # NAT/CGNAT detection
            if nat_type == "CGNAT":
                print()
                print_warning("⚠️  CGNAT DETECTED")
                print_warning("Your ISP uses Carrier-Grade NAT. Port forwarding will NOT work.")
                print_warning("You MUST use a tunneling service (playit.gg, ngrok, etc.).")
                print_info("Use option 8 (Tunneling Manager) to set up external access.")
            elif nat_type == "NAT":
                print()
                print_info("Behind NAT: Port forwarding required for external access.")
                # Test port reachability
                print(f"Testing if port {server_port} is reachable...")
                if self.network_helper.test_port_open(public_ip, server_port):
                    print_success("✅ Port is OPEN and reachable!")
                else:
                    print_warning("❌ Port is CLOSED or filtered.")
                    print_info("External players cannot connect.")
                    print_info("Options:")
                    print_info("  1. Set up port forwarding on your router")
                    print_info("  2. Use a tunneling service (option 8)")
            elif nat_type == "DIRECT":
                print()
                print_success("Direct connection: No NAT detected!")
                # Test port reachability
                print(f"Testing if port {server_port} is reachable...")
                if self.network_helper.test_port_open(public_ip, server_port):
                    print_success("✅ Port is OPEN and reachable!")
                else:
                    print_warning("❌ Port is CLOSED or filtered.")
                    print_info("External players cannot connect.")
                    print_info("Options:")
                    print_info("  1. Check your firewall settings")
                    print_info("  2. Use a tunneling service (option 8)")
        elif public_ip:
            print(f"{UI.colors.BOLD}Connection:{UI.colors.RESET}")
            print(f"  IP: {public_ip}")
            print(f"  Port: {server_port}")
            print(f"  Connection String: {public_ip}:{server_port}")
            print()
            print_info("This appears to be a local/public IP. For external connections,")
            print_info("ensure your router is configured to forward port {server_port}.")
        else:
            print_warning("Could not determine public IP address.")
            
        # Check for active tunnels using NetworkHelper
        tunnel_info = self.network_helper.get_active_tunnel_info()
        if tunnel_info:
            print(f"\n{UI.colors.BOLD}Tunneling Information:{UI.colors.RESET}")
            if tunnel_info['url']:
                print(f"  Active Tunnel: {tunnel_info['url']}")
            else:
                print(f"  Active Tunnel: {tunnel_info['service']} (PID: {tunnel_info['pid']})")
                print_info("Check tunnel logs for connection URL")
        else:
            print(f"\n{UI.colors.BOLD}Tunneling Information:{UI.colors.RESET}")
            print_info("No active tunnels detected.")
            print_info("Use the Tunneling Manager (option 8) to set up tunnels for")
            print_info("external multiplayer access.")
            print_info("For pinggy.io, the connection address will appear in the")
            print_info("terminal output when you start the tunnel.")

    def show_dashboard_connection_info(self, current_server):
        """Show connection information on the dashboard."""
        # Get server configuration to determine port
        config = ConfigManager.load_server_config(current_server)
        server_port = config.get("port", 25565)  # Default Minecraft port
        
        # Try to get server properties for the actual port
        server_path = get_servers_root() / current_server
        properties_file = server_path / "server.properties"
        
        if properties_file.exists():
            try:
                with open(properties_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key == "server-port":
                                server_port = int(value)
                                break
            except Exception as e:
                print_warning(f"Could not read server port from properties: {e}")
        
        # Get LAN and public IP addresses using NetworkHelper
        lan_ip = self.network_helper.get_lan_ip()
        public_ip = self.network_helper.get_public_ip()
        nat_type = self.network_helper.detect_nat_type(lan_ip, public_ip)
        
        print()
        print(f"{UI.colors.BOLD}Connection Information:{UI.colors.RESET}")
        
        # Show LAN connection info
        if lan_ip:
            print(f"  {UI.colors.CYAN}LAN:{UI.colors.RESET} {lan_ip}:{server_port}")
        
        # Check for active tunnels first
        tunnel_info = self.network_helper.get_active_tunnel_info()
        if tunnel_info:
            if tunnel_info['url']:
                print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} {tunnel_info['url']}")
            else:
                print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} {tunnel_info['service']} tunnel (PID: {tunnel_info['pid']})")
        else:
            # If no tunnel, show public IP with NAT warning
            if public_ip and public_ip != lan_ip:
                if nat_type == "CGNAT":
                    print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} CGNAT detected - use tunnel!")
                elif nat_type == "NAT":
                    print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} {public_ip}:{server_port} (NAT)")
                else:
                    print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} {public_ip}:{server_port}")
            else:
                print(f"  {UI.colors.CYAN}Multiplayer:{UI.colors.RESET} No active tunnel")
                print(f"    Use Tunneling Manager (option 8) to set up")

    def _get_tunnel_info(self, server_name, server_port):
        """Get tunnel information for multiplayer connections."""
        try:
            # Check for ngrok tunnels
            import subprocess
            import json
            result = subprocess.run(["curl", "-s", "http://localhost:4040/api/tunnels"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if "tunnels" in data and data["tunnels"]:
                        for tunnel in data["tunnels"]:
                            if tunnel.get("proto") == "tcp":
                                # Extract the public URL
                                public_url = tunnel.get("public_url", "")
                                if public_url.startswith("tcp://"):
                                    # Convert tcp:// to a more user-friendly format
                                    host_port = public_url[6:]  # Remove "tcp://"
                                    return host_port
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        
        # Check for pinggy.io tunnels
        try:
            import subprocess
            import re
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Look for pinggy-related SSH connections
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'ssh' in line and 'pinggy' in line and str(server_port) in line:
                        # For pinggy, we can't extract the actual URL from the process
                        # The user needs to look at the terminal output when starting the tunnel
                        return "See tunnel terminal output"
        except Exception:
            pass
        
        # Check for other tunnel services
        try:
            import subprocess
            # Check for cloudflared tunnels
            result = subprocess.run(["pgrep", "cloudflared"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return "See Cloudflare dashboard"
                
            # Check for playit.gg tunnels
            result = subprocess.run(["pgrep", "playit"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return "See playit.gg dashboard"
                
            # Check for general pinggy processes
            result = subprocess.run(["pgrep", "-f", "ssh.*pinggy"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return "See tunnel terminal output"
        except Exception:
            pass
            
        return None

    def _show_tunnel_info(self, server_name, server_port):
        """Show information about active tunnels."""
        print(f"\n{UI.colors.BOLD}Tunneling Information:{UI.colors.RESET}")
        
        # Check for ngrok tunnels
        try:
            # Try to get ngrok tunnel info
            import subprocess
            import json
            result = subprocess.run(["curl", "-s", "http://localhost:4040/api/tunnels"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if "tunnels" in data and data["tunnels"]:
                        print_info("Ngrok Tunnel Active:")
                        for tunnel in data["tunnels"]:
                            if tunnel.get("proto") == "tcp":
                                # Extract the public URL
                                public_url = tunnel.get("public_url", "")
                                if public_url.startswith("tcp://"):
                                    # Convert tcp:// to a more user-friendly format
                                    host_port = public_url[6:]  # Remove "tcp://"
                                    print(f"  Public Address: {host_port}")
                                    print(f"  Protocol: TCP")
                        return
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        
        # Check for cloudflared tunnels
        try:
            # This is a simplified check - in practice, you might need to check
            # the cloudflared process or config files
            import subprocess
            result = subprocess.run(["pgrep", "cloudflared"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                print_info("Cloudflared Tunnel Active:")
                print("  Check Cloudflare dashboard for connection details")
                return
        except Exception:
            pass
            
        # Check for playit.gg tunnels
        try:
            # Check if playit process is running
            import subprocess
            result = subprocess.run(["pgrep", "playit"], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                print_info("Playit.gg Tunnel Active:")
                print("  Check playit.gg dashboard for connection details")
                return
        except Exception:
            pass
            
        # Check for pinggy.io tunnels
        try:
            # Check if there's an SSH connection to pinggy
            import subprocess
            import re
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Look for pinggy-related SSH connections
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'ssh' in line and 'pinggy' in line and str(server_port) in line:
                        # Try to extract the token from the command
                        match = re.search(r'([a-zA-Z0-9]+)\+tcp@free\.pinggy\.io', line)
                        if match:
                            token_prefix = match.group(1)[:8]  # First 8 characters of token
                            print_info(f"Pinggy.io Tunnel Active (token: {token_prefix}...):")
                        else:
                            print_info("Pinggy.io Tunnel Active:")
                        print("  When you start the tunnel, look for output like:")
                        print("  tcp://randomstring.a.pinggy.link:portnumber")
                        print("  Use this address to connect to your Minecraft server")
                        return
                        
                # Check for general pinggy processes
                result = subprocess.run(["pgrep", "-f", "ssh.*pinggy"], 
                                      capture_output=True, text=True, timeout=3)
                if result.returncode == 0:
                    print_info("Pinggy.io Tunnel Active:")
                    print("  Run the pinggy command to see connection details")
                    return
        except Exception:
            pass
            
        # If no active tunnels found
        print_info("No active tunnels detected.")
        print_info("Use the Tunneling Manager (option 8) to set up tunnels for")
        print_info("external multiplayer access.")
        print_info("For pinggy.io, the connection address will appear in the")
        print_info("terminal output when you start the tunnel.")

    def _get_lan_ip(self):
        """Get the local LAN IP address."""
        return self.network_helper.get_lan_ip()

    def _get_public_ip(self):
        """Get the public IP address."""
        return self.network_helper.get_public_ip()

class NetworkHelper:
    """Network utilities with proper error handling and caching."""
    
    def __init__(self):
        self._public_ip_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes
    
    def get_lan_ip(self):
        """Get LAN IP address with fallback."""
        import socket
        try:
            # Method 1: Connect to external IP (doesn't actually send data)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(2)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            pass
        
        try:
            # Method 2: Get hostname's IP
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            pass
        
        return "127.0.0.1"  # Ultimate fallback
    
    def get_public_ip(self):
        """Get public IP with caching, timeout, and fallbacks."""
        import time
        
        # Return cached IP if valid
        if self._public_ip_cache and (time.time() - self._cache_timestamp < self._cache_ttl):
            return self._public_ip_cache
        
        # Fetch new IP
        services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://icanhazip.com',
            'https://api.my-ip.io/ip',
            'https://checkip.amazonaws.com'
        ]
        
        for service in services:
            try:
                import urllib.request
                req = urllib.request.Request(
                    service,
                    headers={'User-Agent': 'MSM/1.1.0'}
                )
                with urllib.request.urlopen(req, timeout=3) as response:
                    ip = response.read().decode('utf-8').strip()
                    if self._is_valid_ip(ip):
                        self._public_ip_cache = ip
                        self._cache_timestamp = time.time()
                        return ip
            except Exception:
                continue
        
        return None
    
    def _is_valid_ip(self, ip):
        """Validate IPv4 address."""
        import re
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        try:
            return all(0 <= int(octet) <= 255 for octet in ip.split('.'))
        except ValueError:
            return False
    
    def detect_nat_type(self, lan_ip, public_ip):
        """Detect network topology."""
        if not lan_ip or not public_ip:
            return "UNKNOWN"
        
        # Check if public IP is actually private (CGNAT)
        if public_ip.startswith(('10.', '172.16.', '192.168.', '100.64.')):
            return "CGNAT"
        
        # Check if behind NAT
        if lan_ip != public_ip:
            return "NAT"
        
        return "DIRECT"
    
    def test_port_open(self, ip, port, timeout=3):
        """Test if port is reachable."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def get_active_tunnel_info(self):
        """Get information about active tunnels from tunnel manager."""
        try:
            # Try to read tunnel info from tunnel manager files
            from config import get_config_root
            config_root = get_config_root()
            tunnel_pidfile = config_root / "tunnel.pid"
            tunnel_urlfile = config_root / "tunnel_url.txt"
            
            if tunnel_pidfile.exists():
                lines = tunnel_pidfile.read_text().strip().split('\n')
                if len(lines) >= 2:
                    pid = lines[0]
                    service = lines[1]
                    
                    url = None
                    if tunnel_urlfile.exists():
                        url_content = tunnel_urlfile.read_text().strip()
                        if url_content:
                            url = url_content
                    
                    return {
                        "service": service,
                        "pid": pid,
                        "url": url
                    }
        except Exception:
            pass
        
        return None
