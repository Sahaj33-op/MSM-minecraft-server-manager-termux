#!/usr/bin/env python3
"""
tunnel_manager.py - FIXED tunneling with background support
"""

import subprocess
import time
import os
import signal
import threading
from pathlib import Path
from config import CredentialsManager, get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log, run_command


class TunnelManager:
    """Manages tunneling services with background process support."""
    
    def __init__(self):
        self.config_root = get_config_root()
        self.bin_dir = self.config_root / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.tunnel_pidfile = self.config_root / "tunnel.pid"
        self.tunnel_logfile = self.config_root / "tunnel.log"
        self.tunnel_urlfile = self.config_root / "tunnel_url.txt"
    
    def tunneling_menu(self):
        """Tunneling manager menu with status display."""
        while True:
            clear_screen()
            print_header("1.1.0")
            print(f"{UI.colors.BOLD}Tunneling Manager{UI.colors.RESET}\n")
            
            # Show current tunnel status
            status = self.get_tunnel_status()
            if status:
                print(f"{UI.colors.GREEN}✓ Active Tunnel:{UI.colors.RESET}")
                print(f"  Service: {status['service']}")
                print(f"  PID: {status['pid']}")
                if status.get('url'):
                    print(f"  URL: {UI.colors.CYAN}{status['url']}{UI.colors.RESET}")
                print(f"\n{UI.colors.YELLOW}5. Stop active tunnel{UI.colors.RESET}\n")
            else:
                print(f"{UI.colors.GRAY}No active tunnel{UI.colors.RESET}\n")
            
            print("Available services:")
            print("1. playit.gg (recommended - easiest)")
            print("2. ngrok (most popular)")
            print("3. cloudflared (quick tunnel - no login)")
            print("4. pinggy.io (SSH-based - instant)")
            print("0. Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.setup_playit()
            elif choice == "2":
                self.setup_ngrok()
            elif choice == "3":
                self.setup_cloudflared_quick()
            elif choice == "4":
                self.setup_pinggy()
            elif choice == "5" and status:
                self.stop_tunnel()
            elif choice == "0":
                break
            else:
                if choice != "0":
                    print_error("Invalid option")
                    input("\nPress Enter to continue...")
    
    def get_tunnel_status(self):
        """Get status of currently running tunnel."""
        if not self.tunnel_pidfile.exists():
            return None
        
        try:
            pid = int(self.tunnel_pidfile.read_text().strip())
            
            # Check if process is still running
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            
            # Read service name
            lines = self.tunnel_pidfile.read_text().strip().split('\n')
            service = lines[1] if len(lines) > 1 else "unknown"
            
            # Try to read tunnel URL
            url = None
            if self.tunnel_urlfile.exists():
                url = self.tunnel_urlfile.read_text().strip()
            
            return {
                "pid": pid,
                "service": service,
                "url": url
            }
        except (ValueError, ProcessLookupError, PermissionError):
            # Process doesn't exist or pidfile is invalid
            self.tunnel_pidfile.unlink(missing_ok=True)
            self.tunnel_urlfile.unlink(missing_ok=True)
            return None
    
    def stop_tunnel(self):
        """Stop currently running tunnel."""
        status = self.get_tunnel_status()
        if not status:
            print_warning("No tunnel is running")
            input("\nPress Enter to continue...")
            return
        
        try:
            print_info(f"Stopping {status['service']} tunnel (PID: {status['pid']})...")
            os.kill(status['pid'], signal.SIGTERM)
            time.sleep(1)
            
            # Force kill if still running
            try:
                os.kill(status['pid'], 0)
                os.kill(status['pid'], signal.SIGKILL)
            except ProcessLookupError:
                pass
            
            self.tunnel_pidfile.unlink(missing_ok=True)
            self.tunnel_urlfile.unlink(missing_ok=True)
            print_success(f"✅ Tunnel stopped")
        except ProcessLookupError:
            print_warning("Tunnel process already stopped")
            self.tunnel_pidfile.unlink(missing_ok=True)
            self.tunnel_urlfile.unlink(missing_ok=True)
        except Exception as e:
            print_error(f"Failed to stop tunnel: {e}")
        
        input("\nPress Enter to continue...")
    
    def _start_background_process(self, command, service_name):
        """Start a tunnel process in the background."""
        # Stop any existing tunnel
        if self.get_tunnel_status():
            print_warning("Another tunnel is running. Stopping it first...")
            self.stop_tunnel()
            time.sleep(1)
        
        try:
            # Start process with redirected output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )
            
            # Save PID
            self.tunnel_pidfile.write_text(f"{process.pid}\n{service_name}")
            
            # Start URL monitoring thread
            threading.Thread(
                target=self._monitor_tunnel_output,
                args=(process, service_name),
                daemon=True
            ).start()
            
            print_success(f"✅ {service_name} tunnel started in background (PID: {process.pid})")
            print_info("Check 'Tunneling Manager' menu to see connection URL")
            log(f"Started {service_name} tunnel with PID {process.pid}")
            
        except Exception as e:
            print_error(f"Failed to start tunnel: {e}")
            self.tunnel_pidfile.unlink(missing_ok=True)
        
        input("\nPress Enter to continue...")
    
    def _monitor_tunnel_output(self, process, service_name):
        """Monitor tunnel output to extract connection URL."""
        import re
        
        url_patterns = {
            "playit.gg": r"(tcp://[a-z0-9-]+\.playit\.gg:\d+)",
            "ngrok": r"tcp://[0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:\d+",
            "cloudflared": r"(https://[a-z0-9-]+\.trycloudflare\.com)",
            "pinggy": r"tcp://[a-z0-9-]+\.tcp\.pinggy\.io:\d+"
        }
        
        pattern = url_patterns.get(service_name)
        
        try:
            for line in process.stdout:
                # Log output
                with open(self.tunnel_logfile, 'a') as f:
                    f.write(line)
                
                # Extract URL
                if pattern:
                    match = re.search(pattern, line)
                    if match:
                        url = match.group(0)
                        self.tunnel_urlfile.write_text(url)
                        log(f"{service_name} tunnel URL: {url}")
        except Exception as e:
            log(f"Error monitoring tunnel output: {e}")
    
    # ===================================================================
    # PLAYIT.GG - WITH BACKGROUND SUPPORT
    # ===================================================================
    
    def setup_playit(self):
        """Setup playit.gg - runs in background."""
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
                print_success("Playit.gg is already installed\n")
                self._start_playit_background()
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Install playit (same as before)
        print_info("Installing playit.gg...")
        print("\nThis will run:")
        print(f"  {UI.colors.CYAN}1. Add playit GPG key{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}2. Add playit repository{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}3. Install playit{UI.colors.RESET}\n")
        
        confirm = input(f"{UI.colors.YELLOW}Proceed? (Y/n): {UI.colors.RESET}").strip().lower()
        if confirm == "n":
            return
        
        try:
            # Installation commands (same as before)
            print_info("Adding GPG key...")
            subprocess.run(
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | tee $PREFIX/etc/apt/trusted.gpg.d/playit.gpg >/dev/null",
                shell=True,
                check=True,
                timeout=30
            )
            
            print_info("Adding repository...")
            repo_file = Path(os.path.expandvars("$PREFIX/etc/apt/sources.list.d/playit-cloud.list"))
            repo_file.parent.mkdir(parents=True, exist_ok=True)
            repo_file.write_text("deb [signed-by=$PREFIX/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./\n")
            
            print_info("Updating package lists...")
            subprocess.run(["apt", "update"], check=True, timeout=60)
            
            print_info("Installing playit...")
            subprocess.run(["apt", "install", "-y", "playit"], check=True, timeout=120)
            
            print_success("✅ Playit.gg installed!\n")
            self._start_playit_background()
            
        except subprocess.CalledProcessError as e:
            print_error(f"Installation failed: {e}")
            print_info("\nManual installation:")
            print("  curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | tee $PREFIX/etc/apt/trusted.gpg.d/playit.gpg")
            print("  echo 'deb [signed-by=$PREFIX/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./' | tee $PREFIX/etc/apt/sources.list.d/playit-cloud.list")
            print("  apt update && apt install playit")
            input("\nPress Enter to continue...")
        except subprocess.TimeoutExpired:
            print_error("Installation timed out")
            input("\nPress Enter to continue...")
    
    def _start_playit_background(self):
        """Start playit in background and return to menu."""
        print(f"\n{UI.colors.BOLD}Starting Playit Agent{UI.colors.RESET}\n")
        print_info("First time? Visit the claim URL shown in tunnel logs")
        print_info("After claiming, tunnel URL will appear in the menu\n")
        
        self._start_background_process(["playit"], "playit.gg")
    
    # ===================================================================
    # PINGGY - FIXED (NO PASSWORD PROMPT)
    # ===================================================================
    
    def setup_pinggy(self):
        """Setup pinggy.io - SSH-based tunnel (FIXED)."""
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
                print_success("SSH installed\n")
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
        print_info("Tunnel will run in background\n")
        
        # FIXED: Added PasswordAuthentication=no to prevent password prompt
        command = [
            "ssh",
            "-p", "443",
            "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no",  # <-- THIS IS THE FIX
            "-o", "ServerAliveInterval=30",
            "-o", "ExitOnForwardFailure=yes",
            f"-R0:localhost:{server_port}",
            "tcp@free.pinggy.io"
        ]
        
        self._start_background_process(command, "pinggy")
    
    # (Keep ngrok and cloudflared methods the same, just add background support)
