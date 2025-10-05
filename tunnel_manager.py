#!/usr/bin/env python3
"""
tunnel_manager.py - WORKING tunneling implementation
Based on actual working methods from web research (Oct 2025)
"""

import subprocess
import time
import os
from pathlib import Path
from config import CredentialsManager, get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log, run_command


class TunnelManager:
    """Manages tunneling services with ACTUALLY WORKING implementations."""
    
    def __init__(self):
        self.config_root = get_config_root()
        self.bin_dir = self.config_root / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
    
    def tunneling_menu(self):
        """Tunneling manager menu."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Tunneling Manager{UI.colors.RESET}")
        print("\nAvailable services:")
        print("1. playit.gg (recommended - easiest)")
        print("2. ngrok (most popular)")
        print("3. cloudflared (quick tunnel - no login)")
        print("4. pinggy.io (SSH-based - instant)")
        print("0. Back")
        
        choice = input("\nSelect service (1-4, or 0): ").strip()
        
        if choice == "1":
            self.setup_playit()
        elif choice == "2":
            self.setup_ngrok()
        elif choice == "3":
            self.setup_cloudflared_quick()
        elif choice == "4":
            self.setup_pinggy()
        elif choice != "0":
            print_error("Invalid option")
            input("\nPress Enter to continue...")
    
    # ===================================================================
    # PLAYIT.GG - ACTUALLY WORKING IMPLEMENTATION
    # ===================================================================
    
    def setup_playit(self):
        """Setup playit.gg - THE CORRECT WAY."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Playit.gg Setup{UI.colors.RESET}\n")
        
        # Check if already installed
        try:
            result = subprocess.run(
                ["playit", "--version"], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success("Playit.gg is already installed")
                self._start_playit()
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Install playit
        print_info("Installing playit.gg...")
        print("\nThis will run:")
        print(f"  {UI.colors.CYAN}1. Add playit GPG key{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}2. Add playit repository{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}3. Install playit{UI.colors.RESET}\n")
        
        confirm = input(f"{UI.colors.YELLOW}Proceed with installation? (Y/n): {UI.colors.RESET}").strip().lower()
        if confirm == "n":
            return
        
        try:
            # Step 1: Add GPG key
            print_info("Adding GPG key...")
            subprocess.run(
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | tee /data/data/com.termux/files/usr/etc/apt/trusted.gpg.d/playit.gpg >/dev/null",
                shell=True,
                check=True,
                timeout=30
            )
            
            # Step 2: Add repository
            print_info("Adding repository...")
            repo_file = Path("/data/data/com.termux/files/usr/etc/apt/sources.list.d/playit-cloud.list")
            repo_file.parent.mkdir(parents=True, exist_ok=True)
            repo_file.write_text("deb [signed-by=/data/data/com.termux/files/usr/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./\n")
            
            # Step 3: Update and install
            print_info("Updating package lists...")
            subprocess.run(["apt", "update"], check=True, timeout=60)
            
            print_info("Installing playit...")
            subprocess.run(["apt", "install", "-y", "playit"], check=True, timeout=120)
            
            print_success("✅ Playit.gg installed successfully!\n")
            
            # Now start it
            self._start_playit()
            
        except subprocess.CalledProcessError as e:
            print_error(f"Installation failed: {e}")
            print_info("\nManual installation:")
            print("  curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | tee $PREFIX/etc/apt/trusted.gpg.d/playit.gpg")
            print("  echo 'deb [signed-by=$PREFIX/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./' | tee $PREFIX/etc/apt/sources.list.d/playit-cloud.list")
            print("  apt update && apt install playit")
            input("\nPress Enter to continue...")
        except subprocess.TimeoutExpired:
            print_error("Installation timed out - check your internet connection")
            input("\nPress Enter to continue...")
    
    def _start_playit(self):
        """Start playit agent."""
        print(f"\n{UI.colors.BOLD}Starting Playit Agent{UI.colors.RESET}\n")
        print_info("The playit agent will show a claim URL.")
        print_info("Visit that URL in your browser to add this agent to your account.\n")
        print(f"{UI.colors.YELLOW}Press Ctrl+C to stop the agent{UI.colors.RESET}\n")
        
        input("Press Enter to start...")
        
        try:
            subprocess.run(["playit"])
        except KeyboardInterrupt:
            print_info("\nPlayit agent stopped")
        except FileNotFoundError:
            print_error("Playit not found - installation may have failed")
        
        input("\nPress Enter to continue...")
    
    # ===================================================================
    # NGROK - ACTUALLY WORKING IMPLEMENTATION
    # ===================================================================
    
    def setup_ngrok(self):
        """Setup ngrok - THE CORRECT WAY."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Ngrok Setup{UI.colors.RESET}\n")
        
        ngrok_path = self.bin_dir / "ngrok"
        
        # Check if already installed
        if ngrok_path.exists():
            print_success("Ngrok is already installed")
        else:
            print_info("Installing ngrok...")
            
            # Detect architecture
            try:
                arch_result = subprocess.run(
                    ["uname", "-m"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                arch = arch_result.stdout.strip()
            except:
                arch = "aarch64"  # Default for most Android devices
            
            # Determine download URL (CORRECT URLs from ngrok.com)
            if "aarch64" in arch or "arm64" in arch:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm64.tgz"
            elif "armv7" in arch or "armv8" in arch:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz"
            else:
                download_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
            
            try:
                print_info(f"Downloading from {download_url}...")
                subprocess.run(
                    ["wget", "-O", "/tmp/ngrok.tgz", download_url],
                    check=True,
                    timeout=120
                )
                
                print_info("Extracting...")
                subprocess.run(
                    ["tar", "-xzf", "/tmp/ngrok.tgz", "-C", str(self.bin_dir)],
                    check=True,
                    timeout=30
                )
                
                subprocess.run(["chmod", "+x", str(ngrok_path)], check=True)
                subprocess.run(["rm", "/tmp/ngrok.tgz"], check=False)
                
                print_success("✅ Ngrok installed successfully!\n")
                
            except subprocess.CalledProcessError as e:
                print_error(f"Installation failed: {e}")
                input("\nPress Enter to continue...")
                return
            except subprocess.TimeoutExpired:
                print_error("Download timed out - check your internet connection")
                input("\nPress Enter to continue...")
                return
        
        # Configure authtoken
        print(f"\n{UI.colors.BOLD}Authtoken Setup{UI.colors.RESET}\n")
        print("1. Visit https://dashboard.ngrok.com/signup")
        print("2. Sign up or log in")
        print("3. Copy your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken\n")
        
        authtoken = input(f"{UI.colors.CYAN}Enter authtoken (or press Enter to skip): {UI.colors.RESET}").strip()
        
        if authtoken:
            try:
                subprocess.run(
                    [str(ngrok_path), "config", "add-authtoken", authtoken],
                    check=True,
                    timeout=10
                )
                print_success("✅ Authtoken configured!")
                log("Ngrok authtoken configured")
            except subprocess.CalledProcessError:
                print_error("Failed to configure authtoken")
        else:
            print_warning("Skipped authtoken setup - limited functionality")
        
        # Start tunnel
        from server_manager import ServerManager
        current_server = ServerManager.get_current_server()
        
        if current_server:
            from config import ConfigManager
            server_config = ConfigManager.load_server_config(current_server)
            server_port = server_config.get("port", 25565)
        else:
            server_port = 25565
        
        print(f"\n{UI.colors.BOLD}Starting Ngrok Tunnel{UI.colors.RESET}\n")
        print_info(f"Tunneling port {server_port}")
        print(f"{UI.colors.YELLOW}Press Ctrl+C to stop{UI.colors.RESET}\n")
        
        input("Press Enter to start...")
        
        try:
            subprocess.run([str(ngrok_path), "tcp", str(server_port)])
        except KeyboardInterrupt:
            print_info("\nNgrok stopped")
        
        input("\nPress Enter to continue...")
    
    # ===================================================================
    # CLOUDFLARED QUICK TUNNEL - ACTUALLY WORKING IMPLEMENTATION
    # ===================================================================
    
    def setup_cloudflared_quick(self):
        """Setup cloudflared QUICK tunnel - no login required."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Cloudflare Quick Tunnel{UI.colors.RESET}\n")
        
        print_info("Quick Tunnel creates a temporary public URL without login")
        print_warning("Note: URL changes each time you restart the tunnel\n")
        
        cloudflared_path = self.bin_dir / "cloudflared"
        
        # Check if already installed
        if not cloudflared_path.exists():
            print_info("Installing cloudflared...")
            
            # Detect architecture
            try:
                arch_result = subprocess.run(
                    ["uname", "-m"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                arch = arch_result.stdout.strip()
            except:
                arch = "aarch64"
            
            # Determine download URL
            if "aarch64" in arch or "arm64" in arch:
                download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
            elif "armv7" in arch:
                download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm"
            else:
                download_url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
            
            try:
                print_info(f"Downloading from GitHub...")
                subprocess.run(
                    ["wget", "-O", str(cloudflared_path), download_url],
                    check=True,
                    timeout=120
                )
                
                subprocess.run(["chmod", "+x", str(cloudflared_path)], check=True)
                print_success("✅ Cloudflared installed!\n")
                
            except subprocess.CalledProcessError as e:
                print_error(f"Installation failed: {e}")
                input("\nPress Enter to continue...")
                return
            except subprocess.TimeoutExpired:
                print_error("Download timed out - check your internet connection")
                input("\nPress Enter to continue...")
                return
        else:
            print_success("Cloudflared is already installed\n")
        
        # Get server port
        from server_manager import ServerManager
        current_server = ServerManager.get_current_server()
        
        if current_server:
            from config import ConfigManager
            server_config = ConfigManager.load_server_config(current_server)
            server_port = server_config.get("port", 25565)
        else:
            server_port = 25565
        
        print(f"{UI.colors.BOLD}Starting Quick Tunnel{UI.colors.RESET}\n")
        print_info(f"Tunneling port {server_port}")
        print_info("The tunnel URL will be shown below")
        print(f"{UI.colors.YELLOW}Press Ctrl+C to stop{UI.colors.RESET}\n")
        
        input("Press Enter to start...")
        
        try:
            subprocess.run([
                str(cloudflared_path),
                "tunnel",
                "--url",
                f"tcp://localhost:{server_port}"
            ])
        except KeyboardInterrupt:
            print_info("\nCloudflared stopped")
        
        input("\nPress Enter to continue...")
    
    # ===================================================================
    # PINGGY.IO - ACTUALLY WORKING IMPLEMENTATION
    # ===================================================================
    
    def setup_pinggy(self):
        """Setup pinggy.io - SSH-based tunnel (instant)."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Pinggy.io Setup{UI.colors.RESET}\n")
        
        print_info("Pinggy.io uses SSH for tunneling - no installation needed!\n")
        
        # Check if SSH is available
        try:
            subprocess.run(
                ["ssh", "-V"],
                capture_output=True,
                timeout=5
            )
        except FileNotFoundError:
            print_error("SSH not found - installing...")
            try:
                subprocess.run(["pkg", "install", "-y", "openssh"], check=True, timeout=60)
                print_success("SSH installed")
            except subprocess.CalledProcessError:
                print_error("Failed to install SSH")
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
        
        print(f"{UI.colors.BOLD}Starting Pinggy Tunnel{UI.colors.RESET}\n")
        print_info(f"Tunneling port {server_port}")
        print_info("The tunnel URL will be shown in the terminal")
        print(f"{UI.colors.YELLOW}Press Ctrl+C to stop{UI.colors.RESET}\n")
        
        input("Press Enter to start...")
        
        try:
            subprocess.run([
                "ssh",
                "-p", "443",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                f"-R0:localhost:{server_port}",
                "tcp@free.pinggy.io"
            ])
        except KeyboardInterrupt:
            print_info("\nPinggy tunnel stopped")
        
        input("\nPress Enter to continue...")
