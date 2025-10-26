#!/usr/bin/env python3
"""
World Manager - From v1.1.0 branch with backup/restore functionality
ZIP compression, verification, and automated world management
"""
import os
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

class WorldManager:
    """Manages world backups and restoration."""
    
    def __init__(self, logger=None):
        self.logger = logger
    
    def _log(self, level: str, message: str):
        """Log message if logger available"""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")
    
    def create_backup(self, server_name: str, server_path: Path) -> bool:
        """Create a world backup with ZIP compression."""
        try:
            backup_dir = server_path / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"world_backup_{timestamp}.zip"
            backup_path = backup_dir / backup_name
            
            # Find world directories
            world_dirs = [d for d in server_path.iterdir() 
                         if d.is_dir() and 'world' in d.name.lower()]
            
            if not world_dirs:
                self._log('ERROR', 'No world directories found to backup')
                return False
            
            self._log('INFO', f'Creating backup: {backup_name}')
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for world_dir in world_dirs:
                    for root, dirs, files in os.walk(world_dir):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(server_path)
                            zf.write(file_path, arcname)
            
            backup_size = backup_path.stat().st_size
            self._log('SUCCESS', f'Backup created: {backup_name} ({backup_size // 1024} KB)')
            return True
            
        except Exception as e:
            self._log('ERROR', f'Failed to create backup: {e}')
            return False
    
    def list_backups(self, server_path: Path) -> List[str]:
        """List all available backups."""
        backup_dir = server_path / "backups"
        if not backup_dir.exists():
            return []
        
        backups = [f.name for f in backup_dir.iterdir() 
                  if f.is_file() and f.suffix == '.zip']
        return sorted(backups, reverse=True)
    
    def restore_backup(self, server_name: str, server_path: Path, backup_name: str) -> bool:
        """Restore world from backup."""
        try:
            backup_path = server_path / "backups" / backup_name
            if not backup_path.exists():
                self._log('ERROR', f'Backup {backup_name} not found')
                return False
            
            self._log('INFO', f'Restoring from backup: {backup_name}')
            
            # Remove existing world directories
            world_dirs = [d for d in server_path.iterdir() 
                         if d.is_dir() and 'world' in d.name.lower()]
            for world_dir in world_dirs:
                shutil.rmtree(world_dir)
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(server_path)
            
            self._log('SUCCESS', f'Restore completed from {backup_name}')
            return True
            
        except Exception as e:
            self._log('ERROR', f'Failed to restore backup: {e}')
            return False
    
    def delete_backup(self, server_path: Path, backup_name: str) -> bool:
        """Delete a backup file."""
        try:
            backup_path = server_path / "backups" / backup_name
            if backup_path.exists():
                backup_path.unlink()
                self._log('SUCCESS', f'Deleted backup: {backup_name}')
                return True
            else:
                self._log('ERROR', f'Backup {backup_name} not found')
                return False
        except Exception as e:
            self._log('ERROR', f'Failed to delete backup: {e}')
            return False
    
    def get_backup_info(self, server_path: Path, backup_name: str) -> dict:
        """Get information about a backup file."""
        backup_path = server_path / "backups" / backup_name
        if not backup_path.exists():
            return {}
        
        try:
            stat = backup_path.stat()
            return {
                'name': backup_name,
                'size': stat.st_size,
                'size_mb': stat.st_size // (1024 * 1024),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'path': str(backup_path)
            }
        except Exception:
            return {'name': backup_name, 'size': 0, 'size_mb': 0}