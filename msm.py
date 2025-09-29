#!/usr/bin/env python3
"""
Enhanced Minecraft Server Manager (MSM) for Termux - FIXED VERSION
Fixed timeout issues and version ordering problems
Supports: Paper, Purpur, Folia, Vanilla, PocketMine-MP
"""

import os
import sys
import subprocess
import time
import requests
import json
import re
import hashlib
import psutil
import threading
from datetime import datetime
from pathlib import Path
import math
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# --- Configuration ---
SERVER_DIR = os.path.expanduser("~/minecraft-server")
CONFIG_DIR = os.path.expanduser("~/.config/msm")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
BACKUP_DIR = os.path.join(SERVER_DIR, "backups")
SERVER_JAR_NAME = "server.jar"
SCREEN_SESSION_NAME = "mcserver"
NGROK_TIMEOUT = 15
MAX_RAM_PERCENTAGE = 75
VERSIONS_PER_PAGE = 10

# Enhanced timeout and retry configuration
REQUEST_TIMEOUT = (10, 30)  # (connect_timeout, read_timeout)
MAX_RETRIES = 3

# Server Flavors Configuration
SERVER_FLAVORS = {
    "paper": {
        "name": "PaperMC",
        "description": "High-performance Minecraft server with optimizations",
        "api_base": "https://api.papermc.io/v2/projects/paper",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "paper-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java"
    },
    "purpur": {
        "name": "Purpur",
        "description": "Paper fork with extra features and configurability",
        "api_base": "https://api.purpurmc.org/v2/purpur",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "purpur-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java"
    },
    "folia": {
        "name": "Folia",
        "description": "Regionized multi-threaded Paper fork",
        "api_base": "https://api.papermc.io/v2/projects/folia",
        "supports_versions": True,
        "supports_snapshots": False,
        "jar_pattern": "folia-{version}-{build}.jar",
        "default_port": 25565,
        "type": "java"
    },
    "vanilla": {
        "name": "Vanilla Minecraft",
        "description": "Official Minecraft server from Mojang",
        "api_base": "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "server.jar",
        "default_port": 25565,
        "type": "java"
    },
    "pocketmine": {
        "name": "PocketMine-MP",
        "description": "Bedrock Edition server software",
        "api_base": "https://api.github.com/repos/pmmp/PocketMine-MP/releases",
        "supports_versions": True,
        "supports_snapshots": True,
        "jar_pattern": "PocketMine-MP.phar",
        "default_port": 19132,
        "type": "php"
    }
}

# --- ANSI Color Codes ---
class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

def create_robust_session():
    """Create a requests session with retry strategy and proper timeouts."""
    session = requests.Session()

    # Define retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=1,
        raise_on_redirect=False,
        raise_on_status=False
    )

    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set headers
    session.headers.update({
        'User-Agent': 'MSM-Enhanced/3.1 (Minecraft Server Manager)',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    })

    return session

def log_message(level, message):
    """Centralized logging with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color_map = {
        'INFO': C.BLUE,
        'SUCCESS': C.GREEN,
        'WARNING': C.YELLOW,
        'ERROR': C.RED,
        'DEBUG': C.DIM
    }
    color = color_map.get(level, C.RESET)
    print(f"{C.DIM}[{timestamp}]{C.RESET} {color}[{level}]{C.RESET} {message}")

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Prints the enhanced header for the application."""
    clear_screen()
    print(f"{C.BOLD}{C.CYAN}{'=' * 70}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':^20} Enhanced Multi-Flavor Server Manager v3.2 {'':^20}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'':^25} Paper | Purpur | Folia | Vanilla | PocketMine {'':^25}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 70}{C.RESET}")
    print()

def run_command(command, check=True, capture_output=False, timeout=None):
    """Enhanced command runner with timeout and better error handling."""
    try:
        log_message('DEBUG', f"Executing: {command}")
        result = subprocess.run(
            command,
            check=check,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=timeout
        )
        return result if capture_output else True
    except subprocess.TimeoutExpired:
        log_message('ERROR', f"Command timed out: {command}")
        return None if capture_output else False
    except subprocess.CalledProcessError as e:
        log_message('ERROR', f"Command failed: {command}")
        if e.stderr:
            log_message('ERROR', f"stderr: {e.stderr}")
        return None if capture_output else False
    except Exception as e:
        log_message('ERROR', f"Unexpected error: {e}")
        return None if capture_output else False

def get_system_info():
    """Get system memory and CPU information."""
    try:
        total_ram_mb = None

        # Try psutil first
        try:
            import psutil
            total_ram_mb = psutil.virtual_memory().total // (1024 * 1024)
        except:
            pass

        # Try /proc/meminfo
        if total_ram_mb is None:
            try:
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if line.startswith('MemTotal:'):
                            total_ram_mb = int(line.split()[1]) // 1024
                            break
            except:
                pass

        # Fallback
        if total_ram_mb is None:
            total_ram_mb = 4096

        return {
            'total_ram_mb': total_ram_mb,
            'max_safe_ram_mb': int(total_ram_mb * MAX_RAM_PERCENTAGE / 100),
            'cpu_count': os.cpu_count() or 2
        }
    except Exception as e:
        log_message('WARNING', f"Could not detect system info: {e}")
        return {'total_ram_mb': 4096, 'max_safe_ram_mb': 3072, 'cpu_count': 2}

