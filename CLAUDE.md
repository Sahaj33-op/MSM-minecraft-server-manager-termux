# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MSM (Minecraft Server Manager) is a Python CLI tool for managing multiple Minecraft servers on Termux/Android. It supports 7 server flavors: Paper, Purpur, Folia, Vanilla, Fabric, Quilt, and PocketMine-MP.

## Commands

### Running the Application
```bash
# Interactive menu mode
python3 main.py

# CLI automation mode
python3 cli.py <command>

# CLI examples
python3 cli.py server list
python3 cli.py server create myserver
python3 cli.py server install myserver paper --version 1.20.4
python3 cli.py server start myserver
python3 cli.py world backup myserver
python3 cli.py plugin list myserver
python3 cli.py schedule add myserver backup daily --time 03:00
```

### Running Tests
```bash
python -m tests.test_server_manager
python -m tests.test_tunnel_manager_enhanced
python -m tests.test_server_manager_enhanced
```

### Dependencies
```bash
pip install -r requirements.txt  # requests>=2.28.0, psutil>=5.9.0
```

System dependencies: `python3`, `screen`, `openjdk-17` (or 21), `wget`, `curl`

## Architecture

### Entry Points
- `main.py` - Interactive menu-driven interface with graceful shutdown handling
- `cli.py` - Non-interactive CLI for automation/scripting with subcommand parser

### Core Layer (`core/`)
- `config.py` - ConfigManager: loads/saves server configs from `~/.config/msm/`
- `database.py` - DatabaseManager: SQLite for session tracking and statistics
- `monitoring.py` - PerformanceMonitor: threaded CPU/RAM monitoring via psutil
- `scheduler.py` - Scheduler: cron-like task scheduling for backups/restarts
- `logger.py` - EnhancedLogger: rotating file logger with multiple log levels
- `constants.py` - Application-wide constants including security restrictions
- `exceptions.py` - Custom exceptions: MSMError, APIError, DownloadError, ConfigError

### Manager Layer (`managers/`)
- `server_manager.py` - ServerManager: server lifecycle (create, start, stop, install, configure). Uses `screen` sessions for background server execution
- `api_client.py` - API clients for fetching server JARs (PaperMCAPI, PurpurAPI, FoliaAPI, VanillaAPI, FabricAPI, QuiltAPI, PocketMineAPI)
- `world_manager.py` - WorldManager: backup/restore world directories with compression
- `tunnel_manager.py` - TunnelManager: ngrok, cloudflared, pinggy, playit.gg integration
- `plugin_manager.py` - PluginManager: install/enable/disable plugins for Java servers

### Utilities (`utils/`)
- `helpers.py` - Common functions: `sanitize_input()`, `get_java_path()`, `is_screen_session_running()`, `run_command()`, `get_server_directory()`
- `termux_utils.py` - Termux-specific environment detection and optimizations
- `decorators.py` - `@handle_errors`, `@performance_monitor` decorators

### UI Layer (`ui/`)
- `interface.py` - UI class with colored output and menu rendering

### Data Storage
- Server configs: `~/.config/msm/servers/<name>/config.json`
- Database: `~/.config/msm/msm.db`
- Logs: `~/.config/msm/msm.log`
- Server files: `~/minecraft-<name>/`

## Key Patterns

### Server Lifecycle
Servers run in `screen` sessions named `msm_<servername>`. The ServerManager tracks PIDs and monitors processes via psutil. Java servers use G1GC tuning flags; PocketMine uses PHP.

### API Client Pattern
All API clients inherit from `BaseAPI` which provides `set_logger()` and `_log()`. Each client implements `get_versions()` and methods to fetch download URLs.

### Configuration Flow
1. Global config via `ConfigManager.load()` returns dict with `servers` and `current_server`
2. Per-server config via `ConfigManager.load_server_config(name)` includes `server_settings` dict matching server.properties keys

### Error Handling
Custom exceptions (APIError, DownloadError, ConfigError) are caught in main.py's menu loop with user-friendly messages.
