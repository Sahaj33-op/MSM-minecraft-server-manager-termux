#!/usr/bin/env python3
"""
Enhanced Tests for TunnelManager
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.logger import EnhancedLogger
from managers.tunnel_manager import TunnelManager

class TestEnhancedTunnelManager(unittest.TestCase):
    
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
    
    def test_list_tunnels(self):
        """Test listing all tunnels"""
        tunnels = self.tunnel_mgr.list_tunnels()
        self.assertIn('ngrok', tunnels)
        self.assertIn('cloudflared', tunnels)
        self.assertIn('pinggy', tunnels)
        self.assertIn('playit', tunnels)
        
        # Check that all tunnels have status and url
        for name, info in tunnels.items():
            self.assertIn('status', info)
            self.assertIn('url', info)
    
    def test_check_tunnel_status(self):
        """Test checking tunnel status"""
        status_report = self.tunnel_mgr.check_tunnel_status()
        # Should be empty since no tunnels are running
        self.assertIsInstance(status_report, dict)
    
    @patch('shutil.which')
    def test_start_ngrok_missing(self, mock_which):
        """Test ngrok start when ngrok is not installed"""
        mock_which.return_value = None
        result = self.tunnel_mgr.start_ngrok(25565)
        self.assertFalse(result)
    
    @patch('shutil.which')
    def test_start_cloudflared_missing(self, mock_which):
        """Test cloudflared start when cloudflared is not installed"""
        mock_which.return_value = None
        result = self.tunnel_mgr.start_cloudflared(25565)
        self.assertFalse(result)
    
    @patch('shutil.which')
    def test_start_pinggy_missing(self, mock_which):
        """Test pinggy start when ssh is not installed"""
        mock_which.return_value = None
        result = self.tunnel_mgr.start_pinggy(25565)
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()