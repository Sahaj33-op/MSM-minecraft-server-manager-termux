#!/usr/bin/env python3
"""
Performance Monitor - Extracted from main branch msm.py
Real-time CPU/RAM monitoring with threading
"""
import psutil
import threading
import time
from typing import Optional, Dict, Any

class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, db_manager=None, logger=None):
        """Initialize the PerformanceMonitor.
        
        Args:
            db_manager: DatabaseManager instance for storing metrics
            logger: Logger instance for logging messages
        """
        self.db_manager = db_manager
        self.logger = logger
        self.monitor_threads = {}
        self.stop_events = {}
        self._lock = threading.Lock()  # Thread safety lock

    def _log(self, level, message):
        """Log a message using the logger or print to console.
        
        Args:
            level: Log level (INFO, ERROR, WARNING, etc.)
            message: Message to log
        """
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def start_monitoring(self, server_name: str, pid: int) -> bool:
        """Start monitoring a server process.
        
        Args:
            server_name: Name of the server to monitor
            pid: Process ID of the server process
            
        Returns:
            True if monitoring started successfully, False otherwise
        """
        with self._lock:
            if server_name in self.monitor_threads:
                self._log('WARNING', f'Monitoring already active for {server_name}')
                return False

            stop_event = threading.Event()
            monitor_thread = threading.Thread(
                target=self._monitor_thread,
                args=(server_name, pid, stop_event),
                daemon=True,
                name=f"monitor-{server_name}"
            )
            
            self.stop_events[server_name] = stop_event
            self.monitor_threads[server_name] = monitor_thread
            
            monitor_thread.start()
            self._log('INFO', f'Started monitoring {server_name} (PID: {pid})')
            return True

    def stop_monitoring(self, server_name: str) -> bool:
        """Stop monitoring a server.
        
        Args:
            server_name: Name of the server to stop monitoring
            
        Returns:
            True if monitoring stopped successfully, False otherwise
        """
        with self._lock:
            if server_name not in self.stop_events:
                return False

            self.stop_events[server_name].set()
            if server_name in self.monitor_threads:
                thread = self.monitor_threads[server_name]
                thread.join(timeout=5)
                if thread.is_alive():
                    self._log('WARNING', f'Monitor thread for {server_name} did not stop gracefully')
                del self.monitor_threads[server_name]
            del self.stop_events[server_name]
            
            self._log('INFO', f'Stopped monitoring {server_name}')
            return True

    def _monitor_thread(self, server_name: str, pid: int, stop_event: threading.Event):
        """Monitoring thread for a server process.
        
        Args:
            server_name: Name of the server being monitored
            pid: Process ID of the server process
            stop_event: Event to signal thread termination
        """
        process = None
        try:
            process = psutil.Process(pid)
            self._log('INFO', f'Monitoring thread started for {server_name} (PID: {pid})')
            
            while not stop_event.wait(60):  # 60-second intervals
                try:
                    if process.is_running():
                        with process.oneshot():
                            cpu = process.cpu_percent()
                            mem = process.memory_percent()
                            if self.db_manager:
                                try:
                                    self.db_manager.log_performance_metric(server_name, mem, cpu)
                                except Exception as db_error:
                                    self._log('ERROR', f'Database error logging metrics for {server_name}: {db_error}')
                    else:
                        self._log('WARNING', f'Process {pid} for {server_name} is no longer running')
                        break
                except psutil.NoSuchProcess:
                    self._log('WARNING', f'Process {pid} for {server_name} not found')
                    break
                except psutil.AccessDenied:
                    self._log('ERROR', f'Access denied monitoring process {pid} for {server_name}')
                    break
                except Exception as e:
                    self._log('ERROR', f'Error monitoring {server_name}: {e}')
                    # Continue monitoring despite errors
                    continue
                    
        except psutil.NoSuchProcess:
            self._log('WARNING', f'Monitoring failed: Process {pid} for {server_name} not found')
        except psutil.AccessDenied:
            self._log('ERROR', f'Access denied to process {pid} for {server_name}')
        except Exception as e:
            self._log('ERROR', f'Error in monitoring thread for {server_name}: {e}')
        finally:
            # Clean up thread references
            with self._lock:
                if server_name in self.monitor_threads:
                    del self.monitor_threads[server_name]
                if server_name in self.stop_events:
                    del self.stop_events[server_name]
            self._log('INFO', f'Monitoring thread stopped for {server_name}')

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for UI display.
        
        Returns:
            Dictionary containing system information
        """
        try:
            mem = psutil.virtual_memory()
            total_ram_mb = mem.total // (1024 * 1024)
            available_ram_mb = mem.available // (1024 * 1024)
            cpu_count = psutil.cpu_count(logical=True) or 2
            cpu_usage = psutil.cpu_percent(interval=1)
            
            return {
                'total_ram_mb': total_ram_mb,
                'available_ram_mb': available_ram_mb,
                'cpu_count': cpu_count,
                'cpu_usage': cpu_usage
            }
        except Exception as e:
            if self.logger:
                self.logger.log('WARNING', f'Could not detect system info: {e}')
            return {
                'total_ram_mb': 2048,
                'available_ram_mb': 1024,
                'cpu_count': 2,
                'cpu_usage': 0.0
            }

    def get_health_check(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """Perform a health check on the system and optionally a specific server.

        Args:
            server_name: Optional server name to check specific server health

        Returns:
            Dictionary containing health status information
        """
        health = {
            'status': 'healthy',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system': {},
            'warnings': [],
            'errors': []
        }

        # System health checks
        try:
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            health['system'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.5),
                'memory_percent': mem.percent,
                'memory_available_mb': mem.available // (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free // (1024 * 1024 * 1024)
            }

            # Check for high resource usage
            if mem.percent > 90:
                health['warnings'].append(f"High memory usage: {mem.percent:.1f}%")
                health['status'] = 'degraded'

            if disk.percent > 90:
                health['warnings'].append(f"Low disk space: {100 - disk.percent:.1f}% free")
                health['status'] = 'degraded'

        except Exception as e:
            health['errors'].append(f"Failed to get system info: {e}")
            health['status'] = 'unhealthy'

        # Server-specific health check
        if server_name:
            health['server'] = self._check_server_health(server_name)
            if health['server'].get('status') == 'unhealthy':
                health['status'] = 'unhealthy'
            elif health['server'].get('status') == 'degraded' and health['status'] != 'unhealthy':
                health['status'] = 'degraded'

        # Determine overall status based on warnings/errors
        if health['errors']:
            health['status'] = 'unhealthy'
        elif health['warnings'] and health['status'] != 'unhealthy':
            health['status'] = 'degraded'

        return health

    def _check_server_health(self, server_name: str) -> Dict[str, Any]:
        """Check health of a specific server.

        Args:
            server_name: Name of the server to check

        Returns:
            Dictionary containing server health status
        """
        server_health = {
            'name': server_name,
            'status': 'unknown',
            'monitoring_active': False,
            'process_running': False
        }

        with self._lock:
            if server_name in self.monitor_threads:
                server_health['monitoring_active'] = True
                thread = self.monitor_threads[server_name]
                server_health['thread_alive'] = thread.is_alive()

        # Check if server process is running (basic check)
        from utils.helpers import get_screen_session_name, is_screen_session_running

        screen_name = get_screen_session_name(server_name)
        if is_screen_session_running(screen_name):
            server_health['process_running'] = True
            server_health['status'] = 'healthy'
        else:
            server_health['status'] = 'stopped'

        return server_health

    def get_active_monitors(self) -> Dict[str, bool]:
        """Get status of all active monitoring threads.

        Returns:
            Dictionary mapping server names to their monitoring thread status
        """
        with self._lock:
            return {
                name: thread.is_alive()
                for name, thread in self.monitor_threads.items()
            }