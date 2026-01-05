#!/usr/bin/env python3
"""
Database Manager - Extracted from main branch msm.py
SQLite-based statistics, session tracking, and metrics
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any, List, Tuple, Optional

from core.exceptions import DatabaseError

# Database schema version - increment when schema changes
SCHEMA_VERSION = 2

# Migration scripts - each entry is (version, description, sql)
MIGRATIONS: List[Tuple[int, str, str]] = [
    (1, "Initial schema", """
        CREATE TABLE IF NOT EXISTS server_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, flavor TEXT NOT NULL,
            version TEXT NOT NULL, start_time TIMESTAMP NOT NULL, end_time TIMESTAMP,
            duration INTEGER, peak_players INTEGER DEFAULT 0, crash_count INTEGER DEFAULT 0,
            restart_count INTEGER DEFAULT 0, ram_usage_avg REAL, cpu_usage_avg REAL
        );
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, timestamp TIMESTAMP NOT NULL,
            ram_usage REAL NOT NULL, cpu_usage REAL NOT NULL, player_count INTEGER DEFAULT 0,
            tps REAL DEFAULT 20.0, mspt REAL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT NOT NULL, backup_path TEXT NOT NULL,
            backup_size INTEGER NOT NULL, created_at TIMESTAMP NOT NULL, backup_type TEXT DEFAULT 'manual',
            compressed_size INTEGER
        );
        CREATE TABLE IF NOT EXISTS error_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, server_name TEXT, error_type TEXT NOT NULL,
            error_message TEXT NOT NULL, stack_trace TEXT, timestamp TIMESTAMP NOT NULL,
            severity TEXT DEFAULT 'ERROR'
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_server ON server_sessions(server_name);
        CREATE INDEX IF NOT EXISTS idx_metrics_server_time ON performance_metrics(server_name, timestamp);
        CREATE INDEX IF NOT EXISTS idx_backups_server ON backup_history(server_name);
        CREATE INDEX IF NOT EXISTS idx_errors_time ON error_log(timestamp);
    """),
    (2, "Add schema version table and command history", """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS command_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command TEXT NOT NULL,
            server_name TEXT,
            success INTEGER DEFAULT 1,
            executed_at TIMESTAMP NOT NULL,
            duration_ms INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_cmd_history_time ON command_history(executed_at);
    """),
]


class DatabaseManager:
    """Enhanced database management for server statistics and history"""

    def __init__(self, db_path: str):
        """Initialize the DatabaseManager.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _get_current_version(self, conn: sqlite3.Connection) -> int:
        """Get the current schema version from database.

        Args:
            conn: Database connection

        Returns:
            Current schema version (0 if not set)
        """
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if not cursor.fetchone():
                return 0

            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0
        except sqlite3.Error:
            return 0

    def _apply_migration(self, conn: sqlite3.Connection, version: int, description: str, sql: str) -> None:
        """Apply a single migration.

        Args:
            conn: Database connection
            version: Migration version number
            description: Migration description
            sql: SQL to execute
        """
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                (version, datetime.now(), description)
            )
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise DatabaseError(f"Migration {version} failed: {e}")

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        """Run pending database migrations.

        Args:
            conn: Database connection
        """
        # First, ensure schema_version table exists for tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL,
                description TEXT
            )
        """)
        conn.commit()

        current_version = self._get_current_version(conn)

        # Check if we have existing tables (pre-migration database)
        if current_version == 0:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='server_sessions'"
            )
            if cursor.fetchone():
                # Existing database without versioning - mark version 1 as applied
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at, description) VALUES (?, ?, ?)",
                    (1, datetime.now(), "Initial schema (existing)")
                )
                conn.commit()
                current_version = 1

        # Apply pending migrations
        for version, description, sql in MIGRATIONS:
            if version > current_version:
                self._apply_migration(conn, version, description, sql)

    def _init_database(self):
        """Initialize database with comprehensive schema and migrations."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            self._run_migrations(conn)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections with timeout and error handling.

        Yields:
            SQLite connection object

        Raises:
            DatabaseError: If database is locked or corrupted
        """
        conn = None
        try:
            # Add 30-second timeout to prevent indefinite hangs
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "database is locked" in error_msg:
                raise DatabaseError(
                    f"Database is locked. Another process may be using it. "
                    f"Please close other MSM instances and try again."
                )
            elif "database disk image is malformed" in error_msg or "database is malformed" in error_msg:
                import shutil
                import time
                backup_path = f"{self.db_path}.corrupted_{int(time.time())}"
                try:
                    shutil.copy2(self.db_path, backup_path)
                    raise DatabaseError(
                        f"Database is corrupted. Backup saved to: {backup_path}\n"
                        f"The database will be recreated on next startup."
                    )
                except Exception as backup_err:
                    raise DatabaseError(
                        f"Database is corrupted and backup failed: {backup_err}\n"
                        f"Please manually backup {self.db_path} if needed."
                    )
            else:
                raise DatabaseError(f"Database operation failed: {e}")
        except Exception as e:
            raise DatabaseError(f"Unexpected database error: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass  # Ignore errors on close

    def log_session_start(self, server_name: str, flavor: str, version: str) -> int:
        """Log server session start.
        
        Args:
            server_name: Name of the server
            flavor: Server flavor (paper, purpur, etc.)
            version: Server version
            
        Returns:
            ID of the created session
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO server_sessions (server_name, flavor, version, start_time) VALUES (?, ?, ?, ?)",
                (server_name, flavor, version, datetime.now())
            )
            conn.commit()
            return cursor.lastrowid if cursor.lastrowid is not None else 0

    def log_session_end(self, session_id: int):
        """Log server session end with statistics.
        
        Args:
            session_id: ID of the session to end
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_time FROM server_sessions WHERE id = ?", (session_id,))
            start_time_row = cursor.fetchone()
            if start_time_row:
                start_time_str = start_time_row[0]
                start_time = datetime.fromisoformat(start_time_str)
                duration = int((datetime.now() - start_time).total_seconds())

                cursor.execute(
                    "UPDATE server_sessions SET end_time = ?, duration = ? WHERE id = ?",
                    (datetime.now(), duration, session_id)
                )
                conn.commit()

    def log_performance_metric(self, server_name: str, ram_usage: float, cpu_usage: float, player_count: int = 0):
        """Log performance metrics.
        
        Args:
            server_name: Name of the server
            ram_usage: RAM usage percentage
            cpu_usage: CPU usage percentage
            player_count: Number of players (default: 0)
        """
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO performance_metrics (server_name, timestamp, ram_usage, cpu_usage, player_count) VALUES (?, ?, ?, ?, ?)",
                (server_name, datetime.now(), ram_usage, cpu_usage, player_count)
            )
            conn.commit()

    def get_server_statistics(self, server_name: str) -> Dict[str, Any]:
        """Get comprehensive server statistics.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Dictionary containing server statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as total_sessions, AVG(duration) as avg_duration, SUM(duration) as total_uptime, "
                "SUM(crash_count) as total_crashes, SUM(restart_count) as total_restarts "
                "FROM server_sessions WHERE server_name = ? AND end_time IS NOT NULL", (server_name,)
            )
            session_stats = cursor.fetchone()
            cursor.execute(
                "SELECT AVG(ram_usage), AVG(cpu_usage), MAX(player_count) FROM performance_metrics "
                "WHERE server_name = ? AND timestamp > datetime('now', '-24 hours')", (server_name,)
            )
            perf_stats = cursor.fetchone()
            return {
                'total_sessions': session_stats['total_sessions'] if session_stats else 0,
                'avg_duration': session_stats['avg_duration'] if session_stats else 0,
                'total_uptime': session_stats['total_uptime'] if session_stats else 0,
                'total_crashes': session_stats['total_crashes'] if session_stats else 0,
                'total_restarts': session_stats['total_restarts'] if session_stats else 0,
                'avg_ram_usage_24h': perf_stats[0] if perf_stats and perf_stats[0] else 0,
                'avg_cpu_usage_24h': perf_stats[1] if perf_stats and perf_stats[1] else 0,
                'peak_players_24h': perf_stats[2] if perf_stats and perf_stats[2] else 0
            }

    def log_command(self, command: str, server_name: Optional[str] = None,
                    success: bool = True, duration_ms: Optional[int] = None) -> None:
        """Log a command execution to command history.

        Args:
            command: The command that was executed
            server_name: Optional server name associated with the command
            success: Whether the command succeeded (default: True)
            duration_ms: Optional execution duration in milliseconds
        """
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO command_history (command, server_name, success, executed_at, duration_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (command, server_name, 1 if success else 0, datetime.now(), duration_ms)
            )
            conn.commit()

    def get_command_history(self, limit: int = 50, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent command history.

        Args:
            limit: Maximum number of commands to return (default: 50)
            server_name: Optional filter by server name

        Returns:
            List of command history entries
        """
        with self.get_connection() as conn:
            if server_name:
                cursor = conn.execute(
                    "SELECT command, server_name, success, executed_at, duration_ms "
                    "FROM command_history WHERE server_name = ? ORDER BY executed_at DESC LIMIT ?",
                    (server_name, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT command, server_name, success, executed_at, duration_ms "
                    "FROM command_history ORDER BY executed_at DESC LIMIT ?",
                    (limit,)
                )

            return [
                {
                    'command': row['command'],
                    'server_name': row['server_name'],
                    'success': bool(row['success']),
                    'executed_at': row['executed_at'],
                    'duration_ms': row['duration_ms']
                }
                for row in cursor.fetchall()
            ]

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics.

        Returns:
            Dictionary containing database info and statistics
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Get schema version
            current_version = self._get_current_version(conn)

            # Get table row counts
            tables = ['server_sessions', 'performance_metrics', 'backup_history',
                      'error_log', 'command_history']
            row_counts = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_counts[table] = cursor.fetchone()[0]
                except sqlite3.Error:
                    row_counts[table] = 0

            # Get database file size
            db_size = 0
            try:
                db_size = os.path.getsize(self.db_path)
            except OSError:
                pass

            return {
                'schema_version': current_version,
                'target_version': SCHEMA_VERSION,
                'needs_migration': current_version < SCHEMA_VERSION,
                'db_path': self.db_path,
                'db_size_bytes': db_size,
                'db_size_mb': round(db_size / (1024 * 1024), 2),
                'row_counts': row_counts
            }