def validate_file(filepath, expected_size=None, check_zip_bomb=True):
    """Comprehensive file validation with security checks."""
    if not os.path.exists(filepath):
        return False, "File does not exist"

    try:
        stat = os.stat(filepath)

        if stat.st_size == 0:
            return False, "File is empty"

        if check_zip_bomb and stat.st_size > 500 * 1024 * 1024:  # 500MB
            return False, "File suspiciously large (>500MB)"

        if expected_size and abs(stat.st_size - expected_size) > 1024:
            return False, f"File size mismatch. Expected: {expected_size}, Got: {stat.st_size}"

        if not os.access(filepath, os.R_OK):
            return False, "File is not readable"

        # For JAR files, do basic validation
        if filepath.endswith('.jar'):
            try:
                with open(filepath, 'rb') as f:
                    header = f.read(4)
                    if not header.startswith(b'PK'):
                        return False, "Invalid JAR file format"
            except Exception as e:
                return False, f"Cannot validate JAR: {e}"

        return True, "File validation passed"
    except Exception as e:
        return False, f"Validation error: {e}"

def check_dependencies():
    """Enhanced dependency checker based on server type."""
    log_message('INFO', "Checking system dependencies...")

    dependencies = {
        'java': 'openjdk-21',
        'wget': 'wget',
        'tar': 'tar',
        'screen': 'screen',
        'curl': 'curl'
    }

    missing_deps = []

    for command, package in dependencies.items():
        result = run_command(f"command -v {command}", capture_output=True)
        if not result or result.returncode != 0:
            missing_deps.append(package)

    if missing_deps:
        log_message('WARNING', f"Missing dependencies: {', '.join(missing_deps)}")

        if input(f"{C.YELLOW}Install missing dependencies? (y/N): {C.RESET}").lower() == 'y':
            for package in missing_deps:
                log_message('INFO', f"Installing {package}...")
                if not run_command(f"pkg install {package} -y", timeout=300):
                    log_message('ERROR', f"Failed to install {package}")
                    return False
        else:
            log_message('ERROR', "Cannot proceed without required dependencies")
            return False

    log_message('SUCCESS', "All dependencies satisfied")
    return True

def is_snapshot_version(version):
    """Check if a version is a snapshot/pre-release."""
    snapshot_patterns = [
        'pre', 'rc', 'snapshot', 'alpha', 'beta', 'dev', 'experimental'
    ]
    version_lower = version.lower()
    return any(pattern in version_lower for pattern in snapshot_patterns)

def safe_request(session, method, url, **kwargs):
    """Make a safe HTTP request with proper error handling."""
    try:
        kwargs.setdefault('timeout', REQUEST_TIMEOUT)
        response = session.request(method, url, **kwargs)

        if response.status_code == 200:
            return response
        else:
            log_message('WARNING', f"HTTP {response.status_code} for {url}")
            return None

    except requests.exceptions.Timeout:
        log_message('ERROR', f"Request timed out for {url}")
        return None
    except requests.exceptions.ConnectionError:
        log_message('ERROR', f"Connection error for {url}")
        return None
    except requests.exceptions.RequestException as e:
        log_message('ERROR', f"Request failed for {url}: {e}")
        return None

def get_paper_versions(include_snapshots=False):
    """Get available Paper versions with enhanced error handling."""
    session = create_robust_session()

    try:
        log_message('INFO', "Fetching PaperMC versions...")

        # Get project info with retry
        for attempt in range(MAX_RETRIES):
            response = safe_request(session, 'GET', "https://api.papermc.io/v2/projects/paper")
            if response:
                break
            if attempt < MAX_RETRIES - 1:
                log_message('WARNING', f"Retrying in {attempt + 1} seconds...")
                time.sleep(attempt + 1)
        else:
            raise Exception("Failed to fetch versions after all retries")

        data = response.json()
        all_versions = data.get("versions", [])

        if not all_versions:
            raise Exception("No versions found in API response")

        # Filter versions based on snapshot preference
        if include_snapshots:
            versions = all_versions
        else:
            versions = [v for v in all_versions if not is_snapshot_version(v)]

        # Get builds for recent versions (limit to 25 for performance)
        version_info = {}
        for version in versions[-25:]:  # Get more versions but limit API calls
            try:
                builds_response = safe_request(
                    session, 
                    'GET',
                    f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds"
                )

                if builds_response:
                    builds_data = builds_response.json()
                    builds = builds_data.get("builds", [])
                    if builds:
                        latest_build = builds[-1]
                        version_info[version] = {
                            'builds': [b["build"] for b in builds],
                            'latest_build': latest_build["build"],
                            'download_name': latest_build["downloads"]["application"]["name"],
                            'sha256': latest_build["downloads"]["application"].get("sha256"),
                            'is_snapshot': is_snapshot_version(version)
                        }
                else:
                    log_message('DEBUG', f"Skipping builds for {version}")

            except Exception as e:
                log_message('DEBUG', f"Failed to get builds for {version}: {e}")
                continue

        if not version_info:
            raise Exception("No version information could be retrieved")

        log_message('SUCCESS', f"Retrieved {len(version_info)} PaperMC versions")
        return version_info

    except Exception as e:
        log_message('ERROR', f"Failed to fetch Paper versions: {e}")
        return {}
    finally:
        session.close()

