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
        self.db_manager = db_manager
        self.logger = logger
        self.monitor_threads = {}
        self.stop_events = {}

    def _log(self, level, message):
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def start_monitoring(self, server_name: str, pid: int) -> bool:
        """Start monitoring a server process"""
        if server_name in self.monitor_threads:
            self._log('WARNING', f'Monitoring already active for {server_name}')
            return False

        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=self._monitor_thread,
            args=(server_name, pid, stop_event),
            daemon=True
        )
        
        self.stop_events[server_name] = stop_event
        self.monitor_threads[server_name] = monitor_thread
        
        monitor_thread.start()
        self._log('INFO', f'Started monitoring {server_name} (PID: {pid})')
        return True

    def stop_monitoring(self, server_name: str) -> bool:
        """Stop monitoring a server"""
        if server_name not in self.stop_events:
            return False

        self.stop_events[server_name].set()
        if server_name in self.monitor_threads:
            self.monitor_threads[server_name].join(timeout=5)
            del self.monitor_threads[server_name]
        del self.stop_events[server_name]
        
        self._log('INFO', f'Stopped monitoring {server_name}')
        return True

    def _monitor_thread(self, server_name: str, pid: int, stop_event: threading.Event):
        """Monitoring thread for a server process"""
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
                                self.db_manager.log_performance_metric(server_name, mem, cpu)
                    else:
                        self._log('WARNING', f'Process {pid} for {server_name} is no longer running')
                        break
                except psutil.NoSuchProcess:
                    self._log('WARNING', f'Process {pid} for {server_name} not found')
                    break
                except Exception as e:
                    self._log('ERROR', f'Error monitoring {server_name}: {e}')
                    
        except psutil.NoSuchProcess:
            self._log('WARNING', f'Monitoring failed: Process {pid} for {server_name} not found')
        except Exception as e:
            self._log('ERROR', f'Error in monitoring thread for {server_name}: {e}')
        
        self._log('INFO', f'Monitoring thread stopped for {server_name}')

    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for UI display"""
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