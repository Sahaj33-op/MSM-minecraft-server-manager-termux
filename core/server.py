"""Per-server runtime state and lifecycle management."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

from core.constants import (
    AUTO_RESTART_DELAY_SECONDS,
    AUTO_RESTART_POLL_INTERVAL,
    BACKUP_POLL_INTERVAL,
    EULA_FILE,
    MONITOR_INTERVAL,
    PID_FILE_NAME,
    SERVER_FLAVORS,
    SERVER_PROPERTIES_FILE,
    SESSION_FILE_NAME,
    TUNNEL_PID_FILE_NAME,
)
from utils.archive import create_backup_archive, discover_world_directories, safe_extract_zip
from utils.network import download_server_binary, get_ngrok_public_url
from utils.properties import load_properties, write_properties
from utils.rcon import RCONClient, RCONError
from utils.system import (
    build_screen_launch_command,
    check_disk_space,
    format_bytes,
    get_java_path,
    get_screen_name,
    get_server_dir,
    is_pid_running,
    read_pid_file,
    read_text_file,
    remove_file,
    run_command,
    screen_session_exists,
    wait_for_pid_file,
    write_text_file,
)


class ServerInstance:
    """Owns the runtime state for one configured server."""

    def __init__(self, server_name: str, config_manager, db_manager, logger):
        self.server_name = server_name
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.logger = logger
        self._lock = threading.RLock()
        self._manual_stop_requested = False
        self.monitor_stop_event = threading.Event()
        self.auto_restart_stop_event = threading.Event()
        self.backup_stop_event = threading.Event()
        self.monitor_thread: threading.Thread | None = None
        self.auto_restart_thread: threading.Thread | None = None
        self.backup_thread: threading.Thread | None = None
        self.tunnel_process: subprocess.Popen[str] | None = None
        self.tunnel_log_handle = None
        self.next_backup_deadline = time.time()

    @property
    def server_dir(self) -> Path:
        return get_server_dir(self.server_name)

    @property
    def backup_dir(self) -> Path:
        return self.server_dir / "backups"

    @property
    def pid_file(self) -> Path:
        return self.server_dir / PID_FILE_NAME

    @property
    def session_file(self) -> Path:
        return self.server_dir / SESSION_FILE_NAME

    @property
    def tunnel_pid_file(self) -> Path:
        return self.server_dir / TUNNEL_PID_FILE_NAME

    @property
    def screen_name(self) -> str:
        return get_screen_name(self.server_name)

    def refresh_config(self) -> tuple[dict[str, Any], dict[str, Any]]:
        config = self.config_manager.load()
        server_config = config.get("servers", {}).get(self.server_name)
        if not server_config:
            raise RuntimeError(f"Server '{self.server_name}' is not configured.")
        return config, server_config

    def current_pid(self) -> int | None:
        pid = read_pid_file(self.pid_file)
        if pid and is_pid_running(pid):
            return pid
        if pid:
            remove_file(self.pid_file)
        return None

    def current_session_id(self) -> int | None:
        raw = read_text_file(self.session_file)
        if raw and raw.isdigit():
            return int(raw)
        return self.db_manager.get_last_open_session(self.server_name)

    def is_running(self) -> bool:
        return bool(
            self.current_pid()
            or screen_session_exists(self.screen_name, logger=self.logger)
        )

    def ensure_server_files(self) -> None:
        self.server_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def resolve_server_artifact(self, server_config: dict[str, Any]) -> str:
        flavor = server_config["server_flavor"]
        flavor_info = SERVER_FLAVORS[flavor]
        if flavor_info["type"] == "java":
            explicit = self.server_dir / "server.jar"
            if explicit.exists():
                return explicit.name
            jars = sorted(file.name for file in self.server_dir.glob("*.jar"))
            if jars:
                return jars[0]
            raise RuntimeError("No server JAR file found in the server directory.")
        phars = sorted(file.name for file in self.server_dir.glob("*.phar"))
        if phars:
            return phars[0]
        raise RuntimeError("No PocketMine PHAR file found in the server directory.")

    def build_startup_command(self) -> list[str]:
        config, server_config = self.refresh_config()
        flavor = server_config.get("server_flavor")
        version = server_config.get("server_version")
        ram_mb = int(server_config.get("ram_mb", 1024))
        flavor_info = SERVER_FLAVORS.get(flavor)
        if not flavor_info or not version:
            raise RuntimeError("Server is not installed or is missing flavor/version metadata.")

        artifact = self.resolve_server_artifact(server_config)
        if flavor_info["type"] == "java":
            java_binary = get_java_path(version, config, logger=self.logger)
            if not java_binary:
                raise RuntimeError("A compatible Java runtime could not be located.")
            return [
                java_binary,
                f"-Xmx{ram_mb}M",
                f"-Xms{ram_mb}M",
                "-XX:+UseG1GC",
                "-XX:+ParallelRefProcEnabled",
                "-XX:MaxGCPauseMillis=200",
                "-jar",
                artifact,
                "nogui",
            ]
        return ["php", artifact]

    def apply_server_files(self) -> None:
        self.ensure_server_files()
        _config, server_config = self.refresh_config()
        properties = load_properties(self.server_dir / SERVER_PROPERTIES_FILE)
        properties.update(
            {key: str(value) for key, value in server_config.get("server_settings", {}).items()}
        )

        rcon_config = server_config.get("rcon", {})
        if rcon_config.get("enabled"):
            properties["enable-rcon"] = "true"
            properties["rcon.port"] = str(rcon_config.get("port", 25575))
            if rcon_config.get("password"):
                properties["rcon.password"] = str(rcon_config["password"])
        else:
            properties["enable-rcon"] = "false"

        write_properties(
            self.server_dir / SERVER_PROPERTIES_FILE,
            properties,
            header_comment="Managed by MSM. Manual edits are allowed.",
        )
        write_properties(
            self.server_dir / EULA_FILE,
            {"eula": str(server_config.get("eula_accepted", True)).lower()},
        )

    def save_server_properties(self, properties: dict[str, Any]) -> None:
        write_properties(
            self.server_dir / SERVER_PROPERTIES_FILE,
            properties,
            header_comment="Managed by MSM. Manual edits are allowed.",
        )

        def updater(config: dict[str, Any]) -> None:
            server_config = config["servers"][self.server_name]
            settings = server_config.setdefault("server_settings", {})
            for key in ["motd", "online-mode"]:
                if key in properties:
                    settings[key] = str(properties[key])
            for key in ["port", "max-players", "rcon.port"]:
                if key in properties:
                    try:
                        numeric = int(str(properties[key]))
                    except ValueError:
                        continue
                    if key == "rcon.port":
                        server_config.setdefault("rcon", {})["port"] = numeric
                        settings[key] = numeric
                    else:
                        settings[key] = numeric
            if "enable-rcon" in properties:
                enabled = str(properties["enable-rcon"]).lower() == "true"
                server_config.setdefault("rcon", {})["enabled"] = enabled
                settings["enable-rcon"] = str(enabled).lower()
            if "rcon.password" in properties:
                server_config.setdefault("rcon", {})["password"] = str(properties["rcon.password"])

        self.config_manager.mutate(updater)

    def set_eula(self, accepted: bool) -> None:
        write_properties(self.server_dir / EULA_FILE, {"eula": str(accepted).lower()})

        def updater(config: dict[str, Any]) -> None:
            config["servers"][self.server_name]["eula_accepted"] = accepted

        self.config_manager.mutate(updater)

    def create_backup(self, backup_type: str = "manual") -> Path:
        self.ensure_server_files()
        world_dirs = discover_world_directories(self.server_dir)
        if not world_dirs:
            raise RuntimeError("No world directories were found to back up.")
        if not check_disk_space(self.server_dir, required_mb=500, logger=self.logger):
            raise RuntimeError("Insufficient disk space for backup.")
        backup_name = f"world_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        backup_path = self.backup_dir / backup_name
        size = create_backup_archive(self.server_dir, backup_path, world_dirs)
        self.db_manager.log_backup(
            self.server_name,
            str(backup_path),
            size,
            backup_type=backup_type,
        )
        self.logger.log(
            "SUCCESS",
            f"Backup created for {self.server_name}: {backup_name}",
            size=format_bytes(size),
        )
        return backup_path

    def restore_backup(self, backup_name: str) -> Path:
        if self.is_running():
            raise RuntimeError("Stop the server before restoring a backup.")
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise RuntimeError(f"Backup '{backup_name}' does not exist.")
        safe_extract_zip(backup_path, self.server_dir)
        self.logger.log("SUCCESS", f"Restored backup {backup_name}")
        return backup_path

    def list_backups(self) -> list[Path]:
        if not self.backup_dir.exists():
            return []
        return sorted(self.backup_dir.glob("*.zip"), reverse=True)

    def delete_backup(self, backup_name: str) -> None:
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            raise RuntimeError(f"Backup '{backup_name}' does not exist.")
        backup_path.unlink()
        self.logger.log("SUCCESS", f"Deleted backup {backup_name}")

    def install_binary(
        self,
        flavor: str,
        version: str,
        version_info: dict[str, Any],
    ) -> Path:
        self.ensure_server_files()
        if not check_disk_space(self.server_dir, required_mb=500, logger=self.logger):
            raise RuntimeError("Insufficient disk space to install the server binary.")
        artifact = download_server_binary(
            flavor,
            version,
            version_info,
            self.server_dir,
            logger=self.logger,
        )
        if SERVER_FLAVORS[flavor]["type"] == "java":
            self.set_eula(True)
        return artifact

    def start(self) -> bool:
        with self._lock:
            if self.is_running():
                self.logger.log("WARNING", f"{self.server_name} is already running.")
                return False
            self.ensure_server_files()
            self.apply_server_files()
            self._manual_stop_requested = False
            self.monitor_stop_event = threading.Event()
            self.auto_restart_stop_event = threading.Event()
            self.backup_stop_event = threading.Event()
            startup_command = self.build_startup_command()
            launch_command = build_screen_launch_command(
                self.screen_name,
                startup_command,
                self.pid_file,
            )
            started = run_command(launch_command, logger=self.logger, cwd=self.server_dir)
            if not started:
                self.logger.log("ERROR", f"Failed to start {self.server_name} in screen.")
                return False
            pid = wait_for_pid_file(self.pid_file)
            if not pid:
                self.logger.log("ERROR", f"Unable to determine a PID for {self.server_name}.")
                return False
            _config, server_config = self.refresh_config()
            session_id = self.db_manager.log_session_start(
                self.server_name,
                server_config["server_flavor"],
                server_config["server_version"],
            )
            write_text_file(self.session_file, str(session_id))
            self.logger.log("SUCCESS", f"Started {self.server_name}", pid=pid)
            self.resume_background_services()
            return True

    def stop_background_threads(self) -> None:
        self.monitor_stop_event.set()
        self.auto_restart_stop_event.set()
        self.backup_stop_event.set()

    def finalize_session(self) -> None:
        session_id = self.current_session_id()
        if session_id:
            self.db_manager.log_session_end(session_id)
        remove_file(self.session_file)
        remove_file(self.pid_file)

    def stop_tunnel(self) -> None:
        pid = read_pid_file(self.tunnel_pid_file)
        if self.tunnel_process and self.tunnel_process.poll() is None:
            self.tunnel_process.terminate()
            try:
                self.tunnel_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.tunnel_process.kill()
        elif pid and is_pid_running(pid):
            try:
                psutil.Process(pid).terminate()
            except psutil.Error:
                pass
        remove_file(self.tunnel_pid_file)
        if self.tunnel_log_handle:
            self.tunnel_log_handle.close()
            self.tunnel_log_handle = None
        self.tunnel_process = None

    def stop(self, force: bool = False) -> bool:
        with self._lock:
            if not self.is_running():
                self.logger.log("INFO", f"{self.server_name} is not running.")
                self.finalize_session()
                return False
            self._manual_stop_requested = True
            self.stop_background_threads()
            if not force:
                stopped = self.send_command("stop")
                if not stopped:
                    self.logger.log("WARNING", "Graceful stop failed; falling back to screen.")
                for _ in range(20):
                    if not self.is_running():
                        break
                    time.sleep(1)
            if self.is_running():
                run_command(
                    ["screen", "-S", self.screen_name, "-X", "quit"],
                    logger=self.logger,
                    check=False,
                )
                for _ in range(5):
                    if not self.is_running():
                        break
                    time.sleep(1)
            self.stop_tunnel()
            self.finalize_session()
            if self.is_running():
                self.logger.log("ERROR", f"Failed to stop {self.server_name}.")
                return False
            self.logger.log("SUCCESS", f"Stopped {self.server_name}")
            return True

    def send_command(self, command: str) -> bool:
        if not self.is_running():
            self.logger.log("ERROR", f"{self.server_name} is not running.")
            return False
        _config, server_config = self.refresh_config()
        rcon_config = server_config.get("rcon", {})
        if rcon_config.get("enabled") and rcon_config.get("password"):
            try:
                with RCONClient(
                    rcon_config.get("host", "127.0.0.1"),
                    int(rcon_config.get("port", 25575)),
                    str(rcon_config.get("password", "")),
                ) as client:
                    response = client.command(command)
                if response:
                    self.logger.log("INFO", response.strip())
                return True
            except (RCONError, OSError) as exc:
                self.logger.log("WARNING", f"RCON failed, falling back to screen: {exc}")

        result = run_command(
            ["screen", "-S", self.screen_name, "-p", "0", "-X", "stuff", f"{command}\n"],
            logger=self.logger,
            check=False,
        )
        return result is not None

    def resume_background_services(self) -> None:
        if not self.is_running():
            return
        self._manual_stop_requested = False
        self._start_monitor_thread()
        self._start_auto_restart_thread()
        self._start_backup_thread()
        self.start_tunnel()

    def _start_monitor_thread(self) -> None:
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        if not self.current_pid():
            return
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name=f"msm-monitor-{self.server_name}",
            daemon=True,
        )
        self.monitor_thread.start()

    def _start_auto_restart_thread(self) -> None:
        _config, server_config = self.refresh_config()
        if not server_config.get("auto_restart"):
            return
        if self.auto_restart_thread and self.auto_restart_thread.is_alive():
            return
        self.auto_restart_thread = threading.Thread(
            target=self._auto_restart_loop,
            name=f"msm-autorestart-{self.server_name}",
            daemon=True,
        )
        self.auto_restart_thread.start()

    def _start_backup_thread(self) -> None:
        _config, server_config = self.refresh_config()
        if not server_config.get("backup_settings", {}).get("enabled"):
            return
        if self.backup_thread and self.backup_thread.is_alive():
            return
        interval_hours = float(server_config["backup_settings"].get("interval_hours", 6))
        self.next_backup_deadline = time.time() + (interval_hours * 3600)
        self.backup_thread = threading.Thread(
            target=self._backup_loop,
            name=f"msm-backup-{self.server_name}",
            daemon=True,
        )
        self.backup_thread.start()

    def _monitor_loop(self) -> None:
        pid = self.current_pid()
        if not pid:
            return
        try:
            process = psutil.Process(pid)
            process.cpu_percent(interval=None)
        except psutil.Error:
            return

        self.logger.log("INFO", f"Monitoring {self.server_name}", pid=pid)
        while not self.monitor_stop_event.wait(MONITOR_INTERVAL):
            pid = self.current_pid()
            if not pid:
                break
            try:
                if process.pid != pid:
                    process = psutil.Process(pid)
                    process.cpu_percent(interval=None)
                with process.oneshot():
                    cpu_usage = process.cpu_percent(interval=None)
                    ram_usage = process.memory_percent()
                self.db_manager.log_performance_metric(self.server_name, ram_usage, cpu_usage)
            except psutil.Error:
                break
        self.logger.log("INFO", f"Stopped monitoring {self.server_name}")

    def _backup_loop(self) -> None:
        while not self.backup_stop_event.wait(BACKUP_POLL_INTERVAL):
            if not self.is_running():
                break
            _config, server_config = self.refresh_config()
            backup_settings = server_config.get("backup_settings", {})
            if not backup_settings.get("enabled"):
                continue
            interval_hours = float(backup_settings.get("interval_hours", 6))
            if time.time() < self.next_backup_deadline:
                continue
            try:
                self.create_backup(backup_type="scheduled")
            except Exception as exc:
                self.logger.log("ERROR", f"Scheduled backup failed for {self.server_name}: {exc}")
            self.next_backup_deadline = time.time() + (interval_hours * 3600)

    def _auto_restart_loop(self) -> None:
        self.logger.log("INFO", f"Auto-restart enabled for {self.server_name}")
        while not self.auto_restart_stop_event.wait(AUTO_RESTART_POLL_INTERVAL):
            if self._manual_stop_requested:
                break
            if self.is_running():
                continue
            session_id = self.current_session_id()
            if session_id:
                self.db_manager.increment_crash_count(session_id)
                self.db_manager.increment_restart_count(session_id)
                self.db_manager.log_session_end(session_id)
                remove_file(self.session_file)
            self.logger.log("WARNING", f"{self.server_name} exited unexpectedly. Restarting soon.")
            time.sleep(AUTO_RESTART_DELAY_SECONDS)
            if self.auto_restart_stop_event.is_set() or self._manual_stop_requested:
                break
            try:
                startup_command = self.build_startup_command()
                launch_command = build_screen_launch_command(
                    self.screen_name,
                    startup_command,
                    self.pid_file,
                )
                started = run_command(launch_command, logger=self.logger, cwd=self.server_dir)
                if not started:
                    continue
                pid = wait_for_pid_file(self.pid_file)
                if not pid:
                    continue
                _config, server_config = self.refresh_config()
                session_id = self.db_manager.log_session_start(
                    self.server_name,
                    server_config["server_flavor"],
                    server_config["server_version"],
                )
                write_text_file(self.session_file, str(session_id))
                self.logger.log("SUCCESS", f"Auto-restarted {self.server_name}", pid=pid)
                self._start_monitor_thread()
            except Exception as exc:
                self.logger.log("ERROR", f"Auto-restart failed for {self.server_name}: {exc}")
        self.logger.log("INFO", f"Auto-restart disabled for {self.server_name}")

    def start_tunnel(self) -> None:
        _config, server_config = self.refresh_config()
        tunnel_config = server_config.get("tunnel", {})
        if not tunnel_config.get("enabled"):
            return
        if tunnel_config.get("provider", "ngrok") != "ngrok":
            self.logger.log("WARNING", "Only ngrok tunnel management is implemented right now.")
            return
        existing_pid = read_pid_file(self.tunnel_pid_file)
        if existing_pid and is_pid_running(existing_pid):
            return
        binary = tunnel_config.get("binary_path") or _config.get("tunnel_defaults", {}).get(
            "binary_path",
            "ngrok",
        )
        resolved_binary = shutil.which(binary) or binary
        if shutil.which(resolved_binary) is None and not Path(resolved_binary).exists():
            self.logger.log(
                "WARNING",
                f"Ngrok binary '{binary}' was not found. Tunnel startup skipped.",
            )
            return
        port = int(server_config.get("server_settings", {}).get("port", 25565))
        log_path = self.server_dir / ".msm.ngrok.log"
        self.tunnel_log_handle = log_path.open("a", encoding="utf-8")
        self.tunnel_process = subprocess.Popen(
            [resolved_binary, "tcp", str(port), "--log", "stdout"],
            cwd=self.server_dir,
            stdout=self.tunnel_log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        write_text_file(self.tunnel_pid_file, str(self.tunnel_process.pid))
        time.sleep(2)
        public_url = get_ngrok_public_url(port, logger=self.logger)
        if public_url:
            self.logger.log("SUCCESS", f"Ngrok tunnel ready for {self.server_name}: {public_url}")
        else:
            self.logger.log(
                "INFO",
                (
                    f"Ngrok process started for {self.server_name}. "
                    "Check http://127.0.0.1:4040 for status."
                ),
            )
