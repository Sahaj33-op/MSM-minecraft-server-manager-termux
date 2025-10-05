#!/usr/bin/env python3
"""
simple_tunnel_manager.py - Simplified tunneling based on working manual approach
"""

import subprocess
import time
import os
import threading
import json
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from config import get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log

class TunnelState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    FAILED = "failed"

class TunnelService(Enum):
    PLAYIT = "playit.gg"
    NGROK = "ngrok"
    CLOUDFLARED = "cloudflared"
    PINGGY = "pinggy"

@dataclass
class TunnelConfig:
    service: TunnelService
    port: int
    pid: Optional[int] = None
    state: TunnelState = TunnelState.STOPPED
    url: Optional[str] = None
    claim_url: Optional[str] = None

class SimpleTunnelManager:
    """Simple, reliable tunnel management based on proven manual approach."""
    
    def __init__(self):
        self.config_root = get_config_root()
        self.config_root.mkdir(parents=True, exist_ok=True)
        
        # Create bin directory for binary tools
        self.bin_dir = self.config_root / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        self.tunnel_config_file = self.config_root / "tunnel_config.json"
        self.tunnel_logfile = self.config_root / "tunnel.log"
        
        self.current_config: Optional[TunnelConfig] = None
        self._load_config()
    
    def tunneling_menu(self):
        """Simple tunneling menu."""
        while True:
            clear_screen()
            print_header("1.2.0")
            print(f"{UI.colors.BOLD}Simple Tunneling Manager{UI.colors.RESET}\n")
            
            # Show status
            if self.current_config:
                status_color = UI.colors.GREEN if self.current_config.state == TunnelState.RUNNING else UI.colors.RED
                print(f"{status_color}● {self.current_config.state.value.upper()}{UI.colors.RESET} - {self.current_config.service.value}")
                if self.current_config.url:
                    print(f"URL: {UI.colors.CYAN}{self.current_config.url}{UI.colors.RESET}")
                if self.current_config.claim_url:
                    print(f"Claim: {UI.colors.YELLOW}{self.current_config.claim_url}{UI.colors.RESET}")
                print()
            
            print("Available services:")
            print("1. playit.gg (recommended)")
            print("2. ngrok")
            print("3. cloudflared")
            print("4. pinggy.io")
            
            if self.current_config and self.current_config.state == TunnelState.RUNNING:
                print("5. Stop tunnel")
                print("6. View logs")
            
            print("0. Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self._setup_playit()
            elif choice == "2":
                self._setup_ngrok()
            elif choice == "3":
                self._setup_cloudflared()
            elif choice == "4":
                self._setup_pinggy()
            elif choice == "5" and self.current_config:
                self._stop_tunnel()
            elif choice == "6" and self.current_config:
                self._view_logs()
            elif choice == "0":
                break
            else:
                print_error("Invalid option")
                input("Press Enter to continue...")
    
    def _setup_playit(self):
        """Setup playit.gg tunnel using proven method."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}playit.gg Setup{UI.colors.RESET}\n")
        
        try:
            # Stop existing tunnel
            if self.current_config and self.current_config.state == TunnelState.RUNNING:
                print_warning("Stopping existing tunnel...")
                self._stop_tunnel()
            
            # Check if playit is installed
            if not self._check_playit_installed():
                print_info("Installing playit.gg...")
                if not self._install_playit():
                    print_error("Failed to install playit.gg")
                    input("Press Enter to continue...")
                    return
            
            print_success("playit.gg is ready!")
            
            # Get server port
            port = self._get_server_port()
            print_info(f"Using server port: {port}")
            
            # Create config
            self.current_config = TunnelConfig(
                service=TunnelService.PLAYIT,
                port=port,
                state=TunnelState.RUNNING
            )
            
            # Start tunnel
            print_info("Starting playit.gg tunnel...")
            if self._start_playit(port):
                print_success("✅ Tunnel started successfully!")
                self._save_config()
            else:
                print_error("Failed to start tunnel")
                self.current_config.state = TunnelState.FAILED
                self._save_config()
            
        except Exception as e:
            log(f"Playit setup error: {e}")
            print_error(f"Setup failed: {e}")
        
        input("Press Enter to continue...")
    
    def _check_playit_installed(self) -> bool:
        """Check if playit is installed using the correct command."""
        try:
            # Use the correct command: playit version
            result = subprocess.run(["playit", "version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _install_playit(self) -> bool:
        """Install playit using proven method."""
        try:
            commands = [
                # Exact working commands from manual test
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/playit.gpg",
                'echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" > /etc/apt/sources.list.d/playit-cloud.list',
                "apt update",
                "apt install playit -y"
            ]
            
            for i, cmd in enumerate(commands, 1):
                print_info(f"Step {i}/{len(commands)}: Running installation command...")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    log(f"Command failed: {cmd}")
                    log(f"Error: {result.stderr}")
                    print_error(f"Installation step {i} failed")
                    return False
            
            # Verify installation
            if self._check_playit_installed():
                print_success("playit.gg installed successfully!")
                return True
            else:
                print_error("Installation completed but playit command not working")
                return False
                
        except Exception as e:
            log(f"Installation error: {e}")
            print_error(f"Installation error: {e}")
            return False
    
    def _start_playit(self, port: int) -> bool:
        """Start playit tunnel."""
        try:
            # Start playit in background
            cmd = ["playit", "start"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Check if we have a current config
            if not self.current_config:
                return False
                
            self.current_config.pid = process.pid
            
            # Monitor output for URLs
            monitor_thread = threading.Thread(
                target=self._monitor_playit_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("Playit process started successfully!")
                return True
            else:
                print_error("Playit process exited unexpectedly")
                return False
                
        except Exception as e:
            log(f"Failed to start playit: {e}")
            return False
    
    def _monitor_playit_output(self, process):
        """Monitor playit output for URLs."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log output
                    with open(self.tunnel_logfile, 'a') as f:
                        f.write(f"[{datetime.now()}] {line}\n")
                    
                    # Check if we have a current config
                    if not self.current_config:
                        continue
                        
                    # Look for URLs
                    if "tcp://" in line or "joinmc.link" in line:
                        # Extract URL
                        words = line.split()
                        for word in words:
                            if "tcp://" in word or "joinmc.link" in word:
                                self.current_config.url = word
                                self._save_config()
                                break
                    
                    # Look for claim URLs
                    if "claim" in line.lower() and "http" in line:
                        words = line.split()
                        for word in words:
                            if word.startswith("http") and "claim" in word:
                                self.current_config.claim_url = word
                                self._save_config()
                                break
                                
        except Exception as e:
            log(f"Output monitoring error: {e}")
    
    def _stop_tunnel(self):
        """Stop the current tunnel."""
        if not self.current_config or not self.current_config.pid:
            return
        
        try:
            print_info("Stopping tunnel...")
            
            # Kill process
            os.kill(self.current_config.pid, 15)  # SIGTERM
            time.sleep(2)
            
            # Check if still running
            try:
                os.kill(self.current_config.pid, 0)
                # Still running, force kill
                os.kill(self.current_config.pid, 9)  # SIGKILL
            except ProcessLookupError:
                pass  # Process already dead
            
            self.current_config.state = TunnelState.STOPPED
            self.current_config.pid = None
            self.current_config.url = None
            self.current_config.claim_url = None
            self._save_config()
            
            print_success("Tunnel stopped")
            
        except Exception as e:
            log(f"Error stopping tunnel: {e}")
            print_error(f"Error stopping tunnel: {e}")
    
    def _view_logs(self):
        """View tunnel logs."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}Tunnel Logs{UI.colors.RESET}\n")
        
        try:
            if self.tunnel_logfile.exists():
                with open(self.tunnel_logfile, 'r') as f:
                    lines = f.readlines()
                
                # Show last 50 lines
                for line in lines[-50:]:
                    print(line.strip())
            else:
                print_info("No logs available")
                
        except Exception as e:
            print_error(f"Error reading logs: {e}")
        
        input("\nPress Enter to continue...")
    
    def _get_server_port(self) -> int:
        """Get server port (simplified)."""
        try:
            # Try to get from server manager
            from server_manager import ServerManager
            current_server = ServerManager.get_current_server()
            if current_server:
                from config import ConfigManager
                server_config = ConfigManager.load_server_config(current_server)
                return server_config.get("port", 25565)
        except:
            pass
        return 25565
    
    def _save_config(self):
        """Save configuration."""
        if not self.current_config:
            return
        
        try:
            config_data = {
                "service": self.current_config.service.value,
                "port": self.current_config.port,
                "pid": self.current_config.pid,
                "state": self.current_config.state.value,
                "url": self.current_config.url,
                "claim_url": self.current_config.claim_url
            }
            
            with open(self.tunnel_config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
        except Exception as e:
            log(f"Error saving config: {e}")
    
    def _load_config(self):
        """Load configuration."""
        try:
            if self.tunnel_config_file.exists():
                with open(self.tunnel_config_file, 'r') as f:
                    data = json.load(f)
                
                self.current_config = TunnelConfig(
                    service=TunnelService(data["service"]),
                    port=data["port"],
                    pid=data.get("pid"),
                    state=TunnelState(data.get("state", "stopped")),
                    url=data.get("url"),
                    claim_url=data.get("claim_url")
                )
                
                # Verify process is still running
                if self.current_config.pid and self.current_config.state == TunnelState.RUNNING:
                    try:
                        os.kill(self.current_config.pid, 0)
                    except ProcessLookupError:
                        # Process not running
                        self.current_config.state = TunnelState.STOPPED
                        self.current_config.pid = None
                        self._save_config()
                        
        except Exception as e:
            log(f"Error loading config: {e}")
    
    def _setup_ngrok(self):
        """Setup ngrok tunnel."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}ngrok Setup{UI.colors.RESET}\n")
        
        try:
            # Stop existing tunnel
            if self.current_config and self.current_config.state == TunnelState.RUNNING:
                print_warning("Stopping existing tunnel...")
                self._stop_tunnel()
            
            # Check if ngrok is installed
            if not self._check_ngrok_installed():
                print_info("Installing ngrok...")
                if not self._install_ngrok():
                    print_error("Failed to install ngrok")
                    input("Press Enter to continue...")
                    return
            
            print_success("ngrok is ready!")
            
            # Get server port
            port = self._get_server_port()
            print_info(f"Using server port: {port}")
            
            # Create config
            self.current_config = TunnelConfig(
                service=TunnelService.NGROK,
                port=port,
                state=TunnelState.RUNNING
            )
            
            # Start tunnel
            print_info("Starting ngrok tunnel...")
            if self._start_ngrok(port):
                print_success("✅ Tunnel started successfully!")
                self._save_config()
            else:
                print_error("Failed to start tunnel")
                self.current_config.state = TunnelState.FAILED
                self._save_config()
                
        except Exception as e:
            log(f"Ngrok setup error: {e}")
            print_error(f"Setup failed: {e}")
        
        input("Press Enter to continue...")
    
    def _check_ngrok_installed(self) -> bool:
        """Check if ngrok is installed."""
        try:
            result = subprocess.run(["ngrok", "version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _install_ngrok(self) -> bool:
        """Install ngrok."""
        try:
            import platform
            arch_map = {
                "x86_64": "amd64",
                "aarch64": "arm64",
                "armv7l": "arm",
                "i386": "386",
                "i686": "386"
            }
            
            system_arch = platform.machine().lower()
            arch = arch_map.get(system_arch, "amd64")
            
            download_url = f"https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-{arch}.tgz"
            
            # Download
            result = subprocess.run([
                "wget", "-O", "/tmp/ngrok.tgz", download_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception("Download failed")
                
            # Extract
            subprocess.run([
                "tar", "xzf", "/tmp/ngrok.tgz", "-C", str(self.bin_dir)
            ], check=True, timeout=30)
            
            # Make executable
            ngrok_path = self.bin_dir / "ngrok"
            ngrok_path.chmod(0o755)
            
            # Setup authentication
            self._setup_ngrok_auth()
            
            return ngrok_path.exists()
            
        except Exception as e:
            log(f"Ngrok installation failed: {e}")
            return False
    
    def _setup_ngrok_auth(self):
        """Setup ngrok authentication interactively."""
        print_info("Ngrok requires authentication. Please get your auth token from:")
        print_info("https://dashboard.ngrok.com/get-started/your-authtoken")
        
        auth_token = input("Enter your ngrok auth token (or press Enter to skip): ").strip()
        
        if auth_token:
            try:
                result = subprocess.run([
                    str(self.bin_dir / "ngrok"), "authtoken", auth_token
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print_success("✅ Ngrok authentication configured")
                else:
                    print_warning("Authentication setup failed, you may need to configure manually")
                    
            except Exception as e:
                log(f"Ngrok auth setup failed: {e}")
                print_warning("Authentication setup failed")
        else:
            print_warning("Skipping authentication - you'll need to set this up later")
    
    def _start_ngrok(self, port: int) -> bool:
        """Start ngrok tunnel."""
        try:
            # Start ngrok in background
            cmd = [str(self.bin_dir / "ngrok"), "tcp", f"localhost:{port}"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Check if we have a current config
            if not self.current_config:
                return False
                
            self.current_config.pid = process.pid
            
            # Monitor output for URLs
            monitor_thread = threading.Thread(
                target=self._monitor_ngrok_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("Ngrok process started successfully!")
                return True
            else:
                print_error("Ngrok process exited unexpectedly")
                return False
                
        except Exception as e:
            log(f"Failed to start ngrok: {e}")
            return False
    
    def _monitor_ngrok_output(self, process):
        """Monitor ngrok output for URLs."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log output
                    with open(self.tunnel_logfile, 'a') as f:
                        f.write(f"[{datetime.now()}] {line}\n")
                    
                    # Check if we have a current config
                    if not self.current_config:
                        continue
                        
                    # Look for URLs
                    if ".ngrok.io" in line:
                        # Extract URL
                        import re
                        url_pattern = r"(tcp://[0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:[0-9]+)"
                        match = re.search(url_pattern, line)
                        if match:
                            url = match.group(1)
                            self.current_config.url = url
                            self._save_config()
                            break
                                
        except Exception as e:
            log(f"Output monitoring error: {e}")
    
    def _setup_cloudflared(self):
        """Setup cloudflared tunnel."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}cloudflared Setup{UI.colors.RESET}\n")
        
        try:
            # Stop existing tunnel
            if self.current_config and self.current_config.state == TunnelState.RUNNING:
                print_warning("Stopping existing tunnel...")
                self._stop_tunnel()
            
            # Check if cloudflared is installed
            if not self._check_cloudflared_installed():
                print_info("Installing cloudflared...")
                if not self._install_cloudflared():
                    print_error("Failed to install cloudflared")
                    input("Press Enter to continue...")
                    return
            
            print_success("cloudflared is ready!")
            
            # Get server port
            port = self._get_server_port()
            print_info(f"Using server port: {port}")
            
            # Create config
            self.current_config = TunnelConfig(
                service=TunnelService.CLOUDFLARED,
                port=port,
                state=TunnelState.RUNNING
            )
            
            # Start tunnel
            print_info("Starting cloudflared tunnel...")
            if self._start_cloudflared(port):
                print_success("✅ Tunnel started successfully!")
                self._save_config()
            else:
                print_error("Failed to start tunnel")
                self.current_config.state = TunnelState.FAILED
                self._save_config()
                
        except Exception as e:
            log(f"Cloudflared setup error: {e}")
            print_error(f"Setup failed: {e}")
        
        input("Press Enter to continue...")
    
    def _check_cloudflared_installed(self) -> bool:
        """Check if cloudflared is installed."""
        try:
            result = subprocess.run(["cloudflared", "version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _install_cloudflared(self) -> bool:
        """Install cloudflared."""
        try:
            import platform
            arch_map = {
                "x86_64": "amd64",
                "aarch64": "arm64",
                "armv7l": "arm",
                "i386": "386",
                "i686": "386"
            }
            
            system_arch = platform.machine().lower()
            arch = arch_map.get(system_arch, "amd64")
            
            download_url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-{arch}"
            
            target_path = self.bin_dir / "cloudflared"
            
            # Download
            result = subprocess.run([
                "wget", "-O", str(target_path), download_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception("Download failed")
                
            # Make executable
            target_path.chmod(0o755)
            
            return target_path.exists() and target_path.stat().st_size > 0
            
        except Exception as e:
            log(f"Cloudflared installation failed: {e}")
            return False
    
    def _start_cloudflared(self, port: int) -> bool:
        """Start cloudflared tunnel."""
        try:
            # Start cloudflared in background
            cmd = [str(self.bin_dir / "cloudflared"), "tunnel", 
                   "--url", f"tcp://localhost:{port}"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Check if we have a current config
            if not self.current_config:
                return False
                
            self.current_config.pid = process.pid
            
            # Monitor output for URLs
            monitor_thread = threading.Thread(
                target=self._monitor_cloudflared_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("Cloudflared process started successfully!")
                return True
            else:
                print_error("Cloudflared process exited unexpectedly")
                return False
                
        except Exception as e:
            log(f"Failed to start cloudflared: {e}")
            return False
    
    def _monitor_cloudflared_output(self, process):
        """Monitor cloudflared output for URLs."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log output
                    with open(self.tunnel_logfile, 'a') as f:
                        f.write(f"[{datetime.now()}] {line}\n")
                    
                    # Check if we have a current config
                    if not self.current_config:
                        continue
                        
                    # Look for URLs
                    if ".trycloudflare.com" in line:
                        # Extract URL
                        import re
                        url_pattern = r"(https://[a-zA-Z0-9-]+\.trycloudflare\.com)"
                        match = re.search(url_pattern, line)
                        if match:
                            url = match.group(1)
                            self.current_config.url = url
                            self._save_config()
                            break
                                
        except Exception as e:
            log(f"Output monitoring error: {e}")
    
    def _setup_pinggy(self):
        """Setup pinggy tunnel."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}pinggy.io Setup{UI.colors.RESET}\n")
        
        try:
            # Stop existing tunnel
            if self.current_config and self.current_config.state == TunnelState.RUNNING:
                print_warning("Stopping existing tunnel...")
                self._stop_tunnel()
            
            # Check if SSH is available
            if not self._check_ssh_available():
                print_error("SSH is not available on this system")
                input("Press Enter to continue...")
                return
            
            print_success("SSH is available!")
            
            # Get server port
            port = self._get_server_port()
            print_info(f"Using server port: {port}")
            
            # Create config
            self.current_config = TunnelConfig(
                service=TunnelService.PINGGY,
                port=port,
                state=TunnelState.RUNNING
            )
            
            # Start tunnel
            print_info("Starting pinggy tunnel...")
            if self._start_pinggy(port):
                print_success("✅ Tunnel started successfully!")
                self._save_config()
            else:
                print_error("Failed to start tunnel")
                self.current_config.state = TunnelState.FAILED
                self._save_config()
                
        except Exception as e:
            log(f"Pinggy setup error: {e}")
            print_error(f"Setup failed: {e}")
        
        input("Press Enter to continue...")
    
    def _check_ssh_available(self) -> bool:
        """Check if SSH is available."""
        return shutil.which("ssh") is not None
    
    def _start_pinggy(self, port: int) -> bool:
        """Start pinggy tunnel."""
        try:
            # Start SSH tunnel in background
            cmd = ["ssh", "-o", "StrictHostKeyChecking=no",
                   "-o", "ServerAliveInterval=30",
                   "-R", f"0:localhost:{port}",
                   "a.pinggy.io"]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # Check if we have a current config
            if not self.current_config:
                return False
                
            self.current_config.pid = process.pid
            
            # Monitor output for URLs
            monitor_thread = threading.Thread(
                target=self._monitor_pinggy_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait a bit for startup
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("Pinggy process started successfully!")
                return True
            else:
                print_error("Pinggy process exited unexpectedly")
                return False
                
        except Exception as e:
            log(f"Failed to start pinggy: {e}")
            return False
    
    def _monitor_pinggy_output(self, process):
        """Monitor pinggy output for URLs."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log output
                    with open(self.tunnel_logfile, 'a') as f:
                        f.write(f"[{datetime.now()}] {line}\n")
                    
                    # Check if we have a current config
                    if not self.current_config:
                        continue
                        
                    # Look for URLs
                    if ".tcp.pinggy.io" in line or ".a.pinggy.io" in line:
                        # Extract URL
                        import re
                        url_pattern = r"(tcp://[a-zA-Z0-9.-]+\.tcp\.pinggy\.io:[0-9]+)"
                        match = re.search(url_pattern, line)
                        if match:
                            url = match.group(1)
                            self.current_config.url = url
                            self._save_config()
                            break
                                
        except Exception as e:
            log(f"Output monitoring error: {e}")

# For backward compatibility
TunnelManager = SimpleTunnelManager