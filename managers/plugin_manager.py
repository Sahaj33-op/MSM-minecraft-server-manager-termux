#!/usr/bin/env python3
"""
Plugin Manager - Handles listing, installing, enabling/disabling plugins.
"""
import os
import shutil
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import List, Tuple, Optional

# Import custom exceptions
from core.exceptions import PluginError, DownloadError
# Assume logger and UI are passed or imported
# from core.logger import EnhancedLogger
# from ui.interface import UI
from utils.helpers import get_server_directory # Import helper

class PluginManager:
    """Manages plugins for Bukkit/Spigot/Paper servers."""
    
    def __init__(self, logger=None, ui=None):
        """Initialize the PluginManager.
        
        Args:
            logger: Logger instance for logging messages
            ui: UI instance for displaying messages
        """
        self.logger = logger
        self.ui = ui

    def _log(self, level: str, message: str):
        """Log a message using the logger or print to console.
        
        Args:
            level: Log level (INFO, ERROR, WARNING, etc.)
            message: Message to log
        """
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def _print_ui(self, method: str, message: str):
        """Print a message using the UI or print to console.
        
        Args:
            method: UI method to call (print_info, print_error, etc.)
            message: Message to print
        """
        if self.ui and hasattr(self.ui, method):
             getattr(self.ui, method)(message)
        else:
            print(message)

    def _get_plugins_dir(self, server_name: str) -> Path:
        """Gets the plugins directory path for a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Path to the plugins directory
            
        Raises:
            PluginError: If server flavor is not supported for plugins
        """
        server_path = get_server_directory(server_name)
        # Check if server is Java-based (simple check for now)
        server_config = self._load_server_config(server_name) # Helper needed
        flavor = server_config.get('server_flavor')
        if flavor in ["paper", "purpur", "folia", "spigot", "bukkit"]: # Extend as needed
             plugins_dir = server_path / "plugins"
             plugins_dir.mkdir(exist_ok=True)
             return plugins_dir
        else:
             error_msg = f'Plugin management not supported for server flavor: {flavor}'
             self._log('WARNING', error_msg)
             self._print_ui('print_warning', f'Plugins are not supported for server type: {flavor}')
             raise PluginError(error_msg)

    def _load_server_config(self, server_name: str) -> dict:
        """Helper to load server config (needs ConfigManager).
        
        Args:
            server_name: Name of the server
            
        Returns:
            Dictionary containing server configuration
        """
        # In a real scenario, this would import and use ConfigManager
        # For now, a placeholder:
        try:
             from core.config import ConfigManager
             return ConfigManager.load_server_config(server_name)
        except ImportError:
             self._log('ERROR', 'ConfigManager not available for loading server config.')
             return {} # Return empty dict on failure

    def list_plugins(self, server_name: str) -> List[Tuple[str, bool]]:
        """List plugins and their status (enabled/disabled).
        
        Args:
            server_name: Name of the server
            
        Returns:
            List of tuples containing (plugin_name, is_enabled)
            
        Raises:
            PluginError: If plugin directory cannot be accessed
        """
        try:
            plugins_dir = self._get_plugins_dir(server_name)
        except PluginError:
            return []

        plugins = []
        try:
            for item in plugins_dir.iterdir():
                if item.is_file():
                    if item.suffix == '.jar':
                        plugins.append((item.stem, True)) # Enabled
                    elif item.suffixes == ['.jar', '.disabled']:
                         # Handle name like 'MyPlugin.jar.disabled' -> 'MyPlugin'
                         plugin_name = item.name.replace('.jar.disabled', '')
                         plugins.append((plugin_name, False)) # Disabled
            return sorted(plugins, key=lambda p: p[0].lower()) # Sort alphabetically
        except Exception as e:
            error_msg = f"Failed to list plugins for {server_name}: {e}"
            self._log('ERROR', error_msg)
            self._print_ui('print_error', f"Error listing plugins: {e}")
            raise PluginError(error_msg) from e

    def install_plugin(self, server_name: str, source: str) -> bool:
        """Install a plugin from a URL or local path.
        
        Args:
            server_name: Name of the server
            source: URL or local path to the plugin .jar file
            
        Returns:
            True if plugin was installed successfully, False otherwise
            
        Raises:
            PluginError: If installation fails
            DownloadError: If download fails
        """
        try:
            plugins_dir = self._get_plugins_dir(server_name)
        except PluginError as e:
            raise
            
        source_path = Path(source)
        filename = "plugin.jar"  # Default filename
        
        try:
            if source_path.is_file() and source_path.suffix == '.jar':
                # Local file installation
                target_path = plugins_dir / source_path.name
                self._log('INFO', f"Copying local plugin {source_path.name} to {server_name}...")
                shutil.copy2(source_path, target_path)
                self._print_ui('print_success', f"Plugin '{source_path.name}' copied successfully.")
                return True
            elif urllib.parse.urlparse(source).scheme in ['http', 'https']:
                # URL installation
                filename = os.path.basename(urllib.parse.urlparse(source).path)
                if not filename.endswith('.jar'):
                     filename += '.jar' # Basic assumption if no extension
                     
                target_path = plugins_dir / filename
                self._log('INFO', f"Downloading plugin from {source} to {target_path}...")
                self._print_ui('print_info', f"Downloading {filename}...")
                
                # Use urlopen instead of urlretrieve for better control
                req = urllib.request.Request(source, headers={'User-Agent': 'MSM-Plugin-Manager'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    with open(target_path, 'wb') as f:
                        shutil.copyfileobj(response, f)
                
                if not target_path.exists() or target_path.stat().st_size == 0:
                     raise DownloadError("Download failed or resulted in empty file.")

                self._print_ui('print_success', f"Plugin '{filename}' downloaded successfully.")
                return True
            else:
                error_msg = f"Invalid source (not a local .jar file or valid URL): {source}"
                self._log('ERROR', error_msg)
                self._print_ui('print_error', "Invalid source. Must be a URL or a local .jar file path.")
                raise PluginError(error_msg)
        except urllib.error.URLError as e:
            # Clean up potentially incomplete download
            target_path = plugins_dir / filename
            if target_path.exists():
                 try: target_path.unlink()
                 except OSError: pass
            raise DownloadError(f"Failed to download plugin from {source}: {e}") from e
        except Exception as e:
            # Clean up potentially incomplete download
            target_path = plugins_dir / filename
            if target_path.exists():
                 try: target_path.unlink()
                 except OSError: pass
            # Re-raise specific exceptions or wrap generic ones
            if isinstance(e, (PluginError, DownloadError)):
                raise
            else:
                raise PluginError(f"Failed to install plugin from {source}: {e}") from e

    def _find_plugin_file(self, plugins_dir: Path, plugin_name: str) -> Optional[Path]:
        """Finds the .jar or .jar.disabled file for a plugin name.
        
        Args:
            plugins_dir: Path to the plugins directory
            plugin_name: Name of the plugin to find
            
        Returns:
            Path to the plugin file or None if not found
        """
        # Exact match first
        jar_file = plugins_dir / f"{plugin_name}.jar"
        disabled_file = plugins_dir / f"{plugin_name}.jar.disabled"
        
        if jar_file.exists():
            return jar_file
        if disabled_file.exists():
            return disabled_file
            
        # Case-insensitive search as fallback (might be slow with many plugins)
        try:
             for item in plugins_dir.iterdir():
                 if item.is_file():
                      if item.stem.lower() == plugin_name.lower() and item.suffix == '.jar':
                           return item
                      if item.name.lower() == f"{plugin_name}.jar.disabled".lower():
                            return item
        except Exception as e:
             self._log('ERROR', f"Error searching for plugin file: {e}")

        return None # Not found

    def enable_plugin(self, server_name: str, plugin_name: str) -> bool:
        """Enable a disabled plugin by renaming.
        
        Args:
            server_name: Name of the server
            plugin_name: Name of the plugin to enable
            
        Returns:
            True if plugin was enabled successfully, False otherwise
            
        Raises:
            PluginError: If enabling fails
        """
        plugins_dir = self._get_plugins_dir(server_name)

        plugin_file = self._find_plugin_file(plugins_dir, plugin_name)

        if not plugin_file:
            error_msg = f"Plugin '{plugin_name}' not found in {server_name}."
            self._log('ERROR', error_msg)
            self._print_ui('print_error', f"Plugin '{plugin_name}' not found.")
            raise PluginError(error_msg)
            
        if plugin_file.suffix == '.jar':
             self._print_ui('print_info', f"Plugin '{plugin_name}' is already enabled.")
             return True # Already enabled

        if plugin_file.suffixes == ['.jar', '.disabled']:
            try:
                enabled_path = plugins_dir / f"{plugin_name}.jar"
                plugin_file.rename(enabled_path)
                self._log('SUCCESS', f"Enabled plugin '{plugin_name}' for {server_name}.")
                self._print_ui('print_success', f"Plugin '{plugin_name}' enabled.")
                return True
            except Exception as e:
                error_msg = f"Failed to enable plugin '{plugin_name}': {e}"
                self._log('ERROR', error_msg)
                self._print_ui('print_error', f"Failed to enable plugin: {e}")
                raise PluginError(error_msg) from e
        else:
             error_msg = f"Unexpected file type found for plugin '{plugin_name}': {plugin_file.name}"
             self._log('ERROR', error_msg)
             self._print_ui('print_error', "Found unexpected file type for plugin.")
             raise PluginError(error_msg)

    def disable_plugin(self, server_name: str, plugin_name: str) -> bool:
        """Disable an enabled plugin by renaming.
        
        Args:
            server_name: Name of the server
            plugin_name: Name of the plugin to disable
            
        Returns:
            True if plugin was disabled successfully, False otherwise
            
        Raises:
            PluginError: If disabling fails
        """
        plugins_dir = self._get_plugins_dir(server_name)

        plugin_file = self._find_plugin_file(plugins_dir, plugin_name)

        if not plugin_file:
            error_msg = f"Plugin '{plugin_name}' not found in {server_name}."
            self._log('ERROR', error_msg)
            self._print_ui('print_error', f"Plugin '{plugin_name}' not found.")
            raise PluginError(error_msg)
            
        if plugin_file.suffixes == ['.jar', '.disabled']:
             self._print_ui('print_info', f"Plugin '{plugin_name}' is already disabled.")
             return True # Already disabled

        if plugin_file.suffix == '.jar':
            try:
                disabled_path = plugins_dir / f"{plugin_name}.jar.disabled"
                plugin_file.rename(disabled_path)
                self._log('SUCCESS', f"Disabled plugin '{plugin_name}' for {server_name}.")
                self._print_ui('print_success', f"Plugin '{plugin_name}' disabled.")
                return True
            except Exception as e:
                error_msg = f"Failed to disable plugin '{plugin_name}': {e}"
                self._log('ERROR', error_msg)
                self._print_ui('print_error', f"Failed to disable plugin: {e}")
                raise PluginError(error_msg) from e
        else:
             error_msg = f"Unexpected file type found for plugin '{plugin_name}': {plugin_file.name}"
             self._log('ERROR', error_msg)
             self._print_ui('print_error', "Found unexpected file type for plugin.")
             raise PluginError(error_msg)

    def delete_plugin(self, server_name: str, plugin_name: str) -> bool:
        """Delete a plugin.
        
        Args:
            server_name: Name of the server
            plugin_name: Name of the plugin to delete
            
        Returns:
            True if plugin was deleted successfully, False otherwise
            
        Raises:
            PluginError: If deletion fails
        """
        plugins_dir = self._get_plugins_dir(server_name)

        plugin_file = self._find_plugin_file(plugins_dir, plugin_name)

        if not plugin_file:
            error_msg = f"Plugin '{plugin_name}' not found in {server_name}."
            self._log('ERROR', error_msg)
            self._print_ui('print_error', f"Plugin '{plugin_name}' not found.")
            raise PluginError(error_msg)

        try:
            plugin_file.unlink()
            self._log('SUCCESS', f"Deleted plugin '{plugin_name}' from {server_name}.")
            self._print_ui('print_success', f"Plugin '{plugin_name}' deleted.")
            return True
        except Exception as e:
            error_msg = f"Failed to delete plugin '{plugin_name}': {e}"
            self._log('ERROR', error_msg)
            self._print_ui('print_error', f"Failed to delete plugin: {e}")
            raise PluginError(error_msg) from e