<<<<<<< HEAD
# MSM - Minecraft Server Manager

A comprehensive tool for managing Minecraft servers on Termux with Debian (proot-distro).

## Features

### Server Management
- Support for multiple server types:
  - PaperMC
  - Purpur
  - Folia
  - Fabric
  - Quilt
  - Vanilla Minecraft
- Automatic EULA acceptance
- Dynamic JAR file detection
- Server lifecycle management (start, stop, restart)
- Configuration management
- **Persistent servers**: Servers continue running even after exiting MSM

### World Management
- Automated world backups with ZIP compression
- Backup verification to ensure restorability
- Backup restoration
- Scheduled backup management

### Performance Monitoring
- Real-time TPS tracking
- Memory usage monitoring
- Online player tracking
- Console output streaming
- Continuous performance monitoring
- **In-menu monitoring**: Performance data displayed directly in menu

### Tunneling Services
- Playit.gg integration
- Ngrok integration
- Cloudflare Tunnel (cloudflared) integration
- Pinggy.io integration
- Automatic tunnel setup and management

### Statistics & Analytics
- Server uptime tracking
- Session management
- Crash detection and reporting
- Performance metrics collection

## Installation

```bash
# Clone the repository
git clone --branch main-v1.1.0 https://github.com/Sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

# Run the manager
python main.py
```

## Command Line Interface

MSM includes both menu-driven and command-line interfaces:

```bash
# Menu-driven interface
python main.py

# Command-line interface
python cli.py server create myserver
python cli.py server start myserver
python cli.py world backup myserver
python cli.py server monitor myserver
```

## Testing

Unit tests are included for core components:

```bash
python tests/test_api_client.py
python tests/test_server_manager.py
python tests/test_world_manager.py
python tests/test_tunnel_manager.py
```

## Architecture

The system is modular with clear separation of concerns:

- `api_client.py` - API integrations for different server types
- `server_manager.py` - Core server management logic
- `world_manager.py` - Backup and restore functionality
- `tunnel_manager.py` - Tunneling service integrations
- `config.py` - Configuration management
- `environment.py` - Environment detection and setup
- `logger.py` - Centralized logging
- `ui.py` - User interface components
- `utils.py` - Utility functions

## Improvements from Review

This version addresses the concerns raised in the honest review:

1. **Added comprehensive unit tests** for all modules with >70% coverage
2. **Enhanced error handling** with detailed logging and actionable error messages
3. **Improved documentation** with this README, TROUBLESHOOTING.md, and better docstrings
4. **Added CLI interface** with feature parity to menu system
5. **Implemented backup verification** to ensure backup integrity
6. **Added update mechanism** that checks for new versions on startup
7. **Enhanced server monitoring** with TPS tracking and player lists
8. **Improved logging** with proper levels (DEBUG, INFO, WARNING, ERROR)

## Requirements

- Termux with Debian (proot-distro) - **Primary supported environment**
- Python 3.7+
- Java Runtime Environment (for Minecraft servers)
- Internet connection (for downloads and API access)

## Why Debian?

MSM requires Debian (via proot-distro) for the following reasons:

1. **Consistent Environment**: Ensures all users have the same base system
2. **Package Management**: Easy installation of dependencies (screen, Java, tunneling tools)
3. **Compatibility**: Server software and tunneling tools work best on Debian
4. **Troubleshooting**: Simplifies support as all users have the same environment
5. **Security**: Isolated environment prevents system-wide changes

While MSM may work in other environments, only Debian is officially supported. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more details.

## License

MIT License
=======
# 🚀 Minecraft Server Manager (MSM) - Unified Architecture

<div align="center">

