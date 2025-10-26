#!/usr/bin/env python3
"""
Tests for ServerManager
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from core.database import DatabaseManager
from core.logger import EnhancedLogger
from core.monitoring import PerformanceMonitor
from managers.server_manager import ServerManager

class TestServerManager(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / 'test.db'
        self.log_path = self.temp_dir / 'test.log'
        
        self.db = DatabaseManager(str(self.db_path))
        self.logger = EnhancedLogger(str(self.log_path))
        self.monitor = PerformanceMonitor(self.db, self.logger)
        self.server_mgr = ServerManager(self.db, self.logger, self.monitor)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_server(self):
        """Test server creation"""
        result = self.server_mgr.create_server('test_server')
        self.assertTrue(result)
        
        servers = self.server_mgr.list_servers()
        self.assertIn('test_server', servers)
    
    def test_sanitize_server_name(self):
        """Test server name sanitization"""
        result = self.server_mgr.create_server('test server with spaces!')
        self.assertTrue(result)
        
        servers = self.server_mgr.list_servers()
        # Should be sanitized to safe characters
        self.assertTrue(any('test' in s for s in servers))

if __name__ == '__main__':
    unittest.main()