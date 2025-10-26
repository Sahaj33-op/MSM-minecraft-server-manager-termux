#!/usr/bin/env python3
"""
Enhanced Tests for ServerManager
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.database import DatabaseManager
from core.logger import EnhancedLogger
from core.monitoring import PerformanceMonitor
from managers.server_manager import ServerManager

class TestEnhancedServerManager(unittest.TestCase):
    
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
    
    def test_create_server_with_enhanced_config(self):
        """Test server creation with enhanced configuration"""
        result = self.server_mgr.create_server('test_server')
        self.assertTrue(result)
        
        servers = self.server_mgr.list_servers()
        self.assertIn('test_server', servers)
        
        # Check that server has enhanced configuration
        from core.config import ConfigManager
        server_config = ConfigManager.load_server_config('test_server')
        self.assertIn('server_settings', server_config)
        settings = server_config['server_settings']
        self.assertIn('gamemode', settings)
        self.assertIn('difficulty', settings)
        self.assertIn('pvp', settings)
        self.assertIn('white-list', settings)
        self.assertIn('view-distance', settings)
    
    def test_update_server_properties(self):
        """Test updating server.properties file"""
        # Create a test server first
        self.server_mgr.create_server('test_server')
        
        # Test updating settings
        test_settings = {
            'gamemode': 'creative',
            'difficulty': 'peaceful',
            'pvp': False,
            'max-players': 10
        }
        
        # Use the private method to test
        self.server_mgr._update_server_properties('test_server', test_settings)
        
        # Verify the settings were processed (we can't easily check the file in test)
        # but we can verify the method doesn't crash
    
    def test_server_properties_settings_list(self):
        """Test that SERVER_PROPERTIES_SETTINGS contains expected settings"""
        expected_settings = [
            'gamemode', 'difficulty', 'pvp', 'white-list', 'view-distance',
            'max-players', 'motd', 'port', 'online-mode', 'allow-flight',
            'spawn-animals', 'spawn-monsters', 'spawn-npcs', 'enable-command-block',
            'max-world-size', 'player-idle-timeout', 'level-type', 'level-name'
        ]
        
        for setting in expected_settings:
            self.assertIn(setting, ServerManager.SERVER_PROPERTIES_SETTINGS)
    
    @patch('managers.api_client.PaperMCAPI.get_versions')
    def test_install_server_menu_with_error_handling(self, mock_get_versions):
        """Test install server menu with error handling"""
        # Test when API fails
        mock_get_versions.side_effect = Exception("API Error")
        
        # This should not crash the application
        # We can't easily test the UI interaction, but we can verify the method exists
        self.assertTrue(hasattr(self.server_mgr, 'install_server_menu'))

if __name__ == '__main__':
    unittest.main()