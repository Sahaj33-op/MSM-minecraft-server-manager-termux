#!/usr/bin/env python3
"""
API Client - From v1.1.0 branch with all server type support
Paper, Purpur, Folia, Fabric, Quilt, Vanilla APIs
"""
import urllib.request
import urllib.error
import json
import ssl
import time
import random
from typing import List, Dict, Optional, Any, Callable

# Add import for custom exceptions
from core.exceptions import APIError
from core.constants import NetworkConfig

class BaseAPI:
    """Base API client class with shared functionality."""

    # Class variable to hold the logger instance
    logger = None

    # Retry configuration - use centralized constants
    MAX_RETRIES = NetworkConfig.MAX_RETRIES
    BASE_DELAY = NetworkConfig.RETRY_DELAY
    MAX_DELAY = NetworkConfig.MAX_RETRY_DELAY
    JITTER_FACTOR = NetworkConfig.JITTER_FACTOR
    DEFAULT_TIMEOUT = NetworkConfig.DEFAULT_TIMEOUT

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

    @classmethod
    def _calculate_backoff(cls, attempt: int) -> float:
        """Calculate exponential backoff delay with jitter.

        Args:
            attempt: Current retry attempt number (0-indexed)

        Returns:
            Delay in seconds with random jitter
        """
        # Exponential backoff: base_delay * 2^attempt
        delay = min(cls.BASE_DELAY * (2 ** attempt), cls.MAX_DELAY)

        # Add random jitter to prevent thundering herd
        jitter = delay * cls.JITTER_FACTOR * random.random()

        return delay + jitter

    @classmethod
    def _make_request_with_retry(
        cls,
        url: str,
        timeout: int = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: Optional[int] = None
    ) -> Any:
        """Make HTTP request with exponential backoff retry logic.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds (default: uses DEFAULT_TIMEOUT)
            headers: Optional request headers
            max_retries: Override default max retries

        Returns:
            Parsed JSON response data

        Raises:
            APIError: If all retries fail
        """
        retries = max_retries if max_retries is not None else cls.MAX_RETRIES
        request_timeout = timeout if timeout is not None else cls.DEFAULT_TIMEOUT
        last_error = None
        context = ssl.create_default_context()

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers or {})

                with urllib.request.urlopen(req, timeout=request_timeout, context=context) as response:
                    return json.loads(response.read().decode())

            except urllib.error.HTTPError as e:
                last_error = e
                # Don't retry client errors (4xx) except for rate limiting (429)
                if 400 <= e.code < 500 and e.code != 429:
                    raise APIError(f"HTTP error {e.code}: {e.reason}") from e

                # Retry for server errors (5xx) and rate limiting (429)
                if attempt < retries:
                    delay = cls._calculate_backoff(attempt)
                    cls._log(f"Request failed (attempt {attempt + 1}/{retries + 1}), retrying in {delay:.1f}s: {e}", "WARNING")
                    time.sleep(delay)

            except urllib.error.URLError as e:
                last_error = e
                # Network errors - retry
                if attempt < retries:
                    delay = cls._calculate_backoff(attempt)
                    cls._log(f"Network error (attempt {attempt + 1}/{retries + 1}), retrying in {delay:.1f}s: {e}", "WARNING")
                    time.sleep(delay)

            except json.JSONDecodeError as e:
                # Don't retry JSON parsing errors
                raise APIError(f"Failed to decode JSON response: {e}") from e

            except Exception as e:
                last_error = e
                # Unexpected error - retry
                if attempt < retries:
                    delay = cls._calculate_backoff(attempt)
                    cls._log(f"Unexpected error (attempt {attempt + 1}/{retries + 1}), retrying in {delay:.1f}s: {e}", "WARNING")
                    time.sleep(delay)

        # All retries exhausted
        raise APIError(f"Request failed after {retries + 1} attempts: {last_error}") from last_error

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
            data = PaperMCAPI._make_request_with_retry(url)
            versions = data.get("versions", [])
            PaperMCAPI._log(f"Fetched {len(versions)} Paper versions")
            return versions
        except APIError:
            raise
        except Exception as e:
            PaperMCAPI._log(f"Unexpected error fetching Paper versions: {e}", "ERROR")
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
            url = f"{PaperMCAPI.BASE_URL}/projects/paper/versions/{version}/builds"
            data = PaperMCAPI._make_request_with_retry(url)
            builds = data.get("builds", [])
            if builds:
                latest = builds[-1]
                PaperMCAPI._log(f"Latest Paper build for {version}: {latest.get('build')}")
                return latest
            return None
        except APIError:
            raise
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
            data = PurpurAPI._make_request_with_retry(url)
            versions = data.get("versions", [])
            PurpurAPI._log(f"Fetched {len(versions)} Purpur versions")
            return versions
        except APIError:
            raise
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
            data = PurpurAPI._make_request_with_retry(url)
            builds = data.get("builds", {})
            if builds:
                latest = builds[-1]
                PurpurAPI._log(f"Latest Purpur build for {version}: {latest.get('build')}")
                return latest
            return None
        except APIError:
            raise
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
            data = FoliaAPI._make_request_with_retry(url)
            versions = data.get("versions", [])
            FoliaAPI._log(f"Fetched {len(versions)} Folia versions")
            return versions
        except APIError:
            raise
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
            data = FoliaAPI._make_request_with_retry(url)
            builds = data.get("builds", [])
            if builds:
                latest = builds[-1]
                FoliaAPI._log(f"Latest Folia build for {version}: {latest.get('build')}")
                return latest
            return None
        except APIError:
            raise
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
            data = VanillaAPI._make_request_with_retry(VanillaAPI.BASE_URL)
            versions = [version["id"] for version in data.get("versions", [])]
            VanillaAPI._log(f"Fetched {len(versions)} Vanilla versions")
            return versions
        except APIError:
            raise
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
            # First get the version manifest URL with retry
            data = VanillaAPI._make_request_with_retry(VanillaAPI.BASE_URL)

            # Find the version entry
            version_entry = None
            for v in data.get("versions", []):
                if v["id"] == version:
                    version_entry = v
                    break

            if not version_entry:
                VanillaAPI._log(f"Version {version} not found in Vanilla manifest", "ERROR")
                return None

            # Get the version manifest with retry
            manifest = VanillaAPI._make_request_with_retry(version_entry["url"])

            # Extract the server JAR download URL
            download_url = manifest["downloads"]["server"]["url"]
            VanillaAPI._log(f"Generated Vanilla download URL for {version}")
            return download_url

        except APIError:
            raise
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
            data = FabricAPI._make_request_with_retry(url)
            versions = [version["version"] for version in data]
            FabricAPI._log(f"Fetched {len(versions)} Fabric versions")
            return versions
        except APIError:
            raise
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
            data = FabricAPI._make_request_with_retry(url)
            if data:
                loader_version = data[0]["version"]
                FabricAPI._log(f"Latest Fabric loader version: {loader_version}")
                return loader_version
            return None
        except APIError:
            raise
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
            data = QuiltAPI._make_request_with_retry(url)
            versions = [version["version"] for version in data]
            QuiltAPI._log(f"Fetched {len(versions)} Quilt versions")
            return versions
        except APIError:
            raise
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
            data = QuiltAPI._make_request_with_retry(url)
            if data:
                loader_version = data[0]["version"]
                QuiltAPI._log(f"Latest Quilt loader version: {loader_version}")
                return loader_version
            return None
        except APIError:
            raise
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
            headers = {"User-Agent": "MSM-PocketMine-Client"}
            data = PocketMineAPI._make_request_with_retry(
                PocketMineAPI.BASE_URL,
                headers=headers
            )
            versions = [release["tag_name"] for release in data[:20]]  # Get latest 20 releases
            PocketMineAPI._log(f"Fetched {len(versions)} PocketMine versions")
            return versions
        except APIError:
            raise
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
            headers = {"User-Agent": "MSM-PocketMine-Client"}
            data = PocketMineAPI._make_request_with_retry(
                PocketMineAPI.BASE_URL,
                headers=headers
            )

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
        except APIError:
            raise
        except Exception as e:
            PocketMineAPI._log(f"Error generating PocketMine download URL for {version}: {e}", "ERROR")
            return None
