#!/usr/bin/env python3
"""
Tests for TunnelManager
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from core.logger import EnhancedLogger
from managers.tunnel_manager import TunnelManager

class TestTunnelManager(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_path = self.temp_dir / 'test.log'
        
        self.logger = EnhancedLogger(str(self.log_path))
        self.tunnel_mgr = TunnelManager(self.logger)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_tunnel_status(self):
        """Test tunnel status tracking"""
        # Initially no tunnels should be running
        status = self.tunnel_mgr.get_tunnel_status('ngrok')
        self.assertEqual(status, "NOT_STARTED")
    
    def test_tunnel_info(self):
        """Test tunnel information storage"""
        # Test that we can store and retrieve tunnel info
        self.tunnel_mgr._update_tunnel_info('test_tunnel', {'url': 'http://example.com', 'port': 25565})
        url = self.tunnel_mgr.get_tunnel_url('test_tunnel')
        self.assertEqual(url, 'http://example.com')
        
        # Test non-existent tunnel info
        url = self.tunnel_mgr.get_tunnel_url('nonexistent')
        self.assertEqual(url, 'Not available')

if __name__ == '__main__':
    unittest.main()