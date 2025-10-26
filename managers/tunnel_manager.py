#!/usr/bin/env python3
"""
Tunneling Manager (unified):
- No proot required: ngrok, cloudflared, pinggy
- Optional proot required: playit.gg
"""
import shutil, subprocess, os
from environment import EnvironmentManager

class TunnelManager:
    def __init__(self, logger=None):
        self.logger = logger

    def _log(self, level, msg):
        if self.logger: self.logger.log(level, msg)
        else: print(f"[{level}] {msg}")

    def start_ngrok(self, port):
        if not shutil.which('ngrok'):
            self._log('ERROR', 'ngrok not found. Install from ngrok.com and add to PATH.')
            return False
        cmd = ["ngrok", "tcp", str(port)]
        subprocess.Popen(cmd)
        self._log('SUCCESS', f'ngrok started for tcp {port}.')
        return True

    def start_cloudflared(self, port):
        if not shutil.which('cloudflared'):
            self._log('ERROR', 'cloudflared not found. Install: pkg install cloudflared')
            return False
        cmd = ["cloudflared", "tunnel", "--url", f"tcp://localhost:{port}"]
        subprocess.Popen(cmd)
        self._log('SUCCESS', f'cloudflared started for tcp {port}.')
        return True

    def start_pinggy(self, port):
        if not shutil.which('ssh'):
            self._log('ERROR', 'OpenSSH client not found. Install: pkg install openssh')
            return False
        # user must provide token, but we allow a free variant template
        cmd = ["ssh","-o","StrictHostKeyChecking=no","-R",f"0:localhost:{port}","a.pinggy.io"]
        subprocess.Popen(cmd)
        self._log('SUCCESS', f'pinggy started for tcp {port}.')
        return True

    def start_playit(self, port):
        # Playit requires Debian/proot (user choice)
        if not EnvironmentManager.ensure_debian_if_needed('playit'):
            self._log('ERROR', 'Debian environment required for playit.gg. Aborting.')
            return False
        # We assume playit binary is installed in Debian env; just document path
        self._log('INFO', 'Please run playit agent inside Debian (proot-distro login).')
        return True
