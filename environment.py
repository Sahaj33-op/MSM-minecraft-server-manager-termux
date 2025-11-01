<<<<<<< HEAD
# ============================================================================
# environment.py - Handles Termux vs. Debian bootstrap (CLEANED)
# ============================================================================
"""
Environment detection, Debian installation, and proot management.
Removed UI class - imports from ui module instead.
"""

import os
import sys
import subprocess
import shutil
import time
from pathlib import Path

from ui import print_info, print_success, print_warning, print_error, clear_screen, print_header
from logger import log


def is_inside_proot() -> bool:
    """
    Detect if running inside proot using multiple robust checks.
    """
    # Check for proot-specific files/directories
    if Path("/.proot").exists():
        return True
    
    # Check environment variables
    if os.environ.get("PROOT_TMP_DIR"):
        return True
    
    # Check mount information
    try:
        with open("/proc/self/mountinfo", "r") as f:
            mountinfo = f.read().lower()
            if "proot" in mountinfo or "/data/data/com.termux" in mountinfo:
                return True
    except:
        pass
    
    # Check process version info
    try:
        with open("/proc/version", "r") as f:
            version = f.read().lower()
            if "proot" in version or "termux" in version:
                return True
    except:
        pass
    
    # Additional check for Termux environment
    if "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("HOME", ""):
        return True
    
    return False


