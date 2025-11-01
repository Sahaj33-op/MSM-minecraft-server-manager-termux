#!/usr/bin/env python3
"""
API Client - From v1.1.0 branch with all server type support
Paper, Purpur, Folia, Fabric, Quilt, Vanilla APIs
"""
import urllib.request
import urllib.error
import json
import ssl
from typing import List, Dict, Optional

# Add import for custom exceptions
from core.exceptions import APIError

class BaseAPI:
    """Base API client class with shared functionality."""
    
    # Class variable to hold the logger instance
    logger = None
    
    @classmethod
    def set_logger(cls, logger):
        """Set the logger instance for this class.
        
        Args:
            logger: Logger instance to use for logging
        """
        cls.logger = logger
    
    @classmethod
    def _log(cls, message: str, level: str = "INFO"):
        """Log a message using the injected logger or fallback to print.
        
        Args:
            message: Message to log
            level: Log level (default: "INFO")
        """
        if cls.logger:
            cls.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

class PaperMCAPI(BaseAPI):
    """PaperMC API client."""
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Paper versions.
        
        Returns:
            List of available Paper versions or None if an error occurred
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                PaperMCAPI._log(f"Fetched {len(versions)} Paper versions")
                return versions
        except urllib.error.URLError as e:
            # Raise specific exception
            raise APIError(f"Network error fetching Paper versions: {e}") from e 
        except json.JSONDecodeError as e:
            # Raise specific exception
            raise APIError(f"Failed to decode Paper versions JSON: {e}") from e 
        except Exception as e:
            # Keep generic for truly unexpected, but log it
            PaperMCAPI._log(f"Unexpected error fetching Paper versions: {e}", "ERROR")
            # Optionally re-raise as a base MSMError or keep None return
            return None # Or raise MSMError(f"Unexpected: {e}") from e
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version.
        
        Args:
            version: Minecraft version
            
        Returns:
            Dictionary containing build information or None if an error occurred
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper/versions/{version}/builds"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", [])
                if builds:
                    latest = builds[-1]
                    PaperMCAPI._log(f"Latest Paper build for {version}: {latest.get('build')}")
                    return latest
                return None
        except urllib.error.URLError as e:
            # Raise specific exception
            raise APIError(f"Network error fetching Paper build for {version}: {e}") from e 
        except json.JSONDecodeError as e:
            # Raise specific exception
            raise APIError(f"Failed to decode Paper build JSON for {version}: {e}") from e 
        except Exception as e:
            PaperMCAPI._log(f"Failed to fetch Paper build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build.
        
        Args:
            version: Minecraft version
            build: Build number
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
            PaperMCAPI._log(f"Generated Paper download URL for {version} build {build}")
            return url
        except Exception as e:
            PaperMCAPI._log(f"Error generating Paper download URL for {version} build {build}: {e}", "ERROR")
            return None

class PurpurAPI(BaseAPI):
    """Purpur API client."""
    BASE_URL = "https://api.purpurmc.org/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Purpur versions.
        
        Returns:
            List of available Purpur versions or None if an error occurred
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                PurpurAPI._log(f"Fetched {len(versions)} Purpur versions")
                return versions
        except Exception as e:
            PurpurAPI._log(f"Failed to fetch Purpur versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version.
        
        Args:
            version: Minecraft version
            
        Returns:
            Dictionary containing build information or None if an error occurred
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", {})
                if builds:
                    latest = builds[-1]
                    PurpurAPI._log(f"Latest Purpur build for {version}: {latest.get('build')}")
                    return latest
                return None
        except Exception as e:
            PurpurAPI._log(f"Failed to fetch Purpur build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build.
        
        Args:
            version: Minecraft version
            build: Build number
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}/{build}/download"
            PurpurAPI._log(f"Generated Purpur download URL for {version} build {build}")
            return url
        except Exception as e:
            PurpurAPI._log(f"Error generating Purpur download URL for {version} build {build}: {e}", "ERROR")
            return None

class FoliaAPI(BaseAPI):
    """Folia API client (uses Paper API)."""
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Folia versions.
        
        Returns:
            List of available Folia versions or None if an error occurred
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                FoliaAPI._log(f"Fetched {len(versions)} Folia versions")
                return versions
        except Exception as e:
            FoliaAPI._log(f"Failed to fetch Folia versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version.
        
        Args:
            version: Minecraft version
            
        Returns:
            Dictionary containing build information or None if an error occurred
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia/versions/{version}/builds"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", [])
                if builds:
                    latest = builds[-1]
                    FoliaAPI._log(f"Latest Folia build for {version}: {latest.get('build')}")
                    return latest
                return None
        except Exception as e:
            FoliaAPI._log(f"Failed to fetch Folia build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build.
        
        Args:
            version: Minecraft version
            build: Build number
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia/versions/{version}/builds/{build}/downloads/folia-{version}-{build}.jar"
            FoliaAPI._log(f"Generated Folia download URL for {version} build {build}")
            return url
        except Exception as e:
            FoliaAPI._log(f"Error generating Folia download URL for {version} build {build}: {e}", "ERROR")
            return None

class VanillaAPI(BaseAPI):
    """Vanilla Minecraft API client."""
    BASE_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Vanilla versions.
        
        Returns:
            List of available Vanilla versions or None if an error occurred
        """
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.BASE_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [version["id"] for version in data.get("versions", [])]
                VanillaAPI._log(f"Fetched {len(versions)} Vanilla versions")
                return versions
        except Exception as e:
            VanillaAPI._log(f"Failed to fetch Vanilla versions: {e}", "ERROR")
            return None

    @staticmethod
    def get_download_url(version: str) -> Optional[str]:
        """Get download URL for a specific Vanilla version.
        
        Args:
            version: Minecraft version
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            # First get the version manifest URL
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.BASE_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                
            # Find the version entry
            version_entry = None
            for v in data.get("versions", []):
                if v["id"] == version:
                    version_entry = v
                    break
                    
            if not version_entry:
                VanillaAPI._log(f"Version {version} not found in Vanilla manifest", "ERROR")
                return None
                
            # Get the version manifest
            manifest_url = version_entry["url"]
            with urllib.request.urlopen(manifest_url, timeout=10, context=context) as response:
                manifest = json.loads(response.read().decode())
                
            # Extract the server JAR download URL
            download_url = manifest["downloads"]["server"]["url"]
            VanillaAPI._log(f"Generated Vanilla download URL for {version}")
            return download_url
            
        except Exception as e:
            VanillaAPI._log(f"Error generating Vanilla download URL for {version}: {e}", "ERROR")
            return None

class FabricAPI(BaseAPI):
    """Fabric API client."""
    BASE_URL = "https://meta.fabricmc.net/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Fabric versions.
        
        Returns:
            List of available Fabric versions or None if an error occurred
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [version["version"] for version in data]
                FabricAPI._log(f"Fetched {len(versions)} Fabric versions")
                return versions
        except Exception as e:
            FabricAPI._log(f"Failed to fetch Fabric versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_loader() -> Optional[str]:
        """Get the latest Fabric loader version.
        
        Returns:
            Latest Fabric loader version string or None if an error occurred
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                if data:
                    loader_version = data[0]["version"]
                    FabricAPI._log(f"Latest Fabric loader version: {loader_version}")
                    return loader_version
                return None
        except Exception as e:
            FabricAPI._log(f"Failed to fetch Fabric loader version: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """Get download URL for a specific Fabric version.
        
        Args:
            game_version: Minecraft version
            loader_version: Fabric loader version
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/loader/{game_version}/{loader_version}/server/jar"
            FabricAPI._log(f"Generated Fabric download URL for {game_version} with loader {loader_version}")
            return url
        except Exception as e:
            FabricAPI._log(f"Error generating Fabric download URL for {game_version} with loader {loader_version}: {e}", "ERROR")
            return None

class QuiltAPI(BaseAPI):
    """Quilt API client."""
    BASE_URL = "https://meta.quiltmc.org/v3"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Quilt versions.
        
        Returns:
            List of available Quilt versions or None if an error occurred
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [version["version"] for version in data]
                QuiltAPI._log(f"Fetched {len(versions)} Quilt versions")
                return versions
        except Exception as e:
            QuiltAPI._log(f"Failed to fetch Quilt versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_loader() -> Optional[str]:
        """Get the latest Quilt loader version.
        
        Returns:
            Latest Quilt loader version string or None if an error occurred
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                if data:
                    loader_version = data[0]["version"]
                    QuiltAPI._log(f"Latest Quilt loader version: {loader_version}")
                    return loader_version
                return None
        except Exception as e:
            QuiltAPI._log(f"Failed to fetch Quilt loader version: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """Get download URL for a specific Quilt version.
        
        Args:
            game_version: Minecraft version
            loader_version: Quilt loader version
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/loader/{game_version}/{loader_version}/server/jar"
            QuiltAPI._log(f"Generated Quilt download URL for {game_version} with loader {loader_version}")
            return url
        except Exception as e:
            QuiltAPI._log(f"Error generating Quilt download URL for {game_version} with loader {loader_version}: {e}", "ERROR")
            return None

class PocketMineAPI(BaseAPI):
    """PocketMine-MP API client."""
    BASE_URL = "https://api.github.com/repos/pmmp/PocketMine-MP/releases"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available PocketMine versions.
        
        Returns:
            List of available PocketMine versions or None if an error occurred
        """
        try:
            url = PocketMineAPI.BASE_URL
            context = ssl.create_default_context()
            headers = {"User-Agent": "MSM-PocketMine-Client"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [release["tag_name"] for release in data[:20]]  # Get latest 20 releases
                PocketMineAPI._log(f"Fetched {len(versions)} PocketMine versions")
                return versions
        except Exception as e:
            PocketMineAPI._log(f"Failed to fetch PocketMine versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str) -> Optional[str]:
        """Get download URL for a specific PocketMine version.
        
        Args:
            version: PocketMine version
            
        Returns:
            Download URL string or None if an error occurred
        """
        try:
            url = PocketMineAPI.BASE_URL
            context = ssl.create_default_context()
            headers = {"User-Agent": "MSM-PocketMine-Client"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                
            # Find the release with the matching tag
            for release in data:
                if release["tag_name"] == version:
                    # Find the .phar asset
                    for asset in release["assets"]:
                        if asset["name"].endswith(".phar"):
                            PocketMineAPI._log(f"Generated PocketMine download URL for {version}")
                            return asset["browser_download_url"]
                    break
                    
            PocketMineAPI._log(f"PocketMine version {version} not found", "ERROR")
            return None
        except Exception as e:
            PocketMineAPI._log(f"Error generating PocketMine download URL for {version}: {e}", "ERROR")
            return None
