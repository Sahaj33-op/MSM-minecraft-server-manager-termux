#!/usr/bin/env python3
"""
tunnel_manager.py - ULTRA-ROBUST tunneling with enterprise-grade resilience
"""

import subprocess
import time
import os
import signal
import threading
import json
import hashlib
import shutil
import select
import psutil
import socket
import platform
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, cast
from dataclasses import dataclass, asdict, field
from enum import Enum
import re
import logging
from contextlib import contextmanager
import asyncio
import concurrent.futures

# Conditional import for fcntl (Unix-only)
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

from config import CredentialsManager, get_config_root
from ui import UI, clear_screen, print_header, print_info, print_success, print_warning, print_error
from utils import log, run_command

class TunnelState(Enum):
    """Tunnel process states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNHEALTHY = "unhealthy"

class TunnelService(Enum):
    """Supported tunnel services."""
    PLAYIT = "playit.gg"
    NGROK = "ngrok"
    CLOUDFLARED = "cloudflared"
    PINGGY = "pinggy"

@dataclass
class TunnelMetrics:
    """Tunnel performance and health metrics."""
    start_time: datetime
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    last_health_check: Optional[datetime] = None
    uptime_seconds: float = 0.0
    bytes_transferred: int = 0
    restart_count: int = 0
    last_error: Optional[str] = None
    response_times: List[float] = field(default_factory=list)
    
@dataclass
class TunnelConfig:
    """Tunnel configuration and state."""
    service: TunnelService
    port: int
    pid: Optional[int] = None
    state: TunnelState = TunnelState.STOPPED
    url: Optional[str] = None
    claim_url: Optional[str] = None
    config_hash: Optional[str] = None
    last_restart: Optional[datetime] = None
    metrics: Optional[TunnelMetrics] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = TunnelMetrics(start_time=datetime.now())

class TunnelHealthMonitor:
    """Advanced health monitoring for tunnel connections."""
    
    def __init__(self, tunnel_manager):
        self.tunnel_manager = tunnel_manager
        self.monitoring = False
        self.health_thread = None
        self.check_interval = 30  # seconds
        self.failure_threshold = 3
        self.consecutive_failures = 0
        
    def start_monitoring(self):
        """Start health monitoring thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.health_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_thread.start()
        log("Health monitoring started")
        
    def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring = False
        if self.health_thread:
            self.health_thread.join(timeout=5)
        log("Health monitoring stopped")
        
    def _health_check_loop(self):
        """Main health monitoring loop."""
        while self.monitoring:
            try:
                tunnel_config = self.tunnel_manager.get_tunnel_config()
                if tunnel_config and tunnel_config.state == TunnelState.RUNNING:
                    is_healthy = self._perform_health_check(tunnel_config)
                    
                    if is_healthy:
                        self.consecutive_failures = 0
                        tunnel_config.state = TunnelState.RUNNING
                    else:
                        self.consecutive_failures += 1
                        log(f"Health check failed ({self.consecutive_failures}/{self.failure_threshold})")
                        
                        if self.consecutive_failures >= self.failure_threshold:
                            log("Tunnel unhealthy, attempting recovery")
                            tunnel_config.state = TunnelState.UNHEALTHY
                            self.tunnel_manager._attempt_recovery(tunnel_config)
                            
                    tunnel_config.metrics.last_health_check = datetime.now()
                    self.tunnel_manager._save_tunnel_config(tunnel_config)
                    
            except Exception as e:
                log(f"Health monitoring error: {e}")
                
            time.sleep(self.check_interval)
            
    def _perform_health_check(self, tunnel_config: TunnelConfig) -> bool:
        """Perform comprehensive health check."""
        try:
            # Check if process is still running
            if tunnel_config.pid:
                try:
                    os.kill(tunnel_config.pid, 0)
                except ProcessLookupError:
                    log("Process not found during health check")
                    return False
                    
            # Check if URL is still accessible (for HTTP tunnels)
            if tunnel_config.url and tunnel_config.service in [TunnelService.CLOUDFLARED]:
                return self._check_url_health(tunnel_config.url)
                
            # Check if port is still being tunneled (for TCP tunnels)
            if tunnel_config.service in [TunnelService.PLAYIT, TunnelService.NGROK, TunnelService.PINGGY]:
                return self._check_port_health(tunnel_config.port)
                
            return True
            
        except Exception as e:
            log(f"Health check error for {tunnel_config.service.value}: {e}")
            return False
            
    def _check_url_health(self, url: str) -> bool:
        """Check if HTTP tunnel URL is accessible."""
        try:
            import urllib.request
            import urllib.error
            
            start_time = time.time()
            request = urllib.request.Request(url, method='HEAD')
            response = urllib.request.urlopen(request, timeout=10)
            response_time = time.time() - start_time
            
            # Record response time
            tunnel_config = self.tunnel_manager.get_tunnel_config()
            if tunnel_config:
                tunnel_config.metrics.response_times.append(response_time)
                # Keep only last 100 measurements
                tunnel_config.metrics.response_times = tunnel_config.metrics.response_times[-100:]
                
            return response.status < 400
            
        except Exception as e:
            log(f"URL health check failed: {e}")
            return False
            
    def _check_port_health(self, port: int) -> bool:
        """Check if local port is accessible."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except Exception:
            return False

class RobustTunnelManager:
    """Ultra-robust tunnel management with enterprise-grade features."""
    
    def __init__(self):
        self.config_root = get_config_root()
        self.bin_dir = self.config_root / "bin"
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        
        # Enhanced file paths
        self.tunnel_config_file = self.config_root / "tunnel_config.json"
        self.tunnel_lockfile = self.config_root / "tunnel.lock"
        self.tunnel_logfile = self.config_root / "tunnel.log"
        self.tunnel_metrics_file = self.config_root / "tunnel_metrics.json"
        self.recovery_log = self.config_root / "recovery.log"
        
        # State management
        self.current_config: Optional[TunnelConfig] = None
        self.health_monitor = TunnelHealthMonitor(self)
        
        # Advanced configuration
        self.max_restart_attempts = 5
        self.restart_delay_base = 2  # exponential backoff base
        self.max_restart_delay = 300  # 5 minutes max delay
        self.config_check_interval = 5  # seconds
        
        # Service definitions with enhanced patterns
        self.service_patterns = {
            TunnelService.PLAYIT: [
                r"(tcp://[a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"([a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"([a-zA-Z0-9.-]+\.joinmc\.link)",
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg:\d+)",
            ],
            TunnelService.NGROK: [
                r"(tcp://[0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:\d+)",
                r"([0-9]+\.tcp\.[a-z0-9]+\.ngrok\.io:\d+)",
                r"(https?://[a-zA-Z0-9.-]+\.ngrok\.io:\d+)",
            ],
            TunnelService.CLOUDFLARED: [
                r"(https://[a-zA-Z0-9-]+\.trycloudflare\.com)",
                r"(https?://[a-zA-Z0-9.-]+\.trycloudflare\.com)",
            ],
            TunnelService.PINGGY: [
                r"(tcp://[a-zA-Z0-9.-]+\.tcp\.pinggy\.io:\d+)",
                r"([a-zA-Z0-9.-]+\.tcp\.pinggy\.io:\d+)",
                r"(tcp://[a-zA-Z0-9]+\.a\.pinggy\.io:\d+)",
                r"([a-zA-Z0-9]+\.a\.pinggy\.io:\d+)",
            ]
        }
        
        # Load existing configuration
        self._load_tunnel_config()
        
        # Start health monitoring if tunnel is running
        if self.current_config and self.current_config.state == TunnelState.RUNNING:
            self.health_monitor.start_monitoring()
    
    @contextmanager
    def _tunnel_lock(self):
        """Ensure only one tunnel operation at a time."""
        lock_acquired = False
        lock_file = None
        
        try:
            # Use file locking on Unix systems, simple file existence check on Windows
            if FCNTL_AVAILABLE:
                import fcntl
                lock_file = open(self.tunnel_lockfile, 'w')
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
            else:
                # On Windows, use a simple file existence check
                if self.tunnel_lockfile.exists():
                    # Check if the lock file is stale (older than 1 minute)
                    import time
                    if time.time() - self.tunnel_lockfile.stat().st_mtime < 60:
                        raise RuntimeError("Another tunnel operation is in progress")
                # Create lock file
                self.tunnel_lockfile.touch()
                lock_acquired = True
                
            yield
        except BlockingIOError:
            raise RuntimeError("Another tunnel operation is in progress")
        finally:
            if lock_acquired:
                if FCNTL_AVAILABLE and lock_file:
                    import fcntl
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                else:
                    # On Windows, remove the lock file
                    self.tunnel_lockfile.unlink(missing_ok=True)
    
    def tunneling_menu(self):
        """Enhanced tunneling manager menu with detailed status."""
        while True:
            clear_screen()
            print_header("1.2.0")
            print(f"{UI.colors.BOLD}Ultra-Robust Tunneling Manager{UI.colors.RESET}\n")
            
            # Show comprehensive tunnel status
            self._display_tunnel_status()
            
            print("\nAvailable services:")
            print("1. playit.gg (recommended - easiest)")
            print("2. ngrok (most popular)")
            print("3. cloudflared (quick tunnel - no login)")
            print("4. pinggy.io (SSH-based - instant)")
            
            if self.current_config and self.current_config.state != TunnelState.STOPPED:
                print("5. Stop active tunnel")
                print("6. Restart tunnel")
                print("7. Force recovery")
                print("8. View metrics")
                print("9. Export diagnostics")
            
            print("0. Back")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.setup_service(TunnelService.PLAYIT)
            elif choice == "2":
                self.setup_service(TunnelService.NGROK)
            elif choice == "3":
                self.setup_service(TunnelService.CLOUDFLARED)
            elif choice == "4":
                self.setup_service(TunnelService.PINGGY)
            elif choice == "5" and self.current_config:
                self.stop_tunnel()
            elif choice == "6" and self.current_config:
                self.restart_tunnel()
            elif choice == "7" and self.current_config:
                self._force_recovery()
            elif choice == "8" and self.current_config:
                self._show_metrics()
            elif choice == "9" and self.current_config:
                self._export_diagnostics()
            elif choice == "0":
                break
            else:
                if choice != "0":
                    print_error("Invalid option")
                input("\nPress Enter to continue...")
    
    def _display_tunnel_status(self):
        """Display comprehensive tunnel status information."""
        if not self.current_config:
            print(f"{UI.colors.GRAY}No active tunnel{UI.colors.RESET}\n")
            return
            
        config = self.current_config
        
        # Status color based on state
        status_colors = {
            TunnelState.RUNNING: UI.colors.GREEN,
            TunnelState.STARTING: UI.colors.YELLOW,
            TunnelState.STOPPING: UI.colors.YELLOW,
            TunnelState.FAILED: UI.colors.RED,
            TunnelState.UNHEALTHY: UI.colors.RED,
            TunnelState.RECOVERING: UI.colors.YELLOW,
            TunnelState.STOPPED: UI.colors.GRAY,
        }
        
        color = status_colors.get(config.state, UI.colors.RESET)
        print(f"{color}● {config.state.value.upper()} Tunnel:{UI.colors.RESET}")
        print(f"  Service: {config.service.value}")
        print(f"  Port: {config.port}")
        
        if config.pid:
            print(f"  PID: {config.pid}")
            
        if config.url:
            print(f"  URL: {UI.colors.CYAN}{config.url}{UI.colors.RESET}")
            
        if config.claim_url:
            print(f"  Claim: {UI.colors.CYAN}{config.claim_url}{UI.colors.RESET}")
            
        # Show metrics if available
        if config.metrics:
            metrics = config.metrics
            uptime = datetime.now() - metrics.start_time
            print(f"  Uptime: {self._format_timedelta(uptime)}")
            print(f"  Restarts: {metrics.restart_count}")
            
            if metrics.last_health_check:
                last_check = datetime.now() - metrics.last_health_check
                print(f"  Last Health Check: {self._format_timedelta(last_check)} ago")
                
            if metrics.response_times:
                avg_response = sum(metrics.response_times) / len(metrics.response_times)
                print(f"  Avg Response Time: {avg_response:.2f}s")
        
        print()  # Empty line for spacing
    
    def setup_service(self, service: TunnelService):
        """Setup and start a specific tunnel service."""
        try:
            with self._tunnel_lock():
                self._setup_service_internal(service)
        except RuntimeError as e:
            print_error(str(e))
            input("\nPress Enter to continue...")
    
    def _setup_service_internal(self, service: TunnelService):
        """Internal service setup with proper error handling."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}{service.value} Setup{UI.colors.RESET}\n")
        
        # Stop existing tunnel if running
        if self.current_config and self.current_config.state != TunnelState.STOPPED:
            print_warning("Stopping existing tunnel...")
            self.stop_tunnel(show_messages=False)
            
        # Check installation
        if not self._check_service_installed(service):
            if not self._install_service(service):
                return
                
        # Get server port
        port = self._get_server_port()
        
        # Create new configuration
        self.current_config = TunnelConfig(
            service=service,
            port=port,
            state=TunnelState.STARTING,
            metrics=TunnelMetrics(start_time=datetime.now())
        )
        
        # Start the tunnel with retry logic
        success = self._start_tunnel_with_retry()
        
        if success:
            self.health_monitor.start_monitoring()
            print_success(f"✅ {service.value} tunnel started successfully!")
            print_info("Monitor status in the tunneling menu")
        else:
            print_error(f"Failed to start {service.value} tunnel")
            self.current_config.state = TunnelState.FAILED
            
        self._save_tunnel_config()
        input("\nPress Enter to continue...")
    
    def _start_tunnel_with_retry(self) -> bool:
        """Start tunnel with exponential backoff retry logic."""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    delay = min(self.restart_delay_base ** attempt, self.max_restart_delay)
                    print_info(f"Retry attempt {attempt + 1}/{max_attempts} in {delay}s...")
                    time.sleep(delay)
                
                command = self._build_tunnel_command()
                if not command:
                    return False
                    
                # Start process with enhanced monitoring
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid  # Create process group
                )
                
                # Check if we have a current config before accessing attributes
                if not self.current_config:
                    self._cleanup_failed_process(process)
                    return False
                    
                self.current_config.pid = process.pid
                self.current_config.state = TunnelState.STARTING
                if self.current_config and self.current_config.metrics:
                    self.current_config.metrics.connection_attempts += 1
                
                # Start enhanced output monitoring
                monitor_thread = threading.Thread(
                    target=self._enhanced_output_monitor,
                    args=(process,),
                    daemon=True
                )
                monitor_thread.start()
                
                # Wait for tunnel to establish (with timeout)
                if self._wait_for_tunnel_ready(timeout=30):
                    self.current_config.state = TunnelState.RUNNING
                    if self.current_config and self.current_config.metrics:
                        self.current_config.metrics.successful_connections += 1
                    log(f"Tunnel started successfully on attempt {attempt + 1}")
                    return True
                else:
                    print_warning("Tunnel startup timeout, retrying...")
                    self._cleanup_failed_process(process)
                    
            except Exception as e:
                log(f"Tunnel start attempt {attempt + 1} failed: {e}")
                # Check if we have a current config before accessing attributes
                if self.current_config:
                    if self.current_config and self.current_config.metrics:
                        self.current_config.metrics.failed_connections += 1
                        self.current_config.metrics.last_error = str(e)
                
        # Check if we have a current config before accessing attributes
        if self.current_config:
            self.current_config.state = TunnelState.FAILED
        return False
    
    def _enhanced_output_monitor(self, process: subprocess.Popen):
        """Enhanced output monitoring with pattern matching and logging."""
        # Check if we have a current config before accessing attributes
        if not self.current_config:
            return
            
        patterns = self.service_patterns.get(self.current_config.service, [])
        claim_patterns = [
            r"(https?://[a-zA-Z0-9.-]+\.playit\.gg/claim/[a-zA-Z0-9-]+)",
            r"(https?://[a-zA-Z0-9.-]+/claim/[a-zA-Z0-9-]+)"
        ]
        
        try:
            while True:
                # Use select for non-blocking read with timeout
                if process.stdout:
                    ready, _, _ = select.select([process.stdout], [], [], 1.0)
                    
                    if ready:
                        line = process.stdout.readline()
                        if not line:
                            break
                            
                        # Log all output
                        self._append_to_log(line.strip())
                        
                        # Extract URLs
                        self._extract_urls_from_line(line, patterns, claim_patterns)
                
                # Check if process is still running
                if process.poll() is not None:
                    break
                    
        except Exception as e:
            log(f"Output monitoring error: {e}")
        finally:
            # Ensure process cleanup
            if process.poll() is None:
                try:
                    process.terminate()
                except:
                    pass
    
    def _extract_urls_from_line(self, line: str, patterns: List[str], claim_patterns: List[str]):
        """Extract tunnel URLs and claim URLs from output line."""
        # Check if we have a current config
        if not self.current_config:
            return
            
        # Check for claim URLs first (playit.gg specific)
        for pattern in claim_patterns:
            match = re.search(pattern, line)
            if match:
                claim_url = match.group(1)
                self.current_config.claim_url = claim_url
                log(f"Claim URL found: {claim_url}")
                self._save_tunnel_config()
                
        # Check for tunnel URLs
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                url = match.group(1)
                
                # Normalize URL format
                url = self._normalize_tunnel_url(url)
                
                if url != self.current_config.url:
                    self.current_config.url = url
                    log(f"Tunnel URL found: {url}")
                    self._save_tunnel_config()
                    break

    def _normalize_tunnel_url(self, url: str) -> str:
        """Normalize tunnel URL format based on service."""
        if not self.current_config:
            return url
            
        service = self.current_config.service
        
        # Ensure proper protocol prefix
        if service in [TunnelService.PLAYIT, TunnelService.NGROK, TunnelService.PINGGY]:
            if not url.startswith(("tcp://", "https://")):
                # Check if it's a joinmc.link domain
                if ".joinmc.link" in url:
                    url = "https://" + url
                else:
                    url = "tcp://" + url
        elif service == TunnelService.CLOUDFLARED and not url.startswith("https://"):
            url = "https://" + url
            
        return url
    
    def _wait_for_tunnel_ready(self, timeout: int = 30) -> bool:
        """Wait for tunnel to be ready with timeout."""
        # Check if we have a current config
        if not self.current_config:
            return False
            
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if we have a URL
            if self.current_config.url:
                return True
                
            # For some services, just having the process running is enough
            if (self.current_config.service == TunnelService.PINGGY and 
                self.current_config.pid and 
                self._is_process_running(self.current_config.pid)):
                return True
                
            time.sleep(1)
            
        return False
    
    def stop_tunnel(self, show_messages: bool = True):
        """Stop the currently running tunnel with proper cleanup."""
        if not self.current_config:
            if show_messages:
                print_warning("No tunnel is running")
            return
            
        try:
            with self._tunnel_lock():
                self._stop_tunnel_internal(show_messages)
        except RuntimeError as e:
            if show_messages:
                print_error(str(e))
    
    def _stop_tunnel_internal(self, show_messages: bool = True):
        """Internal tunnel stopping logic."""
        # Check if we have a current config
        if not self.current_config:
            return
            
        if show_messages:
            print_info(f"Stopping {self.current_config.service.value} tunnel...")
            
        self.current_config.state = TunnelState.STOPPING
        self.health_monitor.stop_monitoring()
        
        # Stop process gracefully
        if self.current_config.pid:
            self._stop_process_gracefully(self.current_config.pid)
            
        # Clean up state
        self.current_config.state = TunnelState.STOPPED
        self.current_config.pid = None
        self.current_config.url = None
        self.current_config.claim_url = None
        
        self._save_tunnel_config()
        
        if show_messages:
            print_success("✅ Tunnel stopped successfully")
    
    def restart_tunnel(self):
        """Restart the current tunnel with enhanced error handling."""
        # Check if we have a current config
        if not self.current_config:
            print_warning("No tunnel to restart")
            return
            
        print_info("Restarting tunnel...")
        
        # Increment restart count
        if self.current_config and self.current_config.metrics:
            self.current_config.metrics.restart_count += 1
        self.current_config.last_restart = datetime.now()
        
        # Stop current tunnel
        self.stop_tunnel(show_messages=False)
        
        # Wait a bit before restarting
        time.sleep(2)
        
        # Start with retry logic
        success = self._start_tunnel_with_retry()
        
        if success:
            self.health_monitor.start_monitoring()
            print_success("✅ Tunnel restarted successfully!")
        else:
            print_error("Failed to restart tunnel")
            
        self._save_tunnel_config()
        input("\nPress Enter to continue...")
    
    def _attempt_recovery(self, tunnel_config: TunnelConfig):
        """Attempt to recover an unhealthy tunnel."""
        log("Attempting tunnel recovery...")
        tunnel_config.state = TunnelState.RECOVERING
        
        # Log recovery attempt
        recovery_entry = {
            "timestamp": datetime.now().isoformat(),
            "service": tunnel_config.service.value,
            "reason": "health_check_failure",
            "restart_count": tunnel_config.metrics.restart_count if tunnel_config.metrics else 0
        }
        self._log_recovery_attempt(recovery_entry)
        
        # Check if we've exceeded max restart attempts
        if tunnel_config.metrics and tunnel_config.metrics.restart_count >= self.max_restart_attempts:
            log(f"Max restart attempts ({self.max_restart_attempts}) exceeded")
            tunnel_config.state = TunnelState.FAILED
            return
            
        # Attempt restart
        self.restart_tunnel()
    
    def _force_recovery(self):
        """Force recovery of the current tunnel."""
        if not self.current_config:
            print_warning("No tunnel to recover")
            return
            
        print_info("Forcing tunnel recovery...")
        
        # Reset failure counters
        self.health_monitor.consecutive_failures = 0
        if self.current_config and self.current_config.metrics:
            self.current_config.metrics.restart_count = 0
        
        # Attempt restart
        self.restart_tunnel()
    
    # ... [Additional methods for installation, metrics, diagnostics, etc.]
    
    def _check_service_installed(self, service: TunnelService) -> bool:
        """Check if a tunnel service is installed."""
        commands = {
            TunnelService.PLAYIT: ["playit", "--version"],
            TunnelService.NGROK: ["ngrok", "--version"],
            TunnelService.CLOUDFLARED: ["cloudflared", "--version"],
            TunnelService.PINGGY: ["ssh", "-V"]
        }
        
        try:
            result = subprocess.run(
                commands[service],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _get_server_port(self) -> int:
        """Get the current server port."""
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

    def _install_service(self, service: TunnelService) -> bool:
        """Install a tunnel service with comprehensive error handling."""
        print_info(f"Installing {service.value}...")
        
        install_methods = {
            TunnelService.PLAYIT: self._install_playit,
            TunnelService.NGROK: self._install_ngrok,
            TunnelService.CLOUDFLARED: self._install_cloudflared,
            TunnelService.PINGGY: self._install_pinggy
        }
        
        try:
            return install_methods[service]()
        except Exception as e:
            log(f"Installation failed for {service.value}: {e}")
            print_error(f"Installation failed: {e}")
            return False
    
    def _install_playit(self) -> bool:
        """Install playit.gg with multiple fallback methods."""
        install_attempts = [
            self._install_playit_curl,
            self._install_playit_wget,
            self._install_playit_package_manager
        ]
        
        for attempt_num, install_method in enumerate(install_attempts, 1):
            try:
                print_info(f"Installation attempt {attempt_num}/{len(install_attempts)}...")
                if install_method():
                    return True
            except Exception as e:
                log(f"Playit installation method {attempt_num} failed: {e}")
                
        print_error("All playit installation methods failed")
        return False
    
    def _install_playit_curl(self) -> bool:
        """Install playit using curl (primary method)."""
        try:
            # Try direct binary download first (more reliable)
            arch = self._detect_architecture()
            base_url = "https://github.com/playit-cloud/playit-agent/releases/latest/download"
            
            binary_name = f"playit-linux_{arch}"
            download_url = f"{base_url}/{binary_name}"
            target_path = self.bin_dir / "playit"
            
            # Download binary
            result = subprocess.run([
                "curl", "-L", "-o", str(target_path), download_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"Download failed: {result.stderr}")
                
            # Make executable
            target_path.chmod(0o755)
            
            # Add to PATH if not already there
            self._add_to_path(str(self.bin_dir))
            
            return target_path.exists() and target_path.stat().st_size > 0
        except Exception as e:
            log(f"Direct binary download failed: {e}")
            
        # Fallback to script installation
        try:
            commands = [
                ["curl", "-SsL", "https://playit.gg/install.sh", "-o", "/tmp/playit_install.sh"],
                ["chmod", "+x", "/tmp/playit_install.sh"],
                ["bash", "/tmp/playit_install.sh"]
            ]
            
            for cmd in commands:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode != 0:
                    raise Exception(f"Command failed: {' '.join(cmd)}")
                    
            return shutil.which("playit") is not None
        except Exception as e:
            log(f"Script installation failed: {e}")
            return False
    
    def _install_playit_wget(self) -> bool:
        """Install playit using wget (fallback method)."""
        try:
            arch = self._detect_architecture()
            base_url = "https://github.com/playit-cloud/playit-agent/releases/latest/download"
            
            binary_name = f"playit-linux_{arch}"
            download_url = f"{base_url}/{binary_name}"
            target_path = self.bin_dir / "playit"
            
            # Download binary
            result = subprocess.run([
                "wget", "-O", str(target_path), download_url
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"Download failed: {result.stderr}")
                
            # Make executable
            target_path.chmod(0o755)
            
            # Add to PATH if not already there
            self._add_to_path(str(self.bin_dir))
            
            return target_path.exists() and target_path.stat().st_size > 0
        except Exception as e:
            log(f"Wget installation failed: {e}")
            return False
    
    def _install_playit_package_manager(self) -> bool:
        """Install playit using system package manager (tertiary method)."""
        package_managers = [
            (["apt", "update"], ["apt", "install", "-y", "playit"]),
            (["pkg", "update"], ["pkg", "install", "-y", "playit"]),
            (["yum", "update"], ["yum", "install", "-y", "playit"])
        ]
        
        for update_cmd, install_cmd in package_managers:
            try:
                # Try to update package lists
                subprocess.run(update_cmd, capture_output=True, timeout=30, check=True)
                # Try to install
                result = subprocess.run(install_cmd, capture_output=True, timeout=120)
                if result.returncode == 0:
                    return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
                
        return False
    
    def _install_ngrok(self) -> bool:
        """Install ngrok with authentication setup."""
        try:
            # Download and install ngrok
            arch = self._detect_architecture()
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
    
    def _install_cloudflared(self) -> bool:
        """Install cloudflared tunnel."""
        try:
            arch = self._detect_architecture()
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
    
    def _install_pinggy(self) -> bool:
        """Install pinggy (SSH-based, no installation needed)."""
        # Pinggy uses SSH which should be available
        return shutil.which("ssh") is not None
    
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
    
    def _build_tunnel_command(self) -> List[str]:
        """Build the appropriate tunnel command based on service."""
        # Check if we have a current config
        if not self.current_config:
            return []
            
        command_builders = {
            TunnelService.PLAYIT: self._build_playit_command,
            TunnelService.NGROK: self._build_ngrok_command,
            TunnelService.CLOUDFLARED: self._build_cloudflared_command,
            TunnelService.PINGGY: self._build_pinggy_command
        }
        
        try:
            return command_builders[self.current_config.service]()
        except Exception as e:
            log(f"Failed to build command for {self.current_config.service.value}: {e}")
            return []
    
    def _build_playit_command(self) -> List[str]:
        """Build playit.gg command with enhanced options."""
        # Check if we have a current config
        if not self.current_config:
            return []
            
        playit_path = shutil.which("playit") or str(self.bin_dir / "playit")
        
        # Basic command
        command = [playit_path]
        
        # Add port specification
        command.extend(["--port", str(self.current_config.port)])
        
        # Add protocol specification
        command.extend(["--protocol", "tcp"])
        
        # Add configuration directory
        config_dir = self.config_root / "playit_config"
        config_dir.mkdir(exist_ok=True)
        command.extend(["--config", str(config_dir)])
        
        return command

    def _build_ngrok_command(self) -> List[str]:
        """Build ngrok command with enhanced configuration."""
        # Check if we have a current config
        if not self.current_config:
            return []
            
        ngrok_path = shutil.which("ngrok") or str(self.bin_dir / "ngrok")
        
        return [
            ngrok_path, "tcp", 
            f"localhost:{self.current_config.port}",
            "--log", "stdout",
            "--log-level", "info"
        ]

    def _build_cloudflared_command(self) -> List[str]:
        """Build cloudflared tunnel command."""
        # Check if we have a current config
        if not self.current_config:
            return []
            
        cloudflared_path = shutil.which("cloudflared") or str(self.bin_dir / "cloudflared")
        
        return [
            cloudflared_path, "tunnel",
            "--url", f"tcp://localhost:{self.current_config.port}",
            "--no-autoupdate",
            "--logfile", str(self.tunnel_logfile)
        ]

    def _build_pinggy_command(self) -> List[str]:
        """Build pinggy SSH tunnel command."""
        # Check if we have a current config
        if not self.current_config:
            return []
            
        return [
            "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-R", f"0:localhost:{self.current_config.port}",
            "a.pinggy.io"
        ]
    
    def _detect_architecture(self) -> str:
        """Detect system architecture for downloads."""
        import platform
        
        arch_map = {
            "x86_64": "amd64",
            "aarch64": "arm64",
            "armv7l": "arm",
            "i386": "386",
            "i686": "386"
        }
        
        system_arch = platform.machine().lower()
        return arch_map.get(system_arch, "amd64")  # Default to amd64
    
    def _add_to_path(self, path: str):
        """Add directory to PATH if not already present."""
        current_path = os.environ.get("PATH", "")
        if path not in current_path.split(os.pathsep):
            os.environ["PATH"] = f"{path}{os.pathsep}{current_path}"
    
    def _stop_process_gracefully(self, pid: int):
        """Stop a process gracefully with escalating signals."""
        try:
            # First, try SIGTERM
            os.kill(pid, signal.SIGTERM)
            
            # Wait up to 10 seconds for graceful shutdown
            for _ in range(10):
                try:
                    os.kill(pid, 0)  # Check if process still exists
                    time.sleep(1)
                except ProcessLookupError:
                    log(f"Process {pid} terminated gracefully")
                    return
                    
            # If still running, use SIGKILL
            log(f"Process {pid} didn't respond to SIGTERM, using SIGKILL")
            os.kill(pid, signal.SIGKILL)
            
            # Wait a bit more
            time.sleep(2)
            
        except ProcessLookupError:
            # Process already gone
            log(f"Process {pid} already terminated")
        except Exception as e:
            log(f"Error stopping process {pid}: {e}")
    
    def _cleanup_failed_process(self, process: subprocess.Popen):
        """Clean up a failed process and its resources."""
        try:
            if process.poll() is None:
                # Process is still running, terminate it
                process.terminate()
                
                # Wait for termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    
        except Exception as e:
            log(f"Error cleaning up failed process: {e}")
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # Process exists but we don't have permission to signal it
    
    def _append_to_log(self, line: str):
        """Append a line to the tunnel log with rotation."""
        try:
            # Implement log rotation
            if self.tunnel_logfile.exists() and self.tunnel_logfile.stat().st_size > 10 * 1024 * 1024:  # 10MB
                # Rotate log
                backup_log = self.tunnel_logfile.with_suffix('.log.old')
                if backup_log.exists():
                    backup_log.unlink()
                self.tunnel_logfile.rename(backup_log)
            
            # Append new line
            with open(self.tunnel_logfile, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {line}\n")
                
        except Exception as e:
            log(f"Error writing to tunnel log: {e}")
    
    def _save_tunnel_config(self):
        """Save tunnel configuration to disk with atomic writes."""
        if not self.current_config:
            return
            
        try:
            # Safely access metrics
            metrics_data = {}
            if self.current_config.metrics:
                metrics_data = {
                    "start_time": self.current_config.metrics.start_time.isoformat(),
                    "connection_attempts": self.current_config.metrics.connection_attempts,
                    "successful_connections": self.current_config.metrics.successful_connections,
                    "failed_connections": self.current_config.metrics.failed_connections,
                    "last_health_check": self.current_config.metrics.last_health_check.isoformat() if self.current_config.metrics.last_health_check else None,
                    "uptime_seconds": self.current_config.metrics.uptime_seconds,
                    "bytes_transferred": self.current_config.metrics.bytes_transferred,
                    "restart_count": self.current_config.metrics.restart_count,
                    "last_error": self.current_config.metrics.last_error,
                    "response_times": self.current_config.metrics.response_times[-50:] if self.current_config.metrics.response_times else []  # Keep last 50
                }
            else:
                # Default metrics data
                metrics_data = {
                    "start_time": datetime.now().isoformat(),
                    "connection_attempts": 0,
                    "successful_connections": 0,
                    "failed_connections": 0,
                    "last_health_check": None,
                    "uptime_seconds": 0.0,
                    "bytes_transferred": 0,
                    "restart_count": 0,
                    "last_error": None,
                    "response_times": []
                }
            
            config_data = {
                "service": self.current_config.service.value,
                "port": self.current_config.port,
                "pid": self.current_config.pid,
                "state": self.current_config.state.value,
                "url": self.current_config.url,
                "claim_url": self.current_config.claim_url,
                "config_hash": self.current_config.config_hash,
                "last_restart": self.current_config.last_restart.isoformat() if self.current_config.last_restart else None,
                "metrics": metrics_data
            }
            
            # Atomic write
            temp_file = self.tunnel_config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
                
            temp_file.replace(self.tunnel_config_file)
            
        except Exception as e:
            log(f"Error saving tunnel config: {e}")
    
    def _load_tunnel_config(self):
        """Load tunnel configuration from disk."""
        if not self.tunnel_config_file.exists():
            return
            
        try:
            with open(self.tunnel_config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # Reconstruct configuration
            metrics_data = config_data.get("metrics", {})
            metrics = TunnelMetrics(
                start_time=datetime.fromisoformat(metrics_data.get("start_time", datetime.now().isoformat())),
                connection_attempts=metrics_data.get("connection_attempts", 0),
                successful_connections=metrics_data.get("successful_connections", 0),
                failed_connections=metrics_data.get("failed_connections", 0),
                last_health_check=datetime.fromisoformat(metrics_data["last_health_check"]) if metrics_data.get("last_health_check") else None,
                uptime_seconds=metrics_data.get("uptime_seconds", 0.0),
                bytes_transferred=metrics_data.get("bytes_transferred", 0),
                restart_count=metrics_data.get("restart_count", 0),
                last_error=metrics_data.get("last_error"),
                response_times=metrics_data.get("response_times", [])
            )
            
            self.current_config = TunnelConfig(
                service=TunnelService(config_data["service"]),
                port=config_data["port"],
                pid=config_data.get("pid"),
                state=TunnelState(config_data.get("state", "stopped")),
                url=config_data.get("url"),
                claim_url=config_data.get("claim_url"),
                config_hash=config_data.get("config_hash"),
                last_restart=datetime.fromisoformat(config_data["last_restart"]) if config_data.get("last_restart") else None,
                metrics=metrics
            )
            
            # Validate that process is actually running if state says it is
            if (self.current_config.state in [TunnelState.RUNNING, TunnelState.STARTING] and 
                self.current_config.pid and 
                not self._is_process_running(self.current_config.pid)):
                
                log("Tunnel process not found, marking as stopped")
                self.current_config.state = TunnelState.STOPPED
                self.current_config.pid = None
                self.current_config.url = None
                self._save_tunnel_config()
                
        except Exception as e:
            log(f"Error loading tunnel config: {e}")
            self.current_config = None
    
    def _log_recovery_attempt(self, recovery_entry: Dict[str, Any]):
        """Log a recovery attempt for analysis."""
        try:
            # Load existing recovery log
            recovery_data = []
            if self.recovery_log.exists():
                with open(self.recovery_log, 'r', encoding='utf-8') as f:
                    recovery_data = json.load(f)
                    
            # Add new entry
            recovery_data.append(recovery_entry)
            
            # Keep only last 100 entries
            recovery_data = recovery_data[-100:]
            
            # Save back
            with open(self.recovery_log, 'w', encoding='utf-8') as f:
                json.dump(recovery_data, f, indent=2)
                
        except Exception as e:
            log(f"Error logging recovery attempt: {e}")
    
    def _show_metrics(self):
        """Display detailed tunnel metrics."""
        if not self.current_config or not self.current_config.metrics:
            print_warning("No metrics available")
            return
            
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}Tunnel Metrics - {self.current_config.service.value}{UI.colors.RESET}\n")
        
        metrics = self.current_config.metrics
        
        # Uptime information
        uptime = datetime.now() - metrics.start_time
        print(f"Uptime: {self._format_timedelta(uptime)}")
        print(f"Total Restarts: {metrics.restart_count}")
        
        # Connection statistics
        total_attempts = metrics.connection_attempts
        success_rate = (metrics.successful_connections / total_attempts * 100) if total_attempts > 0 else 0
        print(f"Connection Success Rate: {success_rate:.1f}% ({metrics.successful_connections}/{total_attempts})")
        
        # Response times
        if metrics.response_times:
            avg_response = sum(metrics.response_times) / len(metrics.response_times)
            min_response = min(metrics.response_times)
            max_response = max(metrics.response_times)
            
            print(f"Response Time - Avg: {avg_response:.2f}s, Min: {min_response:.2f}s, Max: {max_response:.2f}s")
        
        # Health status
        if metrics.last_health_check:
            last_check = datetime.now() - metrics.last_health_check
            print(f"Last Health Check: {self._format_timedelta(last_check)} ago")
        
        # Error information
        if metrics.last_error:
            print(f"Last Error: {metrics.last_error}")
            
        input("\nPress Enter to continue...")
    
    def _export_diagnostics(self):
        """Export comprehensive diagnostic information."""
        if not self.current_config:
            print_warning("No active tunnel for diagnostics")
            return
            
        print_info("Exporting diagnostics...")
        
        try:
            diagnostics = {
                "timestamp": datetime.now().isoformat(),
                "system_info": {
                    "platform": platform.system(),
                    "architecture": platform.machine(),
                    "python_version": platform.python_version()
                },
                "tunnel_config": asdict(self.current_config) if self.current_config else None,
                "environment": {
                    "path": os.environ.get("PATH", ""),
                    "config_root": str(self.config_root),
                    "bin_dir": str(self.bin_dir)
                },
                "service_availability": {}
            }
            
            # Check service availability
            for service in TunnelService:
                diagnostics["service_availability"][service.value] = self._check_service_installed(service)
            
            # Add recent logs if available
            if self.tunnel_logfile.exists():
                try:
                    with open(self.tunnel_logfile, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        diagnostics["recent_logs"] = lines[-50:]  # Last 50 lines
                except Exception as e:
                    diagnostics["log_read_error"] = str(e)
            
            # Add recovery history
            if self.recovery_log.exists():
                try:
                    with open(self.recovery_log, 'r', encoding='utf-8') as f:
                        diagnostics["recovery_history"] = json.load(f)
                except Exception as e:
                    diagnostics["recovery_read_error"] = str(e)
            
            # Save diagnostics
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            diag_file = self.config_root / f"diagnostics_{timestamp}.json"
            
            with open(diag_file, 'w', encoding='utf-8') as f:
                json.dump(diagnostics, f, indent=2, default=str)
                
            print_success(f"✅ Diagnostics exported to: {diag_file}")
            
        except Exception as e:
            print_error(f"Failed to export diagnostics: {e}")
            log(f"Diagnostic export error: {e}")
            
        input("\nPress Enter to continue...")
    
    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta in human-readable format."""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def get_tunnel_config(self) -> Optional[TunnelConfig]:
        """Get current tunnel configuration."""
        return self.current_config
    
    def cleanup(self):
        """Cleanup resources when shutting down."""
        try:
            self.health_monitor.stop_monitoring()
            
            if self.current_config and self.current_config.pid:
                log("Cleaning up tunnel process on shutdown")
                # Note: We don't auto-stop the tunnel on cleanup as it should persist
                # Users need to explicitly stop tunnels
                
        except Exception as e:
            log(f"Error during cleanup: {e}")

# Alias for backward compatibility
TunnelManager = RobustTunnelManager
