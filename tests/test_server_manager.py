#!/usr/bin/env python3
"""
Unit tests for ServerManager class.
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import shutil

# Add the project root to the path so we can import the modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server_manager import ServerManager
from config import ConfigManager, get_config_root, get_servers_root


class TestServerManager(unittest.TestCase):
    """Test cases for ServerManager class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use temporary directories for testing
        self.test_config_dir = Path(tempfile.mkdtemp())
        self.test_servers_dir = Path(tempfile.mkdtemp())
        
        # Patch the config root and servers root functions
        self.config_patch = patch('config.get_config_root', return_value=self.test_config_dir)
        self.servers_patch = patch('config.get_servers_root', return_value=self.test_servers_dir)
        self.config_patch.start()
        self.servers_patch.start()
        
        # Initialize the server manager
        self.server_manager = ServerManager()
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.config_patch.stop()
        self.servers_patch.stop()
        
        # Clean up temporary directories
        shutil.rmtree(self.test_config_dir, ignore_errors=True)
        shutil.rmtree(self.test_servers_dir, ignore_errors=True)
    
    def test_list_servers_empty(self):
        """Test list_servers when no servers exist."""
        servers = self.server_manager.list_servers()
        self.assertIsInstance(servers, list)
        self.assertEqual(len(servers), 0)
    
    def test_get_current_server_none(self):
        """Test get_current_server when no server is selected."""
        current = self.server_manager.get_current_server()
        self.assertIsNone(current)
    
    def test_set_and_get_current_server(self):
        """Test setting and getting the current server."""
        test_server = "test_server"
        
        # Set current server
        self.server_manager.set_current_server(test_server)
        
        # Get current server
        current = self.server_manager.get_current_server()
        self.assertEqual(current, test_server)
    
    def test_list_servers_with_servers(self):
        """Test list_servers when servers exist."""
        # Create some test server directories
        server1 = self.test_servers_dir / "server1"
        server2 = self.test_servers_dir / "server2"
        server1.mkdir()
        server2.mkdir()
        
        # Create server configs
        config1 = {"name": "server1", "created": 1234567890, "ram_mb": 1024}
        config2 = {"name": "server2", "created": 1234567891, "ram_mb": 2048}
        ConfigManager.save_server_config("server1", config1)
        ConfigManager.save_server_config("server2", config2)
        
        servers = self.server_manager.list_servers()
        self.assertIsInstance(servers, list)
        self.assertEqual(len(servers), 2)
        self.assertIn("server1", servers)
        self.assertIn("server2", servers)
    
    def test_create_server_invalid_name(self):
        """Test server creation with invalid name."""
        # Test empty name
        with patch('builtins.input', return_value=''):
            with patch('server_manager.print_error') as mock_print:
                self.server_manager.create_server_menu()
                mock_print.assert_called_with("Server name cannot be empty")
    
    def test_create_server_invalid_characters(self):
        """Test server creation with invalid characters."""
        # Test name with invalid characters
        with patch('builtins.input', return_value='server@name'):
            with patch('server_manager.print_error') as mock_print:
                self.server_manager.create_server_menu()
                mock_print.assert_called_with("Invalid characters in name")
    
    def test_create_server_already_exists(self):
        """Test server creation when server already exists."""
        # Create a server directory
        server_path = self.test_servers_dir / "testserver"
        server_path.mkdir()
        
        # Try to create the same server
        with patch('builtins.input', return_value='testserver'):
            with patch('server_manager.print_error') as mock_print:
                self.server_manager.create_server_menu()
                mock_print.assert_called_with("Server 'testserver' already exists")
    
    def test_create_server_success(self):
        """Test successful server creation."""
        # Mock user input and time
        with patch('builtins.input', return_value='newserver'):
            with patch('time.time', return_value=1234567890):
                with patch('server_manager.print_success') as mock_success:
                    self.server_manager.create_server_menu()
                    # Check that success message was printed
                    mock_success.assert_called()
    
    def test_switch_server_no_servers(self):
        """Test switching servers when no servers exist."""
        servers = self.server_manager.list_servers()
        self.assertEqual(len(servers), 0)
    
    def test_switch_server_success(self):
        """Test successful server switching."""
        # Create test servers
        server1 = self.test_servers_dir / "server1"
        server2 = self.test_servers_dir / "server2"
        server1.mkdir()
        server2.mkdir()
        
        # Create server configs
        config1 = {"name": "server1", "created": 1234567890, "ram_mb": 1024}
        config2 = {"name": "server2", "created": 1234567891, "ram_mb": 2048}
        ConfigManager.save_server_config("server1", config1)
        ConfigManager.save_server_config("server2", config2)
        
        # Set current server to server1
        self.server_manager.set_current_server("server1")
        current = self.server_manager.get_current_server()
        self.assertEqual(current, "server1")
        
        # Switch to server2
        self.server_manager.set_current_server("server2")
        current = self.server_manager.get_current_server()
        self.assertEqual(current, "server2")
    
    def test_start_server_no_current(self):
        """Test starting server when no server is selected."""
        with patch('server_manager.print_error') as mock_print:
            self.server_manager.start_server_menu()
            mock_print.assert_called_with("No server selected.")
    
    def test_stop_server_no_current(self):
        """Test stopping server when no server is selected."""
        with patch('server_manager.print_error') as mock_print:
            self.server_manager.stop_server_menu()
            mock_print.assert_called_with("No server selected.")
    
    def test_install_update_no_current(self):
        """Test installing update when no server is selected."""
        with patch('server_manager.print_error') as mock_print:
            self.server_manager.install_update_menu()
            mock_print.assert_called_with("No server selected.")


if __name__ == "__main__":
    unittest.main()