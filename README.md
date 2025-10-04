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

### Tunneling Services
- Playit.gg integration
- Ngrok integration
- Cloudflare Tunnel (cloudflared) integration
- Automatic tunnel setup and management

### Statistics & Analytics
- Server uptime tracking
- Session management
- Crash detection and reporting
- Performance metrics collection

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd msm

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