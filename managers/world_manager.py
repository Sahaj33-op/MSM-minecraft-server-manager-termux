#!/usr/bin/env python3
"""
World Manager - Enhanced with backup verification and rotation
"""
import os
import zipfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

# Assume logger is passed or imported if needed
# from core.logger import EnhancedLogger 

class WorldManager:
    """Manages world backups and restoration with verification and rotation."""
    
    def __init__(self, logger=None):
        """Initialize the WorldManager.
        
        Args:
            logger: Logger instance for logging messages
        """
        self.logger = logger
    
    def _log(self, level: str, message: str):
        """Log message if logger available.
        
        Args:
            level: Log level (INFO, ERROR, WARNING, etc.)
            message: Message to log
        """
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")
            
    def _get_backup_dir(self, server_path: Path) -> Path:
        """Gets the backup directory path.
        
        Args:
            server_path: Path to the server directory
            
        Returns:
            Path to the backup directory
        """
        backup_dir = server_path / "backups"
        backup_dir.mkdir(exist_ok=True)
        return backup_dir

    def create_backup(self, server_name: str, server_path: Path) -> bool:
        """Create a world backup with ZIP compression and verification.
        
        Args:
            server_name: Name of the server
            server_path: Path to the server directory
            
        Returns:
            True if backup was created successfully, False otherwise
        """
        backup_dir = self._get_backup_dir(server_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"world_backup_{timestamp}.zip"
        backup_path = backup_dir / backup_name
        
        try:
            # Find world directories (case-insensitive check)
            world_dirs = [d for d in server_path.iterdir() 
                         if d.is_dir() and 'world' in d.name.lower()]
            
            if not world_dirs:
                self._log('ERROR', 'No world directories found to backup')
                return False
            
            self._log('INFO', f'Creating backup: {backup_name}')
            
            # Create the zip file
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for world_dir in world_dirs:
                    self._log('DEBUG', f'Adding directory: {world_dir.name}')
                    for root, dirs, files in os.walk(world_dir):
                        for file in files:
                            file_path = Path(root) / file
                            # arcname ensures paths inside zip are relative to server dir
                            arcname = file_path.relative_to(server_path) 
                            zf.write(file_path, arcname)
            
            backup_size_kb = backup_path.stat().st_size / 1024
            self._log('INFO', f'Backup created: {backup_name} ({backup_size_kb:.1f} KB)')

            # **Backup Verification**
            self._log('INFO', 'Verifying backup integrity...')
            try:
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    bad_file = zf.testzip()
                    if bad_file:
                        raise Exception(f"Corrupt file detected: {bad_file}")
                self._log('SUCCESS', f'Backup {backup_name} verified successfully.')
            except Exception as e:
                self._log('ERROR', f'Backup verification failed: {e}')
                # Delete corrupted backup
                if backup_path.exists():
                    backup_path.unlink()
                self._log('ERROR', f'Deleted corrupted backup: {backup_name}')
                return False # Indicate failure

            # **Apply Backup Rotation** (Example: keep last 7 backups)
            self.rotate_backups(server_path, keep_count=7)

            return True # Indicate success
            
        except Exception as e:
            self._log('ERROR', f'Failed to create backup: {e}')
            # Attempt to clean up potentially partial backup file
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except OSError: 
                    pass # Ignore cleanup error
            return False # Indicate failure
    
    def list_backups(self, server_path: Path) -> List[Path]:
        """List all available backup files, sorted newest first.
        
        Args:
            server_path: Path to the server directory
            
        Returns:
            List of Path objects for backup files
        """
        backup_dir = self._get_backup_dir(server_path)
        if not backup_dir.exists():
            return []
        
        # Get Path objects and sort by modification time
        backups = [f for f in backup_dir.iterdir() if f.is_file() and f.suffix == '.zip']
        backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return backups # Return list of Path objects
    
    def restore_backup(self, server_name: str, server_path: Path, backup_path: Path) -> bool:
        """Restore world from a specific backup Path object.
        
        Args:
            server_name: Name of the server
            server_path: Path to the server directory
            backup_path: Path to the backup file
            
        Returns:
            True if backup was restored successfully, False otherwise
        """
        try:
            if not backup_path.exists():
                self._log('ERROR', f'Backup file not found: {backup_path.name}')
                return False
            
            self._log('INFO', f'Restoring from backup: {backup_path.name}')
            
            # **Important:** Stop the server before restoring! (Handled externally)

            # Find existing world directories to remove
            existing_world_dirs = [d for d in server_path.iterdir() 
                                   if d.is_dir() and 'world' in d.name.lower()]
            
            # Extract backup contents to determine which directories to remove
            world_dirs_in_backup = set()
            try:
                with zipfile.ZipFile(backup_path, 'r') as zf:
                    for item in zf.namelist():
                        # Get the top-level directory name
                        first_part = item.split(os.path.sep, 1)[0]
                        if 'world' in first_part.lower(): # Check if it looks like a world folder
                             world_dirs_in_backup.add(first_part)
            except Exception as e:
                 self._log('ERROR', f"Could not read backup file {backup_path.name}: {e}")
                 return False

            # Remove only the world directories that exist AND are in the backup
            for dir_path in existing_world_dirs:
                 if dir_path.name in world_dirs_in_backup:
                      self._log('INFO', f'Removing existing world directory: {dir_path.name}')
                      shutil.rmtree(dir_path)

            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(server_path)
            
            self._log('SUCCESS', f'Restore completed from {backup_path.name}')
            return True
            
        except Exception as e:
            self._log('ERROR', f'Failed to restore backup: {e}')
            return False
            
    def delete_backup(self, server_path: Path, backup_path: Path) -> bool:
        """Delete a specific backup Path object.
        
        Args:
            server_path: Path to the server directory
            backup_path: Path to the backup file
            
        Returns:
            True if backup was deleted successfully, False otherwise
        """
        try:
            if backup_path.exists():
                backup_path.unlink()
                self._log('SUCCESS', f'Deleted backup: {backup_path.name}')
                return True
            else:
                self._log('ERROR', f'Backup not found: {backup_path.name}')
                return False
        except Exception as e:
            self._log('ERROR', f'Failed to delete backup: {e}')
            return False

    def rotate_backups(self, server_path: Path, keep_count: int = 7):
        """Delete oldest backups, keeping only the specified number.
        
        Args:
            server_path: Path to the server directory
            keep_count: Number of backups to keep (default: 7)
        """
        self._log('INFO', f'Applying backup rotation (keeping last {keep_count})...')
        backups = self.list_backups(server_path) # Already sorted newest first
        
        if len(backups) > keep_count:
            backups_to_delete = backups[keep_count:]
            self._log('INFO', f'Found {len(backups_to_delete)} old backups to delete.')
            deleted_count = 0
            for backup_path in backups_to_delete:
                if self.delete_backup(server_path, backup_path):
                    deleted_count += 1
            if deleted_count > 0:
                 self._log('SUCCESS', f'Deleted {deleted_count} old backups.')
        else:
             self._log('INFO', 'No old backups to delete.')

    def get_backup_info(self, backup_path: Path) -> dict:
        """Get information about a backup Path object.
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            Dictionary containing backup information
        """
        if not backup_path.exists():
            return {}
        
        try:
            stat = backup_path.stat()
            return {
                'name': backup_path.name,
                'size': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_mtime), # Use modification time
                'path': str(backup_path)
            }
        except Exception as e:
            self._log('ERROR', f"Could not get info for {backup_path.name}: {e}")
            return {'name': backup_path.name, 'size': 0, 'size_mb': 0}