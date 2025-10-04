# ============================================================================
# api_client.py - Fetches versions from PaperMC, Purpur, etc.
# ============================================================================
"""
API client for fetching Minecraft server versions and builds.
"""

import urllib.request
import urllib.error
import json
import ssl
from typing import List, Dict, Optional

from utils import log


class PaperMCAPI:
    """PaperMC API client."""
    
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Paper versions.
        API: https://api.papermc.io/v2/projects/paper/versions
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Paper versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Paper versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Paper versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Paper versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """
        Get latest build for a specific version.
        API: https://api.papermc.io/v2/projects/paper/versions/{version}/builds
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper/versions/{version}/builds"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", [])
                if builds:
                    latest = builds[-1]
                    log(f"Latest Paper build for {version}: {latest.get('build')}")
                    return latest
                return None
        except urllib.error.URLError as e:
            log(f"Failed to fetch Paper build for {version} (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Paper build response for {version}: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Paper build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """
        Get download URL for a specific build.
        Format: https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar
        """
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper/versions/{version}/builds/{build}/downloads/paper-{version}-{build}.jar"
            log(f"Generated Paper download URL for {version} build {build}")
            return url
        except Exception as e:
            log(f"Error generating Paper download URL for {version} build {build}: {e}", "ERROR")
            return None


class PurpurAPI:
    """Purpur API client."""
    
    BASE_URL = "https://api.purpurmc.org/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Purpur versions.
        API: https://api.purpurmc.org/v2/purpur
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Purpur versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Purpur versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Purpur versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Purpur versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """
        Get latest build for a specific version.
        API: https://api.purpurmc.org/v2/purpur/{version}
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", [])
                if builds:
                    latest = builds[-1]
                    log(f"Latest Purpur build for {version}: {latest.get('build')}")
                    return latest
                return None
        except urllib.error.URLError as e:
            log(f"Failed to fetch Purpur build for {version} (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Purpur build response for {version}: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Purpur build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """
        Get download URL for a specific build.
        Format: https://api.purpurmc.org/v2/purpur/{version}/{build}/download
        """
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}/{build}/download"
            log(f"Generated Purpur download URL for {version} build {build}")
            return url
        except Exception as e:
            log(f"Error generating Purpur download URL for {version} build {build}: {e}", "ERROR")
            return None


class FoliaAPI:
    """Folia API client."""
    
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Folia versions.
        API: https://api.papermc.io/v2/projects/folia/versions
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Folia versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Folia versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Folia versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Folia versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """
        Get latest build for a specific version.
        API: https://api.papermc.io/v2/projects/folia/versions/{version}/builds
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia/versions/{version}/builds"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", [])
                if builds:
                    latest = builds[-1]
                    log(f"Latest Folia build for {version}: {latest.get('build')}")
                    return latest
                return None
        except urllib.error.URLError as e:
            log(f"Failed to fetch Folia build for {version} (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Folia build response for {version}: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Folia build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """
        Get download URL for a specific build.
        Format: https://api.papermc.io/v2/projects/folia/versions/{version}/builds/{build}/downloads/folia-{version}-{build}.jar
        """
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia/versions/{version}/builds/{build}/downloads/folia-{version}-{build}.jar"
            log(f"Generated Folia download URL for {version} build {build}")
            return url
        except Exception as e:
            log(f"Error generating Folia download URL for {version} build {build}: {e}", "ERROR")
            return None


class FabricAPI:
    """Fabric API client."""
    
    BASE_URL = "https://meta.fabricmc.net/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Fabric versions.
        API: https://meta.fabricmc.net/v2/versions/game
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Filter only stable releases
                versions = [v["version"] for v in data if v.get("stable", False)]
                log(f"Fetched {len(versions)} Fabric versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Fabric versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Fabric versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Fabric versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_loader_versions() -> Optional[List[str]]:
        """
        Fetch available Fabric loader versions.
        API: https://meta.fabricmc.net/v2/versions/loader
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Get the latest few versions
                versions = [v["version"] for v in data[:10]]
                log(f"Fetched {len(versions)} Fabric loader versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Fabric loader versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Fabric loader versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Fabric loader versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """
        Get download URL for Fabric server.
        Format: https://meta.fabricmc.net/v2/versions/loader/{game_version}/{loader_version}/server/jar
        """
        try:
            url = f"{FabricAPI.BASE_URL}/versions/loader/{game_version}/{loader_version}/server/jar"
            log(f"Generated Fabric download URL for game {game_version} loader {loader_version}")
            return url
        except Exception as e:
            log(f"Error generating Fabric download URL for game {game_version} loader {loader_version}: {e}", "ERROR")
            return None


class QuiltAPI:
    """Quilt API client."""
    
    BASE_URL = "https://meta.quiltmc.org/v3"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Quilt versions.
        API: https://meta.quiltmc.org/v3/versions/game
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Filter only versions that have loaders
                versions = [v["version"] for v in data if v.get("has_loader", False)]
                log(f"Fetched {len(versions)} Quilt versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Quilt versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Quilt versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Quilt versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_loader_versions() -> Optional[List[str]]:
        """
        Fetch available Quilt loader versions.
        API: https://meta.quiltmc.org/v3/versions/loader
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Get the latest few versions
                versions = [v["version"] for v in data[:10]]
                log(f"Fetched {len(versions)} Quilt loader versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Quilt loader versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Quilt loader versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Quilt loader versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """
        Get download URL for Quilt server.
        Format: https://meta.quiltmc.org/v3/versions/loader/{game_version}/{loader_version}/server/jar
        """
        try:
            url = f"{QuiltAPI.BASE_URL}/versions/loader/{game_version}/{loader_version}/server/jar"
            log(f"Generated Quilt download URL for game {game_version} loader {loader_version}")
            return url
        except Exception as e:
            log(f"Error generating Quilt download URL for game {game_version} loader {loader_version}: {e}", "ERROR")
            return None


class VanillaAPI:
    """Vanilla Minecraft API client."""
    
    MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """
        Fetch available Vanilla Minecraft versions.
        API: https://launchermeta.mojang.com/mc/game/version_manifest.json
        """
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.MANIFEST_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Get release versions only
                versions = [v["id"] for v in data.get("versions", []) if v.get("type") == "release"]
                log(f"Fetched {len(versions)} Vanilla versions")
                return versions
        except urllib.error.URLError as e:
            log(f"Failed to fetch Vanilla versions (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Vanilla versions response: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Vanilla versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_version_info(version: str) -> Optional[Dict]:
        """
        Get detailed information for a specific Vanilla version.
        """
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.MANIFEST_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                # Find the specific version
                for v in data.get("versions", []):
                    if v.get("id") == version:
                        # Fetch the version details
                        with urllib.request.urlopen(v["url"], timeout=10, context=context) as version_response:
                            version_data = json.loads(version_response.read().decode())
                            log(f"Fetched Vanilla version info for {version}")
                            return version_data
                log(f"Vanilla version {version} not found in manifest")
                return None
        except urllib.error.URLError as e:
            log(f"Failed to fetch Vanilla version info for {version} (network error): {e}", "ERROR")
            return None
        except json.JSONDecodeError as e:
            log(f"Failed to decode Vanilla version info for {version}: {e}", "ERROR")
            return None
        except Exception as e:
            log(f"Unexpected error fetching Vanilla version info for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str) -> Optional[str]:
        """
        Get download URL for Vanilla server.
        """
        try:
            version_info = VanillaAPI.get_version_info(version)
            if not version_info:
                log(f"Failed to get Vanilla version info for {version}", "ERROR")
                return None
                
            # Extract server download URL
            downloads = version_info.get("downloads", {})
            server_download = downloads.get("server", {})
            url = server_download.get("url")
            if url:
                log(f"Generated Vanilla download URL for {version}")
                return url
            else:
                log(f"Vanilla server download URL not found for {version}", "ERROR")
                return None
        except Exception as e:
            log(f"Error generating Vanilla download URL for {version}: {e}", "ERROR")
            return None