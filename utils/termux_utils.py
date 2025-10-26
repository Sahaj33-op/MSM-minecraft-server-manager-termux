#!/usr/bin/env python3
"""
Termux-specific utilities and optimizations
"""
import os
import subprocess
import platform
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from core.constants import TermuxConfig, ErrorMessages

def is_termux_environment() -> bool:
    """Check if running in Termux environment.
    
    Returns:
        True if running in Termux, False otherwise
    """
    try:
        # Check for Termux-specific environment variables
        if os.environ.get('TERMUX_VERSION'):
            return True
        
        # Check for Termux-specific paths
        if os.path.exists('/data/data/com.termux/files/usr/bin'):
            return True
            
        # Check if we're on Android
        if platform.system() == 'Linux':
            try:
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    if 'android' in version_info:
                        return True
            except (FileNotFoundError, PermissionError):
                pass
                
        return False
    except Exception:
        return False

def get_termux_home() -> str:
    """Get Termux home directory.
    
    Returns:
        Termux home directory path
    """
    if is_termux_environment():
        return TermuxConfig.TERMUX_HOME
    return os.path.expanduser('~')

def get_termux_prefix() -> str:
    """Get Termux prefix directory.
    
    Returns:
        Termux prefix directory path
    """
    if is_termux_environment():
        return TermuxConfig.TERMUX_PREFIX
    return '/usr'

