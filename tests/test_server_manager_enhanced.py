#!/usr/bin/env python3
"""
Enhanced Tests for ServerManager
"""
import io
import logging
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import core.config as config_module
from core.database import DatabaseManager
from core.logger import EnhancedLogger
from core.monitoring import PerformanceMonitor
from managers.api_client import PocketMineAPI
from managers.server_manager import ServerManager


class MockHTTPResponse(io.BytesIO):
    """Minimal file-like response object for mocked downloads."""

    def __init__(self, payload: bytes, final_url: str):
        super().__init__(payload)
        self._final_url = final_url

    def geturl(self):
        return self._final_url

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class TestEnhancedServerManager(unittest.TestCase):

    def setUp(self):
        workspace_tmp = Path.cwd() / '.test_tmp'
        workspace_tmp.mkdir(exist_ok=True)
        self.temp_dir = workspace_tmp / f"test_server_enhanced_{uuid.uuid4().hex}"
        self.temp_dir.mkdir()
        self.db_path = self.temp_dir / 'test.db'
        self.log_path = self.temp_dir / 'test.log'

        logging.getLogger('MSM').handlers = []
        self.config_dir = self.temp_dir / '.config' / 'msm'
        self.config_file = self.config_dir / 'config.json'
        self.home_patcher = patch('utils.helpers.get_home_dir', return_value=self.temp_dir)
        self.home_patcher.start()
        config_module.CONFIG_DIR = self.config_dir
        config_module.CONFIG_FILE = self.config_file
        config_module.SERVERS_ROOT = self.temp_dir

        self.db = DatabaseManager(str(self.db_path))
        self.logger = EnhancedLogger(str(self.log_path))
        self.monitor = PerformanceMonitor(self.db, self.logger)
        self.server_mgr = ServerManager(self.db, self.logger, self.monitor)

    def tearDown(self):
        self.db.close()
        self.logger.close()
        self.home_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_server_with_enhanced_config(self):
        """Test server creation with enhanced configuration."""
        result = self.server_mgr.create_server('test_server')
        self.assertTrue(result)

        servers = self.server_mgr.list_servers()
        self.assertIn('test_server', servers)

        server_config = config_module.ConfigManager.load_server_config('test_server')
        self.assertIn('server_settings', server_config)
        settings = server_config['server_settings']
        self.assertIn('gamemode', settings)
        self.assertIn('difficulty', settings)
        self.assertIn('pvp', settings)
        self.assertIn('white-list', settings)
        self.assertIn('view-distance', settings)

    def test_update_server_properties(self):
        """Test updating server.properties file."""
        self.server_mgr.create_server('test_server')
        test_settings = {
            'gamemode': 'creative',
            'difficulty': 'peaceful',
            'pvp': False,
            'max-players': 10
        }

        self.server_mgr._update_server_properties('test_server', test_settings)
        properties_file = self.temp_dir / 'minecraft-test_server' / 'server.properties'
        content = properties_file.read_text()
        self.assertIn('gamemode=creative', content)
        self.assertIn('difficulty=peaceful', content)
        self.assertIn('pvp=false', content)
        self.assertIn('max-players=10', content)

    def test_server_properties_settings_list(self):
        """Test that SERVER_PROPERTIES_SETTINGS contains expected settings."""
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
        """Test install server menu with error handling."""
        mock_get_versions.side_effect = Exception("API Error")
        self.assertTrue(hasattr(self.server_mgr, 'install_server_menu'))

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.api_client.PocketMineAPI.get_download_url')
    @patch('urllib.request.urlopen')
    def test_download_server_pocketmine(self, mock_urlopen, mock_get_dl_url, MockConfigManager, mock_get_dir):
        """Test downloading PocketMine (.phar)."""
        server_name = "bedrock_test"
        mock_server_path = self.temp_dir / server_name
        mock_server_path.mkdir(exist_ok=True)
        mock_get_dir.return_value = mock_server_path

        download_url = "https://github.com/pmmp/PocketMine-MP/releases/download/5.0.0/PocketMine-MP.phar"
        mock_get_dl_url.return_value = download_url
        mock_urlopen.return_value = MockHTTPResponse(b'phar-data', download_url)
        MockConfigManager.load_server_config.return_value = {
            'server_flavor': None,
            'server_version': None,
            'server_settings': {}
        }

        success = self.server_mgr._download_server(server_name, "PocketMine-MP", PocketMineAPI, "5.0.0", "pocketmine")

        self.assertTrue(success)
        mock_get_dl_url.assert_called_once_with("5.0.0")
        self.assertTrue((mock_server_path / "PocketMine-MP.phar").exists())
        MockConfigManager.save_server_config.assert_called_once()
        saved_config = MockConfigManager.save_server_config.call_args[0][1]
        self.assertEqual(saved_config['server_flavor'], 'pocketmine')
        self.assertEqual(saved_config['server_version'], '5.0.0')
        self.assertIsNone(saved_config['server_build'])
        self.assertEqual(saved_config['server_settings']['port'], 19132)

    @patch('managers.server_manager.get_server_directory')
    @patch('managers.server_manager.ConfigManager')
    @patch('managers.server_manager.is_screen_session_running')
    @patch('shutil.which')
    @patch('pathlib.Path.glob')
    @patch('managers.server_manager.run_command')
    @patch('managers.server_manager.get_screen_session_name')
    @patch('core.monitoring.PerformanceMonitor.start_monitoring')
    @patch('core.database.DatabaseManager.log_session_start')
    @patch('managers.server_manager.ServerManager._verify_server_running')
    def test_start_server_pocketmine(
        self,
        mock_verify_running,
        mock_log_session,
        mock_start_monitor,
        mock_get_screen_name,
        mock_run_cmd,
        mock_glob,
        mock_which,
        mock_is_running,
        MockConfigManager,
        mock_get_dir
    ):
        """Test starting a PocketMine server."""
        server_name = "bedrock_test"
        screen_name = "msm-bedrock_test"
        mock_server_path = self.temp_dir / server_name
        mock_server_path.mkdir(exist_ok=True)
        mock_get_dir.return_value = mock_server_path
        mock_get_screen_name.return_value = screen_name
        MockConfigManager.load_server_config.return_value = {
            'server_flavor': 'pocketmine',
            'server_version': '5.0.0',
            'ram_mb': 512
        }
        self.server_mgr.get_current_server = MagicMock(return_value=server_name)
        mock_is_running.return_value = False
        mock_which.side_effect = lambda executable: '/usr/bin/php' if executable == 'php' else '/usr/bin/screen'
        mock_verify_running.return_value = True

        mock_phar_path = MagicMock(spec=Path)
        mock_glob.return_value = [mock_phar_path]
        mock_run_cmd.side_effect = [
            (0, "Screen session started", ""),
            (0, f"12345.{screen_name}\t(Detached)", "")
        ]

        success = self.server_mgr.start_server()

        self.assertTrue(success)
        mock_is_running.assert_called_once_with(screen_name)
        expected_start_cmd = ['screen', '-dmS', screen_name, '/usr/bin/php', str(mock_phar_path)]
        calls = mock_run_cmd.call_args_list
        self.assertEqual(calls[0], call(expected_start_cmd, cwd=str(mock_server_path)))
        self.assertEqual(calls[1], call(['screen', '-ls'], capture_output=True))
        mock_log_session.assert_called_once_with(server_name, 'pocketmine', '5.0.0')
        mock_start_monitor.assert_called_once_with(server_name, 12345)

    @patch('managers.server_manager.ConfigManager.load')
    @patch('managers.server_manager.ConfigManager.save')
    @patch('managers.server_manager.is_port_in_use', return_value=False)
    @patch('builtins.input')
    def test_configure_server_menu_change_port(self, mock_input, mock_is_port_in_use, mock_save, mock_load):
        """Test changing the server port via the config menu."""
        server_name = "config_test"
        self.server_mgr.get_current_server = MagicMock(return_value=server_name)
        mock_load.return_value = {
            'servers': {
                server_name: {
                    'ram_mb': 1024,
                    'auto_restart': False,
                    'server_settings': {
                        'port': 25565,
                        'motd': 'A Minecraft Server',
                        'max-players': 20
                    }
                }
            },
            'current_server': server_name
        }
        mock_input.side_effect = ['2', '25570', '0']

        self.server_mgr.configure_server_menu()

        saved_config = mock_save.call_args[0][0]
        self.assertEqual(saved_config['servers'][server_name]['server_settings']['port'], 25570)

    @patch('managers.server_manager.ConfigManager.load')
    @patch('managers.server_manager.ConfigManager.save')
    @patch('builtins.input')
    def test_configure_server_menu_toggle_auto_restart(self, mock_input, mock_save, mock_load):
        """Test toggling auto restart via the config menu."""
        server_name = "config_test_auto_restart"
        self.server_mgr.get_current_server = MagicMock(return_value=server_name)
        mock_load.return_value = {
            'servers': {
                server_name: {
                    'ram_mb': 1024,
                    'auto_restart': False,
                    'server_settings': {
                        'port': 25565,
                        'motd': 'Test',
                        'max-players': 20
                    }
                }
            },
            'current_server': server_name
        }
        mock_input.side_effect = ['3', '0']

        self.server_mgr.configure_server_menu()

        saved_config = mock_save.call_args[0][0]
        self.assertTrue(saved_config['servers'][server_name]['auto_restart'])


if __name__ == '__main__':
    unittest.main()
