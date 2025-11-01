#!/usr/bin/env python3
"""
Enhanced Tests for TunnelManager
"""
import unittest
import tempfile
import shutil
import subprocess
import json
import signal
import os
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

    @patch('shutil.which')
    @patch('managers.tunnel_manager.subprocess.Popen')
    def test_start_ngrok_success(self, mock_popen, mock_which):
        """Test successful ngrok start"""
        mock_which.return_value = '/usr/bin/ngrok'
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        # --- Execute ---
        result = self.tunnel_mgr.start_ngrok(25565)

        # --- Assert ---
        self.assertTrue(result)
        mock_popen.assert_called_once_with(
            ["ngrok", "tcp", "25565"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.assertIn('ngrok', self.tunnel_mgr.tunnel_processes)
        self.assertEqual(self.tunnel_mgr.tunnel_processes['ngrok'], mock_process)

    @patch('managers.tunnel_manager.subprocess.Popen')
    def test_start_ngrok_failure(self, mock_popen):
        """Test ngrok start failure"""
        mock_popen.side_effect = Exception("Failed to start process")
        
        with patch('shutil.which', return_value='/usr/bin/ngrok'):
            result = self.tunnel_mgr.start_ngrok(25565)
            self.assertFalse(result)

    @patch('managers.tunnel_manager.psutil.pid_exists')
    @patch('managers.tunnel_manager.TunnelManager._save_tunnel_state')
    def test_stop_tunnel_success(self, mock_save_state, mock_pid_exists):
        """Test successful tunnel stop"""
        # Create a mock process
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is running
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()
        
        self.tunnel_mgr.tunnel_processes['ngrok'] = mock_proc
        self.tunnel_mgr.tunnel_info['ngrok'] = {'port': 25565, 'url': 'http://example.com'}
        
        mock_pid_exists.return_value = True  # Process exists

        # --- Execute ---
        result = self.tunnel_mgr.stop_tunnel('ngrok')

        # --- Assert ---
        self.assertTrue(result)
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once()
        mock_save_state.assert_called()
        # Check that tunnel info was cleared
        self.assertNotIn('ngrok', self.tunnel_mgr.tunnel_processes)
        self.assertNotIn('ngrok', self.tunnel_mgr.tunnel_info)

    @patch('managers.tunnel_manager.TunnelManager._save_tunnel_state')
    def test_stop_tunnel_not_running(self, mock_save_state):
        """Test stopping a tunnel that's not running"""
        result = self.tunnel_mgr.stop_tunnel('nonexistent')
        self.assertFalse(result)

    @patch('managers.tunnel_manager.TunnelManager._save_tunnel_state')
    def test_extract_ngrok_url(self, mock_save_state):
        """Test extracting ngrok URL from output"""
        # Setup initial tunnel info
        self.tunnel_mgr.tunnel_info = {'ngrok': {'port': 25565, 'url': 'Extracting...'}}
        
        # Create a mock process
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None  # Process is running
        mock_proc.stdout.readline.return_value = b'https://abcd1234.ngrok.io\n'
        
        # --- Execute ---
        self.tunnel_mgr._extract_ngrok_url(mock_proc, 'ngrok')
        
        # --- Assert ---
        # Check that the URL was extracted and saved
        self.assertIn('ngrok', self.tunnel_mgr.tunnel_info)
        self.assertIn('url', self.tunnel_mgr.tunnel_info['ngrok'])
        self.assertTrue(self.tunnel_mgr.tunnel_info['ngrok']['url'].endswith('.ngrok.io'))

    @patch('managers.tunnel_manager.subprocess.Popen')
    def test_start_cloudflared_success(self, mock_popen):
        """Test successful cloudflared start"""
        mock_process = MagicMock()
        mock_process.pid = 12346
        mock_popen.return_value = mock_process

        with patch('shutil.which', return_value='/usr/bin/cloudflared'):
            result = self.tunnel_mgr.start_cloudflared(25565)
            self.assertTrue(result)
            mock_popen.assert_called_once_with(
                ["cloudflared", "tunnel", "--url", "tcp://localhost:25565"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.assertIn('cloudflared', self.tunnel_mgr.tunnel_processes)
            self.assertEqual(self.tunnel_mgr.tunnel_processes['cloudflared'], mock_process)

    @patch('managers.tunnel_manager.subprocess.Popen')
    def test_start_pinggy_success(self, mock_popen):
        """Test successful pinggy start"""
        mock_process = MagicMock()
        mock_process.pid = 12347
        mock_popen.return_value = mock_process

        with patch('shutil.which', return_value='/usr/bin/ssh'):
            result = self.tunnel_mgr.start_pinggy(25565)
            self.assertTrue(result)
            # Check that ssh command was called (exact command may vary)
            mock_popen.assert_called_once()
            self.assertIn('pinggy', self.tunnel_mgr.tunnel_processes)

if __name__ == '__main__':
    unittest.main()