def check_termux_permissions() -> Dict[str, bool]:
    """Check Termux-specific permissions and capabilities.
    
    Returns:
        Dictionary with permission status
    """
    permissions = {
        'storage': False,
        'camera': False,
        'microphone': False,
        'location': False,
        'phone': False,
        'sms': False,
        'contacts': False
    }
    
    if not is_termux_environment():
        return permissions
    
    try:
        # Check storage permission
        result = subprocess.run(
            ['termux-setup-storage', '--help'],
            capture_output=True,
            text=True,
            timeout=5
        )
        permissions['storage'] = result.returncode == 0
    except Exception:
        pass
    
    # Check other permissions using termux-info if available
    try:
        result = subprocess.run(
            ['termux-info'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info = result.stdout.lower()
            permissions['camera'] = 'camera' in info
            permissions['microphone'] = 'microphone' in info
            permissions['location'] = 'location' in info
            permissions['phone'] = 'phone' in info
            permissions['sms'] = 'sms' in info
            permissions['contacts'] = 'contacts' in info
    except Exception:
        pass
    
    return permissions

def optimize_for_termux() -> Dict[str, any]:
    """Apply Termux-specific optimizations.
    
    Returns:
        Dictionary with optimization results
    """
    optimizations = {
        'memory_optimized': False,
        'battery_optimized': False,
        'network_optimized': False,
        'storage_optimized': False
    }
    
    if not is_termux_environment():
        return optimizations
    
    try:
        # Memory optimization
        # Set lower memory limits for better performance on mobile
        os.environ['PYTHONHASHSEED'] = '0'
        os.environ['PYTHONUNBUFFERED'] = '1'
        optimizations['memory_optimized'] = True
        
        # Battery optimization
        # Reduce CPU usage by limiting background processes
        os.environ['OMP_NUM_THREADS'] = '2'  # Limit OpenMP threads
        optimizations['battery_optimized'] = True
        
        # Network optimization
        # Use shorter timeouts for mobile networks
        os.environ['REQUESTS_TIMEOUT'] = '10'
        optimizations['network_optimized'] = True
        
        # Storage optimization
        # Use Termux's internal storage for better performance
        if os.path.exists(TermuxConfig.TERMUX_HOME):
            os.environ['HOME'] = TermuxConfig.TERMUX_HOME
            optimizations['storage_optimized'] = True
            
    except Exception:
        pass
    
    return optimizations

def get_termux_packages() -> List[str]:
    """Get list of installed Termux packages.
    
    Returns:
        List of installed package names
    """
    if not is_termux_environment():
        return []
    
    try:
        result = subprocess.run(
            ['pkg', 'list-installed'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            packages = []
            for line in result.stdout.split('\n'):
                if line.strip():
                    package_name = line.split()[0]
                    packages.append(package_name)
            return packages
    except Exception:
        pass
    
    return []

def check_required_packages() -> Dict[str, bool]:
    """Check if required packages are installed.
    
    Returns:
        Dictionary with package installation status
    """
    required_packages = {
        'python': False,
        'java': False,
        'screen': False,
        'curl': False,
        'wget': False,
        'git': False,
        'unzip': False,
        'zip': False
    }
    
    installed_packages = get_termux_packages()
    
    for package in required_packages:
        if package in installed_packages:
            required_packages[package] = True
    
    return required_packages

def install_termux_package(package_name: str) -> Tuple[bool, str]:
    """Install a Termux package.
    
    Args:
        package_name: Name of the package to install
        
    Returns:
        Tuple of (success, message)
    """
    if not is_termux_environment():
        return False, "Not running in Termux environment"
    
    try:
        result = subprocess.run(
            ['pkg', 'install', '-y', package_name],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            return True, f"Package '{package_name}' installed successfully"
        else:
            return False, f"Failed to install package '{package_name}': {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, f"Package installation timed out: {package_name}"
    except Exception as e:
        return False, f"Error installing package '{package_name}': {str(e)}"

def get_termux_storage_path() -> Optional[str]:
    """Get Termux storage path for external files.
    
    Returns:
        Storage path if available, None otherwise
    """
    if not is_termux_environment():
        return None
    
    storage_paths = [
        '/sdcard',
        '/storage/emulated/0',
        '/storage/self/primary'
    ]
    
    for path in storage_paths:
        if os.path.exists(path) and os.access(path, os.W_OK):
            return path
    
    return None

def setup_termux_storage() -> bool:
    """Setup Termux storage access.
    
    Returns:
        True if setup successful, False otherwise
    """
    if not is_termux_environment():
        return False
    
    try:
        result = subprocess.run(
            ['termux-setup-storage'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False

def get_android_info() -> Dict[str, str]:
    """Get Android system information.
    
    Returns:
        Dictionary with Android system info
    """
    info = {
        'version': 'Unknown',
        'api_level': 'Unknown',
        'architecture': 'Unknown',
        'manufacturer': 'Unknown',
        'model': 'Unknown'
    }
    
    if not is_termux_environment():
        return info
    
    try:
        # Get Android version
        result = subprocess.run(
            ['getprop', 'ro.build.version.release'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['version'] = result.stdout.strip()
        
        # Get API level
        result = subprocess.run(
            ['getprop', 'ro.build.version.sdk'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['api_level'] = result.stdout.strip()
        
        # Get architecture
        result = subprocess.run(
            ['getprop', 'ro.product.cpu.abi'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['architecture'] = result.stdout.strip()
        
        # Get manufacturer
        result = subprocess.run(
            ['getprop', 'ro.product.manufacturer'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['manufacturer'] = result.stdout.strip()
        
        # Get model
        result = subprocess.run(
            ['getprop', 'ro.product.model'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            info['model'] = result.stdout.strip()
            
    except Exception:
        pass
    
    return info

def optimize_java_for_termux() -> Dict[str, any]:
    """Apply Java optimizations for Termux environment.
    
    Returns:
        Dictionary with optimization results
    """
    optimizations = {
        'heap_size': '512m',
        'gc_algorithm': 'G1GC',
        'gc_tuning': True,
        'memory_optimized': True
    }
    
    if not is_termux_environment():
        return optimizations
    
    # Termux-specific Java optimizations
    try:
        # Get available memory
        import psutil
        mem = psutil.virtual_memory()
        total_mb = mem.total // (1024 * 1024)
        
        # Calculate optimal heap size (use 50% of available memory, max 2GB)
        heap_size = min(total_mb // 2, 2048)
        optimizations['heap_size'] = f"{heap_size}m"
        
        # Use G1GC for better performance on mobile
        optimizations['gc_algorithm'] = 'G1GC'
        optimizations['gc_tuning'] = True
        
    except Exception:
        pass
    
    return optimizations

def get_termux_java_options() -> List[str]:
    """Get optimized Java options for Termux.
    
    Returns:
        List of Java JVM options
    """
    if not is_termux_environment():
        return []
    
    optimizations = optimize_java_for_termux()
    
    options = [
        f"-Xmx{optimizations['heap_size']}",
        f"-Xms{optimizations['heap_size']}",
        f"-XX:+Use{optimizations['gc_algorithm']}",
        "-XX:+UseStringDeduplication",
        "-XX:+OptimizeStringConcat",
        "-XX:+UseCompressedOops",
        "-XX:+UseCompressedClassPointers",
        "-XX:+TieredCompilation",
        "-XX:TieredStopAtLevel=1",  # Faster startup
        "-Djava.awt.headless=true",
        "-Dfile.encoding=UTF-8"
    ]
    
    return options
