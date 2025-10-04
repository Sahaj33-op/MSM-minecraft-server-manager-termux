#!/usr/bin/env python3
"""
Unit tests for TunnelManager class.
"""

import unittest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add the project root to the path so we can import the modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tunnel_manager import TunnelManager


class TestTunnelManager(unittest.TestCase):
    """Test cases for TunnelManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use temporary directory for testing
        self.test_config_dir = Path(tempfile.mkdtemp())
        
        # Patch the config root function
        self.config_patch = patch('config.get_config_root', return_value=self.test_config_dir)
        self.config_patch.start()
        
        # Initialize the tunnel manager
        self.tunnel_manager = TunnelManager()
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.config_patch.stop()
        
        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_config_dir, ignore_errors=True)
    
    def test_tunnel_menu_playit(self):
        """Test tunnel menu selection for playit."""
        with patch('builtins.input', return_value='1'):
            with patch.object(self.tunnel_manager, 'setup_playit') as mock_setup:
                self.tunnel_manager.tunneling_menu()
                mock_setup.assert_called_once()
    
    def test_tunnel_menu_ngrok(self):
        """Test tunnel menu selection for ngrok."""
        with patch('builtins.input', return_value='2'):
            with patch.object(self.tunnel_manager, 'setup_ngrok') as mock_setup:
                self.tunnel_manager.tunneling_menu()
                mock_setup.assert_called_once()
    
    def test_tunnel_menu_cloudflared(self):
        """Test tunnel menu selection for cloudflared."""
        with patch('builtins.input', return_value='3'):
            with patch.object(self.tunnel_manager, 'setup_cloudflared') as mock_setup:
                self.tunnel_manager.tunneling_menu()
                mock_setup.assert_called_once()
    
    def test_tunnel_menu_exit(self):
        """Test tunnel menu exit option."""
        with patch('builtins.input', return_value='0'):
            # Should not call any setup methods
            with patch.object(self.tunnel_manager, 'setup_playit') as mock_playit:
                with patch.object(self.tunnel_manager, 'setup_ngrok') as mock_ngrok:
                    with patch.object(self.tunnel_manager, 'setup_cloudflared') as mock_cloudflared:
                        self.tunnel_manager.tunneling_menu()
                        mock_playit.assert_not_called()
                        mock_ngrok.assert_not_called()
                        mock_cloudflared.assert_not_called()
    
    def test_setup_playit_with_existing_token(self):
        """Test playit setup with existing token."""
        # Mock credentials manager to return existing token
        with patch('config.CredentialsManager.get', return_value='test-token'):
            with patch('builtins.input', return_value='Y'):  # Use existing token
                with patch('tunnel_manager.print_success') as mock_print:
                    self.tunnel_manager.setup_playit()
                    mock_print.assert_called()
    
    def test_setup_playit_without_token(self):
        """Test playit setup without existing token."""
        # Mock credentials manager to return no token
        with patch('config.CredentialsManager.get', return_value=None):
            with patch('builtins.input', return_value=''):  # Skip setup
                with patch('tunnel_manager.print_warning') as mock_print:
                    self.tunnel_manager.setup_playit()
                    mock_print.assert_called_with("Token setup skipped")


if __name__ == "__main__":
    unittest.main()