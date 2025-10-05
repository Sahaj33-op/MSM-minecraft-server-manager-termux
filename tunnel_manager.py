#!/usr/bin/env python3
"""
tunnel_manager.py - Simple playit.gg tunnel management with one-time setup
"""

import subprocess
import time
import os
import threading
import json
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

@dataclass
class TunnelConfig:
    port: int
    pid: Optional[int] = None
    state: TunnelState = TunnelState.STOPPED
    url: Optional[str] = None
    is_setup_complete: bool = False

class PlayitTunnelManager:
    """Simple playit.gg tunnel management with one-time interactive setup."""
    
    def __init__(self):
        self.config_root = get_config_root()
        self.config_root.mkdir(parents=True, exist_ok=True)
        
        self.tunnel_config_file = self.config_root / "playit_config.json"
        self.tunnel_logfile = self.config_root / "playit.log"
        self.setup_complete_file = self.config_root / "playit_setup_complete"
        
        self.current_config: Optional[TunnelConfig] = None
        self._load_config()
    
    def tunneling_menu(self):
        """Simple tunneling menu."""
        while True:
            clear_screen()
            print_header("1.2.0")
            print(f"{UI.colors.BOLD}Playit.gg Tunnel Manager{UI.colors.RESET}\n")
            
            # Check if playit is installed
            if not self._check_playit_installed():
                print_error("❌ playit.gg is not installed")
                print("Please install playit.gg first:")
                print("1. Install playit.gg")
                print("0. Back")
                
                choice = input("\nSelect option: ").strip()
                if choice == "1":
                    self._install_playit()
                elif choice == "0":
                    break
                continue
            
            # Show current status
            if self.current_config:
                status_color = UI.colors.GREEN if self.current_config.state == TunnelState.RUNNING else UI.colors.RED
                print(f"{status_color}● {self.current_config.state.value.upper()}{UI.colors.RESET} - playit.gg")
                if self.current_config.url:
                    print(f"🌐 Tunnel URL: {UI.colors.CYAN}{self.current_config.url}{UI.colors.RESET}")
                print()
            
            # Check if setup is complete
            setup_complete = self._is_setup_complete()
            
            print("Available options:")
            
            if not setup_complete:
                print("1. ⚙️  First-time setup (Interactive)")
                print("2. 📋 View setup instructions")
            else:
                print("1. 🚀 Start tunnel")
                if self.current_config and self.current_config.state == TunnelState.RUNNING:
                    print("2. ⏹️  Stop tunnel")
                    print("3. 🔄 Restart tunnel")
                    print("4. 📋 View logs")
                print("5. 🔧 Re-run setup")
            
            print("0. Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                if not setup_complete:
                    self._run_interactive_setup()
                else:
                    self._start_tunnel()
            elif choice == "2":
                if not setup_complete:
                    self._show_setup_instructions()
                elif self.current_config and self.current_config.state == TunnelState.RUNNING:
                    self._stop_tunnel()
            elif choice == "3" and setup_complete:
                self._restart_tunnel()
            elif choice == "4" and setup_complete:
                self._view_logs()
            elif choice == "5" and setup_complete:
                self._run_interactive_setup()
            elif choice == "0":
                break
            else:
                print_error("Invalid option")
                input("Press Enter to continue...")
    
    def _is_setup_complete(self) -> bool:
        """Check if initial setup has been completed."""
        return self.setup_complete_file.exists()
    
    def _mark_setup_complete(self):
        """Mark setup as complete."""
        self.setup_complete_file.touch()
        if self.current_config:
            self.current_config.is_setup_complete = True
            self._save_config()
    
    def _run_interactive_setup(self):
        """Run playit.gg interactive setup - one time only."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}🔧 Playit.gg Interactive Setup{UI.colors.RESET}\n")
        
        print_info("This will guide you through setting up your playit.gg tunnel.")
        print_info("You only need to do this once!")
        print_info("")
        print_info("During setup, you will:")
        print_info("1. 🔗 Claim your agent (creates your account if needed)")
        print_info("2. 🎯 Create a tunnel for your Minecraft server")
        print_info(f"3. 🔌 Configure it for port {self._get_server_port()}")
        print_info("")
        print_warning("⚠️  This will run interactively - follow the on-screen prompts")
        print_warning("⚠️  Keep this terminal window open during setup")
        print_info("")
        
        confirm = input("🚀 Start interactive setup? (y/N): ").strip().lower()
        if confirm != 'y':
            return
        
        try:
            print_info("🔄 Starting playit.gg interactive setup...")
            print_info("=" * 60)
            
            # Run playit without arguments for interactive setup
            result = subprocess.run(["playit"], 
                                  stdin=None,  # Allow interactive input
                                  stdout=None,  # Show output to user
                                  stderr=None,  # Show errors to user
                                  timeout=600)  # 10 minute timeout
            
            print_info("=" * 60)
            
            if result.returncode == 0:
                print_success("✅ Setup completed successfully!")
                self._mark_setup_complete()
                
                # Test if we can start the tunnel
                print_info("🧪 Testing tunnel startup...")
                if self._test_tunnel_start():
                    print_success("✅ Tunnel is working! You can now use the 'Start tunnel' option.")
                else:
                    print_warning("⚠️  Setup completed but tunnel test failed.")
                    print_info("💡 Try running setup again or check the logs.")
            else:
                print_warning("⚠️  Setup exited. You may need to run it again.")
                print_info("💡 Make sure to complete all the setup steps.")
                
        except subprocess.TimeoutExpired:
            print_warning("⚠️  Setup timed out after 10 minutes.")
            print_info("💡 You can run setup again if needed.")
        except KeyboardInterrupt:
            print_info("⚠️  Setup interrupted by user.")
        except Exception as e:
            print_error(f"❌ Error during setup: {e}")
            log(f"Interactive setup error: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _test_tunnel_start(self) -> bool:
        """Test if tunnel can start (quick test)."""
        try:
            # Try to start tunnel in background
            process = subprocess.Popen(
                ["playit", "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait 5 seconds
            time.sleep(5)
            
            # Check if still running
            if process.poll() is None:
                # It's running, kill it
                process.terminate()
                process.wait(timeout=5)
                return True
            else:
                return False
                
        except Exception as e:
            log(f"Tunnel test error: {e}")
            return False
    
    def _start_tunnel(self):
        """Start the tunnel (after setup is complete)."""
        if not self._is_setup_complete():
            print_error("❌ Please complete setup first!")
            input("Press Enter to continue...")
            return
        
        if self.current_config and self.current_config.state == TunnelState.RUNNING:
            print_warning("⚠️  Tunnel is already running!")
            input("Press Enter to continue...")
            return
        
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}🚀 Starting Playit.gg Tunnel{UI.colors.RESET}\n")
        
        try:
            port = self._get_server_port()
            print_info(f"🔌 Server port: {port}")
            print_info("🔄 Starting tunnel...")
            
            # Start tunnel in background
            process = subprocess.Popen(
                ["playit", "start"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Create/update config
            self.current_config = TunnelConfig(
                port=port,
                pid=process.pid,
                state=TunnelState.RUNNING,
                is_setup_complete=True
            )
            
            print_success(f"✅ Tunnel started! (PID: {process.pid})")
            
            # Start monitoring in background
            monitor_thread = threading.Thread(
                target=self._monitor_tunnel_output,
                args=(process,),
                daemon=True
            )
            monitor_thread.start()
            
            # Save config and wait a moment
            self._save_config()
            time.sleep(3)
            
            # Check if still running
            if process.poll() is None:
                print_success("🎉 Tunnel is running!")
                print_info("💡 Check logs to see your tunnel URL")
                print_info("💡 You can now connect to your server using the tunnel address")
            else:
                print_error("❌ Tunnel stopped unexpectedly")
                self.current_config.state = TunnelState.FAILED
                self._save_config()
                
        except Exception as e:
            log(f"Error starting tunnel: {e}")
            print_error(f"❌ Failed to start tunnel: {e}")
            if self.current_config:
                self.current_config.state = TunnelState.FAILED
                self._save_config()
        
        input("\n📱 Press Enter to continue...")
    
    def _stop_tunnel(self):
        """Stop the running tunnel."""
        if not self.current_config or not self.current_config.pid:
            print_warning("⚠️  No tunnel to stop")
            input("Press Enter to continue...")
            return
        
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}⏹️  Stopping Tunnel{UI.colors.RESET}\n")
        
        try:
            print_info(f"🔄 Stopping tunnel (PID: {self.current_config.pid})...")
            
            # Terminate process
            os.kill(self.current_config.pid, 15)  # SIGTERM
            time.sleep(3)
            
            # Check if still running, force kill if needed
            try:
                os.kill(self.current_config.pid, 0)
                print_info("🔨 Force stopping...")
                os.kill(self.current_config.pid, 9)  # SIGKILL
            except ProcessLookupError:
                pass  # Already stopped
            
            # Update config
            self.current_config.state = TunnelState.STOPPED
            self.current_config.pid = None
            self.current_config.url = None
            self._save_config()
            
            print_success("✅ Tunnel stopped")
            
        except Exception as e:
            log(f"Error stopping tunnel: {e}")
            print_error(f"❌ Error stopping tunnel: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _restart_tunnel(self):
        """Restart the tunnel."""
        print_info("🔄 Restarting tunnel...")
        self._stop_tunnel()
        time.sleep(2)
        self._start_tunnel()
    
    def _monitor_tunnel_output(self, process):
        """Monitor tunnel output for URLs and log everything."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                
                line = line.strip()
                if line:
                    # Log everything
                    with open(self.tunnel_logfile, 'a') as f:
                        f.write(f"[{datetime.now()}] {line}\n")
                    
                    # Extract tunnel URLs
                    if any(keyword in line.lower() for keyword in ['tcp://', 'joinmc.link', 'tunnel']):
                        # Look for URL patterns
                        words = line.split()
                        for word in words:
                            if 'tcp://' in word or 'joinmc.link' in word:
                                if self.current_config:
                                    self.current_config.url = word
                                    self._save_config()
                                    log(f"Found tunnel URL: {word}")
                                break
                                
        except Exception as e:
            log(f"Output monitoring error: {e}")
    
    def _view_logs(self):
        """View tunnel logs."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📋 Tunnel Logs{UI.colors.RESET}\n")
        
        try:
            if self.tunnel_logfile.exists():
                with open(self.tunnel_logfile, 'r') as f:
                    lines = f.readlines()
                
                # Show last 30 lines
                recent_lines = lines[-30:] if len(lines) > 30 else lines
                
                if recent_lines:
                    for line in recent_lines:
                        print(line.strip())
                else:
                    print_info("No logs available yet")
            else:
                print_info("No log file found")
                
        except Exception as e:
            print_error(f"Error reading logs: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _show_setup_instructions(self):
        """Show manual setup instructions."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📋 Setup Instructions{UI.colors.RESET}\n")
        
        print_info("If you prefer to set up manually:")
        print_info("")
        print_info("1. Run: playit")
        print_info("2. Follow the prompts to claim your agent")
        print_info("3. Create a tunnel for TCP")
        print_info(f"4. Set local port to: {self._get_server_port()}")
        print_info("5. Copy the tunnel address for your players")
        print_info("")
        print_info("After manual setup, return here and use 'Start tunnel'")
        
        input("\n📱 Press Enter to continue...")
    
    def _check_playit_installed(self) -> bool:
        """Check if playit is installed."""
        try:
            result = subprocess.run(["playit", "version"], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def _install_playit(self):
        """Install playit.gg using your proven method."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}📦 Installing Playit.gg{UI.colors.RESET}\n")
        
        try:
            commands = [
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/playit.gpg",
                'echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" > /etc/apt/sources.list.d/playit-cloud.list',
                "apt update",
                "apt install playit -y"
            ]
            
            for i, cmd in enumerate(commands, 1):
                print_info(f"📦 Step {i}/{len(commands)}: Running installation command...")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    print_error(f"❌ Installation step {i} failed")
                    print_error(f"Error: {result.stderr}")
                    input("Press Enter to continue...")
                    return
            
            if self._check_playit_installed():
                print_success("✅ Playit.gg installed successfully!")
            else:
                print_error("❌ Installation completed but playit command not working")
                
        except Exception as e:
            print_error(f"❌ Installation error: {e}")
        
        input("\n📱 Press Enter to continue...")
    
    def _get_server_port(self) -> int:
        """Get server port."""
        try:
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
                "port": self.current_config.port,
                "pid": self.current_config.pid,
                "state": self.current_config.state.value,
                "url": self.current_config.url,
                "is_setup_complete": self.current_config.is_setup_complete
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
                    port=data["port"],
                    pid=data.get("pid"),
                    state=TunnelState(data.get("state", "stopped")),
                    url=data.get("url"),
                    is_setup_complete=data.get("is_setup_complete", False)
                )
                
                # Verify process is still running
                if self.current_config.pid and self.current_config.state == TunnelState.RUNNING:
                    try:
                        os.kill(self.current_config.pid, 0)
                    except ProcessLookupError:
                        self.current_config.state = TunnelState.STOPPED
                        self.current_config.pid = None
                        self._save_config()
                        
        except Exception as e:
            log(f"Error loading config: {e}")

# For backward compatibility
TunnelManager = PlayitTunnelManager