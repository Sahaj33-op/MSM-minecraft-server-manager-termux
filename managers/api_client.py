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

def log(message: str, level: str = "INFO"):
    """Simple logging fallback"""
    print(f"[{level}] {message}")

class PaperMCAPI:
    """PaperMC API client."""
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Paper versions."""
        try:
            url = f"{PaperMCAPI.BASE_URL}/projects/paper"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Paper versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Paper versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version."""
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
        except Exception as e:
            log(f"Failed to fetch Paper build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build."""
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
        """Fetch available Purpur versions."""
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Purpur versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Purpur versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version."""
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                builds = data.get("builds", {})
                if builds:
                    latest = builds[-1]
                    log(f"Latest Purpur build for {version}: {latest.get('build')}")
                    return latest
                return None
        except Exception as e:
            log(f"Failed to fetch Purpur build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build."""
        try:
            url = f"{PurpurAPI.BASE_URL}/purpur/{version}/{build}/download"
            log(f"Generated Purpur download URL for {version} build {build}")
            return url
        except Exception as e:
            log(f"Error generating Purpur download URL for {version} build {build}: {e}", "ERROR")
            return None

class FoliaAPI:
    """Folia API client (uses Paper API)."""
    BASE_URL = "https://api.papermc.io/v2"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Folia versions."""
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = data.get("versions", [])
                log(f"Fetched {len(versions)} Folia versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Folia versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get latest build for a specific version."""
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
        except Exception as e:
            log(f"Failed to fetch Folia build for {version}: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str, build: int) -> Optional[str]:
        """Get download URL for a specific build."""
        try:
            url = f"{FoliaAPI.BASE_URL}/projects/folia/versions/{version}/builds/{build}/downloads/folia-{version}-{build}.jar"
            log(f"Generated Folia download URL for {version} build {build}")
            return url
        except Exception as e:
            log(f"Error generating Folia download URL for {version} build {build}: {e}", "ERROR")
            return None

class VanillaAPI:
    """Vanilla Minecraft API client."""
    BASE_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available Vanilla versions."""
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.BASE_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [v["id"] for v in data.get("versions", [])]
                log(f"Fetched {len(versions)} Vanilla versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Vanilla versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(version: str) -> Optional[str]:
        """Get download URL for a specific version."""
        try:
            context = ssl.create_default_context()
            with urllib.request.urlopen(VanillaAPI.BASE_URL, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                for v in data.get("versions", []):
                    if v["id"] == version:
                        with urllib.request.urlopen(v["url"], timeout=10, context=context) as ver_response:
                            ver_data = json.loads(ver_response.read().decode())
                            return ver_data["downloads"]["server"]["url"]
                return None
        except Exception as e:
            log(f"Failed to get Vanilla download URL for {version}: {e}", "ERROR")
            return None

class FabricAPI:
    """Fabric API client."""
    BASE_URL = "https://meta.fabricmc.net/v2/versions"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available game versions."""
        try:
            url = f"{FabricAPI.BASE_URL}/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [v["version"] for v in data if v.get("stable", False)]
                log(f"Fetched {len(versions)} Fabric game versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Fabric versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_loader_versions() -> Optional[List[str]]:
        """Fetch available loader versions."""
        try:
            url = f"{FabricAPI.BASE_URL}/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [v["version"] for v in data]
                log(f"Fetched {len(versions)} Fabric loader versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Fabric loader versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """Get Fabric server download URL."""
        try:
            installer_url = f"{FabricAPI.BASE_URL}/installer"
            context = ssl.create_default_context()
            with urllib.request.urlopen(installer_url, timeout=10, context=context) as response:
                installer_data = json.loads(response.read().decode())
                installer_version = installer_data[0]["version"]
                
            url = f"https://meta.fabricmc.net/v2/versions/loader/{game_version}/{loader_version}/{installer_version}/server/jar"
            log(f"Generated Fabric download URL for {game_version} with loader {loader_version}")
            return url
        except Exception as e:
            log(f"Error generating Fabric download URL: {e}", "ERROR")
            return None

class QuiltAPI:
    """Quilt API client."""
    BASE_URL = "https://meta.quiltmc.org/v3/versions"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available game versions."""
        try:
            url = f"{QuiltAPI.BASE_URL}/game"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [v["version"] for v in data if v.get("stable", False)]
                log(f"Fetched {len(versions)} Quilt game versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Quilt versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_loader_versions() -> Optional[List[str]]:
        """Fetch available loader versions."""
        try:
            url = f"{QuiltAPI.BASE_URL}/loader"
            context = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=10, context=context) as response:
                data = json.loads(response.read().decode())
                versions = [v["version"] for v in data]
                log(f"Fetched {len(versions)} Quilt loader versions")
                return versions
        except Exception as e:
            log(f"Failed to fetch Quilt loader versions: {e}", "ERROR")
            return None
    
    @staticmethod
    def get_download_url(game_version: str, loader_version: str) -> Optional[str]:
        """Get Quilt server download URL."""
        try:
            url = f"https://meta.quiltmc.org/v3/versions/loader/{game_version}/{loader_version}/0.0.0/server/jar"
            log(f"Generated Quilt download URL for {game_version} with loader {loader_version}")
            return url
        except Exception as e:
            log(f"Error generating Quilt download URL: {e}", "ERROR")
            return None

class PocketMineAPI:
    """PocketMine-MP API client."""
    
    BASE_URL = "https://api.github.com/repos/pmmp/PocketMine-MP/releases"
    
    @staticmethod
    def get_versions() -> Optional[List[str]]:
        """Fetch available PocketMine versions (tags) from GitHub Releases."""
        try:
            url = PocketMineAPI.BASE_URL
            context = ssl.create_default_context()
            # Add User-Agent header to avoid potential blocking
            req = urllib.request.Request(url, headers={'User-Agent': 'MSM-Server-Manager'})
            with urllib.request.urlopen(req, timeout=15, context=context) as response:
                data = json.loads(response.read().decode())
                # Get non-draft and non-prerelease versions
                versions = [
                    r["tag_name"] for r in data 
                    if not r.get("draft", True) # Exclude drafts
                       # Adjust if you want pre-releases: and not r.get("prerelease", False) 
                       and any(asset.get("name", "").endswith(".phar") for asset in r.get("assets", [])) # Ensure phar exists
                ]
                log(f"Fetched {len(versions)} PocketMine versions")
                return versions # GitHub API often returns newest first, may need sorting depending on preference
        except Exception as e:
            log(f"Failed to fetch PocketMine versions: {e}", "ERROR")
            return None

    @staticmethod
    def get_latest_build(version: str) -> Optional[Dict]:
        """Get build info (download asset) for a specific version tag."""
        try:
            # GitHub API uses tags, so we fetch info for the specific tag
            url = f"{PocketMineAPI.BASE_URL}/tags/{version}" 
            context = ssl.create_default_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'MSM-Server-Manager'})
            with urllib.request.urlopen(req, timeout=15, context=context) as response:
                release_data = json.loads(response.read().decode())
                for asset in release_data.get("assets", []):
                    if asset.get("name", "").endswith(".phar"):
                        log(f"Found PocketMine asset for {version}: {asset['name']}")
                        return {
                            "build": asset.get("id"), # Use asset ID as a pseudo-build number
                            "download_url": asset.get("browser_download_url"),
                            "filename": asset.get("name")
                        }
                log(f"No .phar asset found for PocketMine version {version}", "WARNING")
                return None
        except Exception as e:
            log(f"Failed to fetch PocketMine build info for {version}: {e}", "ERROR")
            return None

    @staticmethod
    def get_download_url(version: str, build_info: dict) -> Optional[str]:
        """Get download URL directly from the build_info dictionary."""
        # For PocketMine, the build_info already contains the direct download URL
        url = build_info.get("download_url")
        if url:
             log(f"Using PocketMine download URL: {url}")
             return url
        else:
            log(f"Missing download_url in build_info for PocketMine {version}", "ERROR")
            return None