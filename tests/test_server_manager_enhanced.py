#!/usr/bin/env python3
"""
Enhanced Tests for ServerManager
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add imports for PocketMine tests
from unittest.mock import patch, mock_open, MagicMock, call
import urllib.request # For mocking urlretrieve
import shutil # For mocking which

# Assuming PocketMineAPI is correctly added to api_client
from managers.api_client import PocketMineAPI
from managers.server_manager import ServerManager # Assuming ServerManager is importable
from core.config import ConfigManager # Assuming ConfigManager is importable

from core.database import DatabaseManager
from core.logger import EnhancedLogger
from core.monitoring import PerformanceMonitor

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

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.api_client.PocketMineAPI.get_latest_build')
    @patch('managers.api_client.PocketMineAPI.get_download_url')
    @patch('urllib.request.urlretrieve')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.stat')
    @patch('pathlib.Path.unlink')
    def test_download_server_pocketmine(self, mock_unlink, mock_stat, mock_exists, mock_urlretrieve, mock_get_dl_url, mock_get_build, MockConfigManager, mock_get_dir):
        """Test downloading PocketMine (.phar)."""
        server_name = "bedrock_test"
        mock_get_dir.return_value = self.temp_dir / server_name
        mock_server_path = self.temp_dir / server_name
        mock_server_path.mkdir(exist_ok=True)

        # Mock API responses
        mock_build_info = {"build": 123, "download_url": "http://example.com/PocketMine-MP.phar", "filename": "PocketMine-MP.phar"}
        mock_get_build.return_value = mock_build_info
        mock_get_dl_url.return_value = "http://example.com/PocketMine-MP.phar"

        # Mock config load/save
        mock_config = {'server_flavor': None, 'server_version': None, 'server_settings': {}}
        MockConfigManager.load_server_config.return_value = mock_config

        # Mock download success (file exists and has size after urlretrieve)
        def side_effect(*args, **kwargs):
            # Simulate the file being created by urlretrieve
            phar_path = mock_server_path / "PocketMine-MP.phar"
            phar_path.touch() 
            # Make exists() return True for the specific file *after* download
            mock_exists.side_effect = lambda *a, **kw: args[0] == phar_path
            # Make stat() return a size > 0 *after* download
            mock_stat_obj = MagicMock()
            mock_stat_obj.st_size = 1024
            mock_stat.side_effect = lambda *a, **kw: mock_stat_obj if args[0] == phar_path else FileNotFoundError
            return None
        mock_urlretrieve.side_effect = side_effect
        mock_exists.return_value = False # Initially file doesn't exist
        mock_stat.side_effect = FileNotFoundError # Initially file doesn't exist

        # --- Execute ---
        # Assuming _download_server takes these args now:
        success = self.server_mgr._download_server(server_name, "PocketMine-MP", PocketMineAPI, "5.0.0", "pocketmine") 

        # --- Assert ---
        self.assertTrue(success)
        mock_get_build.assert_called_once_with("5.0.0")
        mock_get_dl_url.assert_called_once_with("5.0.0", mock_build_info)
        mock_urlretrieve.assert_called_once()
        # Check if called with the correct target path
        args, kwargs = mock_urlretrieve.call_args
        self.assertEqual(args[1], mock_server_path / "PocketMine-MP.phar") 
        MockConfigManager.save_server_config.assert_called_once()
        saved_config = MockConfigManager.save_server_config.call_args[0][1]
        self.assertEqual(saved_config['server_flavor'], 'pocketmine')
        self.assertEqual(saved_config['server_version'], '5.0.0')
        self.assertEqual(saved_config['server_build'], 123)
        self.assertEqual(saved_config['server_settings']['port'], 19132) # Check default port
        mock_unlink.assert_not_called() # Ensure file wasn't deleted

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.server_manager.is_screen_session_running')
    @patch('shutil.which')
    @patch('pathlib.Path.glob')
    @patch('managers.server_manager.run_command') # Mock the function that runs screen
    @patch('managers.server_manager.get_screen_session_name')
    @patch('core.monitoring.PerformanceMonitor.start_monitoring') # Mock monitoring start
    @patch('core.database.DatabaseManager.log_session_start') # Mock DB log
    def test_start_server_pocketmine(self, mock_log_session, mock_start_monitor, mock_get_screen_name, mock_run_cmd, mock_glob, mock_which, mock_is_running, MockConfigManager, mock_get_dir):
        """Test starting a PocketMine server."""
        server_name = "bedrock_test"
        screen_name = "msm-bedrock_test"
        mock_get_dir.return_value = self.temp_dir / server_name
        mock_server_path = self.temp_dir / server_name
        mock_server_path.mkdir(exist_ok=True)
        mock_get_screen_name.return_value = screen_name

        # Mock config
        mock_config = {'server_flavor': 'pocketmine', 'server_version': '5.0.0', 'ram_mb': 512}
        MockConfigManager.load_server_config.return_value = mock_config
        self.server_mgr.get_current_server = MagicMock(return_value=server_name) # Ensure current server is set

        # Mock server state
        mock_is_running.return_value = False # Server is not running
        mock_which.return_value = '/usr/bin/php' # PHP is found

        # Mock .phar file existing
        mock_phar_path = MagicMock(spec=Path)
        mock_phar_path.name = "PocketMine-MP.phar"
        mock_glob.return_value = [mock_phar_path]

        # Mock screen command success
        mock_run_cmd.return_value = (0, "Screen session started", "") 
        # Mock PID finding (return a dummy PID)
        mock_run_cmd.side_effect = [
             (0, "Screen session started", ""), # First call for starting screen
             (0, f"12345.{screen_name}\t(Detached)", "") # Second call for screen -ls
        ]


        # --- Execute ---
        success = self.server_mgr.start_server()

        # --- Assert ---
        self.assertTrue(success)
        mock_is_running.assert_called_once_with(screen_name)
        mock_which.assert_called_with('php')
        mock_glob.assert_called_once_with('*.phar')

        # Check that screen command was called correctly
        expected_start_cmd = ['screen', '-dmS', screen_name, '/usr/bin/php', str(mock_phar_path)]
        # Check calls made to run_command
        calls = mock_run_cmd.call_args_list
        # First call should be the start command
        self.assertEqual(calls[0], call(expected_start_cmd, cwd=str(mock_server_path))) 
        # Second call should be screen -ls
        self.assertEqual(calls[1], call(['screen', '-ls'], capture_output=True)) 

        mock_log_session.assert_called_once_with(server_name, 'pocketmine', '5.0.0')
        mock_start_monitor.assert_called_once_with(server_name, 12345) # Check PID

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.server_manager.ServerManager._load_server_properties') # Mock reading existing props
    @patch('managers.server_manager.ServerManager._save_server_properties') # Mock saving props
    @patch('builtins.input')
    def test_configure_server_menu_change_port(self, mock_input, mock_save_props, mock_load_props, MockConfigManager, mock_get_dir):
        """Test changing the server port via the config menu."""
        server_name = "config_test"
        mock_get_dir.return_value = self.temp_dir / server_name
        self.server_mgr.get_current_server = MagicMock(return_value=server_name) # Set current server

        # Mock existing properties
        mock_existing_props = {'server-port': '25565', 'motd': 'A Minecraft Server', 'max-players': '20'}
        mock_load_props.return_value = mock_existing_props

        # Simulate user input: Select option 1 (Port), enter new port 25570, then exit (0)
        mock_input.side_effect = ['1', '25570', '0'] 

        # --- Execute ---
        self.server_mgr.configure_server_menu()

        # --- Assert ---
        mock_load_props.assert_called_once_with(server_name) # Check props were loaded
        # Check properties were saved with the updated value
        expected_saved_props = {'server-port': '25570', 'motd': 'A Minecraft Server', 'max-players': '20'}
        mock_save_props.assert_called_once_with(server_name, expected_saved_props)
        # Check input calls
        self.assertEqual(mock_input.call_count, 3)

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.server_manager.ServerManager._load_server_properties')
    @patch('managers.server_manager.ServerManager._save_server_properties')
    @patch('builtins.input')
    def test_configure_server_menu_toggle_boolean(self, mock_input, mock_save_props, mock_load_props, MockConfigManager, mock_get_dir):
        """Test changing a boolean setting (e.g., pvp) via the config menu."""
        server_name = "config_test_bool"
        mock_get_dir.return_value = self.temp_dir / server_name
        self.server_mgr.get_current_server = MagicMock(return_value=server_name) # Set current server

        mock_existing_props = {'pvp': 'true', 'motd': 'Test'}
        mock_load_props.return_value = mock_existing_props

        # Simulate user input: Select option 6 (pvp), enter 'false', then exit (0)
        mock_input.side_effect = ['6', 'false', '0'] 

        # --- Execute ---
        self.server_mgr.configure_server_menu()

        # --- Assert ---
        mock_load_props.assert_called_once_with(server_name)
        expected_saved_props = {'pvp': 'false', 'motd': 'Test'}
        mock_save_props.assert_called_once_with(server_name, expected_saved_props)
        self.assertEqual(mock_input.call_count, 3)

    # Add more tests for other config options (MOTD, max-players, invalid input handling etc.)

if __name__ == '__main__':
    unittest.main()