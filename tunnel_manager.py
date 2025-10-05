#!/usr/bin/env python3
"""
tunnel_manager.py - Simple & Reliable Playit.gg Tunnel Management
Architecture: One-time setup, then one-click operations
"""

import subprocess
import time
import os
import signal
import threading
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

from config import get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log

class TunnelState(Enum):
    """Simple tunnel states for easy management."""
    NOT_SETUP = "not_setup"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"

class TunnelManager:
    """
    Simple, reliable playit.gg tunnel management.
    Focus: One-time setup, then one-click start/stop operations.
    """
    
    def __init__(self):
        """Initialize tunnel manager with MSM-style file structure."""
        self.config_root = get_config_root()
        
        # MSM-style file organization
        self.tunnel_pidfile = self.config_root / "tunnel.pid"
        self.tunnel_logfile = self.config_root / "tunnel.log"
        self.tunnel_config_file = self.config_root / "tunnel_config.json"
        self.setup_complete_marker = self.config_root / ".playit_setup_complete"
        
        # Initialize config
        self.config = self._load_config()
        
        # Clean up stale processes on startup
        self._cleanup_stale_processes()
    
    # ==========================================
    # MAIN MENU INTEGRATION (MSM Compatibility)
    # ==========================================
    
    def get_tunnel_url_for_main_menu(self) -> Optional[str]:
        """Get tunnel URL for display in main MSM menu."""
        status = self.get_tunnel_status()
        if status and status.get("running") and status.get("url"):
            return status["url"]
        return None
    
    def get_tunnel_status(self) -> Optional[Dict[str, Any]]:
        """
        Get tunnel status for MSM compatibility.
        Returns dict with keys: pid, service, url, running
        """
        if not self.tunnel_pidfile.exists():
            return None
        
        try:
            pid_content = self.tunnel_pidfile.read_text().strip()
            lines = pid_content.split('\n')
            pid = int(lines[0])
            service = lines[1] if len(lines) > 1 else "playit.gg"
            
            # Check if process is actually running
            os.kill(pid, 0)  # Will raise ProcessLookupError if not running
            
            # Get tunnel URL from config
            tunnel_url = self.config.get("tunnel_url")
            
            return {
                "pid": pid,
                "service": service,
                "url": tunnel_url,
                "running": True
            }
            
        except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
            # Clean up stale files
            self._cleanup_stale_files()
            return None
    
    # ==========================================
    # MAIN TUNNELING MENU
    # ==========================================
    
    def tunneling_menu(self):
        """Main tunneling menu following MSM patterns."""
        while True:
            clear_screen()
            print_header("1.2.0")
            print(f"{UI.colors.BOLD}🌐 Tunneling Manager{UI.colors.RESET}\n")
            
            # Show current status
            self._display_tunnel_status()
            
            # Show appropriate menu based on setup state
            if not self._is_setup_complete():
                self._show_setup_menu()
            else:
                self._show_operation_menu()
            
            choice = input(f"\n{UI.colors.YELLOW}Select option: {UI.colors.RESET}").strip()
            
            if choice == "0":
                break
            
            self._handle_menu_choice(choice)
    
    def _display_tunnel_status(self):
        """Display current tunnel status (MSM style)."""
        status = self.get_tunnel_status()
        
        if status and status['running']:
            print(f"{UI.colors.GREEN}🟢 TUNNEL ACTIVE{UI.colors.RESET}")
            print(f"   Service: playit.gg")
            print(f"   PID: {status['pid']}")
            
            if status.get('url'):
                print(f"   URL: {UI.colors.CYAN}{status['url']}{UI.colors.RESET}")
                # Extract connection info for users
                if "tcp://" in status['url']:
                    server_address = status['url'].replace("tcp://", "")
                    print(f"   📋 Give players: {UI.colors.GREEN}{server_address}{UI.colors.RESET}")
            else:
                print(f"   ⏳ Starting up... (check logs for URL)")
            print()
        elif self._is_setup_complete():
            print(f"{UI.colors.GRAY}⚪ Tunnel configured but stopped{UI.colors.RESET}\n")
        else:
            print(f"{UI.colors.GRAY}⚪ Tunnel not set up{UI.colors.RESET}\n")
    
    def _show_setup_menu(self):
        """Show setup menu when playit.gg hasn't been configured."""
        print("🔧 Initial Setup Required:")
        
        if not self._check_playit_installed():
            print("1. 📦 Install playit.gg")
            print("2. 📋 Show installation instructions")
        else:
            print("1. ⚙️  Run interactive setup (one-time)")
            print("2. 📋 Manual setup instructions")
            print("3. 🔄 Re-install playit.gg")
        
        print("0. ← Back")
    
    def _show_operation_menu(self):
        """Show operation menu when setup is complete."""
        status = self.get_tunnel_status()
        is_running = status and status['running']
        
        print("🚀 Tunnel Operations:")
        
        if is_running:
            print("1. ⏹️  Stop tunnel")
            print("2. 🔄 Restart tunnel")
            print("3. 📊 Show tunnel info")
            print("4. 📋 View logs")
            print("5. 🔧 Re-run setup")
        else:
            print("1. ▶️  Start tunnel")
            print("2. 📊 Show tunnel info")
            print("3. 📋 View logs")
            print("4. 🔧 Re-run setup")
        
        print("0. ← Back")
    
    def _handle_menu_choice(self, choice: str):
        """Handle menu selection based on current state."""
        if not self._is_setup_complete():
            # Setup menu choices
            if choice == "1":
                if not self._check_playit_installed():
                    self._install_playit()
                else:
                    self._run_interactive_setup()
            elif choice == "2":
                self._show_setup_instructions()
            elif choice == "3":
                self._install_playit()
            else:
                print_error("❌ Invalid option")
                time.sleep(1)
        else:
            # Operation menu choices
            status = self.get_tunnel_status()
            is_running = status and status['running']
            
            if choice == "1":
                if is_running:
                    self._stop_tunnel()
                else:
                    self._start_tunnel()
            elif choice == "2":
                if is_running:
                    self._restart_tunnel()
                else:
                    self._show_tunnel_info()
            elif choice == "3":
                if is_running:
                    self._show_tunnel_info()
                else:
                    self._view_logs()
            elif choice == "4":
                if is_running:
                    self._view_logs()
                else:
                    self._run_interactive_setup()
            elif choice == "5" and is_running:
                self._run_interactive_setup()
            else:
                print_error("❌ Invalid option")
                time.sleep(1)
    
    # ==========================================
    # SETUP OPERATIONS (One-time)
    # ==========================================
    
    def _is_setup_complete(self) -> bool:
        """Check if initial playit setup is complete."""
        return (self.setup_complete_marker.exists() and 
                self.config.get("is_setup_complete", False))
    
    def _check_playit_installed(self) -> bool:
        """Check if playit is properly installed."""
        try:
            # Use correct command syntax from your demo
            result = subprocess.run(["playit", "version"], 
                                  capture_output=True, text=True, timeout=10)
            log(f"Playit version check: return_code={result.returncode}")
            log(f"Playit version output: {result.stdout}")
            return result.returncode == 0
        except FileNotFoundError:
            log("Playit command not found")
            return False
        except Exception as e:
            log(f"Playit check error: {e}")
            return False
    
    def _install_playit(self):
        """Install playit.gg using your proven APT method."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📦 Installing Playit.gg{UI.colors.RESET}\n")
        
        print_info("Installing playit.gg using the official APT repository...")
        print_info("This is the same method that worked in your manual test.")
        print()
        
        try:
            # Your exact working commands from the demo
            commands = [
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/playit.gpg",
                'echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" > /etc/apt/sources.list.d/playit-cloud.list',
                "apt update",
                "apt install playit -y"
            ]
            
            for i, cmd in enumerate(commands, 1):
                print_info(f"📦 Step {i}/{len(commands)}: Running installation command...")
                log(f"Running command: {cmd}")
                
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, 
                                          text=True, timeout=120)
                    
                    log(f"Command exit code: {result.returncode}")
                    log(f"Command stdout: {result.stdout}")
                    log(f"Command stderr: {result.stderr}")
                    
                    if result.returncode != 0:
                        print_error(f"❌ Installation step {i} failed")
                        print_error(f"Command: {cmd}")
                        print_error(f"Error: {result.stderr}")
                        self._show_installation_troubleshooting(cmd, result)
                        input("\n📱 Press Enter to continue...")
                        return
                    else:
                        print_success(f"✅ Step {i} completed successfully")
                        
                except subprocess.TimeoutExpired:
                    print_error(f"❌ Step {i} timed out after 2 minutes")
                    input("\n📱 Press Enter to continue...")
                    return
                except Exception as e:
                    print_error(f"❌ Step {i} failed with exception: {e}")
                    log(f"Installation step {i} exception: {e}")
                    input("\n📱 Press Enter to continue...")
                    return
            
            # Verify installation
            print_info("🔍 Verifying installation...")
            if self._check_playit_installed():
                print_success("✅ Playit.gg installed successfully!")
                print_info("💡 You can now run interactive setup")
            else:
                print_error("❌ Installation completed but playit command not working")
                self._show_verification_troubleshooting()
                
        except Exception as e:
            print_error(f"❌ Installation error: {e}")
            log(f"Installation exception: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _run_interactive_setup(self):
        """Run the one-time interactive setup."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}🔧 Playit.gg Interactive Setup{UI.colors.RESET}\n")
        
        if not self._check_playit_installed():
            print_error("❌ playit.gg is not installed. Install it first.")
            input("📱 Press Enter to continue...")
            return
        
        print_info("This will set up your playit.gg account and tunnels.")
        print_warning("⚠️  You only need to do this ONCE!")
        print()
        print_info("During setup, you will:")
        print_info("1. 🔗 Claim your agent (creates account if needed)")
        print_info("2. 🎯 Create a tunnel for your Minecraft server")
        print_info(f"3. 🔌 Configure it for port: {self._get_server_port()}")
        print()
        print_warning("⚠️  This runs interactively - follow all prompts carefully")
        print_warning("⚠️  Keep this terminal window open during setup")
        print_info("💡 When asked for tunnel type, choose: TCP")
        print_info(f"💡 When asked for local port, use: {self._get_server_port()}")
        print()
        
        confirm = input("🚀 Start interactive setup? (y/N): ").strip().lower()
        if confirm != 'y':
            return
        
        try:
            print_info("🔄 Starting playit.gg interactive setup...")
            print("=" * 60)
            log("Starting interactive playit setup")
            
            # Run playit without arguments for interactive setup (your proven method)
            result = subprocess.run(["playit"], 
                                  stdin=None,    # Allow interactive input
                                  stdout=None,   # Show output to user
                                  stderr=None,   # Show errors to user
                                  timeout=600)   # 10 minute timeout
            
            print("=" * 60)
            log(f"Interactive setup completed with return code: {result.returncode}")
            
            if result.returncode == 0:
                print_success("✅ Setup completed successfully!")
                
                # Mark setup as complete
                self.setup_complete_marker.touch()
                self.config["is_setup_complete"] = True
                self.config["setup_completed_at"] = datetime.now().isoformat()
                self._save_config()
                
                print_info("🧪 Testing tunnel startup...")
                if self._test_tunnel_start():
                    print_success("✅ Tunnel test successful! Ready to use.")
                else:
                    print_warning("⚠️  Setup completed but tunnel test failed.")
                    print_info("💡 Try using 'Start tunnel' to test manually.")
            else:
                print_warning("⚠️  Setup may be incomplete (non-zero exit code).")
                print_info("💡 You can run setup again if needed.")
                log(f"Setup exit code: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            print_warning("⚠️  Setup timed out after 10 minutes.")
            print_info("💡 You can run setup again - it may just need more time.")
            log("Interactive setup timed out")
        except KeyboardInterrupt:
            print_info("⚠️  Setup interrupted by user (Ctrl+C).")
            print_info("💡 You can run setup again anytime.")
            log("Interactive setup interrupted by user")
        except Exception as e:
            print_error(f"❌ Setup error: {e}")
            log(f"Interactive setup error: {e}")
            self._show_setup_troubleshooting(e)
        
        input("\n📱 Press Enter to continue...")
    
    def _test_tunnel_start(self) -> bool:
        """Quick test to see if tunnel can start properly."""
        try:
            log("Testing tunnel startup")
            
            # Try to start tunnel in background briefly
            process = subprocess.Popen(
                ["playit", "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait 5 seconds to see if it starts
            time.sleep(5)
            
            # Check if still running
            if process.poll() is None:
                # It's running, stop it
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                log("Tunnel test successful - process started and was stopped")
                return True
            else:
                log(f"Tunnel test failed - process exited with code {process.returncode}")
                return False
                
        except Exception as e:
            log(f"Tunnel test exception: {e}")
            return False
    
    # ==========================================
    # TUNNEL OPERATIONS (Daily use)
    # ==========================================
    
    def _start_tunnel(self):
        """Start the tunnel (after setup is complete)."""
        if not self._is_setup_complete():
            print_error("❌ Please complete setup first!")
            input("📱 Press Enter to continue...")
            return
        
        # Check if already running
        status = self.get_tunnel_status()
        if status and status['running']:
            print_warning("⚠️  Tunnel is already running!")
            input("📱 Press Enter to continue...")
            return
        
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}🚀 Starting Tunnel{UI.colors.RESET}\n")
        
        try:
            server_port = self._get_server_port()
            print_info(f"🔌 Detected server port: {server_port}")
            print_info("🔄 Starting playit.gg tunnel...")
            
            log("Starting tunnel with playit start command")
            
            # Start tunnel in background (your working method)
            process = subprocess.Popen(
                ["playit", "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Save PID to pidfile (MSM style)
            with open(self.tunnel_pidfile, 'w') as f:
                f.write(f"{process.pid}\nplayit.gg\n")
            
            log(f"Tunnel process started with PID: {process.pid}")
            print_success(f"✅ Tunnel process started! (PID: {process.pid})")
            
            # Start output monitoring in background
            monitor_thread = threading.Thread(
                target=self._monitor_tunnel_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Wait a moment for startup
            print_info("⏳ Waiting for tunnel to establish...")
            time.sleep(5)
            
            # Check if process is still running
            if process.poll() is None:
                print_success("🎉 Tunnel is running!")
                print_info("💡 Check logs or tunnel info to see your connection URL")
                print_info("💡 URL will appear in main menu when detected")
            else:
                print_error("❌ Tunnel stopped unexpectedly")
                self._cleanup_stale_files()
                self._show_startup_troubleshooting()
                
        except Exception as e:
            log(f"Error starting tunnel: {e}")
            print_error(f"❌ Failed to start tunnel: {e}")
            self._cleanup_stale_files()
            self._show_startup_troubleshooting()
        
        input("\n📱 Press Enter to continue...")
    
    def _stop_tunnel(self):
        """Stop the running tunnel."""
        status = self.get_tunnel_status()
        if not status or not status['running']:
            print_warning("⚠️  No tunnel is currently running")
            input("📱 Press Enter to continue...")
            return
        
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}⏹️  Stopping Tunnel{UI.colors.RESET}\n")
        
        try:
            pid = status['pid']
            print_info(f"🔄 Stopping tunnel process (PID: {pid})...")
            log(f"Stopping tunnel with PID: {pid}")
            
            # Graceful shutdown first
            os.kill(pid, signal.SIGTERM)
            time.sleep(3)
            
            # Check if still running, force kill if needed
            try:
                os.kill(pid, 0)  # Check if still exists
                print_info("🔨 Force stopping...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            except ProcessLookupError:
                pass  # Already stopped
            
            # Clean up files
            self._cleanup_stale_files()
            
            # Clear tunnel URL from config
            self.config["tunnel_url"] = None
            self.config["last_stopped_at"] = datetime.now().isoformat()
            self._save_config()
            
            print_success("✅ Tunnel stopped successfully")
            log("Tunnel stopped successfully")
            
        except ProcessLookupError:
            print_info("ℹ️  Process was already stopped")
            self._cleanup_stale_files()
        except PermissionError:
            print_error("❌ Permission denied - unable to stop process")
        except Exception as e:
            log(f"Error stopping tunnel: {e}")
            print_error(f"❌ Error stopping tunnel: {e}")
            self._cleanup_stale_files()
        
        input("\n📱 Press Enter to continue...")
    
    def _restart_tunnel(self):
        """Restart the tunnel."""
        print_info("🔄 Restarting tunnel...")
        self._stop_tunnel()
        time.sleep(2)
        self._start_tunnel()
    
    # ==========================================
    # MONITORING & OUTPUT PROCESSING
    # ==========================================
    
    def _monitor_tunnel_output(self, process):
        """Monitor tunnel output for URLs and log everything."""
        try:
            log("Starting tunnel output monitoring")
            
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log everything to file
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(self.tunnel_logfile, 'a', encoding='utf-8') as f:
                        f.write(f"[{timestamp}] {line}\n")
                    
                    # Extract tunnel URLs using multiple patterns
                    self._extract_urls_from_line(line)
                    
        except Exception as e:
            log(f"Output monitoring error: {e}")
        finally:
            log("Tunnel output monitoring ended")
    
    def _extract_urls_from_line(self, line: str):
        """Extract tunnel URLs from playit output."""
        line_lower = line.lower()
        
        # Look for various URL patterns
        url_patterns = [
            r'tcp://[^\s]+',           # tcp://example.playit.gg:12345
            r'[^\s]*\.playit\.gg[^\s]*',  # anything.playit.gg
            r'joinmc\.link/[^\s]+',    # joinmc.link/abcd
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, line, re.IGNORECASE)
            for match in matches:
                # Clean up the match
                url = match.strip('.,!?;')
                
                if self._is_valid_tunnel_url(url):
                    log(f"Found tunnel URL: {url}")
                    
                    # Save to config
                    self.config["tunnel_url"] = url
                    self.config["url_found_at"] = datetime.now().isoformat()
                    self._save_config()
                    
                    return  # Stop after first valid URL
    
    def _is_valid_tunnel_url(self, url: str) -> bool:
        """Check if extracted URL looks like a valid tunnel URL."""
        url_lower = url.lower()
        
        # Must contain playit or joinmc and look like a proper URL
        if not any(domain in url_lower for domain in ['playit.gg', 'joinmc.link']):
            return False
        
        # Should not be a claim URL or other non-tunnel URL
        if any(word in url_lower for word in ['claim', 'dashboard', 'login', 'register']):
            return False
        
        # Should be reasonably short (tunnel URLs aren't super long)
        if len(url) > 100:
            return False
            
        return True
    
    # ==========================================
    # INFORMATION & TROUBLESHOOTING
    # ==========================================
    
    def _show_tunnel_info(self):
        """Show detailed tunnel information."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📊 Tunnel Information{UI.colors.RESET}\n")
        
        # Current status
        status = self.get_tunnel_status()
        if status and status['running']:
            print(f"{UI.colors.GREEN}🟢 Status: RUNNING{UI.colors.RESET}")
            print(f"Process ID: {status['pid']}")
            
            if status.get('url'):
                print(f"Tunnel URL: {UI.colors.CYAN}{status['url']}{UI.colors.RESET}")
                
                if "tcp://" in status['url']:
                    server_address = status['url'].replace("tcp://", "")
                    print(f"Server Address: {UI.colors.GREEN}{server_address}{UI.colors.RESET}")
                    print(f"📋 Give this address to your players!")
            else:
                print("Tunnel URL: Not detected yet (check logs)")
        else:
            print(f"{UI.colors.GRAY}⚪ Status: STOPPED{UI.colors.RESET}")
        
        print()
        
        # Configuration info
        print("📋 Configuration:")
        print(f"Setup Complete: {'Yes' if self._is_setup_complete() else 'No'}")
        print(f"Playit Installed: {'Yes' if self._check_playit_installed() else 'No'}")
        print(f"Server Port: {self._get_server_port()}")
        
        # Timestamps
        if self.config.get("setup_completed_at"):
            print(f"Setup Date: {self.config['setup_completed_at']}")
        if self.config.get("url_found_at"):
            print(f"URL Found: {self.config['url_found_at']}")
        
        print()
        
        # File locations
        print("📁 File Locations:")
        print(f"Config: {self.tunnel_config_file}")
        print(f"Logs: {self.tunnel_logfile}")
        print(f"PID File: {self.tunnel_pidfile}")
        
        input("\n📱 Press Enter to continue...")
    
    def _view_logs(self):
        """View tunnel logs with detailed information."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📋 Tunnel Logs{UI.colors.RESET}\n")
        
        try:
            if self.tunnel_logfile.exists():
                # Show file info
                stat = self.tunnel_logfile.stat()
                size_kb = stat.st_size / 1024
                modified = datetime.fromtimestamp(stat.st_mtime)
                
                print(f"Log file: {self.tunnel_logfile}")
                print(f"Size: {size_kb:.1f} KB")
                print(f"Modified: {modified}")
                print("-" * 60)
                
                # Read and show logs
                with open(self.tunnel_logfile, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                if lines:
                    # Show last 50 lines
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    
                    for line in recent_lines:
                        line = line.rstrip()
                        # Highlight URLs
                        if any(pattern in line.lower() for pattern in ['tcp://', 'playit.gg', 'joinmc.link']):
                            print(f"{UI.colors.CYAN}{line}{UI.colors.RESET}")
                        elif "error" in line.lower() or "failed" in line.lower():
                            print(f"{UI.colors.RED}{line}{UI.colors.RESET}")
                        else:
                            print(line)
                    
                    if len(lines) > 50:
                        print(f"\n... showing last 50 of {len(lines)} lines")
                else:
                    print("Log file is empty")
                    
            else:
                print("No log file found")
                print("Logs are created when tunnel starts")
                
        except Exception as e:
            print_error(f"Error reading logs: {e}")
            log(f"Log viewing error: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _show_setup_instructions(self):
        """Show manual setup instructions."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📋 Manual Setup Instructions{UI.colors.RESET}\n")
        
        print_info("If you prefer to set up playit.gg manually:")
        print()
        print("1. Open a terminal and run: playit")
        print("2. Follow the prompts to claim your agent")
        print("3. When asked for tunnel type, choose: TCP")
        print(f"4. When asked for local port, enter: {self._get_server_port()}")
        print("5. Copy the tunnel address it provides")
        print("6. Return to MSM and use 'Start tunnel'")
        print()
        print_info("After manual setup, MSM will be able to start/stop tunnels automatically.")
        
        input("\n📱 Press Enter to continue...")
    
    # ==========================================
    # TROUBLESHOOTING (Detailed for Development)
    # ==========================================
    
    def _show_installation_troubleshooting(self, failed_command: str, result):
        """Show detailed installation troubleshooting."""
        print()
        print_warning("🛠️  Installation Troubleshooting:")
        print()
        print(f"Failed command: {failed_command}")
        print(f"Exit code: {result.returncode}")
        print(f"Error output: {result.stderr}")
        print()
        print("Common solutions:")
        
        if "permission denied" in result.stderr.lower():
            print("• Try running with sudo/root permissions")
            print("• Check if you're in a proot-distro environment")
        
        if "connection" in result.stderr.lower() or "network" in result.stderr.lower():
            print("• Check internet connection: ping google.com")
            print("• Try running the command manually")
        
        if "gpg" in failed_command:
            print("• GPG might not be installed: apt install gnupg")
            print("• Try: gpg --version")
        
        print()
        print("Debug information:")
        print(f"• Command: {failed_command}")
        print(f"• Working directory: {os.getcwd()}")
        print(f"• User: {os.getenv('USER', 'unknown')}")
        print(f"• PATH: {os.getenv('PATH', 'unknown')}")
    
    def _show_verification_troubleshooting(self):
        """Show troubleshooting when installation completes but verification fails."""
        print()
        print_warning("🛠️  Installation Verification Failed:")
        print()
        print("Installation completed but 'playit version' doesn't work.")
        print()
        print("Troubleshooting steps:")
        print("1. Check if playit is in PATH:")
        print("   which playit")
        print("   ls -la /usr/bin/playit")  
        print("   ls -la /usr/local/bin/playit")
        print()
        print("2. Try running playit directly:")
        print("   playit --help")
        print("   playit version")
        print()
        print("3. Check installation logs:")
        print(f"   cat {self.tunnel_logfile}")
        print()
        print("4. Manual installation:")
        print("   curl -L https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-amd64 -o playit")
        print("   chmod +x playit")
        print("   sudo mv playit /usr/local/bin/")
    
    def _show_setup_troubleshooting(self, error: Exception):
        """Show troubleshooting for setup failures."""
        print()
        print_warning("🛠️  Setup Troubleshooting:")
        print()
        print(f"Setup failed with error: {error}")
        print()
        print("Common solutions:")
        print("• Make sure playit.gg is properly installed")
        print("• Check internet connection")
        print("• Try running 'playit' manually to see what happens")
        print("• Make sure you're following the interactive prompts")
        print()
        print("Manual setup:")
        print("1. Run: playit")
        print("2. Follow prompts to claim agent")
        print("3. Create TCP tunnel")
        print(f"4. Use port: {self._get_server_port()}")
        print("5. Return to MSM")
    
    def _show_startup_troubleshooting(self):
        """Show troubleshooting for tunnel startup failures."""
        print()
        print_warning("🛠️  Startup Troubleshooting:")
        print()
        print("Tunnel failed to start or stopped unexpectedly.")
        print()
        print("Debug steps:")
        print("1. Check if playit.gg is set up:")
        print("   playit --help")
        print()
        print("2. Try manual start:")
        print("   playit start")
        print()
        print("3. Check logs:")
        print(f"   tail -f {self.tunnel_logfile}")
        print()
        print("4. Verify setup:")
        print("   playit tunnels")
        print()
        print("5. Re-run setup if needed")
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def _get_server_port(self) -> int:
        """Auto-detect server port from MSM server configuration."""
        try:
            # Try to import and get current server info
            from server_manager import ServerManager
            current_server = ServerManager.get_current_server()
            
            if current_server:
                from config import ConfigManager
                server_config = ConfigManager.load_server_config(current_server)
                port = server_config.get("port", 25565)
                log(f"Auto-detected server port: {port}")
                return port
        except Exception as e:
            log(f"Could not auto-detect server port: {e}")
        
        # Default Minecraft port
        return 25565
    
    def _load_config(self) -> Dict[str, Any]:
        """Load tunnel configuration from JSON file."""
        default_config = {
            "is_setup_complete": False,
            "tunnel_url": None,
            "claim_url": None,
            "auto_detected_port": 25565,
            "setup_completed_at": None,
            "url_found_at": None,
            "last_started_at": None,
            "last_stopped_at": None
        }
        
        try:
            if self.tunnel_config_file.exists():
                with open(self.tunnel_config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Merge with defaults to handle new keys
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                
                return config
        except Exception as e:
            log(f"Error loading config: {e}")
        
        return default_config
    
    def _save_config(self):
        """Save tunnel configuration to JSON file."""
        try:
            # Ensure directory exists
            self.tunnel_config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.tunnel_config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            log("Config saved successfully")
        except Exception as e:
            log(f"Error saving config: {e}")
    
    def _cleanup_stale_processes(self):
        """Clean up stale processes and files on startup."""
        if self.tunnel_pidfile.exists():
            try:
                pid_content = self.tunnel_pidfile.read_text().strip()
                pid = int(pid_content.split('\n')[0])
                
                # Check if process exists
                os.kill(pid, 0)
                log(f"Found existing tunnel process: {pid}")
            except (ProcessLookupError, ValueError, PermissionError):
                log("Cleaning up stale PID file")
                self._cleanup_stale_files()
    
    def _cleanup_stale_files(self):
        """Clean up stale PID and related files."""
        try:
            self.tunnel_pidfile.unlink(missing_ok=True)
            log("Cleaned up stale files")
        except Exception as e:
            log(f"Error cleaning up files: {e}")

# For backward compatibility with existing MSM code
TunnelManager = TunnelManager
