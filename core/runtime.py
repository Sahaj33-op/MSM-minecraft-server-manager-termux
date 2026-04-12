"""Runtime registry for active server instances."""

from __future__ import annotations

import threading
from pathlib import Path

from core.server import ServerInstance
from utils.system import (
    get_screen_name,
    get_server_dir,
    is_pid_running,
    read_pid_file,
    remove_file,
    screen_session_exists,
)


class RuntimeManager:
    """Keeps one ServerInstance per configured server."""

    def __init__(self, config_manager, db_manager, logger):
        self.config_manager = config_manager
        self.db_manager = db_manager
        self.logger = logger
        self._lock = threading.RLock()
        self._instances: dict[str, ServerInstance] = {}

    def get_instance(self, server_name: str) -> ServerInstance:
        with self._lock:
            instance = self._instances.get(server_name)
            if instance is None:
                instance = ServerInstance(
                    server_name,
                    self.config_manager,
                    self.db_manager,
                    self.logger,
                )
                self._instances[server_name] = instance
            return instance

    def resume_running_servers(self) -> None:
        config = self.config_manager.load()
        for server_name in config.get("servers", {}):
            instance = self.get_instance(server_name)
            if instance.is_running():
                instance.resume_background_services()

    def is_server_running(self, server_name: str) -> bool:
        pid_file = Path(get_server_dir(server_name)) / ".msm.pid"
        pid = read_pid_file(pid_file)
        if pid and is_pid_running(pid):
            return True
        if pid:
            remove_file(pid_file)
        return screen_session_exists(get_screen_name(server_name), logger=self.logger)

    def running_servers(self) -> list[str]:
        config = self.config_manager.load()
        return [
            server_name
            for server_name in config.get("servers", {})
            if self.is_server_running(server_name)
        ]