def get_vanilla_versions(include_snapshots=False):
    """Get available Vanilla Minecraft versions with proper ordering - FIXED VERSION."""
    session = create_robust_session()

    try:
        log_message('INFO', "Fetching Vanilla Minecraft versions...")

        # Get version manifest with retry
        for attempt in range(MAX_RETRIES):
            response = safe_request(session, 'GET', "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
            if response:
                break
            if attempt < MAX_RETRIES - 1:
                log_message('WARNING', f"Retrying in {attempt + 1} seconds...")
                time.sleep(attempt + 1)
        else:
            raise Exception("Failed to fetch version manifest after all retries")

        data = response.json()
        all_versions = data.get("versions", [])

        if not all_versions:
            raise Exception("No versions found in manifest")

        # Process versions and maintain original API order (newest first)
        version_info = {}

        for version_data in all_versions:
            version = version_data["id"]
            version_type = version_data["type"]

            # Determine if it's a snapshot
            if version_type == "release":
                is_snap = False
            elif version_type in ["snapshot", "old_alpha", "old_beta"]:
                is_snap = True
            else:
                is_snap = is_snapshot_version(version)

            # Include based on snapshot preference
            if include_snapshots or not is_snap:
                version_info[version] = {
                    'type': version_type,
                    'url': version_data["url"],
                    'release_time': version_data["releaseTime"],
                    'is_snapshot': is_snap,
                    'order': len(version_info)  # Preserve original order
                }

        # Convert to list maintaining API order (newest first)
        sorted_versions = sorted(version_info.items(), key=lambda x: x[1]['order'])
        final_version_info = {k: v for k, v in sorted_versions}

        log_message('SUCCESS', f"Retrieved {len(final_version_info)} Vanilla versions")
        return final_version_info

    except Exception as e:
        log_message('ERROR', f"Failed to fetch Vanilla versions: {e}")
        return {}
    finally:
        session.close()

def get_purpur_versions(include_snapshots=False):
    """Get available Purpur versions with enhanced error handling."""
    session = create_robust_session()

    try:
        log_message('INFO', "Fetching Purpur versions...")

        # Get versions with retry
        for attempt in range(MAX_RETRIES):
            response = safe_request(session, 'GET', "https://api.purpurmc.org/v2/purpur")
            if response:
                break
            if attempt < MAX_RETRIES - 1:
                log_message('WARNING', f"Retrying in {attempt + 1} seconds...")
                time.sleep(attempt + 1)
        else:
            raise Exception("Failed to fetch versions after all retries")

        data = response.json()
        all_versions = data.get("versions", [])

        # Purpur typically doesn't have snapshots, but filter just in case
        if include_snapshots:
            versions = all_versions
        else:
            versions = [v for v in all_versions if not is_snapshot_version(v)]

        version_info = {}
        for version in versions[-25:]:  # Last 25 versions
            try:
                builds_response = safe_request(
                    session,
                    'GET', 
                    f"https://api.purpurmc.org/v2/purpur/{version}"
                )

                if builds_response:
                    builds_data = builds_response.json()
                    builds = builds_data.get("builds", {}).get("all", [])
                    if builds:
                        latest_build = builds[-1]
                        version_info[version] = {
                            'builds': builds,
                            'latest_build': latest_build,
                            'download_url': f"https://api.purpurmc.org/v2/purpur/{version}/{latest_build}/download",
                            'is_snapshot': is_snapshot_version(version)
                        }
            except Exception as e:
                log_message('DEBUG', f"Failed to get Purpur builds for {version}: {e}")
                continue

        log_message('SUCCESS', f"Retrieved {len(version_info)} Purpur versions")
        return version_info

    except Exception as e:
        log_message('ERROR', f"Failed to fetch Purpur versions: {e}")
        return {}
    finally:
        session.close()

def get_folia_versions(include_snapshots=False):
    """Get available Folia versions with enhanced error handling."""
    session = create_robust_session()

    try:
        log_message('INFO', "Fetching Folia versions...")

        # Get versions with retry
        for attempt in range(MAX_RETRIES):
            response = safe_request(session, 'GET', "https://api.papermc.io/v2/projects/folia")
            if response:
                break
            if attempt < MAX_RETRIES - 1:
                log_message('WARNING', f"Retrying in {attempt + 1} seconds...")
                time.sleep(attempt + 1)
        else:
            raise Exception("Failed to fetch versions after all retries")

        data = response.json()
        all_versions = data.get("versions", [])

        # Filter versions based on snapshot preference
        if include_snapshots:
            versions = all_versions
        else:
            versions = [v for v in all_versions if not is_snapshot_version(v)]

        version_info = {}
        for version in versions[-25:]:
            try:
                builds_response = safe_request(
                    session,
                    'GET',
                    f"https://api.papermc.io/v2/projects/folia/versions/{version}/builds"
                )

                if builds_response:
                    builds_data = builds_response.json()
                    builds = builds_data.get("builds", [])
                    if builds:
                        latest_build = builds[-1]
                        version_info[version] = {
                            'builds': [b["build"] for b in builds],
                            'latest_build': latest_build["build"],
                            'download_name': latest_build["downloads"]["application"]["name"],
                            'sha256': latest_build["downloads"]["application"].get("sha256"),
                            'is_snapshot': is_snapshot_version(version)
                        }
            except Exception as e:
                log_message('DEBUG', f"Failed to get Folia builds for {version}: {e}")
                continue

        log_message('SUCCESS', f"Retrieved {len(version_info)} Folia versions")
        return version_info

    except Exception as e:
        log_message('ERROR', f"Failed to fetch Folia versions: {e}")
        return {}
    finally:
        session.close()

def get_pocketmine_versions(include_snapshots=False):
    """Get available PocketMine-MP versions with enhanced error handling."""
    session = create_robust_session()

    try:
        log_message('INFO', "Fetching PocketMine-MP versions...")

        # Get releases with retry
        for attempt in range(MAX_RETRIES):
            response = safe_request(session, 'GET', "https://api.github.com/repos/pmmp/PocketMine-MP/releases")
            if response:
                break
            if attempt < MAX_RETRIES - 1:
                log_message('WARNING', f"Retrying in {attempt + 1} seconds...")
                time.sleep(attempt + 1)
        else:
            raise Exception("Failed to fetch releases after all retries")

        releases = response.json()

        version_info = {}
        for release in releases[:25]:  # Last 25 releases
            version = release["tag_name"]
            is_prerelease = release["prerelease"]

            # Include based on snapshot preference
            if include_snapshots or not is_prerelease:
                if not release["draft"]:
                    assets = release.get("assets", [])

                    # Find the PHAR file
                    phar_asset = None
                    for asset in assets:
                        if asset["name"].endswith(".phar"):
                            phar_asset = asset
                            break

                    if phar_asset:
                        version_info[version] = {
                            'download_url': phar_asset["browser_download_url"],
                            'filename': phar_asset["name"],
                            'size': phar_asset["size"],
                            'published_at': release["published_at"],
                            'is_snapshot': is_prerelease
                        }

        log_message('SUCCESS', f"Retrieved {len(version_info)} PocketMine versions")
        return version_info

    except Exception as e:
        log_message('ERROR', f"Failed to fetch PocketMine versions: {e}")
        return {}
    finally:
        session.close()

def paginate_versions(versions, current_page=1, per_page=VERSIONS_PER_PAGE):
    """Paginate version list and return page info."""
    total_versions = len(versions)
    total_pages = math.ceil(total_versions / per_page) if total_versions > 0 else 1

    # Ensure current_page is within bounds
    current_page = max(1, min(current_page, total_pages))

    # Calculate start and end indices
    start_idx = (current_page - 1) * per_page
    end_idx = min(start_idx + per_page, total_versions)

    # Get versions for current page
    page_versions = versions[start_idx:end_idx]

    return {
        'versions': page_versions,
        'current_page': current_page,
        'total_pages': total_pages,
        'total_versions': total_versions,
        'start_idx': start_idx,
        'end_idx': end_idx,
        'has_prev': current_page > 1,
        'has_next': current_page < total_pages
    }

def display_version_page(flavor, page_info, version_info, include_snapshots):
    """Display a paginated version selection page."""
    print_header()

    # Header with snapshot toggle info
    snapshot_status = f"{C.GREEN}ON{C.RESET}" if include_snapshots else f"{C.RED}OFF{C.RESET}"
    print(f"{C.BOLD}Version Selection - {SERVER_FLAVORS[flavor]['name']}{C.RESET}")
    print(f"{C.DIM}Snapshots/Pre-releases: {snapshot_status} | Page {page_info['current_page']}/{page_info['total_pages']}{C.RESET}\n")

    if not page_info['versions']:
        print(f"{C.YELLOW}No versions found{C.RESET}")
        return

    print(f"{C.BOLD}Available Versions:{C.RESET}")

    # Display versions for current page
    for i, version in enumerate(page_info['versions'], 1):
        info = version_info[version]
        global_idx = page_info['start_idx'] + i

        # Add snapshot indicator
        snapshot_indicator = f"{C.YELLOW}📷{C.RESET}" if info.get('is_snapshot', False) else "  "

        if flavor in ['paper', 'folia']:
            latest_build = info.get('latest_build', 'Unknown')
            print(f"{snapshot_indicator}{C.BOLD}{i:2}.{C.RESET} {version} (Build {latest_build})")
        elif flavor == 'purpur':
            latest_build = info.get('latest_build', 'Unknown')
            print(f"{snapshot_indicator}{C.BOLD}{i:2}.{C.RESET} {version} (Build {latest_build})")
        elif flavor == 'vanilla':
            release_time = info.get('release_time', '').split('T')[0]
            version_type = info.get('type', 'release')
            type_indicator = f"({version_type})" if version_type != 'release' else ""
            print(f"{snapshot_indicator}{C.BOLD}{i:2}.{C.RESET} {version} {type_indicator} ({release_time})")
        elif flavor == 'pocketmine':
            published = info.get('published_at', '').split('T')[0]
            pre_indicator = "(pre-release)" if info.get('is_snapshot', False) else ""
            print(f"{snapshot_indicator}{C.BOLD}{i:2}.{C.RESET} {version} {pre_indicator} ({published})")

    # Navigation help
    print(f"\n{C.DIM}Navigation:{C.RESET}")
    nav_options = []

    if page_info['has_prev']:
        nav_options.append("'p' or 'prev' - Previous page")
    if page_info['has_next']:
        nav_options.append("'n' or 'next' - Next page")

    nav_options.extend([
        "'s' or 'snap' - Toggle snapshots",
        "'q' or 'quit' - Back to main menu",
        "Number - Select version",
        "'latest' - Select latest version"
    ])

    for option in nav_options:
        print(f"  {option}")

def select_server_flavor():
    """Interactive server flavor selection menu."""
    print_header()
    print(f"{C.BOLD}Server Flavor Selection{C.RESET}\n")

    print(f"{C.BOLD}Available Server Types:{C.RESET}")
    for i, (key, flavor) in enumerate(SERVER_FLAVORS.items(), 1):
        status = f"{C.GREEN}✓{C.RESET}"
        snapshot_support = f"{C.CYAN}📷{C.RESET}" if flavor['supports_snapshots'] else f"{C.DIM}⚪{C.RESET}"
        print(f"  {C.BOLD}{i}.{C.RESET} {status} {flavor['name']} {snapshot_support}")
        print(f"      {C.DIM}{flavor['description']}{C.RESET}")
        if key == "pocketmine":
            print(f"      {C.DIM}Port: {flavor['default_port']} (Bedrock Edition){C.RESET}")
        else:
            print(f"      {C.DIM}Port: {flavor['default_port']} (Java Edition){C.RESET}")
        print()

    print(f"{C.DIM}Legend: ✓ Available | 📷 Supports Snapshots/Pre-releases{C.RESET}")

    while True:
        try:
            choice = input(f"\n{C.BOLD}Select server flavor (1-{len(SERVER_FLAVORS)}): {C.RESET}").strip()

            if not choice:
                continue

            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(SERVER_FLAVORS):
                selected_flavor = list(SERVER_FLAVORS.keys())[choice_idx]
                log_message('SUCCESS', f"Selected: {SERVER_FLAVORS[selected_flavor]['name']}")
                return selected_flavor
            else:
                print(f"{C.RED}Please enter a number between 1 and {len(SERVER_FLAVORS)}{C.RESET}")
        except ValueError:
            print(f"{C.RED}Please enter a valid number{C.RESET}")

def select_server_version(flavor):
    """Interactive version selection with pagination and snapshot toggle."""
    # Get version getters
    version_getters = {
        'paper': get_paper_versions,
        'purpur': get_purpur_versions,
        'folia': get_folia_versions,
        'vanilla': get_vanilla_versions,
        'pocketmine': get_pocketmine_versions
    }

    if flavor not in version_getters:
        log_message('ERROR', f"Version selection not implemented for {flavor}")
        return None, None

    # Initialize state
    include_snapshots = False
    current_page = 1
    version_info = None

    while True:
        # Fetch versions with current snapshot setting
        log_message('INFO', f"Loading available versions for {SERVER_FLAVORS[flavor]['name']}...")
        version_info = version_getters[flavor](include_snapshots)

        if not version_info:
            log_message('ERROR', "No versions available")
            input("Press Enter to continue...")
            return None, None

        # Convert to list and keep original order for all flavors except vanilla
        versions = list(version_info.keys())

        # For most flavors, reverse to get newest first
        # Vanilla is already in newest-first order from the API
        if flavor != 'vanilla':
            versions.reverse()

        # Paginate versions
        page_info = paginate_versions(versions, current_page)

        # Display current page
        display_version_page(flavor, page_info, version_info, include_snapshots)

        # Get user input
        choice = input(f"\n{C.BOLD}Select option: {C.RESET}").strip().lower()

        if not choice:
            continue

        # Handle navigation commands
        if choice in ['q', 'quit']:
            return None, None
        elif choice in ['s', 'snap']:
            if SERVER_FLAVORS[flavor]['supports_snapshots']:
                include_snapshots = not include_snapshots
                current_page = 1  # Reset to first page
                continue
            else:
                print(f"{C.YELLOW}{SERVER_FLAVORS[flavor]['name']} doesn't support snapshots{C.RESET}")
                time.sleep(2)
                continue
        elif choice in ['p', 'prev'] and page_info['has_prev']:
            current_page -= 1
            continue
        elif choice in ['n', 'next'] and page_info['has_next']:
            current_page += 1
            continue
        elif choice == 'latest':
            if versions:
                selected_version = versions[0]
                selected_info = version_info[selected_version]
                log_message('SUCCESS', f"Selected: {selected_version} (latest)")
                return selected_version, selected_info

        # Handle version selection by number
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(page_info['versions']):
                selected_version = page_info['versions'][choice_num - 1]
                selected_info = version_info[selected_version]
                log_message('SUCCESS', f"Selected: {selected_version}")
                return selected_version, selected_info
            else:
                print(f"{C.RED}Please enter a number between 1 and {len(page_info['versions'])}{C.RESET}")
                time.sleep(2)
        except ValueError:
            print(f"{C.RED}Invalid input. Use numbers, 'next', 'prev', 'snap', 'latest', or 'quit'{C.RESET}")
            time.sleep(2)

# Continue with rest of the functions...
def verify_file_integrity(filepath, expected_sha256):
    """Verify file integrity using SHA256 hash."""
    if not expected_sha256:
        return True

    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        calculated = sha256_hash.hexdigest()
        return calculated.lower() == expected_sha256.lower()
    except:
        return False

def verify_file_integrity_sha1(filepath, expected_sha1):
    """Verify file integrity using SHA1 hash."""
    if not expected_sha1:
        return True

    try:
        sha1_hash = hashlib.sha1()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha1_hash.update(chunk)

        calculated = sha1_hash.hexdigest()
        return calculated.lower() == expected_sha1.lower()
    except:
        return False

def load_config():
    """Load configuration with flavor support."""
    default_config = {
        "server_flavor": "paper",
        "server_version": None,
        "ram_mb": 2048,
        "ngrok_authtoken": None,
        "auto_backup": True,
        "backup_interval_hours": 24,
        "max_backups": 5,
        "include_snapshots": False,
        "server_settings": {
            "motd": "Enhanced MSM Server",
            "difficulty": "normal",
            "max-players": 20,
            "view-distance": 10,
            "port": 25565
        }
    }

    if not os.path.exists(CONFIG_FILE):
        return default_config

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)

        # Merge with defaults for new keys
        for key, value in default_config.items():
            if key not in config:
                config[key] = value

        return config
    except Exception as e:
        log_message('WARNING', f"Config file corrupted, using defaults: {e}")
        return default_config

