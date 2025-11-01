#!/usr/bin/env python3
"""
Database Manager - Extracted from main branch msm.py
SQLite-based statistics, session tracking, and metrics
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, Any

class DatabaseManager:
    """Enhanced database management for server statistics and history"""
    
    def __init__(self, db_path: str):
        """Initialize the DatabaseManager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize database with comprehensive schema."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript('''
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
            ''')

    @contextmanager
    def get_connection(self):
        """Context manager for database connections.
        
        Yields:
            SQLite connection object
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            if conn:
                conn.close()

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