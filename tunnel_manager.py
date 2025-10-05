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
        print(" 4. pinggy.io")
        print()
        
        choice = input("Select service (1-4, or 0): ").strip()
        
        if choice == "1":
            self.setup_playit()
        elif choice == "2":
            self.setup_ngrok()
        elif choice == "3":
            self.setup_cloudflared()
        elif choice == "4":
            self.setup_pinggy()
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
        print(f"{UI.colors.BOLD}Installation:{UI.colors.RESET}")
        print("Playit.gg can be installed using the following commands:")
        print(f"   {UI.colors.CYAN}curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/playit.gpg >/dev/null{UI.colors.RESET}")
        print(f"   {UI.colors.CYAN}echo \"deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./\" | sudo tee /etc/apt/sources.list.d/playit-cloud.list{UI.colors.RESET}")
        print(f"   {UI.colors.CYAN}sudo apt update && sudo apt install playit{UI.colors.RESET}")
        print()
        
        # Try to install playit automatically
        try:
            print_info("Attempting automatic installation...")
            # Create directories if they don't exist
            subprocess.run(["mkdir", "-p", "/etc/apt/trusted.gpg.d"], check=True)
            subprocess.run(["mkdir", "-p", "/etc/apt/sources.list.d"], check=True)
            
            # Download and add the GPG key using shell commands
            subprocess.run("curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | tee /etc/apt/trusted.gpg.d/playit.gpg >/dev/null", 
                          shell=True, check=True)
            
            # Add repository
            with open("/etc/apt/sources.list.d/playit-cloud.list", "w") as f:
                f.write("deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./\n")
            
            # Update and install
            subprocess.run(["apt", "update"], check=True)
            subprocess.run(["apt", "install", "-y", "playit"], check=True)
            print_success("Playit.gg installed successfully")
                
        except Exception as e:
            print_error(f"Automatic installation failed: {e}")
            print_info("Please install manually using the commands above")
        
        print()
        print(f"{UI.colors.BOLD}1. Run agent:{UI.colors.RESET} {UI.colors.CYAN}playit{UI.colors.RESET}")
        print()
        print(f"{UI.colors.BOLD}2. Visit claim URL{UI.colors.RESET} (shown in terminal)")
        print(f"{UI.colors.BOLD}3. Approve agent{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}4. Copy secret{UI.colors.RESET} from ~/.config/playit/playit.toml")
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
                # Try to install ngrok via snap first (more common method)
                try:
                    subprocess.run(["snap", "install", "ngrok"], check=True)
                    print_success("Ngrok installed successfully via snap")
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to apt installation
                    try:
                        subprocess.run(["apt", "update"], check=True)
                        subprocess.run(["apt", "install", "-y", "ngrok"], check=True)
                        print_success("Ngrok installed successfully via apt")
                    except subprocess.CalledProcessError:
                        # Final fallback - manual installation instructions
                        raise Exception("Failed to install ngrok automatically")
            except Exception:
                print_error("Failed to install ngrok automatically")
                print_info("Please install manually:")
                print(f"   {UI.colors.CYAN}Snap: snap install ngrok{UI.colors.RESET}")
                print(f"   {UI.colors.CYAN}APT: apt update && apt install -y ngrok{UI.colors.RESET}")
                print(f"   {UI.colors.CYAN}Or visit: https://ngrok.com/download{UI.colors.RESET}")
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
                subprocess.run(["ngrok", "tcp", str(server_port)])
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
    
    def setup_pinggy(self):
        """Setup pinggy.io tunnel."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Pinggy.io Setup{UI.colors.RESET}\n")
        
        # Check if SSH is installed
        try:
            result = subprocess.run(["ssh", "-V"], capture_output=True, text=True)
            if result.returncode != 0:
                raise FileNotFoundError
            print_success("SSH client found (required for pinggy)")
        except FileNotFoundError:
            print_error("SSH client not found. Pinggy.io requires SSH.")
            print_info("Please install SSH client:")
            print(f"   {UI.colors.CYAN}apt update && apt install -y openssh-client{UI.colors.RESET}")
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
        
        # Show pinggy setup instructions
        print()
        print_info("=== Pinggy.io Setup ===")
        print()
        print(f"{UI.colors.BOLD}1. Visit:{UI.colors.RESET} https://pinggy.io/")
        print(f"{UI.colors.BOLD}2. Sign up or log in{UI.colors.RESET}")
        print(f"{UI.colors.BOLD}3. Get your tunnel token{UI.colors.RESET} from the dashboard")
        print()
        print(f"{UI.colors.BOLD}SSH Key Setup:{UI.colors.RESET}")
        print("Pinggy.io requires SSH key authentication. Set up your keys:")
        print(f"   {UI.colors.CYAN}ssh-keygen -t rsa{UI.colors.RESET} (if you don't have SSH keys)")
        print(f"   {UI.colors.CYAN}ssh-copy-id token+tcp@free.pinggy.io{UI.colors.RESET} (replace 'token' with your actual token)")
        print()
        
        # Get user input for token
        token = CredentialsManager.get("pinggy_token")
        if token:
            print_success(f"Existing token: {token[:8]}...")
            confirm = input("Use existing? (Y/n): ").strip().lower()
            if confirm == 'n':
                token = input(f"{UI.colors.CYAN}Enter pinggy.io token (or skip): {UI.colors.RESET}").strip()
                if token:
                    CredentialsManager.set("pinggy_token", token)
                    print_success("Token saved")
                    log("Pinggy token configured")
        else:
            token = input(f"{UI.colors.CYAN}Enter pinggy.io token (or skip): {UI.colors.RESET}").strip()
            if token:
                CredentialsManager.set("pinggy_token", token)
                print_success("Token saved")
                log("Pinggy token configured")
        
        # Show how to start tunnel
        print()
        if token:
            print_info("To start your pinggy.io tunnel with token, run:")
            print(f"   {UI.colors.CYAN}ssh -p 443 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R0:localhost:{server_port} {token}+tcp@free.pinggy.io{UI.colors.RESET}")
            print()
            print_info("First set up SSH key authentication:")
            print(f"   {UI.colors.CYAN}ssh-copy-id {token}+tcp@free.pinggy.io{UI.colors.RESET}")
            tunnel_target = f"{token}+tcp@free.pinggy.io"
        else:
            print_info("To start your pinggy.io tunnel without token, run:")
            print(f"   {UI.colors.CYAN}ssh -p 443 -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -R0:localhost:{server_port} tcp@free.pinggy.io{UI.colors.RESET}")
            print()
            print_info("Note: Without a token, you'll get a temporary URL that changes each time")
            tunnel_target = "tcp@free.pinggy.io"
        
        print_info("Or start it automatically now:")
        
        # Offer to start tunnel automatically
        confirm = input(f"{UI.colors.YELLOW}Start pinggy.io tunnel now? (y/N): {UI.colors.RESET}").strip().lower()
        if confirm == 'y':
            print_info("Starting pinggy.io tunnel...")
            print_info("Press Ctrl+C to stop")
            try:
                # Start the pinggy tunnel with proper options
                subprocess.run([
                    "ssh", "-p", "443",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ServerAliveInterval=30",
                    "-o", "PasswordAuthentication=no",
                    f"-R0:localhost:{server_port}", 
                    tunnel_target
                ])
            except KeyboardInterrupt:
                print_info("\nTunnel stopped")
            except Exception as e:
                print_error(f"Failed to start tunnel: {e}")
                print_info("Make sure you have SSH access and internet connectivity")
                print_info("You may need to set up SSH key authentication first")
        
        input("\nPress Enter to continue...")
    
    def start_pinggy_tunnel(self, server_port):
        """Start a pinggy.io tunnel programmatically."""
        # Get token from credentials
        token = CredentialsManager.get("pinggy_token")
        
        try:
            print_info(f"Starting pinggy.io tunnel on port {server_port}...")
            # Start the pinggy tunnel with proper options
            import subprocess
            import time
            
            if token:
                tunnel_target = f"{token}+tcp@free.pinggy.io"
                print_info(f"Using token-based authentication: {token[:8]}...")
            else:
                tunnel_target = "tcp@free.pinggy.io"
                print_info("Using anonymous connection (temporary URL)")
            
            # Start the pinggy tunnel with proper options
            process = subprocess.Popen([
                "ssh", "-p", "443",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-o", "PasswordAuthentication=no",
                f"-R0:localhost:{server_port}", 
                tunnel_target
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Wait a moment for the tunnel to start
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("Pinggy.io tunnel started successfully!")
                print_info("Tunnel process running in background")
                print_info("Check terminal output for connection details")
                return True
            else:
                # Process ended, check for errors
                stdout, stderr = process.communicate()
                print_error(f"Failed to start pinggy.io tunnel: {stderr}")
                return False
                
        except Exception as e:
            print_error(f"Failed to start pinggy.io tunnel: {e}")
            return False