class EnvironmentManager:
    """Manages environment detection and Debian installation."""
    
    @staticmethod
    def is_debian() -> bool:
        """Check if current proot environment is Debian."""
        if not is_inside_proot():
            return False
        
        try:
            with open("/etc/os-release", "r") as f:
                os_release = f.read().lower()
                if "debian" in os_release:
                    log("Confirmed Debian distribution")
                    return True
        except:
            pass
        
        log("Not Debian distribution")
        return False
    
    @staticmethod
    def is_proot_distro_installed() -> bool:
        """Check if proot-distro command is available."""
        result = shutil.which("proot-distro")
        if result:
            log(f"proot-distro found at: {result}")
            return True
        log("proot-distro not found")
        return False
    
    @staticmethod
    def is_debian_installed() -> bool:
        """
        Check if Debian is installed via proot-distro.
        Most reliable: try to read /etc/os-release inside debian proot.
        """
        if not EnvironmentManager.is_proot_distro_installed():
            return False
        
        try:
            result = subprocess.run(
                ["proot-distro", "login", "debian", "--", "cat", "/etc/os-release"],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if result.returncode == 0 and "debian" in result.stdout.lower():
                log("Debian confirmed installed (via os-release check)")
                return True
        except:
            pass
        
        log("Debian not found in installed distributions")
        return False
    
    @staticmethod
    def install_proot_distro():
        """Install proot-distro package via pkg."""
        if not shutil.which("pkg"):
            print_error("`pkg` command not found.")
            print_error("This script requires Termux to run.")
            print_info("If on non-Termux: pkg install proot-distro")
            log("pkg command not found", "ERROR")
            sys.exit(1)
        
        print_info("Installing proot-distro...")
        log("Starting proot-distro installation")
        
        try:
            print_info("Updating package lists...")
            subprocess.run(["pkg", "update"], check=True, timeout=120)
            
            print_info("Installing proot-distro package...")
            subprocess.run(["pkg", "install", "proot-distro", "-y"], check=True, timeout=300)
            
            print_success("proot-distro installed successfully")
            log("proot-distro installation completed")
            
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install proot-distro: {e}")
            log(f"proot-distro installation failed: {e}", "ERROR")
            sys.exit(1)
        except subprocess.TimeoutExpired:
            print_error("Installation timed out")
            log("proot-distro installation timed out", "ERROR")
            sys.exit(1)
    
    @staticmethod
    def install_debian():
        """Install Debian distribution via proot-distro."""
        print_info("Installing Debian distribution...")
        print_info("This may take several minutes and requires ~500MB download")
        log("Starting Debian installation")
        
        # Check disk space
        try:
            stat = shutil.disk_usage(Path.home())
            free_gb = stat.free / (1024**3)
            if free_gb < 2:
                print_warning(f"Low disk space: {free_gb:.1f}GB free. Recommended: 2GB+")
                confirm = input("Continue anyway? (y/N): ").strip().lower()
                if confirm != 'y':
                    print_error("Installation cancelled by user")
                    sys.exit(1)
        except:
            pass
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                print_info(f"Installation attempt {attempt}/{max_retries}...")
                
                subprocess.run(
                    ["proot-distro", "install", "debian"],
                    check=True,
                    timeout=1800
                )
                
                print_success("Debian installed successfully")
                log("Debian installation completed")
                
                # Install python3 and essentials
                print_info("Installing Python 3 and essential packages...")
                try:
                    subprocess.run(
                        ["proot-distro", "login", "debian", "--", "apt-get", "update"],
                        check=True,
                        timeout=300
                    )
                    subprocess.run(
                        ["proot-distro", "login", "debian", "--", "apt-get", "install", "-y", 
                         "python3", "python3-pip", "openjdk-17-jre-headless", "screen", 
                         "curl", "gnupg", "zip", "unzip", "wget"],
                        check=True,
                        timeout=600
                    )
                    print_success("Essential packages installed")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Package installation issues: {e}")
                    print_warning("You may need to install python3/java manually")
                
                return
                
            except subprocess.CalledProcessError as e:
                print_error(f"Debian installation failed (attempt {attempt}): {e}")
                log(f"Debian installation attempt {attempt} failed: {e}", "ERROR")
                
                if attempt < max_retries:
                    print_warning("Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print_error("All installation attempts failed")
                    sys.exit(1)
                    
            except subprocess.TimeoutExpired:
                print_error(f"Installation timed out (attempt {attempt})")
                log(f"Debian installation attempt {attempt} timed out", "ERROR")
                
                if attempt < max_retries:
                    print_warning("Retrying...")
                    time.sleep(5)
                else:
                    print_error("Installation timed out")
                    sys.exit(1)
    
    @staticmethod
    def copy_and_launch_into_debian():
        """
        Copy entire msm directory into Debian and relaunch.
        Uses binary-safe piping via tar.
        """
        print_info("Preparing to launch MSM inside Debian...")
        log("Copying MSM into Debian environment")
        
        try:
            # Get msm directory
            msm_dir = Path(__file__).parent.resolve()
            debian_msm_dir = "/root/msm"
            
            # Create tar archive
            import tarfile
            import tempfile
            
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
                tar_path = tmp.name
            
            print_info("Creating MSM archive...")
            with tarfile.open(tar_path, 'w') as tar:
                tar.add(msm_dir, arcname='msm')
            
            # Copy and extract inside Debian
            print_info("Copying into Debian...")
            with open(tar_path, 'rb') as f:
                tar_data = f.read()
            
            cmd = [
                "proot-distro", "login", "debian", "--shared-tmp", "--",
                "bash", "-lc",
                f"cd /root && cat > msm.tar && tar -xf msm.tar && rm msm.tar && chmod +x {debian_msm_dir}/main.py"
            ]
            
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = proc.communicate(input=tar_data, timeout=60)
            
            # Clean up temp file
            Path(tar_path).unlink()
            
            if proc.returncode != 0:
                print_error(f"Failed to copy: {stderr.decode(errors='ignore')}")
                sys.exit(1)
            
            print_success("MSM copied successfully")
            
            # Verify python3
            check_py = subprocess.run(
                ["proot-distro", "login", "debian", "--", "which", "python3"],
                capture_output=True,
                timeout=10
            )
            
            if check_py.returncode != 0:
                print_warning("Python 3 not found, installing...")
                subprocess.run(
                    ["proot-distro", "login", "debian", "--", "apt-get", "update"],
                    check=True,
                    timeout=120
                )
                subprocess.run(
                    ["proot-distro", "login", "debian", "--", "apt-get", "install", "-y", "python3"],
                    check=True,
                    timeout=300
                )
            
            print_info("Relaunching inside Debian...")
            log("Relaunching inside Debian")
            
            # Relaunch
            os.execvp("proot-distro", [
                "proot-distro", "login", "debian", "--shared-tmp", "--",
                "python3", f"{debian_msm_dir}/main.py"
            ])
            
        except Exception as e:
            print_error(f"Copy error: {e}")
            log(f"Copy error: {e}", "ERROR")
            sys.exit(1)
    
    @staticmethod
    def ensure_debian_environment():
        """Ensure Debian is available and running."""
        if EnvironmentManager.is_debian():
            print_success("Running inside Debian environment")
            log("Environment check: Inside Debian")
            return
        
        print_warning("Debian environment required but not detected")
        log("Debian environment not detected, starting setup")
        
        if not EnvironmentManager.is_proot_distro_installed():
            print_info("proot-distro not found, installing...")
            EnvironmentManager.install_proot_distro()
        
        if not EnvironmentManager.is_debian_installed():
            print_info("Debian not installed, installing now...")
            EnvironmentManager.install_debian()
        
        EnvironmentManager.copy_and_launch_into_debian()
    
    @staticmethod
    def install_debian_only():
        """Install Debian only and exit."""
        if not EnvironmentManager.is_proot_distro_installed():
            EnvironmentManager.install_proot_distro()
        if not EnvironmentManager.is_debian_installed():
            EnvironmentManager.install_debian()
        print_success("Debian installation completed")
    
    @staticmethod
    def environment_menu():
        """Environment manager and tests menu."""
        from config import get_servers_root
        from utils import detect_total_ram_mb, suggest_ram_allocation
        from ui import Colors
        
        clear_screen()
        print_header("1.1.0")
        print(f"\n{Colors.BOLD}Environment Manager{Colors.RESET}\n")
        
        print_info("Running environment tests...")
        print()
        
        if EnvironmentManager.is_debian():
            print_success("Debian proot detected")
        else:
            print_error("Not running in Debian proot")
        
        if shutil.which("java"):
            print_success("Java available")
            try:
                result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
                version_line = result.stderr.split('\n')[0]
                print_info(f"  {version_line}")
            except:
                pass
        else:
            print_error("Java not found")
            print_info("  Install: apt install openjdk-17-jre-headless")
        
        if shutil.which("screen"):
            print_success("screen available")
        else:
            print_warning("screen not found (optional)")
            print_info("  Install: apt install screen")
        
        try:
            servers_root = get_servers_root()
            check_path = servers_root if servers_root.exists() else servers_root.parent
            stat = shutil.disk_usage(check_path)
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            print_info(f"Disk: {free_gb:.1f}GB free / {total_gb:.1f}GB total")
        except:
            print_warning("Could not check disk space")
        
        total_ram = detect_total_ram_mb()
        suggested = suggest_ram_allocation()
        print_info(f"RAM: {total_ram}MB total, suggested: {suggested}MB")
        
        print()
        print_warning("Note: proot has 10-50% performance overhead")
        
        input("\nPress Enter to continue...")
=======
#!/usr/bin/env python3
"""
Environment detection with optional proot (Debian) support.
- Default: native Termux (no proot required)
- Optional: ensure Debian via proot-distro when playit.gg chosen
"""
import os, shutil, subprocess

class EnvironmentManager:
    @staticmethod
    def is_termux():
        return 'com.termux' in (os.environ.get('PREFIX','')) or os.path.exists('/data/data/com.termux')

    @staticmethod
    def has_proot_distro():
        return shutil.which('proot-distro') is not None

    @staticmethod
    def ensure_debian_if_needed(reason: str = ""):
        """Only require Debian when a feature needs it (e.g., playit.gg)."""
        if reason != 'playit':
            return True
        if EnvironmentManager.in_debian():
            return True
        if not EnvironmentManager.has_proot_distro():
            print("proot-distro not found. Install with: pkg install proot-distro")
            return False
        print("Launching Debian (proot-distro) for playit.gg...")
        # Caller should re-exec inside debian environment.
        return True

    @staticmethod
    def in_debian():
        # naive heuristic: presence of /etc/debian_version
        return os.path.exists('/etc/debian_version')
>>>>>>> unify-merge-for-release
