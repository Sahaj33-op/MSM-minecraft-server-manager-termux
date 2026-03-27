#!/usr/bin/env python3
"""
Shared performance dashboard helpers.
"""
import re
import time
from collections import deque
from pathlib import Path
from typing import Optional

import psutil

from utils.helpers import (
    get_screen_session_name,
    get_server_directory,
    is_screen_session_running,
    run_command
)


class LogTailer:
    """Read only newly appended log content between refreshes."""

    def __init__(self, path: Path):
        self.path = path
        self._position = 0

    def read_new_lines(self):
        try:
            with open(self.path, "r", errors="ignore") as handle:
                handle.seek(self._position)
                data = handle.read()
                self._position = handle.tell()
        except OSError:
            return []

        if not data:
            return []
        return data.splitlines()


def _find_server_process(screen_name: str) -> Optional[psutil.Process]:
    """Find the screen process or Java/PHP child for a running server."""
    result = run_command(['screen', '-ls'], capture_output=True)
    if result[0] != 0:
        return None

    match = re.search(rf'(\d+)\.{re.escape(screen_name)}\s', result[1])
    if not match:
        return None

    parent = psutil.Process(int(match.group(1)))
    for child in parent.children(recursive=True):
        try:
            if child.name().lower() in ['java', 'php']:
                return child
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return parent


def show_performance_dashboard(server_mgr, monitor, ui, logger, version: str = "Unified") -> bool:
    """Display live performance metrics for the currently selected server."""
    current_server = server_mgr.get_current_server()
    if not current_server:
        if ui:
            ui.print_error("No server selected")
        return False

    screen_name = get_screen_session_name(current_server)
    if not is_screen_session_running(screen_name):
        if ui:
            ui.print_warning(f"Server '{current_server}' is not running.")
        return False

    logger.log('INFO', f"Starting performance dashboard for {current_server}")
    print(f"{ui.colors.CYAN}Starting Performance Dashboard for '{current_server}'... Press Ctrl+C to exit.{ui.colors.RESET}")
    time.sleep(2)

    server_path = get_server_directory(current_server)
    log_path = server_path / "logs" / "latest.log"
    log_tailer = LogTailer(log_path)
    recent_lines = deque(maxlen=200)

    if log_path.exists():
        try:
            with open(log_path, "r", errors="ignore") as handle:
                recent_lines.extend(line.rstrip("\n") for line in handle.readlines()[-200:])
                log_tailer._position = handle.tell()
        except OSError:
            pass

    try:
        server_process = _find_server_process(screen_name)
        if not server_process:
            ui.print_warning("Could not find server process PID. Displaying limited info.")

        while True:
            sys_info = monitor.get_system_info() if monitor else None
            ui.print_header(version=version, system_info=sys_info)
            print(f"{ui.colors.BOLD}Performance Dashboard: {current_server}{ui.colors.RESET} (Press Ctrl+C to exit)\n")

            cpu_percent = "N/A"
            mem_rss_mb = "N/A"

            if server_process:
                try:
                    if server_process.is_running():
                        with server_process.oneshot():
                            cpu_percent = f"{server_process.cpu_percent():.1f}%"
                            mem_info = server_process.memory_info()
                            mem_rss_mb = f"{mem_info.rss / (1024 * 1024):.1f} MB"
                    else:
                        ui.print_warning("Server process stopped running.")
                        break
                except psutil.NoSuchProcess:
                    ui.print_warning("Server process disappeared.")
                    break
                except Exception as exc:
                    logger.log('ERROR', f"Error getting process stats: {exc}")
                    cpu_percent = "Error"
                    mem_rss_mb = "Error"

            print(f"  {ui.colors.CYAN}CPU Usage:{ui.colors.RESET}  {cpu_percent}")
            print(f"  {ui.colors.CYAN}RAM Usage:{ui.colors.RESET}  {mem_rss_mb}")

            recent_lines.extend(log_tailer.read_new_lines())
            tps_info = "N/A (Log parsing)"
            player_count = "N/A (Log parsing)"

            try:
                for line in reversed(recent_lines):
                    tps_match = re.search(r'TPS from last 1m, 5m, 15m:\s*\*([\d\.]+),\s*([\d\.]+),\s*([\d\.]+)', line)
                    if tps_match:
                        tps_info = f"{float(tps_match.group(1)):.1f} (1m)"
                        break

                players = set()
                for line in recent_lines:
                    join_match = re.search(r'\]:\s*(\w+)\[.*logged in', line)
                    quit_match = re.search(r'\]:\s*(\w+)\s*left the game', line)
                    disc_match = re.search(r'\]:\s*(\w+)\s*lost connection', line)
                    if join_match:
                        players.add(join_match.group(1))
                    elif quit_match:
                        players.discard(quit_match.group(1))
                    elif disc_match:
                        players.discard(disc_match.group(1))
                player_count = str(len(players))
            except Exception as exc:
                logger.log('DEBUG', f"Failed to parse log for TPS/Players: {exc}")
                tps_info = "Error parsing log"
                player_count = "Error parsing log"

            print(f"  {ui.colors.CYAN}TPS (est.):{ui.colors.RESET} {tps_info}")
            print(f"  {ui.colors.CYAN}Players:{ui.colors.RESET}    {player_count}")

            time.sleep(5)

    except KeyboardInterrupt:
        logger.log('INFO', "Performance dashboard stopped by user.")
        print("\nExiting dashboard...")
        time.sleep(1)
        return True
    except Exception as exc:
        logger.log('ERROR', f"Error in performance dashboard: {exc}")
        if ui:
            ui.print_error(f"Dashboard error: {exc}")
        return False
