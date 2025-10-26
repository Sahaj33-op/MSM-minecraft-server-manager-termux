#!/usr/bin/env python3
"""
Temporary shim: expose monitoring API separate from msm monolith.
Will be replaced by extracted core/monitoring.py
"""
from msm import server_monitor_thread as _thread

# Provide a minimal monitor facade
class PerformanceMonitor:
    def __init__(self, db=None):
        self.db = db
    def start_monitoring(self, server_name, pid):
        # In final version, run thread; here it's a no-op placeholder
        return True
