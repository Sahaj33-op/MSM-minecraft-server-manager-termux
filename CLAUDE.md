# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSM (Minecraft Server Manager) is a Python CLI tool for managing multiple Minecraft servers on Termux/Android. It supports 7 server flavors: Paper, Purpur, Folia, Vanilla, Fabric, Quilt, and PocketMine-MP.

## Commands

### Running the Application
```bash
# Interactive menu mode
python3 main.py
python3 main.py --help

# CLI automation mode
python3 cli.py <command>

# CLI examples
python3 cli.py server list
python3 cli.py server create myserver
python3 cli.py server install myserver paper --version 1.20.4
python3 cli.py server start myserver
python3 cli.py server stop myserver
python3 cli.py server configure myserver port 25566
python3 cli.py world backup myserver
python3 cli.py world list-backups myserver
python3 cli.py plugin list myserver
python3 cli.py schedule add myserver backup daily --time 03:00
python3 cli.py stats myserver
python3 cli.py dashboard myserver  # Live performance dashboard
python3 cli.py console myserver    # Attach to server console
python3 cli.py health              # System health check
python3 cli.py health --server myserver  # Include server health
python3 cli.py db-info             # Database statistics
```

### Running Tests
```bash
# Run individual test modules
python -m tests.test_server_manager
python -m tests.test_tunnel_manager_enhanced
python -m tests.test_server_manager_enhanced
python -m tests.test_core_modules  # Database, logger, monitoring, validation tests

# Run with pytest (if installed)
python -m pytest tests/
```

### Dependencies
```bash
pip install -r requirements.txt  # requests>=2.28.0, psutil>=5.9.0
```

System dependencies: `python3`, `screen`, `openjdk-17` (or 21), `wget`, `curl`, `php` (for PocketMine only)

## Architecture

### Entry Points
- `main.py` - Interactive menu-driven interface with graceful shutdown handling
- `cli.py` - Non-interactive CLI for automation/scripting with subcommand parser

### Core Layer (`core/`)
- `config.py` - ConfigManager: loads/saves server configs from `~/.config/msm/`
- `database.py` - DatabaseManager: SQLite for session tracking and statistics
- `monitoring.py` - PerformanceMonitor: threaded CPU/RAM monitoring via psutil
- `scheduler.py` - Scheduler: cron-like task scheduling for backups/restarts (runs in daemon thread)
- `logger.py` - EnhancedLogger: rotating file logger with multiple log levels
- `constants.py` - Configuration classes: ServerConfig, SecurityConfig, TermuxConfig, NetworkConfig
- `exceptions.py` - Custom exceptions: MSMError, APIError, DownloadError, ConfigError, ServerError

### Manager Layer (`managers/`)
- `server_manager.py` - ServerManager: server lifecycle (create, start, stop, install, configure). Uses `screen` sessions for background server execution
- `api_client.py` - API clients for fetching server JARs (PaperMCAPI, PurpurAPI, FoliaAPI, VanillaAPI, FabricAPI, QuiltAPI, PocketMineAPI)
- `world_manager.py` - WorldManager: backup/restore world directories with compression
- `tunnel_manager.py` - TunnelManager: ngrok, cloudflared, pinggy, playit.gg integration
- `plugin_manager.py` - PluginManager: install/enable/disable plugins for Java servers

### Utilities (`utils/`)
- `helpers.py` - Common functions: `sanitize_input()`, `get_java_path()`, `is_screen_session_running()`, `run_command()`, `get_server_directory()`, `validate_port()`, `is_port_in_use()`
- `termux_utils.py` - Termux-specific environment detection and optimizations
- `decorators.py` - `@handle_errors`, `@performance_monitor` decorators

### UI Layer (`ui/`)
- `interface.py` - UI class with colored output and menu rendering

### Data Storage
- Server configs: `~/.config/msm/servers/<name>/config.json`
- Global config: `~/.config/msm/config.json`
- Scheduled tasks: `~/.config/msm/schedule.json`
- Database: `~/.config/msm/msm.db`
- Logs: `~/.config/msm/msm.log`
- Server files: `~/minecraft-<name>/`
- World backups: `~/minecraft-<name>/backups/`

## Key Patterns

### Dependency Initialization
Managers are wired together in a specific order (see `cli.py:init_cli_system()`):
```python
logger = EnhancedLogger(log_file)
db = DatabaseManager(db_file)
monitor = PerformanceMonitor(db, logger)
server_mgr = ServerManager(db, logger, monitor)
world_mgr = WorldManager(logger)
scheduler = Scheduler(config_dir, logger, server_mgr, world_mgr)
```

### Server Lifecycle
Servers run in `screen` sessions named `msm_<servername>`. The ServerManager tracks PIDs and monitors processes via psutil. Java servers use G1GC tuning flags; PocketMine uses PHP.

Server start flow:
1. Check EULA acceptance (Java servers only) - prompts user and stores in config
2. Write `eula.txt` and update `server.properties`
3. Launch in screen session: `screen -dmS msm_<name> java -jar server.jar nogui`
4. Verify process is running via psutil
5. Start performance monitoring thread

### API Client Pattern
All API clients inherit from `BaseAPI` which provides `set_logger()` and `_log()`. Each client implements `get_versions()` and `get_download_url()`. The logger is set globally via `BaseAPI.set_logger(logger)` in ServerManager.__init__.

### Configuration Flow
1. Global config via `ConfigManager.load()` returns dict with `servers` and `current_server`
2. Per-server config via `ConfigManager.load_server_config(name)` includes `server_settings` dict matching server.properties keys
3. Current server context: `ConfigManager.get_current_server()` / `set_current_server(name)`

### Scheduler Pattern
Tasks have frequency options: `hourly`, `daily`, `weekly@<day>` (e.g., `weekly@sun`). The scheduler runs in a daemon thread, checking every 60 seconds. For restart tasks, it saves/restores server context to avoid affecting the current user session.

### Security
Input sanitization via `sanitize_input()`. Blocked shell metacharacters: `& | ; && || > < \` $ ( )`. Protected paths defined in `SecurityConfig.SENSITIVE_PATHS`. Port validation: 1-65535 range with in-use detection.

### Error Handling
Custom exceptions (APIError, DownloadError, ConfigError, ServerError) are caught in main.py's menu loop with user-friendly messages.
