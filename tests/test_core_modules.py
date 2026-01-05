#!/usr/bin/env python3
"""
Tests for core modules - database, logger, monitoring, and validation functions
"""
import unittest
import tempfile
import shutil
import os
import time
from pathlib import Path
from datetime import datetime

from core.database import DatabaseManager, SCHEMA_VERSION, MIGRATIONS
from core.logger import EnhancedLogger, CompressedRotatingFileHandler
from core.monitoring import PerformanceMonitor
from core.exceptions import DatabaseError, MSMError
from utils.helpers import (
    sanitize_input, validate_server_name, validate_minecraft_version,
    validate_port, validate_ram_allocation, validate_max_players, is_port_in_use
)


class TestDatabaseManager(unittest.TestCase):
    """Tests for DatabaseManager class"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = str(self.temp_dir / 'test.db')
        self.db = DatabaseManager(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_creation(self):
        """Test that database file is created"""
        self.assertTrue(os.path.exists(self.db_path))

    def test_schema_version(self):
        """Test that schema version is set correctly"""
        info = self.db.get_database_info()
        self.assertEqual(info['schema_version'], SCHEMA_VERSION)
        self.assertFalse(info['needs_migration'])

    def test_session_logging(self):
        """Test session start and end logging"""
        session_id = self.db.log_session_start('test_server', 'paper', '1.20.4')
        self.assertIsNotNone(session_id)
        self.assertGreater(session_id, 0)

        # End the session
        self.db.log_session_end(session_id)

    def test_performance_metrics(self):
        """Test performance metric logging"""
        self.db.log_performance_metric('test_server', 50.0, 25.0, 5)

        stats = self.db.get_server_statistics('test_server')
        # Stats should exist (even if zeros due to time filtering)
        self.assertIsNotNone(stats)

    def test_command_history(self):
        """Test command history logging and retrieval"""
        self.db.log_command('test_command', 'test_server', True, 100)
        self.db.log_command('failed_command', 'test_server', False, 50)

        history = self.db.get_command_history(limit=10)
        self.assertEqual(len(history), 2)

        # Check most recent first
        self.assertEqual(history[0]['command'], 'failed_command')
        self.assertFalse(history[0]['success'])

        # Filter by server
        server_history = self.db.get_command_history(limit=10, server_name='test_server')
        self.assertEqual(len(server_history), 2)

    def test_database_info(self):
        """Test database info retrieval"""
        info = self.db.get_database_info()

        self.assertIn('schema_version', info)
        self.assertIn('target_version', info)
        self.assertIn('db_path', info)
        self.assertIn('row_counts', info)
        self.assertIsInstance(info['row_counts'], dict)


class TestEnhancedLogger(unittest.TestCase):
    """Tests for EnhancedLogger class"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_path = str(self.temp_dir / 'test.log')
        # Clear any existing MSM logger handlers
        import logging
        msm_logger = logging.getLogger('MSM')
        msm_logger.handlers = []

    def tearDown(self):
        # Clean up logger handlers
        import logging
        msm_logger = logging.getLogger('MSM')
        for handler in msm_logger.handlers[:]:
            handler.close()
            msm_logger.removeHandler(handler)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_logger_creation(self):
        """Test that logger is created and log file exists"""
        logger = EnhancedLogger(self.log_path)
        logger.log('INFO', 'Test message')
        # Force flush to ensure file is written
        for handler in logger.logger.handlers:
            handler.flush()
        self.assertTrue(os.path.exists(self.log_path))

    def test_log_levels(self):
        """Test various log levels"""
        logger = EnhancedLogger(self.log_path)

        logger.log('DEBUG', 'Debug message')
        logger.log('INFO', 'Info message')
        logger.log('WARNING', 'Warning message')
        logger.log('ERROR', 'Error message')
        logger.log('SUCCESS', 'Success message')

        # Read log file and verify content
        with open(self.log_path, 'r') as f:
            content = f.read()

        self.assertIn('Info message', content)
        self.assertIn('Warning message', content)
        self.assertIn('Error message', content)

    def test_logger_with_kwargs(self):
        """Test logging with extra kwargs"""
        logger = EnhancedLogger(self.log_path)
        logger.log('INFO', 'Message with data', key='value', number=42)

        with open(self.log_path, 'r') as f:
            content = f.read()

        self.assertIn('Message with data', content)

    def test_compressed_handler_option(self):
        """Test that compression option is respected"""
        logger_compressed = EnhancedLogger(self.log_path, compress_backups=True)
        self.assertTrue(logger_compressed.compress_backups)

        log_path_2 = str(self.temp_dir / 'test2.log')
        logger_uncompressed = EnhancedLogger(log_path_2, compress_backups=False)
        self.assertFalse(logger_uncompressed.compress_backups)


class TestPerformanceMonitor(unittest.TestCase):
    """Tests for PerformanceMonitor class"""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = str(self.temp_dir / 'test.db')
        self.log_path = str(self.temp_dir / 'test.log')

        self.db = DatabaseManager(self.db_path)
        self.logger = EnhancedLogger(self.log_path)
        self.monitor = PerformanceMonitor(self.db, self.logger)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_system_info(self):
        """Test system info retrieval"""
        info = self.monitor.get_system_info()

        self.assertIn('total_ram_mb', info)
        self.assertIn('available_ram_mb', info)
        self.assertIn('cpu_count', info)
        self.assertIn('cpu_usage', info)

        self.assertGreater(info['total_ram_mb'], 0)
        self.assertGreater(info['cpu_count'], 0)

    def test_health_check(self):
        """Test health check functionality"""
        health = self.monitor.get_health_check()

        self.assertIn('status', health)
        self.assertIn('timestamp', health)
        self.assertIn('system', health)
        self.assertIn('warnings', health)
        self.assertIn('errors', health)

        # Status should be one of expected values
        self.assertIn(health['status'], ['healthy', 'degraded', 'unhealthy'])

    def test_active_monitors(self):
        """Test active monitors list (should be empty initially)"""
        monitors = self.monitor.get_active_monitors()
        self.assertEqual(monitors, {})


