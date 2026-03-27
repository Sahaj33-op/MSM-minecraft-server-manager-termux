#!/usr/bin/env python3
"""
Tests for ServerManager
"""
import unittest
import tempfile
import shutil
import logging
import uuid
from pathlib import Path
from unittest.mock import patch

from core.database import DatabaseManager
from core.logger import EnhancedLogger
from core.monitoring import PerformanceMonitor
from managers.server_manager import ServerManager
import core.config as config_module

class TestServerManager(unittest.TestCase):
    
    def setUp(self):
        workspace_tmp = Path.cwd() / '.test_tmp'
        workspace_tmp.mkdir(exist_ok=True)
        self.temp_dir = workspace_tmp / f"test_server_{uuid.uuid4().hex}"
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
    
    def test_create_server(self):
        """Test server creation"""
        result = self.server_mgr.create_server('test_server')
        self.assertTrue(result)
        
        servers = self.server_mgr.list_servers()
        self.assertIn('test_server', servers)
    
    def test_reject_invalid_server_name(self):
        """Test invalid server names are rejected."""
        result = self.server_mgr.create_server('test server with spaces!')
        self.assertFalse(result)

        servers = self.server_mgr.list_servers()
        self.assertFalse(any('test server with spaces!' == s for s in servers))

if __name__ == '__main__':
    unittest.main()
