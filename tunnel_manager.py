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

# Conditional imports for platform-specific modules
try:
    import fcntl
    FCNTL_AVAILABLE = True
except ImportError:
    FCNTL_AVAILABLE = False

try:
    import select
    SELECT_AVAILABLE = True
except ImportError:
    SELECT_AVAILABLE = False

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
        
        # Thread safety
        self._config_lock = threading.RLock()
        
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
                r"(https?://[a-zA-Z0-9.-]+\.joinmc\.link:\d+)",
                r"([a-zA-Z0-9]+\.joinmc\.link:\d+)",
                r"(tcp://[a-zA-Z0-9]+\.joinmc\.link:\d+)",
                # Additional patterns for playit.gg URLs
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg)",
                r"(https?://[a-zA-Z0-9.-]+\.joinmc\.link)",
                r"([a-zA-Z0-9.-]+\.playit\.gg)",
                r"(playit\.gg/[a-zA-Z0-9.-]+)",
                r"(joinmc\.link/[a-zA-Z0-9.-]+)",
                # Additional patterns to capture more URL formats
                r"([a-zA-Z0-9.-]+\.playit\.gg)",
                r"([a-zA-Z0-9]+\.joinmc\.link)",
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"(https?://[a-zA-Z0-9.-]+\.joinmc\.link:\d+)",
                r"([a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"([a-zA-Z0-9.-]+\.joinmc\.link:\d+)"
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
            if FCNTL_AVAILABLE:
                try:
                    import fcntl
                    lock_file = open(self.tunnel_lockfile, 'w')
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    lock_acquired = True
                except BlockingIOError:
                    raise RuntimeError("Another tunnel operation is in progress")
            else:
                # Windows fallback
                if self.tunnel_lockfile.exists():
                    import time
                    # Check if the lock file is stale (older than 1 minute)
                    if time.time() - self.tunnel_lockfile.stat().st_mtime < 60:
                        raise RuntimeError("Another tunnel operation is in progress")
                
                # Create lock file
                self.tunnel_lockfile.touch()
                lock_acquired = True
                
            yield
            
        finally:
            if lock_acquired:
                if FCNTL_AVAILABLE and lock_file:
                    try:
                        import fcntl
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                        lock_file.close()
                    except:
                        pass
                
                # Clean up lock file
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
                print("10. View tunnel logs")
            
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
            elif choice == "10" and self.current_config:
                self._view_tunnel_logs()
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
        elif config.state == TunnelState.RUNNING:
            # Show a message when tunnel is running but URL is not detected
            print(f"  URL: {UI.colors.YELLOW}Not detected yet - check logs{UI.colors.RESET}")
            
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
        """Internal service setup with comprehensive error handling and debugging."""
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}{service.value} Setup{UI.colors.RESET}\n")
        
        try:
            # Stop existing tunnel if running
            if self.current_config and self.current_config.state != TunnelState.STOPPED:
                print_warning("Stopping existing tunnel...")
                self.stop_tunnel(show_messages=False)
                time.sleep(2)  # Give it time to stop
            
            # Check installation with detailed logging
            print_info(f"Checking {service.value} installation...")
            log(f"Checking installation for {service.value}")
            
            if not self._check_service_installed(service):
                print_info(f"{service.value} not found, installing...")
                log(f"Installing {service.value}")
                
                # Install with detailed progress
                if not self._install_service_with_progress(service):
                    print_error(f"❌ Failed to install {service.value}")
                    self._show_installation_help(service)
                    input("\nPress Enter to continue...")
                    return
                
                print_success(f"✅ {service.value} installed successfully!")
            else:
                print_success(f"✅ {service.value} is already installed")
            
            # Verify installation works
            print_info("Verifying installation...")
            log(f"Verifying {service.value} installation")
            
            if not self._verify_service_installation(service):
                print_error(f"❌ {service.value} installation verification failed")
                self._show_installation_help(service)
                input("\nPress Enter to continue...")
                return
            
            print_success(f"✅ {service.value} verification successful")
            
            # Get server port
            port = self._get_server_port()
            print_info(f"Using server port: {port}")
            log(f"Server port: {port}")
            
            # Create new configuration
            print_info("Creating tunnel configuration...")
            self.current_config = TunnelConfig(
                service=service,
                port=port,
                state=TunnelState.STARTING,
                metrics=TunnelMetrics(start_time=datetime.now())
            )
            
            # Save initial configuration
            self._save_tunnel_config()
            log(f"Created tunnel configuration for {service.value} on port {port}")
            
            # Start the tunnel with enhanced retry logic
            print_info(f"Starting {service.value} tunnel...")
            log(f"Starting tunnel for {service.value}")
            
            success = self._start_tunnel_with_detailed_progress()
            
            if success:
                self.health_monitor.start_monitoring()
                print_success(f"✅ {service.value} tunnel started successfully!")
                
                # Show connection information
                self._show_tunnel_connection_info()
                
                print_info("💡 Tip: Use option 8 to view detailed metrics")
                print_info("💡 Tip: Use option 10 to view tunnel logs")
                
            else:
                print_error(f"❌ Failed to start {service.value} tunnel")
                self.current_config.state = TunnelState.FAILED
                
                # Show troubleshooting information
                self._show_startup_troubleshooting(service)
            
            # Always save final configuration
            self._save_tunnel_config()
            
        except Exception as e:
            error_msg = f"Setup failed for {service.value}: {e}"
            log(error_msg)
            print_error(f"❌ Setup error: {str(e)}")
            
            if self.current_config:
                self.current_config.state = TunnelState.FAILED
                if self.current_config.metrics:
                    self.current_config.metrics.last_error = str(e)
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
                    
                log(f"Starting tunnel with command: {' '.join(command)}")
                
                # Start process with enhanced monitoring
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid if os.name != 'nt' else None  # Create process group (Unix only)
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
                    log(f"Tunnel startup timeout. Command: {' '.join(command)}")
                    # Log the last few lines of the tunnel log for debugging
                    if self.tunnel_logfile.exists():
                        try:
                            with open(self.tunnel_logfile, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                                last_lines = lines[-10:] if len(lines) > 10 else lines
                                log(f"Last tunnel log lines: {last_lines}")
                        except Exception as e:
                            log(f"Error reading tunnel log: {e}")
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
        """Enhanced output monitoring with cross-platform support."""
        # Thread-safe access to current config
        current_config = self.get_tunnel_config()
        if not current_config:
            return
            
        patterns = self.service_patterns.get(current_config.service, [])
        claim_patterns = [
            r"(https?://[a-zA-Z0-9.-]+\.playit\.gg/claim/[a-zA-Z0-9-]+)",
            r"(https?://[a-zA-Z0-9.-]+/claim/[a-zA-Z0-9-]+)"
        ]
        
        try:
            while True:
                if process.stdout:
                    # Platform-aware non-blocking read
                    if os.name == 'nt' or not SELECT_AVAILABLE:  # Windows or select not available
                        # Use polling approach
                        if process.poll() is not None:
                            break
                        line = process.stdout.readline()
                        if not line:
                            time.sleep(0.1)
                            continue
                    else:  # Unix-like with select available
                        try:
                            if SELECT_AVAILABLE:
                                import select
                                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                                if not ready:
                                    if process.poll() is not None:
                                        break
                                    continue
                                line = process.stdout.readline()
                                if not line:
                                    break
                            else:
                                # Fallback if select is not available even on Unix
                                if process.poll() is not None:
                                    break
                                line = process.stdout.readline()
                                if not line:
                                    time.sleep(0.1)
                                    continue
                        except Exception:
                            # Handle select errors gracefully
                            if process.poll() is not None:
                                break
                            time.sleep(0.1)
                            continue
                    
                    # Log all output for debugging
                    line = line.strip()
                    log(f"Tunnel output: {line}")
                    
                    # Process the line
                    self._append_to_log(line)
                    self._extract_urls_from_line(line, patterns, claim_patterns, current_config)
                    
        except Exception as e:
            log(f"Output monitoring error: {e}")
        finally:
            # Ensure process cleanup
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    try:
                        process.kill()
                    except:
                        pass
    
    def _extract_urls_from_line(self, line: str, patterns: List[str], claim_patterns: List[str], current_config: Optional[TunnelConfig] = None):
        """Extract tunnel URLs and claim URLs from output line."""
        # Use provided config or get current config thread-safely
        if current_config is None:
            current_config = self.get_tunnel_config()
            
        # Check if we have a current config
        if not current_config:
            return
            
        # Enhanced debugging for playit.gg
        if current_config.service == TunnelService.PLAYIT:
            log(f"Processing playit.gg output line: {line}")
            
        # Check for claim URLs first (playit.gg specific)
        for pattern in claim_patterns:
            match = re.search(pattern, line)
            if match:
                claim_url = match.group(1)
                current_config.claim_url = claim_url
                log(f"Claim URL found: {claim_url}")
                self._save_tunnel_config()
                
        # Check for tunnel URLs
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                url = match.group(1)
                
                # Normalize URL format
                url = self._normalize_tunnel_url(url, current_config)
                
                if url != current_config.url:
                    current_config.url = url
                    log(f"Tunnel URL found: {url}")
                    self._save_tunnel_config()
                    break
            
        # Additional check for playit.gg specific formats
        if current_config.service == TunnelService.PLAYIT:
            # Check for common playit.gg URL patterns that might be missed
            playit_patterns = [
                r"([a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"([a-zA-Z0-9.-]+\.joinmc\.link:\d+)",
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg:\d+)",
                r"(https?://[a-zA-Z0-9.-]+\.joinmc\.link:\d+)",
                r"([a-zA-Z0-9.-]+\.playit\.gg)",
                r"([a-zA-Z0-9.-]+\.joinmc\.link)",
                r"(https?://[a-zA-Z0-9.-]+\.playit\.gg)",
                r"(https?://[a-zA-Z0-9.-]+\.joinmc\.link)"
            ]
            
            for pattern in playit_patterns:
                match = re.search(pattern, line)
                if match:
                    url = match.group(1)
                    # Normalize URL format
                    url = self._normalize_tunnel_url(url, current_config)
                    
                    if url != current_config.url:
                        current_config.url = url
                        log(f"Additional playit.gg URL found: {url}")
                        self._save_tunnel_config()
                        break

    def _normalize_tunnel_url(self, url: str, current_config: Optional[TunnelConfig] = None) -> str:
        """Normalize tunnel URL format based on service."""
        # Use provided config or get current config thread-safely
        if current_config is None:
            current_config = self.get_tunnel_config()
            
        if not current_config:
            return url
            
        service = current_config.service
        
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
            
        # Additional normalization for playit.gg URLs
        if service == TunnelService.PLAYIT:
            # Add default port if missing for playit.gg
            if not re.search(r":\d+$", url) and not url.startswith("https://"):
                # If it's a playit.gg or joinmc.link URL without port, add default Minecraft port
                if ".playit.gg" in url or ".joinmc.link" in url:
                    if not url.startswith(("tcp://", "https://")):
                        url = "tcp://" + url + ":25565"
                    elif not re.search(r":\d+$", url):
                        url = url + ":25565"
            
        return url
    
    def _wait_for_tunnel_ready(self, timeout: int = 30) -> bool:
        """Wait for tunnel to be ready with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Thread-safe access to current config
            current_config = self.get_tunnel_config()
            
            # Check if we have a current config
            if not current_config:
                return False
                
            # Check if we have a URL
            if current_config.url:
                return True
                
            # For playit.gg, also check if process is running and has been running for a while
            # This is because playit might not always output a URL but still be working
            if (current_config.service == TunnelService.PLAYIT and 
                current_config.pid and 
                self._is_process_running(current_config.pid)):
                # If process has been running for more than 5 seconds, consider it ready
                if current_config.metrics and current_config.metrics.start_time:
                    uptime = datetime.now() - current_config.metrics.start_time
                    if uptime.total_seconds() > 5:
                        log("Playit.gg process running, assuming tunnel is ready")
                        # Even if no URL found, mark as ready since the process is running
                        # This allows users to check the logs for the actual URL
                        return True
                        
            # For some services, just having the process running is enough
            if (current_config.service == TunnelService.PINGGY and 
                current_config.pid and 
                self._is_process_running(current_config.pid)):
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
    
    def _install_service_with_progress(self, service: TunnelService) -> bool:
        """Install service with detailed progress feedback."""
        try:
            print_info("🔄 Starting installation process...")
            
            # Get installation methods for this service
            install_methods = self._get_install_methods(service)
            
            for attempt_num, (method_name, install_method) in enumerate(install_methods, 1):
                try:
                    print_info(f"📦 Installation attempt {attempt_num}/{len(install_methods)}: {method_name}")
                    log(f"Trying installation method: {method_name}")
                    
                    if install_method():
                        print_success(f"✅ Installation successful using {method_name}")
                        return True
                    else:
                        print_warning(f"⚠️  Method {attempt_num} ({method_name}) failed")
                        
                except Exception as e:
                    error_msg = f"Method {attempt_num} ({method_name}) failed: {e}"
                    log(error_msg)
                    print_warning(f"⚠️  {error_msg}")
            
            return False
            
        except Exception as e:
            log(f"Installation process failed: {e}")
            return False
    
    def _get_install_methods(self, service: TunnelService):
        """Get ordered list of installation methods for a service."""
        if service == TunnelService.PLAYIT:
            return [
                ("Direct Binary Download", self._install_playit_direct_binary_v016),
                ("APT Repository", self._install_playit_official_apt),
                ("Fallback Binary", self._install_playit_fallback_binary),
                ("Manual Wrapper", self._install_playit_manual_wrapper)
            ]
        elif service == TunnelService.NGROK:
            return [
                ("Direct Download", self._install_ngrok)
            ]
        elif service == TunnelService.CLOUDFLARED:
            return [
                ("Direct Download", self._install_cloudflared)
            ]
        elif service == TunnelService.PINGGY:
            return [
                ("SSH Availability", self._install_pinggy)
            ]
        
        return []
    
    def _verify_service_installation(self, service: TunnelService) -> bool:
        """Verify that a service is properly installed and working."""
        try:
            print_info("🔍 Running installation verification...")
            
            if service == TunnelService.PLAYIT:
                return self._verify_playit_detailed()
            elif service == TunnelService.NGROK:
                return self._verify_ngrok_detailed()
            elif service == TunnelService.CLOUDFLARED:
                return self._verify_cloudflared_detailed()
            elif service == TunnelService.PINGGY:
                return self._verify_pinggy_detailed()
            
            return False
            
        except Exception as e:
            log(f"Service verification failed: {e}")
            return False
    
    def _install_playit(self) -> bool:
        """Install playit.gg using the most reliable direct binary download method."""
        try:
            print_info("Installing playit.gg...")
            log("Attempting direct binary installation")
            
            # Use only the direct binary download method as it's most reliable
            return self._install_playit_direct_binary_v016()
            
        except Exception as e:
            error_msg = f"Playit installation failed: {e}"
            log(error_msg)
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            print_error(f"Failed to install playit.gg: {e}")
            self._show_playit_troubleshooting()
            return False

    def _install_playit_official_apt(self) -> bool:
        """Install playit using the official APT method from playit.gg."""
        try:
            log("Attempting official APT installation")
            
            # Official commands from playit.gg documentation
            commands = [
                # Add GPG key
                "curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/playit.gpg",
                # Add repository  
                'echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" > /etc/apt/sources.list.d/playit-cloud.list',
                # Update package lists
                "apt update",
                # Install playit
                "apt install playit -y"
            ]
            
            for i, cmd in enumerate(commands, 1):
                log(f"Executing command {i}/{len(commands)}: {cmd}")
                print_info(f"Executing step {i}/{len(commands)}...")
                
                # Run with sudo if available
                full_cmd = f"sudo {cmd}" if shutil.which("sudo") else cmd
                
                result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=120)
                
                if result.returncode != 0:
                    log(f"Command failed with exit code {result.returncode}")
                    log(f"STDOUT: {result.stdout}")
                    log(f"STDERR: {result.stderr}")
                    print_error(f"Step {i} failed: {result.stderr[:100]}...")
                    return False
                    
            # Verify installation and update PATH
            log("Installation commands completed, verifying installation...")
            playit_path = shutil.which("playit")
            if playit_path is not None:
                log(f"Playit found in PATH at: {playit_path}")
                print_success("✅ playit.gg installed successfully via APT!")
                # Ensure the directory is in PATH
                self._add_to_path(os.path.dirname(playit_path))
                return True
            else:
                # Check common installation paths
                log("Playit not found in PATH, checking common locations...")
                common_paths = ["/usr/bin/playit", "/usr/local/bin/playit"]
                for path in common_paths:
                    if os.path.exists(path):
                        if os.access(path, os.X_OK):
                            log(f"Playit found at {path} and is executable")
                            print_success("✅ playit.gg installed successfully via APT!")
                            # Add to PATH
                            self._add_to_path(os.path.dirname(path))
                            return True
                        else:
                            log(f"Playit found at {path} but is not executable")
                
                # If still not found, try to find it with find command
                try:
                    log("Trying to locate playit with find command...")
                    find_result = subprocess.run(["find", "/", "-name", "playit", "-type", "f", "-executable"], 
                                               capture_output=True, text=True, timeout=30)
                    if find_result.returncode == 0 and find_result.stdout.strip():
                        found_paths = find_result.stdout.strip().split('\n')
                        for path in found_paths:
                            if path:
                                log(f"Found playit at: {path}")
                                print_success("✅ playit.gg installed successfully via APT!")
                                # Add to PATH
                                self._add_to_path(os.path.dirname(path))
                                return True
                except Exception as e:
                    log(f"Find command failed: {e}")
                
                log("Playit installation completed but binary not found or not executable")
                print_warning("Installation completed but playit command not found or not executable")
                return False
                
        except Exception as e:
            log(f"APT installation failed: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            print_error(f"Failed to install playit.gg: {e}")
            return False

    def _find_playit_binary(self) -> Optional[str]:
        """Find playit binary in common locations."""
        # Check common locations where playit might be installed
        common_paths = [
            "/usr/bin/playit",
            "/usr/local/bin/playit",
            str(self.bin_dir / "playit")
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
        
        # Try to find with find command
        try:
            find_result = subprocess.run(["find", "/", "-name", "playit", "-type", "f", "-executable"], 
                                       capture_output=True, text=True, timeout=30)
            if find_result.returncode == 0 and find_result.stdout.strip():
                found_paths = find_result.stdout.strip().split('\n')
                for path in found_paths:
                    if path:
                        return path
        except Exception as e:
            log(f"Find command failed: {e}")
        
        return None

    def _install_playit_direct_binary_v016(self) -> bool:
        """Install playit using direct binary download from v0.16.2 release."""
        try:
            arch = self._detect_architecture_playit()
            log(f"Detected architecture for playit: {arch}")
            
            # Official binary URLs from playit.gg (v0.16.2)
            binary_urls = {
                "amd64": "https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-amd64",
                "i686": "https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-i686", 
                "arm": "https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-armv7",
                "arm64": "https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-aarch64"
            }
            
            # Try the detected architecture first, then fallbacks
            arch_priority = [arch, "amd64", "arm64", "arm", "i686"]
            
            target_path = self.bin_dir / "playit"
            
            for try_arch in arch_priority:
                if try_arch not in binary_urls:
                    continue
                    
                download_url = binary_urls[try_arch]
                log(f"Trying to download {try_arch} binary from: {download_url}")
                
                try:
                    # Download using curl with better error handling
                    result = subprocess.run([
                        "curl", "-L", "-f", "--connect-timeout", "30", 
                        "--max-time", "180", "-o", str(target_path), 
                        "--user-agent", "MSM-TunnelManager/1.2.0",
                        download_url
                    ], capture_output=True, text=True, timeout=200)
                    
                    if result.returncode == 0:
                        # Verify download
                        if target_path.exists() and target_path.stat().st_size > 5000:  # At least 5KB
                            # Make executable
                            target_path.chmod(0o755)
                            self._add_to_path(str(self.bin_dir))
                            
                            # Test the binary
                            test_result = subprocess.run([str(target_path), "--version"], 
                                                       capture_output=True, timeout=15)
                            if test_result.returncode == 0:
                                log(f"Successfully downloaded and verified playit binary ({try_arch})")
                                return True
                            else:
                                log(f"Binary test failed for {try_arch}: {test_result.stderr}")
                        else:
                            log(f"Downloaded file is too small or missing for {try_arch}")
                    else:
                        log(f"Download failed for {try_arch}: {result.stderr}")
                        
                    # Clean up failed download
                    target_path.unlink(missing_ok=True)
                    
                except subprocess.TimeoutExpired:
                    log(f"Download timeout for {try_arch}")
                    target_path.unlink(missing_ok=True)
                except Exception as e:
                    log(f"Download error for {try_arch}: {e}")
                    target_path.unlink(missing_ok=True)
            
            return False
            
        except Exception as e:
            log(f"Direct binary installation failed: {e}")
            return False

    def _install_playit_fallback_binary(self) -> bool:
        """Fallback installation using wget and latest release API."""
        try:
            log("Attempting fallback binary installation")
            
            # Try to get latest release info
            latest_url = "https://api.github.com/repos/playit-cloud/playit-agent/releases/latest"
            
            try:
                result = subprocess.run([
                    "curl", "-s", "--connect-timeout", "15", "--max-time", "30", latest_url
                ], capture_output=True, text=True, timeout=35)
                
                if result.returncode == 0:
                    import json
                    release_data = json.loads(result.stdout)
                    assets = release_data.get("assets", [])
                    
                    # Find Linux binary for our architecture
                    arch = self._detect_architecture_playit()
                    arch_patterns = {
                        "amd64": ["amd64", "x86_64"],
                        "arm64": ["aarch64", "arm64"],
                        "arm": ["armv7", "arm"],
                        "i686": ["i686", "386"]
                    }
                    
                    patterns = arch_patterns.get(arch, ["amd64"])
                    
                    for asset in assets:
                        asset_name = asset.get("name", "").lower()
                        if "linux" in asset_name and any(p in asset_name for p in patterns):
                            download_url = asset.get("browser_download_url")
                            if download_url:
                                log(f"Found latest release asset: {asset_name}")
                                return self._download_and_install_binary(download_url)
                                
            except Exception as e:
                log(f"Failed to get latest release info: {e}")
            
            # Fallback to direct URLs
            arch = self._detect_architecture_playit()
            fallback_urls = [
                f"https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-linux-{arch}",
                "https://github.com/playit-cloud/playit-agent/releases/latest/download/playit-linux-amd64"
            ]
            
            for url in fallback_urls:
                if self._download_and_install_binary(url):
                    return True
                    
            return False
            
        except Exception as e:
            log(f"Fallback binary installation failed: {e}")
            return False

    def _install_playit_manual_wrapper(self) -> bool:
        """Create a wrapper script that downloads playit on first run."""
        try:
            log("Creating manual wrapper script")
            
            wrapper_script = self.bin_dir / "playit"
            wrapper_content = '''#!/bin/bash
# Playit.gg Auto-Installer Wrapper Script
# Downloads and runs playit.gg binary automatically

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAYIT_BINARY="$SCRIPT_DIR/playit-binary"

download_playit() {
    echo "🔄 Downloading playit.gg binary..."
    
    # Detect architecture
    ARCH=$(uname -m)
    case $ARCH in
        x86_64) PLAYIT_ARCH="amd64" ;;
        aarch64) PLAYIT_ARCH="aarch64" ;;
        armv7l) PLAYIT_ARCH="armv7" ;;
        i686|i386) PLAYIT_ARCH="i686" ;;
        *) PLAYIT_ARCH="amd64" ;;
    esac
    
    # Official download URL (v0.16.2)
    URL="https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-$PLAYIT_ARCH"
    
    echo "📥 Downloading from: $URL"
    
    if command -v curl >/dev/null 2>&1; then
        curl -L -f --connect-timeout 30 --max-time 180 "$URL" -o "$PLAYIT_BINARY"
    elif command -v wget >/dev/null 2>&1; then
        wget --timeout=180 --connect-timeout=30 "$URL" -O "$PLAYIT_BINARY"
    else
        echo "❌ Error: Neither curl nor wget available"
        exit 1
    fi
    
    if [ ! -f "$PLAYIT_BINARY" ] || [ $(stat -c%s "$PLAYIT_BINARY" 2>/dev/null || echo 0) -lt 5000 ]; then
        echo "❌ Download failed or file too small"
        rm -f "$PLAYIT_BINARY"
        exit 1
    fi
    
    chmod +x "$PLAYIT_BINARY"
    echo "✅ Download completed successfully!"
}

# Check if binary exists and is executable
if [ ! -f "$PLAYIT_BINARY" ] || [ ! -x "$PLAYIT_BINARY" ]; then
    download_playit
fi

# Run the binary with all arguments
exec "$PLAYIT_BINARY" "$@"
'''
            
            with open(wrapper_script, 'w') as f:
                f.write(wrapper_content)
            
            wrapper_script.chmod(0o755)
            self._add_to_path(str(self.bin_dir))
            
            log("Wrapper script created successfully")
            return True
            
        except Exception as e:
            log(f"Manual wrapper creation failed: {e}")
            return False

    def _detect_architecture_playit(self) -> str:
        """Detect architecture specifically for playit.gg downloads."""
        import platform
        
        machine = platform.machine().lower()
        
        # Map to playit.gg architecture names
        arch_map = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64", 
            "arm64": "arm64",
            "armv8": "arm64",
            "armv7l": "arm",
            "armv7": "arm", 
            "armv6l": "arm",
            "i386": "i686",
            "i686": "i686"
        }
        
        detected = arch_map.get(machine, "amd64")
        log(f"Architecture detection: {machine} -> {detected}")
        return detected

    def _download_and_install_binary(self, url: str) -> bool:
        """Download and install binary from given URL."""
        try:
            target_path = self.bin_dir / "playit"
            log(f"Downloading binary from: {url}")
            
            # Try curl first, then wget
            download_commands = [
                ["curl", "-L", "-f", "--connect-timeout", "30", "--max-time", "180", "-o", str(target_path), url],
                ["wget", "--timeout=180", "--connect-timeout=30", url, "-O", str(target_path)]
            ]
            
            for cmd in download_commands:
                if not shutil.which(cmd[0]):
                    continue
                    
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
                    
                    if result.returncode == 0 and target_path.exists():
                        file_size = target_path.stat().st_size
                        if file_size > 5000:  # At least 5KB
                            target_path.chmod(0o755)
                            self._add_to_path(str(self.bin_dir))
                            
                            # Test binary
                            test_result = subprocess.run([str(target_path), "--version"], 
                                                       capture_output=True, timeout=15)
                            if test_result.returncode == 0:
                                log(f"Successfully installed playit binary ({file_size} bytes)")
                                return True
                            else:
                                log(f"Binary test failed: {test_result.stderr}")
                        else:
                            log(f"Downloaded file too small: {file_size} bytes")
                    else:
                        log(f"Download failed with {cmd[0]}: {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    log(f"Download timeout with {cmd[0]}")
                except Exception as e:
                    log(f"Download error with {cmd[0]}: {e}")
                    
                # Clean up failed download
                target_path.unlink(missing_ok=True)
            
            return False
            
        except Exception as e:
            log(f"Binary download and install failed: {e}")
            return False

    def _verify_playit_installation(self) -> bool:
        """Verify that playit is properly installed and working."""
        try:
            # Check if playit command is available
            playit_path = shutil.which("playit")
            
            # If not found in PATH, check common installation locations
            if not playit_path:
                log("Playit not found in PATH, checking common locations...")
                # Check common locations where APT might install playit
                common_paths = [
                    "/usr/bin/playit",
                    "/usr/local/bin/playit",
                    str(self.bin_dir / "playit")
                ]
                
                for path in common_paths:
                    log(f"Checking {path}...")
                    if os.path.exists(path):
                        log(f"Found playit at {path}")
                        if os.access(path, os.X_OK):
                            log(f"Playit at {path} is executable")
                            playit_path = path
                            # Add to PATH for current session
                            self._add_to_path(os.path.dirname(path))
                            break
                        else:
                            log(f"Playit at {path} is not executable")
                    else:
                        log(f"Playit not found at {path}")
            
            if not playit_path:
                log("playit command not found in PATH or common locations")
                # Try to refresh PATH and check again
                os.environ["PATH"] = os.environ.get("PATH", "") + ":" + "/usr/bin:/usr/local/bin:" + str(self.bin_dir)
                playit_path = shutil.which("playit")
                if playit_path:
                    log(f"Found playit after PATH refresh: {playit_path}")
            
            if not playit_path:
                log("playit command still not found after all checks")
                return False
            
            log(f"Found playit at: {playit_path}")
            
            # Test version command
            log("Testing playit --version...")
            result = subprocess.run([playit_path, "--version"], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                version_output = result.stdout.strip()
                log(f"Playit version check successful: {version_output}")
                return True
            else:
                log(f"Playit version check failed with return code {result.returncode}")
                log(f"STDERR: {result.stderr}")
                log(f"STDOUT: {result.stdout}")
                
                # Try with shell=True in case there are environment issues
                log("Retrying with shell=True...")
                result2 = subprocess.run(f"{playit_path} --version", 
                                       shell=True, capture_output=True, text=True, timeout=15)
                if result2.returncode == 0:
                    version_output = result2.stdout.strip()
                    log(f"Playit version check successful on retry: {version_output}")
                    return True
                else:
                    log(f"Playit version check failed on retry with return code {result2.returncode}")
                    log(f"STDERR: {result2.stderr}")
                    log(f"STDOUT: {result2.stdout}")
                    
                    # Try with full environment
                    log("Retrying with full environment...")
                    env = os.environ.copy()
                    env["PATH"] = os.environ.get("PATH", "") + ":" + os.path.dirname(playit_path)
                    result3 = subprocess.run([playit_path, "--version"], 
                                           capture_output=True, text=True, timeout=15, env=env)
                    if result3.returncode == 0:
                        version_output = result3.stdout.strip()
                        log(f"Playit version check successful with full environment: {version_output}")
                        return True
                    else:
                        log(f"Playit version check failed with full environment: {result3.stderr}")
                
                return False
                
        except subprocess.TimeoutExpired:
            log("Playit version check timed out")
            return False
        except Exception as e:
            log(f"Playit verification failed with exception: {e}")
            import traceback
            log(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _show_installation_help(self, service: TunnelService):
        """Show installation troubleshooting help for a service."""
        print_warning(f"\n🛠️  {service.value} Installation Help:")
        
        if service == TunnelService.PLAYIT:
            print_info("1. Manual installation commands:")
            print_info("   # Direct binary download:")
            print_info("   curl -L https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-amd64 -o playit")
            print_info("   chmod +x playit")
            print_info("   sudo mv playit /usr/local/bin/")
            print_info("")
            print_info("2. APT method (if you have sudo access):")
            print_info("   curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/playit.gpg >/dev/null")
            print_info('   echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" | sudo tee /etc/apt/sources.list.d/playit-cloud.list')
            print_info("   sudo apt update && sudo apt install playit")
        elif service == TunnelService.NGROK:
            print_info("1. Download from: https://ngrok.com/download")
            print_info("2. Move to PATH: sudo mv ngrok /usr/local/bin/")
            print_info("3. Authenticate: ngrok authtoken YOUR_TOKEN")
        elif service == TunnelService.CLOUDFLARED:
            print_info("1. Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/")
            print_info("2. Make executable: chmod +x cloudflared")
            print_info("3. Move to PATH: sudo mv cloudflared /usr/local/bin/")
        elif service == TunnelService.PINGGY:
            print_info("1. SSH should be available by default on most systems")
            print_info("2. Test with: ssh -V")
        
        print_info("")
        print_info("Check logs for detailed errors:")
        print_info(f"   cat {self.tunnel_logfile}")

    def _show_playit_troubleshooting(self):
        """Show troubleshooting information for playit.gg installation."""
        print_warning("\n🛠️  Playit.gg Installation Troubleshooting:")
        print_info("1. Manual installation commands:")
        print_info("   # APT method (if you have sudo access):")
        print_info("   curl -SsL https://playit-cloud.github.io/ppa/key.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/playit.gpg >/dev/null")
        print_info('   echo "deb [signed-by=/etc/apt/trusted.gpg.d/playit.gpg] https://playit-cloud.github.io/ppa/data ./" | sudo tee /etc/apt/sources.list.d/playit-cloud.list')
        print_info("   sudo apt update && sudo apt install playit")
        print_info("")
        print_info("2. Direct binary download:")
        print_info("   curl -L https://github.com/playit-cloud/playit-agent/releases/download/v0.16.2/playit-linux-amd64 -o playit")
        print_info("   chmod +x playit")
        print_info("   ./playit --version")
        print_info("")
        print_info("3. Check system requirements:")
        print_info("   - Internet connectivity: ping github.com")
        print_info("   - Available tools: which curl wget")
        print_info("   - Disk space: df -h")
        print_info(f"   - Architecture: uname -m")
        print_info("")
        print_info("4. Check logs for detailed errors:")
        print_info(f"   cat {self.tunnel_logfile}")

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
            
        # Try to find playit in PATH first
        playit_path = shutil.which("playit")
        
        # If not found, check common locations
        if not playit_path:
            common_paths = [
                "/usr/bin/playit",
                "/usr/local/bin/playit",
                str(self.bin_dir / "playit")
            ]
            
            for path in common_paths:
                if os.path.exists(path) and os.access(path, os.X_OK):
                    playit_path = path
                    break
        
        # If still not found, use default
        if not playit_path:
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
        
        # Add flags to make it more verbose for better URL detection
        command.extend(["--log-level", "debug"])  # Increased verbosity
        
        # Add flag to show all connection information
        command.extend(["--show-connection-info"])
        
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
        """Stop a process gracefully with platform awareness."""
        try:
            if os.name == 'nt':  # Windows
                import subprocess
                result = subprocess.run(['taskkill', '/PID', str(pid), '/F'], 
                                       capture_output=True, timeout=10)
                if result.returncode != 0:
                    log(f"Failed to kill process {pid} on Windows: {result.stderr}")
            else:  # Unix-like
                # First, try SIGTERM
                os.kill(pid, signal.SIGTERM)
                
                # Wait up to 10 seconds for graceful shutdown
                for _ in range(10):
                    try:
                        os.kill(pid, 0)
                        time.sleep(1)
                    except ProcessLookupError:
                        log(f"Process {pid} terminated gracefully")
                        return
                        
                # If still running, use SIGKILL
                log(f"Process {pid} didn't respond to SIGTERM, using SIGKILL")
                os.kill(pid, signal.SIGKILL)
                time.sleep(2)
                
        except ProcessLookupError:
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
        """Save tunnel configuration to disk with atomic writes and thread safety."""
        with self._config_lock:
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
    
    def _view_tunnel_logs(self):
        """View recent tunnel logs to help with debugging."""
        if not self.current_config:
            print_warning("No active tunnel")
            return
            
        clear_screen()
        print_header("1.2.0")
        print(f"{UI.colors.BOLD}Tunnel Logs - {self.current_config.service.value}{UI.colors.RESET}\n")
        
        if not self.tunnel_logfile.exists():
            print_info("No log file found")
            input("\nPress Enter to continue...")
            return
            
        try:
            # Read last 50 lines of log file
            with open(self.tunnel_logfile, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
            if not recent_lines:
                print_info("Log file is empty")
            else:
                print(f"{UI.colors.BOLD}Recent log output:{UI.colors.RESET}")
                for line in recent_lines:
                    # Remove timestamp if present
                    clean_line = line
                    if line.startswith('[') and ']' in line:
                        clean_line = line.split(']', 1)[1].strip() if len(line.split(']', 1)) > 1 else line
                    print(f"  {clean_line.rstrip()}")
                    
        except Exception as e:
            print_error(f"Error reading logs: {e}")
            
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
        """Get current tunnel configuration thread-safely."""
        with self._config_lock:
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

    def _verify_playit_detailed(self) -> bool:
        """Detailed verification for playit.gg installation."""
        try:
            # Check if command exists
            playit_path = shutil.which("playit")
            if not playit_path:
                # Try common locations
                common_paths = [
                    str(self.bin_dir / "playit"),
                    "/usr/local/bin/playit",
                    "/usr/bin/playit",
                    str(Path.home() / ".local/bin/playit")
                ]
                
                for path in common_paths:
                    if Path(path).exists():
                        playit_path = path
                        break
        
            if not playit_path:
                log("Playit command not found in PATH or common locations")
                return False
        
            log(f"Found playit at: {playit_path}")
        
            # Check if file is executable
            if not os.access(playit_path, os.X_OK):
                log(f"Playit binary at {playit_path} is not executable")
                try:
                    os.chmod(playit_path, 0o755)
                    log("Made playit binary executable")
                except Exception as e:
                    log(f"Failed to make playit executable: {e}")
                    return False
        
            # Test version command with timeout
            print_info("Testing playit version command...")
            result = subprocess.run([playit_path, "--version"], 
                                  capture_output=True, text=True, timeout=15)
        
            if result.returncode == 0:
                version_output = result.stdout.strip()
                log(f"Playit version check successful: {version_output}")
                print_success(f"✅ Playit version: {version_output}")
                return True
            else:
                log(f"Playit version check failed. Return code: {result.returncode}")
                log(f"STDOUT: {result.stdout}")
                log(f"STDERR: {result.stderr}")
                print_warning(f"Version check failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            log("Playit version check timed out")
            print_warning("Version check timed out")
            return False
        except Exception as e:
            log(f"Playit verification failed: {e}")
            print_warning(f"Verification error: {e}")
            return False
    
    def _verify_ngrok_detailed(self) -> bool:
        """Detailed verification for ngrok installation."""
        try:
            ngrok_path = shutil.which("ngrok")
            if not ngrok_path:
                common_paths = [
                    str(self.bin_dir / "ngrok"),
                    "/usr/local/bin/ngrok",
                    "/usr/bin/ngrok"
                ]
                for path in common_paths:
                    if Path(path).exists():
                        ngrok_path = path
                        break
            
            if not ngrok_path:
                return False
            
            result = subprocess.run([ngrok_path, "version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                log(f"Ngrok version: {result.stdout.strip()}")
                return True
            
            return False
        except Exception as e:
            log(f"Ngrok verification failed: {e}")
            return False
    
    def _verify_cloudflared_detailed(self) -> bool:
        """Detailed verification for cloudflared installation."""
        try:
            cloudflared_path = shutil.which("cloudflared")
            if not cloudflared_path:
                common_paths = [
                    str(self.bin_dir / "cloudflared"),
                    "/usr/local/bin/cloudflared",
                    "/usr/bin/cloudflared"
                ]
                for path in common_paths:
                    if Path(path).exists():
                        cloudflared_path = path
                        break
            
            if not cloudflared_path:
                return False
            
            result = subprocess.run([cloudflared_path, "version"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                log(f"Cloudflared version: {result.stdout.strip()}")
                return True
            
            return False
        except Exception as e:
            log(f"Cloudflared verification failed: {e}")
            return False
    
    def _verify_pinggy_detailed(self) -> bool:
        """Detailed verification for pinggy installation."""
        try:
            ssh_path = shutil.which("ssh")
            if not ssh_path:
                return False
            
            result = subprocess.run([ssh_path, "-V"], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 or result.stderr:
                log(f"SSH version: {result.stderr.strip()}")
                return True
            
            return False
        except Exception as e:
            log(f"Pinggy (SSH) verification failed: {e}")
            return False
    
    def _start_tunnel_with_detailed_progress(self) -> bool:
        """Start tunnel with detailed progress feedback."""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                if attempt > 0:
                    delay = min(2 ** attempt, 30)  # Max 30 second delay
                    print_info(f"🔄 Retry attempt {attempt + 1}/{max_attempts} in {delay}s...")
                    time.sleep(delay)
                
                print_info(f"🚀 Starting tunnel (attempt {attempt + 1}/{max_attempts})...")
                
                # Build command
                command = self._build_tunnel_command()
                if not command:
                    print_error("❌ Failed to build tunnel command")
                    return False
                
                log(f"Starting tunnel with command: {' '.join(command)}")
                
                # Start process
                print_info("📡 Launching tunnel process...")
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    preexec_fn=os.setsid if os.name != 'nt' else None
                )
                
                if not self.current_config:
                    self._cleanup_failed_process(process)
                    return False
                
                self.current_config.pid = process.pid
                self.current_config.state = TunnelState.STARTING
                
                if self.current_config.metrics:
                    self.current_config.metrics.connection_attempts += 1
                
                log(f"Tunnel process started with PID: {process.pid}")
                print_success(f"✅ Process started (PID: {process.pid})")
                
                # Start output monitoring
                print_info("👁️  Monitoring tunnel output...")
                monitor_thread = threading.Thread(
                    target=self._enhanced_output_monitor,
                    args=(process,),
                    daemon=True
                )
                monitor_thread.start()
                
                # Wait for tunnel to be ready with progress updates
                print_info("⏳ Waiting for tunnel connection...")
                if self._wait_for_tunnel_ready_with_progress(timeout=60):
                    self.current_config.state = TunnelState.RUNNING
                    if self.current_config.metrics:
                        self.current_config.metrics.successful_connections += 1
                    
                    log(f"Tunnel started successfully on attempt {attempt + 1}")
                    print_success("✅ Tunnel connection established!")
                    return True
                else:
                    print_warning(f"⚠️  Tunnel startup timeout (attempt {attempt + 1})")
                    self._cleanup_failed_process(process)
                    
            except Exception as e:
                error_msg = f"Tunnel start attempt {attempt + 1} failed: {e}"
                log(error_msg)
                print_error(f"❌ {error_msg}")
                
                if self.current_config and self.current_config.metrics:
                    self.current_config.metrics.failed_connections += 1
                    self.current_config.metrics.last_error = str(e)
        
        if self.current_config:
            self.current_config.state = TunnelState.FAILED
        return False
    
    def _wait_for_tunnel_ready_with_progress(self, timeout: int = 60) -> bool:
        """Wait for tunnel with progress updates."""
        start_time = time.time()
        last_update = start_time
        
        while time.time() - start_time < timeout:
            current_config = self.get_tunnel_config()
            
            if not current_config:
                return False
            
            # Show progress every 10 seconds
            current_time = time.time()
            if current_time - last_update >= 10:
                elapsed = int(current_time - start_time)
                remaining = timeout - elapsed
                print_info(f"⏳ Still waiting... ({elapsed}s elapsed, {remaining}s remaining)")
                last_update = current_time
            
            # Check if we have a URL
            if current_config.url:
                log(f"Tunnel URL detected: {current_config.url}")
                print_success(f"🌐 Tunnel URL: {current_config.url}")
                return True
            
            # For playit.gg, be more patient and check different conditions
            if current_config.service == TunnelService.PLAYIT:
                if current_config.pid and self._is_process_running(current_config.pid) and current_config.metrics and current_config.metrics.start_time:
                    uptime = datetime.now() - current_config.metrics.start_time
                    
                    # Give playit.gg more time and check logs
                    if uptime.total_seconds() > 15:
                        if self._check_tunnel_logs_for_success():
                            print_success("✅ Tunnel appears to be working (check logs for URL)")
                            return True
            
            time.sleep(2)
        
        print_error(f"❌ Tunnel startup timeout after {timeout} seconds")
        return False
    
    def _show_tunnel_connection_info(self):
        """Show detailed tunnel connection information."""
        if not self.current_config:
            return
        
        print("\n" + "="*60)
        print(f"🎉 {self.current_config.service.value.upper()} TUNNEL ACTIVE")
        print("="*60)
        
        if self.current_config.url:
            print(f"🌐 Connection URL: {UI.colors.CYAN}{self.current_config.url}{UI.colors.RESET}")
            
            # Show appropriate connection instructions
            if self.current_config.service == TunnelService.PLAYIT:
                if "tcp://" in self.current_config.url:
                    # Extract host and port from tcp://host:port
                    url_parts = self.current_config.url.replace("tcp://", "").split(":")
                    if len(url_parts) == 2:
                        host, port = url_parts
                        print(f"📝 Minecraft Server Address: {UI.colors.GREEN}{host}:{port}{UI.colors.RESET}")
                elif "joinmc.link" in self.current_config.url:
                    print(f"📝 Minecraft Server Address: {UI.colors.GREEN}{self.current_config.url}{UI.colors.RESET}")
        else:
            print("⚠️  URL not detected yet - check tunnel logs")
        
        if self.current_config.claim_url:
            print(f"🔗 Claim URL: {UI.colors.YELLOW}{self.current_config.claim_url}{UI.colors.RESET}")
        
        print(f"🔌 Local Port: {self.current_config.port}")
        print(f"🆔 Process ID: {self.current_config.pid}")
        print("="*60)
    
    def _show_startup_troubleshooting(self, service: TunnelService):
        """Show troubleshooting for tunnel startup failures."""
        print_warning("\n🛠️  Tunnel Startup Troubleshooting:")
        print_info("1. Check if your Minecraft server is running:")
        print_info(f"   netstat -ln | grep {self.current_config.port if self.current_config else 25565}")
        print_info("2. Check tunnel logs for detailed errors:")
        print_info(f"   tail -f {self.tunnel_logfile}")
        print_info("3. Try manual tunnel setup:")
        
        if service == TunnelService.PLAYIT:
            print_info("   playit --help")
        elif service == TunnelService.NGROK:
            print_info(f"   ngrok tcp {self.current_config.port if self.current_config else 25565}")
        
        print_info("4. Check system resources:")
        print_info("   free -h && df -h")
    
    def _check_tunnel_logs_for_success(self) -> bool:
        """Check tunnel logs for success indicators."""
        try:
            if not self.tunnel_logfile.exists():
                return False
            
            with open(self.tunnel_logfile, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for success indicators
            success_patterns = [
                "tunnel established",
                "connection successful",  
                "ready to accept",
                "tunnel is active",
                "tcp://",
                "joinmc.link",
                "playit.gg",
                "tunnel online"
            ]
            
            content_lower = content.lower()
            for pattern in success_patterns:
                if pattern in content_lower:
                    log(f"Found success indicator in logs: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            log(f"Error checking tunnel logs: {e}")
            return False

# Alias for backward compatibility
TunnelManager = RobustTunnelManager
