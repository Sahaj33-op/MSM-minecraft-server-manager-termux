#!/usr/bin/env python3
"""
Custom exceptions for MSM.
"""

class MSMError(Exception):
    """Base exception for MSM errors."""
    pass

class ConfigError(MSMError):
    """Errors related to configuration loading/saving."""
    pass

class EnvironmentError(MSMError):
    """Errors related to the execution environment (Debian, missing deps)."""
    pass

class APIError(MSMError):
    """Errors related to fetching data from external APIs."""
    pass

class DownloadError(MSMError):
    """Errors related to downloading server files."""
    pass

class ServerProcessError(MSMError):
    """Errors related to starting/stopping/managing the server process."""
    pass

class TunnelError(MSMError):
    """Errors related to tunneling services."""
    pass

class BackupError(MSMError):
     """Errors related to world backups."""
     pass

class PluginError(MSMError):
     """Errors related to plugin management."""
     pass

class DatabaseError(MSMError):
     """Errors related to database operations."""
     pass

class ServerError(MSMError):
     """Errors related to server operations."""
     pass