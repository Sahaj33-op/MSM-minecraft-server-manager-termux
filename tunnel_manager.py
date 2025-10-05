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
                else:
                    print(f"  URL: {UI.colors.YELLOW}Checking... (see logs for claim URL){UI.colors.RESET}")
                    # Show last few lines of tunnel log for claim URL
                    if self.tunnel_logfile.exists():
                        try:
                            lines = self.tunnel_logfile.read_text().strip().split('\n')
                            # Show last 5 lines
                            for line in lines[-5:]:
                                if 'claim' in line.lower() or 'http' in line:
                                    print(f"    {UI.colors.GRAY}{line}{UI.colors.RESET}")
                                    break
                        except Exception:
                            pass
                print(f"\n{UI.colors.YELLOW}5. Stop active tunnel{UI.colors.RESET}\n")
            else:
                print(f"{UI.colors.GRAY}No active tunnel{UI.colors.RESET}\n")
            
            print("Available services:")
            print("1. playit.gg (recommended - easiest)")
            print("2. ngrok (most popular)")
            print("3. cloudflared (quick tunnel - no login)")
            print("4. pinggy.io (SSH-based - instant)")
            if status:
                print("5. Stop active tunnel")
            print("0. Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.setup_playit()
            elif choice == "2":
                self.setup_ngrok()
            elif choice == "3":
                self.setup_cloudflared()
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
        # First check if we have a PID file
        if self.tunnel_pidfile.exists():
            try:
                # Read the PID file which contains PID on first line and service on second line
                lines = self.tunnel_pidfile.read_text().strip().split('\n')
                if len(lines) >= 2:
                    pid = int(lines[0].strip())
                    service = lines[1].strip()
                    
                    # Check if process is still running
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    
                    # Try to read tunnel URL
                    url = None
                    if self.tunnel_urlfile.exists():
                        url_content = self.tunnel_urlfile.read_text().strip()
                        if url_content:
                            url = url_content
                    
                    return {
                        "pid": pid,
                        "service": service,
                        "url": url
                    }
                else:
                    # Invalid PID file format, remove it
                    self.tunnel_pidfile.unlink(missing_ok=True)
            except (ValueError, ProcessLookupError, PermissionError, IndexError):
                # Process doesn't exist or pidfile is invalid
                self.tunnel_pidfile.unlink(missing_ok=True)
                self.tunnel_urlfile.unlink(missing_ok=True)
        
        # If no PID file or invalid, try to detect running tunnel processes
        try:
            # Check for playit process
            result = subprocess.run(["pgrep", "playit"], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Get the first PID
                pids = result.stdout.strip().split('\n')
                if pids:
                    pid = int(pids[0])
                    return {
                        "pid": pid,
                        "service": "playit.gg",
                        "url": None
                    }
                
            # Check for ngrok process
            result = subprocess.run(["pgrep", "ngrok"], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Get the first PID
                pids = result.stdout.strip().split('\n')
                if pids:
                    pid = int(pids[0])
                    return {
                        "pid": pid,
                        "service": "ngrok",
                        "url": None
                    }
                
            # Check for cloudflared process
            result = subprocess.run(["pgrep", "cloudflared"], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Get the first PID
                pids = result.stdout.strip().split('\n')
                if pids:
                    pid = int(pids[0])
                    return {
                        "pid": pid,
                        "service": "cloudflared",
                        "url": None
                    }
                
            # Check for pinggy SSH process
            result = subprocess.run(["pgrep", "-f", "ssh.*tcp@free.pinggy.io"], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                # Get the first PID
                pids = result.stdout.strip().split('\n')
                if pids:
                    pid = int(pids[0])
                    return {
                        "pid": pid,
                        "service": "pinggy",
                        "url": None
                    }
        except Exception as e:
            # Log the error but don't fail
            log(f"Error detecting tunnel processes: {e}")
            pass
            
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
            
            # Save PID and service name
            with open(self.tunnel_pidfile, 'w') as f:
                f.write(f"{process.pid}\n{service_name}")
            
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
        
        # Enhanced patterns for better URL detection
        enhanced_patterns = {
            "playit.gg": [
                r"(tcp://[a-z0-9-]+\.playit\.gg:\d+)",
                r"(tcp://[a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"([a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg:\d+)"
            ],
            "ngrok": [
                r"(tcp://[0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:\d+)",
                r"([0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:\d+)"
            ],
            "cloudflared": [
                r"(https://[a-z0-9-]+\.trycloudflare\.com)",
                r"(https://[a-zA-Z0-9.-]+\.trycloudflare\.com)"
            ],
            "pinggy": [
                r"(tcp://[a-z0-9-]+\.tcp\.pinggy\.io:\d+)",
                r"(tcp://[a-zA-Z0-9.-]+\.tcp\.pinggy\.io:\d+)",
                r"([a-zA-Z0-9.-]+\.tcp\.pinggy\.io:\d+)"
            ]
        }
        
        patterns = enhanced_patterns.get(service_name, [])
        
        try:
            for line in process.stdout:
                # Log output
                with open(self.tunnel_logfile, 'a') as f:
                    f.write(line)
                
                # Extract URL using enhanced patterns
                for pattern in patterns:
                    match = re.search(pattern, line)
                    if match:
                        url = match.group(1) if match.groups() else match.group(0)
                        # Ensure proper protocol prefix
                        if service_name in ["playit.gg", "ngrok", "pinggy"] and not url.startswith(("tcp://", "https://")):
                            url = "tcp://" + url
                        elif service_name == "cloudflared" and not url.startswith("https://"):
                            url = "https://" + url
                        self.tunnel_urlfile.write_text(url)
                        log(f"{service_name} tunnel URL: {url}")
                        return  # Found a URL, no need to check other patterns or lines
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
        except Exception as e:
            print_error(f"Installation error: {e}")
            input("\nPress Enter to continue...")
    
    def _start_playit_background(self):
        """Start playit in background and return to menu."""
        print(f"\n{UI.colors.BOLD}Starting Playit Agent{UI.colors.RESET}\n")
        print_info("First time? Visit the claim URL shown in tunnel logs")
        print_info("After claiming, tunnel URL will appear in the menu\n")
        
        # Create a more detailed startup message
        print_info("Starting playit.gg agent in background...")
        print_info("Check the tunneling manager for connection details")
        print_info("The claim URL will appear in the logs shortly\n")
        
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
        except Exception as e:
            print_error(f"Error checking SSH: {e}")
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
    
    # ===================================================================
    # NGROK - WITH BACKGROUND SUPPORT
    # ===================================================================
    
    def setup_ngrok(self):
        """Setup ngrok - runs in background."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Ngrok Setup{UI.colors.RESET}\n")
        
        # Check if already installed
        try:
            result = subprocess.run(
                ["ngrok", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success("Ngrok is already installed\n")
                self._start_ngrok_background()
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Install ngrok with proper repository setup
        print_info("Installing ngrok...")
        print("\nThis will run:")
        print(f"  {UI.colors.CYAN}1. Add ngrok GPG key{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}2. Add ngrok repository{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}3. Update package lists{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}4. Install ngrok{UI.colors.RESET}\n")
        
        confirm = input(f"{UI.colors.YELLOW}Proceed? (Y/n): {UI.colors.RESET}").strip().lower()
        if confirm == "n":
            return
        
        try:
            print_info("Adding ngrok GPG key...")
            subprocess.run(
                "curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null",
                shell=True,
                check=True,
                timeout=30
            )
            
            print_info("Adding ngrok repository...")
            subprocess.run(
                'echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" | tee /etc/apt/sources.list.d/ngrok.list',
                shell=True,
                check=True,
                timeout=30
            )
            
            print_info("Updating package lists...")
            subprocess.run(["apt", "update"], check=True, timeout=60)
            
            print_info("Installing ngrok...")
            subprocess.run(["apt", "install", "-y", "ngrok"], check=True, timeout=120)
            
            print_success("✅ Ngrok installed!\n")
            self._start_ngrok_background()
            
        except subprocess.CalledProcessError as e:
            print_error(f"Installation failed: {e}")
            print_info("\nManual installation:")
            print("  curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null")
            print('  echo "deb https://ngrok-agent.s3.amazonaws.com bookworm main" | tee /etc/apt/sources.list.d/ngrok.list')
            print("  apt update && apt install ngrok")
            print("  Or download from https://ngrok.com/download")
            input("\nPress Enter to continue...")
        except subprocess.TimeoutExpired:
            print_error("Installation timed out")
            input("\nPress Enter to continue...")
    
    def _start_ngrok_background(self):
        """Start ngrok in background and return to menu."""
        # Get server port
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
        print_info("Tunnel will run in background\n")
        
        command = ["ngrok", "tcp", str(server_port)]
        self._start_background_process(command, "ngrok")
    
    # ===================================================================
    # CLOUDFLARED - WITH BACKGROUND SUPPORT
    # ===================================================================
    
    def setup_cloudflared(self):
        """Setup cloudflared - runs in background."""
        clear_screen()
        print_header("1.1.0")
        print(f"{UI.colors.BOLD}Cloudflared Setup{UI.colors.RESET}\n")
        
        # Check if already installed
        try:
            result = subprocess.run(
                ["cloudflared", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success("Cloudflared is already installed\n")
                self._start_cloudflared_background()
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Install cloudflared
        print_info("Installing cloudflared...")
        print("\nThis will run:")
        print(f"  {UI.colors.CYAN}1. Update package lists{UI.colors.RESET}")
        print(f"  {UI.colors.CYAN}2. Install cloudflared{UI.colors.RESET}\n")
        
        confirm = input(f"{UI.colors.YELLOW}Proceed? (Y/n): {UI.colors.RESET}").strip().lower()
        if confirm == "n":
            return
        
        try:
            print_info("Updating package lists...")
            subprocess.run(["apt", "update"], check=True, timeout=60)
            
            # Try to install from package manager first
            try:
                print_info("Installing cloudflared...")
                subprocess.run(["apt", "install", "-y", "cloudflared"], check=True, timeout=120)
                print_success("✅ Cloudflared installed!\n")
                self._start_cloudflared_background()
                return
            except subprocess.CalledProcessError:
                print_warning("Package installation failed, trying manual installation...")
            
            # Manual installation for cloudflared
            print_info("Downloading cloudflared binary...")
            subprocess.run(
                "curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb",
                shell=True,
                check=True,
                timeout=120
            )
            
            print_info("Installing cloudflared package...")
            subprocess.run(["dpkg", "-i", "cloudflared.deb"], check=True, timeout=60)
            
            # Clean up
            subprocess.run(["rm", "-f", "cloudflared.deb"], check=True, timeout=10)
            
            print_success("✅ Cloudflared installed!\n")
            self._start_cloudflared_background()
            
        except subprocess.CalledProcessError as e:
            print_error(f"Installation failed: {e}")
            print_info("\nManual installation:")
            print("  Download from: https://github.com/cloudflare/cloudflared/releases")
            print("  Or try: apt update && apt install cloudflared")
            input("\nPress Enter to continue...")
        except subprocess.TimeoutExpired:
            print_error("Installation timed out")
            input("\nPress Enter to continue...")
    
    def _start_cloudflared_background(self):
        """Start cloudflared in background and return to menu."""
        # Get server port
        from server_manager import ServerManager
        current_server = ServerManager.get_current_server()
        
        if current_server:
            from config import ConfigManager
            server_config = ConfigManager.load_server_config(current_server)
            server_port = server_config.get("port", 25565)
        else:
            server_port = 25565
        
        print(f"\n{UI.colors.BOLD}Starting Cloudflared Tunnel{UI.colors.RESET}\n")
        print_info(f"Tunneling port {server_port}")
        print_info("Tunnel will run in background\n")
        
        command = ["cloudflared", "tunnel", "--url", f"tcp://localhost:{server_port}"]
        self._start_background_process(command, "cloudflared")
