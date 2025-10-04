#!/usr/bin/env python3
"""
Unit tests for API client modules.
"""

import unittest
import sys
from pathlib import Path

# Add the project root to the path so we can import the modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api_client import PaperMCAPI, PurpurAPI, FoliaAPI, FabricAPI, QuiltAPI, VanillaAPI


class TestPaperMCAPI(unittest.TestCase):
    """Test cases for PaperMCAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = PaperMCAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:  # If we got versions, check that it's a list
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_latest_build(self):
        """Test that get_latest_build returns build info for a valid version."""
        versions = PaperMCAPI.get_versions()
        if versions:
            latest_version = versions[-1]  # Get the latest version
            build_info = PaperMCAPI.get_latest_build(latest_version)
            self.assertIsNotNone(build_info)
            if build_info:
                self.assertIsInstance(build_info, dict)
                self.assertIn("build", build_info)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = PaperMCAPI.get_versions()
        if versions:
            latest_version = versions[-1]
            build_info = PaperMCAPI.get_latest_build(latest_version)
            if build_info:
                build_number = build_info.get("build")
                if build_number:
                    url = PaperMCAPI.get_download_url(latest_version, build_number)
                    self.assertIsNotNone(url)
                    if url:
                        self.assertIsInstance(url, str)
                        self.assertTrue(url.startswith("http"))


class TestPurpurAPI(unittest.TestCase):
    """Test cases for PurpurAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = PurpurAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_latest_build(self):
        """Test that get_latest_build returns build info for a valid version."""
        versions = PurpurAPI.get_versions()
        if versions:
            latest_version = versions[-1]
            build_info = PurpurAPI.get_latest_build(latest_version)
            self.assertIsNotNone(build_info)
            if build_info:
                self.assertIsInstance(build_info, dict)
                self.assertIn("build", build_info)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = PurpurAPI.get_versions()
        if versions:
            latest_version = versions[-1]
            build_info = PurpurAPI.get_latest_build(latest_version)
            if build_info:
                build_number = build_info.get("build")
                if build_number:
                    url = PurpurAPI.get_download_url(latest_version, build_number)
                    self.assertIsNotNone(url)
                    if url:
                        self.assertIsInstance(url, str)
                        self.assertTrue(url.startswith("http"))


class TestFoliaAPI(unittest.TestCase):
    """Test cases for FoliaAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = FoliaAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_latest_build(self):
        """Test that get_latest_build returns build info for a valid version."""
        versions = FoliaAPI.get_versions()
        if versions:
            latest_version = versions[-1]
            build_info = FoliaAPI.get_latest_build(latest_version)
            self.assertIsNotNone(build_info)
            if build_info:
                self.assertIsInstance(build_info, dict)
                self.assertIn("build", build_info)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = FoliaAPI.get_versions()
        if versions:
            latest_version = versions[-1]
            build_info = FoliaAPI.get_latest_build(latest_version)
            if build_info:
                build_number = build_info.get("build")
                if build_number:
                    url = FoliaAPI.get_download_url(latest_version, build_number)
                    self.assertIsNotNone(url)
                    if url:
                        self.assertIsInstance(url, str)
                        self.assertTrue(url.startswith("http"))


class TestFabricAPI(unittest.TestCase):
    """Test cases for FabricAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = FabricAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_loader_versions(self):
        """Test that get_loader_versions returns a list of loader versions."""
        loader_versions = FabricAPI.get_loader_versions()
        self.assertIsNotNone(loader_versions)
        if loader_versions:
            self.assertIsInstance(loader_versions, list)
            self.assertGreater(len(loader_versions), 0)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = FabricAPI.get_versions()
        loader_versions = FabricAPI.get_loader_versions()
        if versions and loader_versions:
            game_version = versions[0]  # Get a game version
            loader_version = loader_versions[0]  # Get a loader version
            url = FabricAPI.get_download_url(game_version, loader_version)
            self.assertIsNotNone(url)
            if url:
                self.assertIsInstance(url, str)
                self.assertTrue(url.startswith("http"))


class TestQuiltAPI(unittest.TestCase):
    """Test cases for QuiltAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = QuiltAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_loader_versions(self):
        """Test that get_loader_versions returns a list of loader versions."""
        loader_versions = QuiltAPI.get_loader_versions()
        self.assertIsNotNone(loader_versions)
        if loader_versions:
            self.assertIsInstance(loader_versions, list)
            self.assertGreater(len(loader_versions), 0)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = QuiltAPI.get_versions()
        loader_versions = QuiltAPI.get_loader_versions()
        if versions and loader_versions:
            game_version = versions[0] if versions else "1.20.1"
            loader_version = loader_versions[0] if loader_versions else "0.19.2"
            url = QuiltAPI.get_download_url(game_version, loader_version)
            self.assertIsNotNone(url)
            if url:
                self.assertIsInstance(url, str)
                self.assertTrue(url.startswith("http"))


class TestVanillaAPI(unittest.TestCase):
    """Test cases for VanillaAPI class."""
    
    def test_get_versions(self):
        """Test that get_versions returns a list of versions."""
        versions = VanillaAPI.get_versions()
        self.assertIsNotNone(versions)
        if versions:
            self.assertIsInstance(versions, list)
            self.assertGreater(len(versions), 0)
    
    def test_get_version_info(self):
        """Test that get_version_info returns version details."""
        versions = VanillaAPI.get_versions()
        if versions:
            version = versions[0]  # Get the first version
            version_info = VanillaAPI.get_version_info(version)
            self.assertIsNotNone(version_info)
            if version_info:
                self.assertIsInstance(version_info, dict)
    
    def test_get_download_url(self):
        """Test that get_download_url returns a valid URL."""
        versions = VanillaAPI.get_versions()
        if versions:
            version = versions[0]  # Get the first version
            url = VanillaAPI.get_download_url(version)
            self.assertIsNotNone(url)
            if url:
                self.assertIsInstance(url, str)
                self.assertTrue(url.startswith("http"))


if __name__ == "__main__":
    unittest.main()