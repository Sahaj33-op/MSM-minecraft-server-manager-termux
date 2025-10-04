# ============================================================================
# tunnel_manager.py - Manages Playit.gg, Ngrok, or other tunnels
# ============================================================================
"""
Tunneling service management (playit.gg, ngrok, cloudflared).
"""

import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

from config import CredentialsManager, get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log, run_command


class TunnelManager:
    """Manages tunneling services."""
    
    def tunneling_menu(self):
        """Tunneling manager menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Tunneling Manager{UI.colors.RESET}\n")
        
        print("Available services:")
        print(" 1. playit.gg (recommended)")
        print(" 2. ngrok")
        print(" 3. cloudflared (Cloudflare Tunnel)")
        print()
        
        choice = input("Select service (1-3, or 0): ").strip()
        
        if choice == "1":
            self.setup_playit()
        elif choice == "2":
            self.setup_ngrok()
        elif choice == "3":
            self.setup_cloudflared()
        elif choice != "0":
            print_error("Invalid option")
            input("\nPress Enter to continue...")
    
    def setup_playit(self):
        """Setup playit.gg token."""
        print_info("Playit.gg Token Setup")
        print()
        
        token = CredentialsManager.get("playit_token")
        if token:
            print_success(f"Existing token: {token[:16]}...")
            confirm = input("Use existing? (Y/n): ").strip().lower()
            if confirm != 'n':
                return
        
        print()
        print_info("=== Playit.gg Setup ===")
        print()
        print(f"{UI.colors.BOLD}1. Install playit agent:{UI.colors.RESET}")
        print(f"   {UI.colors.CYAN}curl -fsSL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/playit.gpg{UI.colors.RESET}")
        print(f"   {UI.colors.CYAN}echo 'deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./' > /etc/apt/sources.list.d/playit-cloud.list{UI.colors.RESET}")
        print(f"   {UI.colors.CYAN}apt update && apt install -y playit{UI.colors.RESET}")
        print()
        print(f"   {UI.colors.YELLOW}Requires gnupg: apt install gnupg{UI.colors.RESET}")
        print()
        print(f"{UI.colors.BOLD}2. Run agent:{UI.colors.RESET} {UI.colors.CYAN}playit{UI.colors.RESET}")
        print()
        print(f"{UI.colors.BOLD}3. Visit claim URL{UI.colors.RESET} (shown in terminal)")
        print(f"{UI.colors.BOLD}4. Approve agent{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}5. Copy secret{UI.colors.RESET} from ~/.config/playit/playit.toml")
        print()
        
        token_input = input(f"{UI.colors.CYAN}Enter secret key (or skip): {UI.colors.RESET}").strip()
        
        if token_input:
            CredentialsManager.set("playit_token", token_input)
            print_success("Token saved")
            log("Playit token configured")
        else:
            print_warning("Token setup skipped")
            
        input("\nPress Enter to continue...")
    
    def setup_ngrok(self):
        """Setup ngrok tunnel."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Ngrok Setup{UI.colors.RESET}\n")
        
        # Check if ngrok is installed
        try:
            result = subprocess.run(["ngrok", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise FileNotFoundError
            print_success(f"Ngrok found: {result.stdout.strip()}")
        except FileNotFoundError:
            print_warning("Ngrok not found. Installing...")
            try:
                # Try to install ngrok
                subprocess.run(["apt", "update"], check=True)
                subprocess.run(["apt", "install", "-y", "ngrok"], check=True)
                print_success("Ngrok installed successfully")
            except subprocess.CalledProcessError:
                print_error("Failed to install ngrok automatically")
                print_info("Please install manually:")
                print(f"   {UI.colors.CYAN}apt update && apt install -y ngrok{UI.colors.RESET}")
                input("\nPress Enter to continue...")
                return
        
        # Get auth token
        auth_token = CredentialsManager.get("ngrok_auth_token")
        if auth_token:
            print_success("Ngrok auth token found")
        else:
            print_info("Ngrok auth token required")
            print()
            print("1. Visit https://dashboard.ngrok.com/signup")
            print("2. Sign up or log in")
            print("3. Copy your auth token from https://dashboard.ngrok.com/get-started/your-authtoken")
            print()
            
            token_input = input(f"{UI.colors.CYAN}Enter auth token (or skip): {UI.colors.RESET}").strip()
            if token_input:
                CredentialsManager.set("ngrok_auth_token", token_input)
                # Set the auth token
                try:
                    subprocess.run(["ngrok", "config", "add-authtoken", token_input], check=True)
                    print_success("Auth token configured")
                    log("Ngrok auth token configured")
                except subprocess.CalledProcessError as e:
                    print_error(f"Failed to configure auth token: {e}")
            else:
                print_warning("Auth token setup skipped")
        
        # Get server port
        from server_manager import ServerManager
        current_server = ServerManager.get_current_server()
        if current_server:
            from config import ConfigManager
            server_config = ConfigManager.load_server_config(current_server)
            server_port = server_config.get("port", 25565)
        else:
            server_port = 25565
            
        print_info(f"Using server port: {server_port}")
        
        # Start tunnel
        confirm = input(f"\n{UI.colors.YELLOW}Start ngrok tunnel on port {server_port}? (y/N): {UI.colors.RESET}").strip().lower()
        if confirm == 'y':
            print_info("Starting ngrok tunnel...")
            print_info("Press Ctrl+C to stop")
            try:
                subprocess.run(["ngrok", "http", str(server_port)])
            except KeyboardInterrupt:
                print_info("\nTunnel stopped")
            except Exception as e:
                print_error(f"Failed to start tunnel: {e}")
        
        input("\nPress Enter to continue...")
    
    def setup_cloudflared(self):
        """Setup Cloudflare Tunnel (cloudflared)."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Cloudflare Tunnel Setup{UI.colors.RESET}\n")
        
        # Check if cloudflared is installed
        try:
            result = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                raise FileNotFoundError
            print_success(f"Cloudflared found: {result.stdout.strip()}")
        except FileNotFoundError:
            print_warning("Cloudflared not found. Installing...")
            try:
                # Install cloudflared
                subprocess.run(["apt", "update"], check=True)
                subprocess.run(["apt", "install", "-y", "curl"], check=True)
                
                # Download and install cloudflared
                print_info("Downloading cloudflared...")
                urllib.request.urlretrieve(
                    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb",
                    "/tmp/cloudflared.deb"
                )
                
                subprocess.run(["dpkg", "-i", "/tmp/cloudflared.deb"], check=True)
                subprocess.run(["rm", "/tmp/cloudflared.deb"], check=True)
                print_success("Cloudflared installed successfully")
            except Exception as e:
                print_error(f"Failed to install cloudflared: {e}")
                print_info("Please install manually:")
                print(f"   {UI.colors.CYAN}Visit https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/{UI.colors.RESET}")
                input("\nPress Enter to continue...")
                return
        
        # Login to Cloudflare
        print_info("Cloudflare login required")
        print()
        print("1. Visit https://dash.cloudflare.com/sign-up")
        print("2. Sign up or log in")
        print("3. Navigate to Zero Trust > Access > Tunnels")
        print()
        
        confirm = input(f"{UI.colors.YELLOW}Run cloudflared login? (y/N): {UI.colors.RESET}").strip().lower()
        if confirm == 'y':
            try:
                print_info("Please complete the login in your browser...")
                subprocess.run(["cloudflared", "tunnel", "login"], check=True)
                print_success("Login successful")
            except subprocess.CalledProcessError:
                print_error("Login failed")
                input("\nPress Enter to continue...")
                return
        
        # Get server port
        from server_manager import ServerManager
        current_server = ServerManager.get_current_server()
        if current_server:
            from config import ConfigManager
            server_config = ConfigManager.load_server_config(current_server)
            server_port = server_config.get("port", 25565)
        else:
            server_port = 25565
            
        print_info(f"Using server port: {server_port}")
        
        # Create tunnel
        tunnel_name = input(f"\n{UI.colors.CYAN}Enter tunnel name (default: msm-tunnel): {UI.colors.RESET}").strip()
        if not tunnel_name:
            tunnel_name = "msm-tunnel"
            
        try:
            print_info(f"Creating tunnel: {tunnel_name}")
            subprocess.run(["cloudflared", "tunnel", "create", tunnel_name], check=True)
            
            # Create config file
            config_root = get_config_root()
            tunnel_config = config_root / "tunnels" / f"{tunnel_name}.yml"
            tunnel_config.parent.mkdir(parents=True, exist_ok=True)
            
            with open(tunnel_config, "w") as f:
                f.write(f"""
tunnel: {tunnel_name}
credentials-file: {config_root}/certs/{tunnel_name}.json

ingress:
  - hostname: your-domain.com
    service: http://localhost:{server_port}
  - service: http_status:404
""")
            
            print_success(f"Tunnel config created: {tunnel_config}")
            print_info("Edit the config file to set your domain")
            
            # Start tunnel
            confirm = input(f"\n{UI.colors.YELLOW}Start tunnel now? (y/N): {UI.colors.RESET}").strip().lower()
            if confirm == 'y':
                print_info("Starting tunnel...")
                print_info("Press Ctrl+C to stop")
                try:
                    subprocess.run(["cloudflared", "tunnel", "--config", str(tunnel_config), "run", tunnel_name])
                except KeyboardInterrupt:
                    print_info("\nTunnel stopped")
                except Exception as e:
                    print_error(f"Failed to start tunnel: {e}")
                    
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to create tunnel: {e}")
        
        input("\nPress Enter to continue...")