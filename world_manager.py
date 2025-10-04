# ============================================================================
# world_manager.py - Handles backups, restores, and world operations
# ============================================================================
"""
World backup and restore operations.
"""

import shutil
import os
from pathlib import Path
from datetime import datetime

from ui import clear_screen, print_header, print_info, print_warning, print_success, print_error, UI
from server_manager import ServerManager
from config import get_servers_root
from utils import log


class WorldManager:
    """Manages world backups and restores."""
    
    def world_manager_menu(self):
        """World manager menu."""
        while True:
            clear_screen()
            print_header("1.1.0")
            print(f"\n{UI.colors.BOLD}World Manager{UI.colors.RESET}\n")
            
            current_server = ServerManager.get_current_server()
            if not current_server:
                print_error("No server selected.")
                input("\nPress Enter to continue...")
                return
            
            print_info(f"Managing backups for: {current_server}")
            print()
            print("Options:")
            print(" 1. Create backup")
            print(" 2. List backups")
            print(" 3. Restore from backup")
            print(" 0. Back to main menu")
            print()
            
            choice = input(f"{UI.colors.YELLOW}Select option (0-3): {UI.colors.RESET}").strip()
            
            if choice == "1":
                self.create_backup(current_server)
            elif choice == "2":
                self.list_backups(current_server)
            elif choice == "3":
                self.restore_backup(current_server)
            elif choice == "0":
                return
            else:
                print_error("Invalid option. Please try again.")
                input("\nPress Enter to continue...")
    
    def create_backup(self, server_name):
        """Create a backup of the server's world folders."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Create Backup{UI.colors.RESET}\n")
        
        server_path = get_servers_root() / server_name
        if not server_path.exists():
            print_error(f"Server directory not found: {server_path}")
            input("\nPress Enter to continue...")
            return
        
        # Create backups directory if it doesn't exist
        backups_dir = server_path / "backups"
        backups_dir.mkdir(exist_ok=True)
        
        # Find world directories (standard Minecraft world folder names)
        world_dirs = []
        for item in server_path.iterdir():
            if item.is_dir() and item.name in ["world", "world_nether", "world_the_end"]:
                world_dirs.append(item)
        
        if not world_dirs:
            print_warning("No world directories found.")
            input("\nPress Enter to continue...")
            return
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{server_name}_{timestamp}"
        backup_path = backups_dir / backup_name
        
        print_info(f"Creating backup: {backup_name}")
        
        try:
            # Create a temporary directory to hold all world folders
            temp_dir = backups_dir / f"temp_{timestamp}"
            temp_dir.mkdir(exist_ok=True)
            
            # Copy world directories to temporary directory
            for world_dir in world_dirs:
                print_info(f"Copying {world_dir.name}...")
                shutil.copytree(world_dir, temp_dir / world_dir.name)
            
            # Create zip archive
            print_info("Creating zip archive...")
            shutil.make_archive(str(backup_path), 'zip', temp_dir)
            
            # Remove temporary directory
            shutil.rmtree(temp_dir)
            
            # Get backup file size
            backup_file = backup_path.with_suffix('.zip')
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            
            # Verify backup integrity
            print_info("Verifying backup integrity...")
            try:
                # Test if the ZIP file can be opened and read
                import zipfile
                with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                    # Test the ZIP file structure
                    bad_file = zip_ref.testzip()
                    if bad_file:
                        raise Exception(f"Corrupt file in backup: {bad_file}")
                    # Check that we have the expected world directories
                    zip_contents = zip_ref.namelist()
                    expected_worlds = [world_dir.name for world_dir in world_dirs]
                    found_worlds = [item.split('/')[0] for item in zip_contents if '/' in item]
                    found_worlds = list(set(found_worlds))  # Remove duplicates
                    
                    missing_worlds = set(expected_worlds) - set(found_worlds)
                    if missing_worlds:
                        raise Exception(f"Missing world directories in backup: {missing_worlds}")
                
                print_success(f"Backup verified successfully: {backup_file.name} ({size_mb:.1f} MB)")
                log(f"Backup created and verified for {server_name}: {backup_file.name}")
                
            except Exception as verify_error:
                print_error(f"Backup verification failed: {verify_error}")
                log(f"Backup verification failed for {server_name}: {verify_error}", "ERROR")
                # Remove the corrupted backup
                if backup_file.exists():
                    backup_file.unlink()
                return
                
        except Exception as e:
            print_error(f"Failed to create backup: {e}")
            log(f"Backup failed for {server_name}: {e}", "ERROR")
            
            # Clean up temporary directory if it exists
            temp_dir = backups_dir / f"temp_{timestamp}"
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
        
        input("\nPress Enter to continue...")
    
    def list_backups(self, server_name):
        """List all backups for the server."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}List Backups{UI.colors.RESET}\n")
        
        server_path = get_servers_root() / server_name
        backups_dir = server_path / "backups"
        
        if not backups_dir.exists():
            print_info("No backups directory found.")
            input("\nPress Enter to continue...")
            return
        
        backup_files = list(backups_dir.glob("*.zip"))
        
        if not backup_files:
            print_info("No backups found.")
            input("\nPress Enter to continue...")
            return
        
        print_info(f"Backups for {server_name}:")
        print()
        print(f"{'Name':<30} {'Size (MB)':<10} {'Date'}")
        print("-" * 50)
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        for backup_file in backup_files:
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            print(f"{backup_file.name:<30} {size_mb:<10.1f} {mod_time.strftime('%Y-%m-%d %H:%M')}")
        
        print()
        input("Press Enter to continue...")
    
    def restore_backup(self, server_name):
        """Restore a backup to the server."""
        clear_screen()
        print_header("1.1.0")
        print(f"\n{UI.colors.BOLD}Restore Backup{UI.colors.RESET}\n")
        
        server_path = get_servers_root() / server_name
        backups_dir = server_path / "backups"
        
        if not backups_dir.exists():
            print_info("No backups directory found.")
            input("\nPress Enter to continue...")
            return
        
        backup_files = list(backups_dir.glob("*.zip"))
        
        if not backup_files:
            print_info("No backups found.")
            input("\nPress Enter to continue...")
            return
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        print_info("Available backups:")
        for i, backup_file in enumerate(backup_files, 1):
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            mod_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            print(f" {i}. {backup_file.name} ({size_mb:.1f} MB) - {mod_time.strftime('%Y-%m-%d %H:%M')}")
        
        print()
        choice = input(f"{UI.colors.YELLOW}Select backup to restore (1-{len(backup_files)}) or 0 to cancel: {UI.colors.RESET}").strip()
        
        if choice == "0":
            return
        
        try:
            index = int(choice) - 1
            if 0 <= index < len(backup_files):
                selected_backup = backup_files[index]
                
                confirm = input(f"\n{UI.colors.YELLOW}Are you sure you want to restore {selected_backup.name}? This will overwrite existing world data. (y/N): {UI.colors.RESET}").strip().lower()
                
                if confirm == 'y':
                    print_info(f"Restoring backup: {selected_backup.name}")
                    
                    # Extract backup to temporary directory
                    temp_extract_dir = backups_dir / f"temp_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    temp_extract_dir.mkdir(exist_ok=True)
                    
                    try:
                        # Extract the zip file
                        shutil.unpack_archive(str(selected_backup), str(temp_extract_dir), 'zip')
                        
                        # Remove existing world directories
                        for world_name in ["world", "world_nether", "world_the_end"]:
                            world_dir = server_path / world_name
                            if world_dir.exists():
                                print_info(f"Removing existing {world_name}...")
                                shutil.rmtree(world_dir)
                        
                        # Copy extracted world directories to server directory
                        for item in temp_extract_dir.iterdir():
                            if item.is_dir() and item.name in ["world", "world_nether", "world_the_end"]:
                                print_info(f"Restoring {item.name}...")
                                shutil.copytree(item, server_path / item.name)
                        
                        # Clean up temporary directory
                        shutil.rmtree(temp_extract_dir)
                        
                        print_success("Backup restored successfully!")
                        log(f"Backup restored for {server_name}: {selected_backup.name}")
                        
                    except Exception as e:
                        print_error(f"Failed to restore backup: {e}")
                        log(f"Backup restore failed for {server_name}: {e}", "ERROR")
                        
                        # Clean up temporary directory if it exists
                        if temp_extract_dir.exists():
                            shutil.rmtree(temp_extract_dir)
                else:
                    print_info("Restore cancelled.")
            else:
                print_error("Invalid selection.")
        except ValueError:
            print_error("Invalid input.")
        
        input("\nPress Enter to continue...")