def save_config(config):
    """Save configuration with backup."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        log_message('SUCCESS', "Configuration saved")
    except Exception as e:
        log_message('ERROR', f"Failed to save config: {e}")

def download_server_jar(flavor, version, version_info):
    """Download the selected server jar file with enhanced session handling."""
    server_jar_path = os.path.join(SERVER_DIR, SERVER_JAR_NAME)
    session = create_robust_session()

    try:
        log_message('INFO', f"Downloading {SERVER_FLAVORS[flavor]['name']} {version}...")

        if flavor == 'paper':
            build = version_info['latest_build']
            jar_name = version_info['download_name']
            download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{build}/downloads/{jar_name}"
            expected_hash = version_info.get('sha256')

        elif flavor == 'purpur':
            build = version_info['latest_build']
            download_url = version_info['download_url']
            expected_hash = None

        elif flavor == 'folia':
            build = version_info['latest_build']
            jar_name = version_info['download_name']
            download_url = f"https://api.papermc.io/v2/projects/folia/versions/{version}/builds/{build}/downloads/{jar_name}"
            expected_hash = version_info.get('sha256')

        elif flavor == 'vanilla':
            # Get version manifest
            response = safe_request(session, 'GET', version_info['url'])
            if not response:
                raise Exception("Failed to get version manifest")

            manifest = response.json()
            download_url = manifest['downloads']['server']['url']
            expected_hash = manifest['downloads']['server']['sha1']

        elif flavor == 'pocketmine':
            download_url = version_info['download_url']
            server_jar_path = os.path.join(SERVER_DIR, version_info['filename'])
            expected_hash = None

        # Download with progress
        download_cmd = f"wget --progress=bar --show-progress --timeout=60 --tries=3 -O '{server_jar_path}' '{download_url}'"
        if not run_command(download_cmd, timeout=900):  # 15 minute timeout for large files
            log_message('ERROR', "Download failed")
            return False

        # Validate file
        is_valid, message = validate_file(server_jar_path)
        if not is_valid:
            log_message('ERROR', f"Downloaded file validation failed: {message}")
            os.remove(server_jar_path)
            return False

        # Verify hash if available
        if expected_hash and flavor != 'vanilla':  # Paper uses SHA256
            if verify_file_integrity(server_jar_path, expected_hash):
                log_message('SUCCESS', "File integrity verified")
            else:
                log_message('WARNING', "File integrity check failed")
        elif expected_hash and flavor == 'vanilla':  # Vanilla uses SHA1
            if verify_file_integrity_sha1(server_jar_path, expected_hash):
                log_message('SUCCESS', "File integrity verified")
            else:
                log_message('WARNING', "File integrity check failed")

        log_message('SUCCESS', f"Downloaded {SERVER_FLAVORS[flavor]['name']} {version}")
        return True

    except Exception as e:
        log_message('ERROR', f"Download failed: {e}")
        return False
    finally:
        session.close()

def install_server():
    """Enhanced server installation with flavor selection and pagination."""
    log_message('INFO', "Starting server installation process...")

    # Create directories
    os.makedirs(SERVER_DIR, exist_ok=True)

    # Select server flavor
    selected_flavor = select_server_flavor()
    if not selected_flavor:
        return

    # Select version with pagination
    selected_version, version_info = select_server_version(selected_flavor)
    if not selected_version or not version_info:
        return

    # Confirmation
    print_header()
    print(f"{C.BOLD}Installation Summary:{C.RESET}")
    print(f"Server: {C.CYAN}{SERVER_FLAVORS[selected_flavor]['name']}{C.RESET}")
    print(f"Version: {C.CYAN}{selected_version}{C.RESET}")

    if version_info.get('is_snapshot', False):
        print(f"Type: {C.YELLOW}Snapshot/Pre-release{C.RESET}")

    if selected_flavor in ['paper', 'purpur', 'folia']:
        build = version_info.get('latest_build', 'Unknown')
        print(f"Build: {C.CYAN}{build}{C.RESET}")

    print(f"Port: {C.CYAN}{SERVER_FLAVORS[selected_flavor]['default_port']}{C.RESET}")

    if input(f"\n{C.BOLD}Proceed with installation? (Y/n): {C.RESET}").lower() != 'n':
        # Download server
        if download_server_jar(selected_flavor, selected_version, version_info):
            # Accept EULA for Java servers
            if SERVER_FLAVORS[selected_flavor]['type'] == 'java':
                eula_path = os.path.join(SERVER_DIR, "eula.txt")
                try:
                    with open(eula_path, 'w') as f:
                        f.write("# EULA automatically accepted by Enhanced MSM\n")
                        f.write("# https://account.mojang.com/documents/minecraft_eula\n")
                        f.write("eula=true\n")
                    log_message('SUCCESS', "EULA accepted automatically")
                except Exception as e:
                    log_message('WARNING', f"Could not create EULA file: {e}")

            # Update config
            config = load_config()
            config['server_flavor'] = selected_flavor
            config['server_version'] = selected_version
            config['server_settings']['port'] = SERVER_FLAVORS[selected_flavor]['default_port']
            save_config(config)

            log_message('SUCCESS', "Server installation completed!")
            print(f"\n{C.GREEN}✅ Installation successful!{C.RESET}")
            print(f"Server: {SERVER_FLAVORS[selected_flavor]['name']} {selected_version}")

            if version_info.get('is_snapshot', False):
                print(f"{C.YELLOW}⚠️  Note: This is a snapshot/pre-release version{C.RESET}")
        else:
            log_message('ERROR', "Installation failed")

    input("\nPress Enter to continue...")

def is_server_running():
    """Enhanced server status check."""
    result = run_command(f"screen -ls | grep {SCREEN_SESSION_NAME}", capture_output=True)
    if not result or result.returncode != 0:
        return False

    # Check for Java or PHP process based on server type
    config = load_config()
    server_flavor = config.get('server_flavor', 'paper')

    if SERVER_FLAVORS[server_flavor]['type'] == 'java':
        process_check = run_command("pgrep -f 'java.*server.jar'", capture_output=True)
    else:  # PHP for PocketMine
        process_check = run_command("pgrep -f 'php.*phar'", capture_output=True)

    return process_check and process_check.returncode == 0

def start_server():
    """Enhanced server startup with multi-flavor support."""
    print_header()

    if is_server_running():
        log_message('WARNING', "Server is already running!")
        input("Press Enter to continue...")
        return

    config = load_config()
    server_flavor = config.get('server_flavor', 'paper')

    # Check if server is installed
    if server_flavor == 'pocketmine':
        server_files = [f for f in os.listdir(SERVER_DIR) if f.endswith('.phar')]
        if not server_files:
            log_message('ERROR', "PocketMine server not found! Please install first.")
            input("Press Enter to continue...")
            return
        server_executable = server_files[0]
    else:
        server_jar_path = os.path.join(SERVER_DIR, SERVER_JAR_NAME)
        if not os.path.exists(server_jar_path):
            log_message('ERROR', "server.jar not found! Please install first.")
            input("Press Enter to continue...")
            return
        server_executable = SERVER_JAR_NAME

    ram_mb = config.get('ram_mb', 2048)
    system_info = get_system_info()

    # RAM check
    if ram_mb > system_info['max_safe_ram_mb']:
        log_message('WARNING', f"RAM allocation ({ram_mb}MB) exceeds safe limit")
        if input("Continue anyway? (y/N): ").lower() != 'y':
            return

    log_message('INFO', f"Starting {SERVER_FLAVORS[server_flavor]['name']} server...")

    # Build startup command based on server type
    if SERVER_FLAVORS[server_flavor]['type'] == 'java':
        # Java servers
        java_args = [
            f"-Xmx{ram_mb}M",
            f"-Xms{ram_mb}M",
            "-XX:+UseG1GC",
            "-XX:+ParallelRefProcEnabled",
            "-XX:MaxGCPauseMillis=200",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+DisableExplicitGC",
            "-XX:+AlwaysPreTouch"
        ]
        startup_command = f"java {' '.join(java_args)} -jar {server_executable} nogui"
    else:
        # PHP servers (PocketMine)
        startup_command = f"php -dphar.readonly=0 {server_executable}"

    # Start server
    screen_cmd = f"cd '{SERVER_DIR}' && screen -dmS {SCREEN_SESSION_NAME} {startup_command}"
    if not run_command(screen_cmd):
        log_message('ERROR', "Failed to start server")
        input("Press Enter to continue...")
        return

    log_message('SUCCESS', "Server started successfully!")

    # Wait and verify
    time.sleep(5)
    if is_server_running():
        print(f"{C.GREEN}✅ Server is running!{C.RESET}")
        print(f"Flavor: {SERVER_FLAVORS[server_flavor]['name']}")
        print(f"Version: {config.get('server_version', 'Unknown')}")
        print(f"Port: {config['server_settings']['port']}")
        print(f"Console: screen -r {SCREEN_SESSION_NAME}")
    else:
        log_message('ERROR', "Server failed to start properly")

    input("\nPress Enter to continue...")

def main():
    """Enhanced main function with better error handling."""
    if not check_dependencies():
        sys.exit(1)

    while True:
        try:
            print_header()

            config = load_config()
            server_flavor = config.get('server_flavor', 'paper')
            server_version = config.get('server_version', 'Not installed')

            # Status display
            server_status = f"{C.GREEN}ONLINE{C.RESET}" if is_server_running() else f"{C.RED}OFFLINE{C.RESET}"

            # Show snapshot preference if server supports it
            if SERVER_FLAVORS[server_flavor]['supports_snapshots']:
                snap_pref = config.get('include_snapshots', False)
                snap_status = f"{C.CYAN}📷{C.RESET}" if snap_pref else ""
            else:
                snap_status = ""

            print(f"Current: {C.CYAN}{SERVER_FLAVORS[server_flavor]['name']}{C.RESET} {server_version} {snap_status}")
            print(f"Status: Server [{server_status}]\n")

            # Menu
            print(f"{C.BOLD}Main Menu:{C.RESET}")
            print(f"  {C.BOLD}1.{C.RESET} Start Server")
            print(f"  {C.BOLD}2.{C.RESET} Stop Server")
            print(f"  {C.BOLD}3.{C.RESET} Install/Change Server")
            print(f"  {C.BOLD}4.{C.RESET} Configure Server")
            print(f"  {C.BOLD}5.{C.RESET} Server Console")
            print(f"  {C.BOLD}6.{C.RESET} Exit")

            choice = input(f"\n{C.BOLD}Choose option: {C.RESET}").strip()

            if choice == '1':
                start_server()
            elif choice == '2':
                # Basic stop functionality
                if is_server_running():
                    log_message('INFO', "Stopping server...")
                    run_command(f'screen -S {SCREEN_SESSION_NAME} -p 0 -X stuff "stop\n"')
                    time.sleep(3)
                    log_message('SUCCESS', "Server stopped")
                else:
                    log_message('INFO', "Server is not running")
                input("Press Enter to continue...")
            elif choice == '3':
                install_server()
            elif choice == '4':
                print(f"{C.YELLOW}Configuration wizard not yet implemented{C.RESET}")
                input("Press Enter to continue...")
            elif choice == '5':
                if is_server_running():
                    print(f"{C.CYAN}Connecting to server console...{C.RESET}")
                    print(f"{C.DIM}Press Ctrl+A then D to detach from console{C.RESET}")
                    time.sleep(2)
                    run_command(f"screen -r {SCREEN_SESSION_NAME}")
                else:
                    log_message('WARNING', "Server is not running")
                    input("Press Enter to continue...")
            elif choice == '6':
                print(f"\n{C.CYAN}Goodbye! 👋{C.RESET}")
                sys.exit(0)
            else:
                log_message('ERROR', "Invalid choice")
                time.sleep(1)

        except KeyboardInterrupt:
            print(f"\n\n{C.YELLOW}Interrupted by user{C.RESET}")
            sys.exit(0)

if __name__ == "__main__":
    main()
