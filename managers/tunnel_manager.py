#!/usr/bin/env python3
"""
Tunneling Manager (unified):
- No proot required: ngrok, cloudflared, pinggy
- Optional proot required: playit.gg
"""
import shutil
import subprocess
import os
import json
import time
import psutil
import threading
import re
from pathlib import Path
from environment import EnvironmentManager

class TunnelManager:
    """Manages various tunneling services for exposing local servers to the internet."""
    
    def __init__(self, logger=None):
        """Initialize the TunnelManager.
        
        Args:
            logger: Logger instance for logging messages
        """
        self.logger = logger
        self.tunnel_processes = {}  # Track tunnel processes
        self.tunnel_info = {}       # Store tunnel information
        self.config_dir = Path(os.path.expanduser("~/.config/msm"))
        self.tunnel_state_file = self.config_dir / "tunnel_state.json"
        self._load_tunnel_state()
        self.url_extraction_threads = {}  # Threads for URL extraction

    def _log(self, level, msg):
        """Log a message using the logger or print to console.
        
        Args:
            level: Log level (INFO, ERROR, WARNING, etc.)
            msg: Message to log
        """
        if self.logger: 
            self.logger.log(level, msg)
        else: 
            print(f"[{level}] {msg}")

    def _save_tunnel_state(self):
        """Save tunnel state to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            state = {
                'processes': {name: {'pid': proc.pid if proc.poll() is None else None} 
                             for name, proc in self.tunnel_processes.items()},
                'info': self.tunnel_info
            }
            self.tunnel_state_file.write_text(json.dumps(state, indent=2))
        except Exception as e:
            self._log('DEBUG', f'Failed to save tunnel state: {e}')

    def _load_tunnel_state(self):
        """Load tunnel state from file."""
        try:
            if self.tunnel_state_file.exists():
                state = json.loads(self.tunnel_state_file.read_text())
                self.tunnel_info = state.get('info', {})
                # We can't restore processes directly, but we can restore info
        except Exception as e:
            self._log('DEBUG', f'Failed to load tunnel state: {e}')

    def _update_tunnel_info(self, tunnel_name, info):
        """Update tunnel information.
        
        Args:
            tunnel_name: Name of the tunnel
            info: Dictionary containing tunnel information
        """
        self.tunnel_info[tunnel_name] = info
        self._save_tunnel_state()

    def _extract_ngrok_url(self, proc, tunnel_name):
        """Extract URL from ngrok output.
        
        Args:
            proc: Process object for the tunnel
            tunnel_name: Name of the tunnel
        """
        try:
            # Wait a moment for ngrok to start
            time.sleep(2)
            url = "Not available"
            while proc.poll() is None:  # While process is running
                output = proc.stdout.readline().decode('utf-8')
                if output:
                    # Look for URL pattern in ngrok output
                    url_match = re.search(r'https://[a-zA-Z0-9\-\.]+\.ngrok\.io', output)
                    if url_match:
                        url = url_match.group(0)
                        self._update_tunnel_info(tunnel_name, {'url': url, 'started_at': time.time()})
                        self._log('INFO', f'{tunnel_name} URL: {url}')
                        break
        except Exception as e:
            self._log('DEBUG', f'Error extracting {tunnel_name} URL: {e}')

    def _extract_cloudflared_url(self, proc, tunnel_name):
        """Extract URL from cloudflared output.
        
        Args:
            proc: Process object for the tunnel
            tunnel_name: Name of the tunnel
        """
        try:
            # Wait a moment for cloudflared to start
            time.sleep(2)
            url = "Not available"
            while proc.poll() is None:  # While process is running
                output = proc.stdout.readline().decode('utf-8')
                if output:
                    # Look for URL pattern in cloudflared output
                    url_match = re.search(r'https://[a-zA-Z0-9\-\.]+\.trycloudflare\.com', output)
                    if url_match:
                        url = url_match.group(0)
                        self._update_tunnel_info(tunnel_name, {'url': url, 'started_at': time.time()})
                        self._log('INFO', f'{tunnel_name} URL: {url}')
                        break
        except Exception as e:
            self._log('DEBUG', f'Error extracting {tunnel_name} URL: {e}')

    def get_tunnel_status(self, tunnel_name):
        """Get status of a tunnel.
        
        Args:
            tunnel_name: Name of the tunnel
            
        Returns:
            Status of the tunnel (RUNNING, STOPPED, NOT_STARTED)
        """
        if tunnel_name in self.tunnel_processes:
            proc = self.tunnel_processes[tunnel_name]
            if proc.poll() is None:  # Still running
                return "RUNNING"
            else:
                # Process finished
                del self.tunnel_processes[tunnel_name]
                return "STOPPED"
        return "NOT_STARTED"

    def stop_tunnel(self, tunnel_name):
        """Stop a running tunnel.
        
        Args:
            tunnel_name: Name of the tunnel to stop
            
        Returns:
            True if tunnel was stopped successfully, False otherwise
        """
        if tunnel_name in self.tunnel_processes:
            try:
                proc = self.tunnel_processes[tunnel_name]
                # Try graceful termination first
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    proc.kill()
                    proc.wait()
                del self.tunnel_processes[tunnel_name]
                if tunnel_name in self.tunnel_info:
                    del self.tunnel_info[tunnel_name]
                if tunnel_name in self.url_extraction_threads:
                    del self.url_extraction_threads[tunnel_name]
                self._save_tunnel_state()
                self._log('SUCCESS', f'{tunnel_name} tunnel stopped')
                return True
            except Exception as e:
                self._log('ERROR', f'Failed to stop {tunnel_name} tunnel: {e}')
                return False
        return False

    def get_tunnel_url(self, tunnel_name):
        """Get tunnel URL if available.
        
        Args:
            tunnel_name: Name of the tunnel
            
        Returns:
            URL of the tunnel or "Not available" if not available
        """
        return self.tunnel_info.get(tunnel_name, {}).get('url', 'Not available')

    def list_tunnels(self):
        """List all tunnels and their status.
        
        Returns:
            Dictionary containing tunnel information
        """
        tunnels = {}
        for name in ['ngrok', 'cloudflared', 'pinggy', 'playit']:
            tunnels[name] = {
                'status': self.get_tunnel_status(name),
                'url': self.get_tunnel_url(name)
            }
        return tunnels

    def start_ngrok(self, port):
        """Start ngrok tunnel for the specified port.
        
        Args:
            port: Port number to tunnel
            
        Returns:
            True if tunnel was started successfully, False otherwise
        """
        if not shutil.which('ngrok'):
            self._log('ERROR', 'ngrok not found. Install from ngrok.com and add to PATH.')
            return False
        
        # Security: Validate port number
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                self._log('ERROR', f'Invalid port number: {port}')
                return False
        except (ValueError, TypeError):
            self._log('ERROR', f'Invalid port number: {port}')
            return False
        
        cmd = ["ngrok", "tcp", str(port_int)]
        try:
            proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                shell=False,  # Security: Never use shell=True
                text=True
            )
            self.tunnel_processes['ngrok'] = proc
            self._update_tunnel_info('ngrok', {'port': port_int, 'started_at': time.time(), 'url': 'Extracting...'})
            self._save_tunnel_state()
            
            # Start URL extraction thread
            url_thread = threading.Thread(
                target=self._extract_ngrok_url, 
                args=(proc, 'ngrok'), 
                daemon=True,
                name=f"ngrok-extract-{port_int}"
            )
            self.url_extraction_threads['ngrok'] = url_thread
            url_thread.start()
            
            self._log('SUCCESS', f'ngrok started for tcp {port_int}.')
            return True
        except FileNotFoundError:
            self._log('ERROR', 'ngrok command not found')
            return False
        except PermissionError:
            self._log('ERROR', 'Permission denied starting ngrok')
            return False
        except Exception as e:
            self._log('ERROR', f'Failed to start ngrok: {e}')
            return False

    def start_cloudflared(self, port):
        """Start cloudflared tunnel for the specified port.
        
        Args:
            port: Port number to tunnel
            
        Returns:
            True if tunnel was started successfully, False otherwise
        """
        if not shutil.which('cloudflared'):
            self._log('ERROR', 'cloudflared not found. Install: pkg install cloudflared')
            return False
        cmd = ["cloudflared", "tunnel", "--url", f"tcp://localhost:{port}"]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.tunnel_processes['cloudflared'] = proc
            self._update_tunnel_info('cloudflared', {'port': port, 'started_at': time.time(), 'url': 'Extracting...'})
            self._save_tunnel_state()
            
            # Start URL extraction thread
            url_thread = threading.Thread(target=self._extract_cloudflared_url, args=(proc, 'cloudflared'), daemon=True)
            self.url_extraction_threads['cloudflared'] = url_thread
            url_thread.start()
            
            self._log('SUCCESS', f'cloudflared started for tcp {port}.')
            return True
        except Exception as e:
            self._log('ERROR', f'Failed to start cloudflared: {e}')
            return False

    def start_pinggy(self, port):
        """Start pinggy tunnel for the specified port.
        
        Args:
            port: Port number to tunnel
            
        Returns:
            True if tunnel was started successfully, False otherwise
        """
        if not shutil.which('ssh'):
            self._log('ERROR', 'OpenSSH client not found. Install: pkg install openssh')
            return False
        # user must provide token, but we allow a free variant template