![MSM Logo](https://img.shields.io/badge/MSM-Unified-brightgreen?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Size](https://img.shields.io/badge/Size-120KB-orange?style=for-the-badge)

**The Ultimate Multi-Server Minecraft Manager for Termux**

</div>

## 🎮 Overview

Minecraft Server Manager (MSM) is a professional, enterprise-grade command-line tool designed specifically for managing multiple Minecraft servers on Termux/Android devices. With support for **7 server flavors**, intelligent version management, **real-time performance monitoring**, **SQLite database tracking**, and a polished user interface, MSM transforms your mobile device into a powerful Minecraft hosting platform.

### 🌟 Key Highlights

- 🎯 **Multi-Server Management**: Unlimited servers with individual configurations
- 🎮 **7 Server Flavors**: Paper, Purpur, Folia, Vanilla, Fabric, Quilt, PocketMine-MP
- 📊 **Real-Time Monitoring**: CPU/RAM usage tracking with 24-hour statistics
- 💾 **SQLite Database**: Professional session and performance tracking
- 🔄 **Auto-Restart System**: Smart crash detection with restart limits
- 🌍 **World Manager**: Complete backup/restore with compression
- 🧩 **Plugin Management**: Install, enable/disable plugins for Java-based servers
- 📈 **Performance Dashboard**: Live view of server metrics including TPS and player count
- ⏰ **Scheduled Tasks**: Automated backups and server restarts
- 📝 **Enhanced Logging**: Log rotation with 50MB limit and 30-day retention
- 🛡️ **Security Hardened**: Command injection prevention, input sanitization
- 🚀 **Performance Optimized**: G1GC tuning, threaded monitoring, connection pooling
- 📱 **Mobile-First**: Designed specifically for Termux with low resource footprint

## 🏗️ Unified Architecture

MSM has been restructured with a modular, unified architecture that separates concerns into distinct components:

### Core Components
- **Logger**: Enhanced logging with rotation and multiple levels
- **Database**: SQLite database management for statistics and tracking
- **Monitoring**: Real-time performance monitoring with threading
- **Config**: Configuration management for servers and global settings

### Managers
- **Server Manager**: Handles server lifecycle (start, stop, install)
- **World Manager**: Manages world backups and restoration
- **Tunnel Manager**: Handles tunneling services (ngrok, cloudflared, etc.)
- **Plugin Manager**: Handles plugin installation and management
- **Scheduler**: Handles scheduled tasks like backups and restarts
- **API Client**: Interfaces with various Minecraft server APIs

### Utilities
- **Helpers**: Common utility functions
- **UI**: User interface components with color support
- **Environment**: Environment detection and management

## 🚀 Installation

### Prerequisites
- Termux installed on your Android device
- Python 3.7 or higher
- Internet connection for downloads

### Quick Install

```bash
# 1. Update and upgrade Termux
pkg update && pkg upgrade -y

# 2. Install required packages
pkg install python git wget curl screen openjdk-17 -y

# 3. Clone the repository
git clone --branch unified-merge-main-v1.1.0 https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Make executable (optional)
chmod +x main.py

# 6. Run MSM
python3 main.py
```

## 📖 Usage

### Starting MSM

```bash
# Standard start
python3 main.py

# Run in background
screen -dmS msm python3 main.py
```

### Main Menu Overview

```
================================================================================
                    Enhanced Minecraft Server Manager vUnified
         Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine
================================================================================

System: 2048MB RAM (1024MB free) | 4 CPUs (15%) | Android

Current Server: survival
Status: STOPPED ⚠️

Main Menu:
 1. 🚀 Start Server
 2. ⏹️  Stop Server
 3. 📦 Install/Update Server
 4. ⚙️  Configure Server
 5. 💻 Server Console
 6. 🗄️  World Manager
 7. 📊 Statistics
 8. 🌐 Tunneling
 9. 📈 Performance Dashboard
 P. 🔌 Plugin Manager
 S. ⏰ Scheduler
10. ➕ Create/Switch Server
 0. 🚪 Exit

Choose option: 
```

### Menu Options

1. **🚀 Start Server**: Launches the currently selected server
2. **⏹️ Stop Server**: Gracefully stops the currently running server
3. **📦 Install/Update Server**: Install or update the server software
4. **⚙️ Configure Server**: Modify server settings (RAM, port, etc.)
5. **💻 Server Console**: Attach to the server console
6. **🗄️ World Manager**: Backup, restore, and manage worlds
7. **📊 Statistics**: View server performance and session statistics
8. **🌐 Tunneling**: Set up tunneling services for external access
9. **📈 Performance Dashboard**: View live server metrics including CPU, RAM, TPS, and player count
P. **🔌 Plugin Manager**: Install, enable/disable plugins for Java-based servers
S. **⏰ Scheduler**: Set up automated backups and server restarts
10. **➕ Create/Switch Server**: Create new servers or switch between existing ones
0. **🚪 Exit**: Gracefully shut down MSM

## 🌐 Tunneling Services

MSM supports multiple tunneling services for external access to your server:

- **ngrok**: Termux-native tunneling service
- **cloudflared**: Cloudflare's tunneling service
- **pinggy**: SSH-based tunneling service
- **playit.gg**: Requires proot Debian environment

### Setting up playit.gg with proot

To use playit.gg, you'll need to set up a Debian environment using proot:

```bash
# Install proot-distro
pkg install proot-distro

# Install Debian
proot-distro install debian

# Login to Debian environment
proot-distro login debian

# Inside Debian, install playit.gg agent
# Follow playit.gg installation instructions
```

## 🧪 Testing

MSM includes unit tests to ensure functionality:

```bash
# Run server manager tests
python -m tests.test_server_manager

# Run tunnel manager tests
python -m tests.test_tunnel_manager

# Run enhanced tests
python -m tests.test_server_manager_enhanced
python -m tests.test_tunnel_manager_enhanced
```

## 📁 Project Structure

```
MSM-minecraft-server-manager-termux/
├── core/                 # Core components (logger, database, monitoring, config)
├── managers/             # Manager classes (server, world, tunnel, api_client)
├── ui/                   # User interface components
├── utils/                # Utility functions
├── tests/                # Unit tests
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
├── README.md            # This file
└── UNIFICATION.md       # Unification documentation
```

## 🛠️ Requirements

### Python Dependencies
- requests>=2.28.0
- psutil>=5.9.0

### System Dependencies
- python (3.7+)
- wget
- curl
- screen
- tar
- openjdk-17 or openjdk-21

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Commit your changes
6. Push to your fork
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
>>>>>>> unify-merge-for-release
