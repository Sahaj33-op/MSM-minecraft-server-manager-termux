from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from utils.archive import safe_extract_zip
from utils.system import get_required_java


def test_safe_extract_zip_blocks_path_traversal():
    temp_path = Path(".test_tmp") / "zip-slip"
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)
    temp_path.mkdir(parents=True, exist_ok=True)
    try:
        archive_path = temp_path / "bad.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("../escape.txt", "owned")

        with pytest.raises(ValueError, match="Blocked unsafe archive member"):
            safe_extract_zip(archive_path, temp_path / "server")
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


def test_get_required_java_handles_1_20_5_and_older_releases():
    assert get_required_java("1.20.5") == "21"
    assert get_required_java("1.20.4") == "17"
    assert get_required_java("1.16.5") == "8"
