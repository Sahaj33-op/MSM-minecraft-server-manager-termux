# Minecraft Server Manager (MSM)

A production-grade command-line application for managing multiple Minecraft servers on Termux (Android). MSM provides comprehensive server lifecycle management, real-time performance monitoring, automated scheduling, and support for seven distinct server platforms.

---

## Table of Contents

- [Features](#features)
- [Supported Server Platforms](#supported-server-platforms)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Tunneling Services](#tunneling-services)
- [Security](#security)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Server Management
- Multi-server instance support with isolated configurations
- Server lifecycle control (start, stop, restart) via GNU Screen sessions
- Automated server software installation and updates
- Real-time server console access
- Configurable server properties (port, gamemode, difficulty, MOTD, etc.)

### Performance Monitoring
- Live CPU and memory usage tracking per server process
- TPS (Ticks Per Second) estimation via log parsing
- Active player count detection
- 24-hour statistical aggregation
- SQLite-backed session and performance history

### Automation
- Scheduled backups with configurable frequency (hourly, daily, weekly)
- Automated server restarts
- Background scheduler with thread-safe execution
- Persistent task configuration

### World Management
- Compressed world backups with tar/gzip
- Backup listing with timestamps
- Point-in-time world restoration
- Backup deletion and cleanup

### Plugin Management
- Plugin installation from URL or local filesystem
- Enable/disable plugins without deletion
- Plugin inventory listing
- Compatible with Paper, Purpur, Folia, and Spigot-based servers

### Tunneling Integration
- ngrok TCP tunneling (Termux-native)
- Cloudflare Tunnel support
- Pinggy SSH tunneling
- playit.gg integration (requires proot Debian)
- URL extraction and status monitoring

### Termux Optimization
- Automatic environment detection
- Mobile-specific resource optimizations
- Required package verification
- Android device information retrieval

---

## Supported Server Platforms

| Platform | Type | API Source |
|----------|------|------------|
| Paper | Java Edition | PaperMC API |
| Purpur | Java Edition | PurpurMC API |
| Folia | Java Edition (Multi-threaded) | PaperMC API |
| Vanilla | Java Edition | Mojang API |
| Fabric | Java Edition (Modded) | FabricMC API |
| Quilt | Java Edition (Modded) | QuiltMC API |
| PocketMine-MP | Bedrock Edition | GitHub Releases |

---

## System Requirements

### Platform
- Android device with Termux installed (F-Droid recommended)
- Termux environment with storage access configured (`termux-setup-storage`)

### Termux Environment
- **PREFIX**: `/data/data/com.termux/files/usr`
- **HOME**: `/data/data/com.termux/files/home`
- Uses Bionic libc (Android's C library)

### Dependencies

**System Packages (Termux):**
```
python
openjdk-17 (or openjdk-21)
screen
wget
curl
tar
git
```

**Python Packages:**
```
requests>=2.28.0
psutil>=5.9.0
```

---

## Installation

### Termux Setup

```bash
# Install Termux from F-Droid (recommended over Play Store)
# https://f-droid.org/packages/com.termux/

# Grant storage access (required for external storage)
termux-setup-storage

# Update package repositories
pkg update && pkg upgrade -y

# Install system dependencies
pkg install python git wget curl screen openjdk-17 -y

# Clone the repository
git clone --branch unified-merge-main-v1.1.0 \
    https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git

# Navigate to project directory
cd MSM-minecraft-server-manager-termux

# Install Python dependencies
pip install -r requirements.txt

# Launch MSM
python3 main.py
```

### Keeping Server Running

Use `termux-wake-lock` to prevent Android from killing background processes:

```bash
# Acquire wake lock before starting long-running servers
termux-wake-lock

# Start MSM
python3 main.py

# Release wake lock when done (or it auto-releases on exit)
termux-wake-unlock
```

---

## Usage

### Starting MSM

```bash
# Interactive mode
python3 main.py

# Background execution
screen -dmS msm python3 main.py
screen -r msm  # Reattach to session
```

### Command-Line Options

```bash
python3 main.py --help     # Display help information
python3 main.py --version  # Display version information
```

### Main Menu

```
================================================================================
                    Enhanced Minecraft Server Manager vUnified
         Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine
================================================================================

System: 2048MB RAM (1024MB free) | 4 CPUs (15%) | Android

Current Server: survival
Status: RUNNING

Main Menu:
 1. Start Server
 2. Stop Server
 3. Install/Update Server
 4. Configure Server
 5. Server Console
 6. World Manager
 7. Statistics
 8. Tunneling
 9. Performance Dashboard
 P. Plugin Manager
 S. Scheduler
10. Create/Switch Server
 0. Exit
```

### Common Workflows

**Creating a New Server:**
1. Select option `10` (Create/Switch Server)
2. Choose `n` for new server
3. Enter server name
4. Select option `3` (Install/Update Server)
5. Choose server platform and version
6. Configure RAM allocation and port

**Backing Up a World:**
1. Select option `6` (World Manager)
2. Choose `1` (Create Backup)
3. Backup is saved with timestamp to `backups/` directory

**Scheduling Automated Backups:**
1. Select option `S` (Scheduler)
2. Choose `a` (Add Task)
3. Select `backup` as task type
4. Choose target server
5. Set frequency (`daily`, `hourly`, `weekly@sun`)
6. Set execution time (HH:MM format)

---

## Architecture

```
MSM-minecraft-server-manager-termux/
├── main.py                 # Application entry point
├── cli.py                  # CLI argument handling
├── environment.py          # Environment detection utilities
│
├── core/                   # Core infrastructure
│   ├── config.py           # Configuration management
│   ├── constants.py        # Application constants
│   ├── database.py         # SQLite database operations
│   ├── exceptions.py       # Custom exception classes
│   ├── logger.py           # Enhanced logging with rotation
│   ├── monitoring.py       # Performance monitoring
│   └── scheduler.py        # Task scheduling
│
├── managers/               # Business logic managers
│   ├── api_client.py       # Server API clients
│   ├── plugin_manager.py   # Plugin operations
│   ├── server_manager.py   # Server lifecycle management
│   ├── tunnel_manager.py   # Tunneling services
│   └── world_manager.py    # World backup/restore
│
├── ui/                     # User interface
│   └── interface.py        # Terminal UI components
│
├── utils/                  # Utility modules
│   ├── decorators.py       # Function decorators
│   ├── helpers.py          # Helper functions
│   └── termux_utils.py     # Termux-specific utilities
│
└── tests/                  # Unit tests
    ├── test_server_manager.py
    ├── test_server_manager_enhanced.py
    ├── test_tunnel_manager_enhanced.py
    └── test_core_modules.py
```

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| `DatabaseManager` | SQLite operations, session tracking, performance metrics |
| `EnhancedLogger` | Log rotation, multi-level logging, file management |
| `PerformanceMonitor` | CPU/RAM monitoring, system metrics collection |
| `ConfigManager` | Server and global configuration persistence |
| `ServerManager` | Server installation, start/stop, console access |
| `WorldManager` | Backup creation, restoration, deletion |
| `TunnelManager` | External tunnel service integration |
| `PluginManager` | Plugin installation, enable/disable, deletion |
| `Scheduler` | Background task execution, cron-like scheduling |

---

## Configuration

### Directory Structure

```
$HOME/.config/msm/          # Termux: /data/data/com.termux/files/home/.config/msm/
├── msm.log                 # Application logs
├── msm.db                  # SQLite database
├── config.json             # Global configuration
└── schedule.json           # Scheduled tasks

$HOME/minecraft-<server-name>/
├── server.jar              # Server executable
├── server.properties       # Minecraft server configuration
├── world/                  # World data
├── plugins/                # Plugins directory (Java servers)
├── logs/                   # Server logs
└── backups/                # World backups
```

### Server Configuration Options

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `ram_mb` | integer | 1024 | Allocated RAM in megabytes |
| `port` | integer | 25565 | Server listening port |
| `gamemode` | string | survival | Default gamemode |
| `difficulty` | string | normal | World difficulty |
| `max-players` | integer | 20 | Maximum concurrent players |
| `pvp` | boolean | true | Player vs player combat |
| `online-mode` | boolean | true | Mojang authentication |
| `motd` | string | - | Server message of the day |

---

## Tunneling Services

Tunneling allows external players to connect to your Termux-hosted server.

### ngrok

Requires ngrok installation and authentication:

```bash
# Download ngrok for Android/ARM from ngrok.com
# Configure auth token
ngrok authtoken <your-token>
```

### Cloudflare Tunnel

```bash
pkg install cloudflared
```

### Pinggy

Uses SSH tunneling without additional installation:

```bash
pkg install openssh
```

### playit.gg

Requires proot-distro with Debian:

```bash
# Install proot-distro
pkg install proot-distro

# Install and configure Debian
proot-distro install debian
proot-distro login debian

# Inside Debian: follow playit.gg agent installation
```

---

## Security

MSM implements multiple security measures:

- **Input Sanitization**: All user inputs are validated against injection patterns
- **Shell Metacharacter Blocking**: Characters like `&`, `|`, `;`, `$` are filtered
- **Path Traversal Prevention**: Directory paths are validated against sensitive locations
- **Command Whitelisting**: Only approved commands are executed
- **Port Validation**: Network ports are validated within valid ranges (1-65535)
- **Subprocess Isolation**: Commands execute with `shell=False` to prevent injection

### Protected Paths

The following paths are blocked to prevent accidental damage:

```
/system, /proc, /sys, /dev
/data/system, /data/misc
/data/data (except Termux home)
```

---

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test modules
python -m tests.test_server_manager
python -m tests.test_server_manager_enhanced
python -m tests.test_tunnel_manager_enhanced
```

### Test Coverage

Tests cover:
- Server creation and lifecycle management
- PocketMine installation and startup
- Configuration menu interactions
- Tunnel manager port validation
- API client error handling

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/description`)
3. Implement changes with appropriate tests
4. Ensure all tests pass
5. Submit a pull request with detailed description

### Code Standards

- Follow PEP 8 style guidelines
- Include type hints for function signatures
- Document public methods with docstrings
- Handle exceptions with custom exception classes

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [PaperMC](https://papermc.io/) - Paper and Folia server software
- [PurpurMC](https://purpurmc.org/) - Purpur server software
- [FabricMC](https://fabricmc.net/) - Fabric mod loader
- [QuiltMC](https://quiltmc.org/) - Quilt mod loader
- [PocketMine-MP](https://pmmp.io/) - Bedrock Edition server
- [Termux](https://termux.dev/) - Android terminal emulator