class TestInputValidation(unittest.TestCase):
    """Tests for input validation functions"""

    def test_sanitize_input(self):
        """Test input sanitization"""
        # Normal input
        self.assertEqual(sanitize_input('test_server'), 'test_server')

        # Input with path traversal
        sanitized = sanitize_input('../../../etc/passwd')
        self.assertNotIn('..', sanitized)
        self.assertNotIn('/', sanitized)

        # Input with spaces and special chars
        sanitized = sanitize_input('test server!@#$%')
        self.assertRegex(sanitized, r'^[a-zA-Z0-9_.-]+$')

    def test_validate_server_name_valid(self):
        """Test valid server names"""
        valid_names = ['server1', 'my_server', 'test.server', 'server-1', 'MyServer2024']

        for name in valid_names:
            is_valid, msg = validate_server_name(name)
            self.assertTrue(is_valid, f"'{name}' should be valid: {msg}")

    def test_validate_server_name_invalid(self):
        """Test invalid server names"""
        invalid_cases = [
            ('', 'empty'),
            ('../path', 'path traversal'),
            ('server/name', 'slash'),
            ('server;name', 'shell metachar'),
            ('server|name', 'pipe'),
            ('.server', 'starts with dot'),
            ('CON', 'reserved name'),
            ('a' * 100, 'too long'),
        ]

        for name, desc in invalid_cases:
            is_valid, msg = validate_server_name(name)
            self.assertFalse(is_valid, f"'{name}' ({desc}) should be invalid")

    def test_validate_minecraft_version_valid(self):
        """Test valid Minecraft versions"""
        valid_versions = ['1.20.4', '1.19', '1.20', '24w10a', '1.18.2-pre1']

        for version in valid_versions:
            is_valid, msg = validate_minecraft_version(version)
            self.assertTrue(is_valid, f"'{version}' should be valid: {msg}")

    def test_validate_minecraft_version_invalid(self):
        """Test invalid Minecraft versions"""
        invalid_versions = ['', 'invalid!version', 'version with spaces']

        for version in invalid_versions:
            is_valid, msg = validate_minecraft_version(version)
            self.assertFalse(is_valid, f"'{version}' should be invalid")

    def test_validate_port_valid(self):
        """Test valid port numbers"""
        valid_ports = [1, 80, 443, 25565, 65535]

        for port in valid_ports:
            result = validate_port(port)
            self.assertTrue(result)

    def test_validate_port_invalid(self):
        """Test invalid port numbers"""
        invalid_ports = [0, -1, 65536, 100000]

        for port in invalid_ports:
            with self.assertRaises(ValueError):
                validate_port(port)

    def test_validate_port_type_error(self):
        """Test port validation with wrong type"""
        with self.assertRaises(ValueError):
            validate_port("25565")

    def test_validate_ram_allocation_valid(self):
        """Test valid RAM allocations"""
        is_valid, msg = validate_ram_allocation(1024)
        self.assertTrue(is_valid)

        is_valid, msg = validate_ram_allocation(2048)
        self.assertTrue(is_valid)

    def test_validate_ram_allocation_too_low(self):
        """Test RAM allocation below minimum"""
        is_valid, msg = validate_ram_allocation(256)
        self.assertFalse(is_valid)
        self.assertIn('too low', msg.lower())

    def test_validate_ram_allocation_too_high(self):
        """Test RAM allocation above maximum"""
        is_valid, msg = validate_ram_allocation(16384)
        self.assertFalse(is_valid)
        self.assertIn('too high', msg.lower())

    def test_validate_max_players_valid(self):
        """Test valid max players settings"""
        for players in [1, 20, 100, 1000]:
            result = validate_max_players(players)
            self.assertTrue(result)

    def test_validate_max_players_invalid(self):
        """Test invalid max players settings"""
        for players in [0, -1, 1001]:
            with self.assertRaises(ValueError):
                validate_max_players(players)


class TestMigrations(unittest.TestCase):
    """Tests for database migration system"""

    def test_migrations_format(self):
        """Test that migrations are properly formatted"""
        for version, description, sql in MIGRATIONS:
            self.assertIsInstance(version, int)
            self.assertIsInstance(description, str)
            self.assertIsInstance(sql, str)
            self.assertGreater(version, 0)
            self.assertTrue(len(description) > 0)
            self.assertTrue(len(sql) > 0)

    def test_migrations_sequential(self):
        """Test that migration versions are sequential"""
        versions = [v for v, _, _ in MIGRATIONS]
        for i, v in enumerate(versions):
            self.assertEqual(v, i + 1, f"Migration {i} should be version {i + 1}")

    def test_schema_version_matches_migrations(self):
        """Test that SCHEMA_VERSION matches latest migration"""
        latest_migration = max(v for v, _, _ in MIGRATIONS)
        self.assertEqual(SCHEMA_VERSION, latest_migration)


if __name__ == '__main__':
    unittest.main()
