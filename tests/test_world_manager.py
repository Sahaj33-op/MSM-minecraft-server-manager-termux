#!/usr/bin/env python3
"""
Unit tests for WorldManager class.
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add the project root to the path so we can import the modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from world_manager import WorldManager
from config import ConfigManager, get_config_root, get_servers_root


class TestWorldManager(unittest.TestCase):
    """Test cases for WorldManager class."""
    
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
        
        # Initialize the world manager
        self.world_manager = WorldManager()
    
    def tearDown(self):
        """Tear down test fixtures after each test method."""
        self.config_patch.stop()
        self.servers_patch.stop()
        
        # Clean up temporary directories
        shutil.rmtree(self.test_config_dir, ignore_errors=True)
        shutil.rmtree(self.test_servers_dir, ignore_errors=True)
    
    def test_create_backup_no_server(self):
        """Test creating backup when no server is selected."""
        with patch('server_manager.ServerManager.get_current_server', return_value=None):
            with patch('world_manager.print_error') as mock_print:
                self.world_manager.create_backup(None)
                mock_print.assert_called_with("No server selected.")
    
    def test_create_backup_no_server_directory(self):
        """Test creating backup when server directory doesn't exist."""
        server_name = "testserver"
        with patch('world_manager.print_error') as mock_print:
            self.world_manager.create_backup(server_name)
            # Should show error about server directory not found
            mock_print.assert_called()
    
    def test_create_backup_no_world_directories(self):
        """Test creating backup when no world directories exist."""
        server_name = "testserver"
        server_path = self.test_servers_dir / server_name
        server_path.mkdir(parents=True)
        
        with patch('server_manager.ServerManager.get_current_server', return_value=server_name):
            with patch('world_manager.print_warning') as mock_print:
                self.world_manager.create_backup(server_name)
                mock_print.assert_called_with("No world directories found.")
    
    def test_create_backup_success(self):
        """Test successful backup creation."""
        server_name = "testserver"
        server_path = self.test_servers_dir / server_name
        server_path.mkdir(parents=True)
        
        # Create a world directory
        world_path = server_path / "world"
        world_path.mkdir()
        
        # Create a test file in the world directory
        test_file = world_path / "level.dat"
        test_file.write_text("test data")
        
        with patch('server_manager.ServerManager.get_current_server', return_value=server_name):
            with patch('world_manager.print_success') as mock_print:
                self.world_manager.create_backup(server_name)
                # Should show success message
                mock_print.assert_called()
    
    def test_list_backups_no_server(self):
        """Test listing backups when no server is selected."""
        with patch('server_manager.ServerManager.get_current_server', return_value=None):
            with patch('world_manager.print_error') as mock_print:
                self.world_manager.list_backups(None)
                mock_print.assert_called_with("No server selected.")
    
    def test_list_backups_no_backups_directory(self):
        """Test listing backups when backups directory doesn't exist."""
        server_name = "testserver"
        server_path = self.test_servers_dir / server_name
        server_path.mkdir(parents=True)
        
        with patch('server_manager.ServerManager.get_current_server', return_value=server_name):
            with patch('world_manager.print_info') as mock_print:
                self.world_manager.list_backups(server_name)
                mock_print.assert_called_with("No backups directory found.")
    
    def test_list_backups_no_backups(self):
        """Test listing backups when no backups exist."""
        server_name = "testserver"
        server_path = self.test_servers_dir / server_name
        server_path.mkdir(parents=True)
        
        # Create backups directory
        backups_dir = server_path / "backups"
        backups_dir.mkdir()
        
        with patch('server_manager.ServerManager.get_current_server', return_value=server_name):
            with patch('world_manager.print_info') as mock_print:
                self.world_manager.list_backups(server_name)
                mock_print.assert_called_with("No backups found.")
    
    def test_restore_backup_no_server(self):
        """Test restoring backup when no server is selected."""
        with patch('server_manager.ServerManager.get_current_server', return_value=None):
            with patch('world_manager.print_error') as mock_print:
                self.world_manager.restore_backup(None)
                mock_print.assert_called_with("No server selected.")


if __name__ == "__main__":
    unittest.main()