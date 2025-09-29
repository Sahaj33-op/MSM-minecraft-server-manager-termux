# 🚀 Minecraft Server Manager (MSM) - Termux

<div align="center">

![MSM Logo](https://img.shields.io/badge/MSM-v1-brightgreen?style=for-the-badge&logo=minecraft&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.7+-blue?style=for-the-badge&logo=python&logoColor=white)
![Termux](https://img.shields.io/badge/Termux-Compatible-black?style=for-the-badge&logo=android&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**The Ultimate Multi-Flavor Minecraft Server Manager for Termux**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Supported Servers](#-supported-servers) • [Configuration](#-configuration) • [Contributing](#-contributing)

</div>

---

## 🎮 Overview

Enhanced Minecraft Server Manager (MSM) is a powerful, feature-rich command-line tool designed specifically for managing Minecraft servers on Termux/Android devices. With support for multiple server flavors, intelligent version management, and a user-friendly interface, MSM makes running Minecraft servers on mobile devices effortless.

### 🌟 Key Highlights

- **Multi-Flavor Support**: Seamlessly manage Paper, Purpur, Folia, Vanilla, and PocketMine-MP servers
- **Smart Version Management**: Paginated version selection with snapshot/pre-release filtering
- **Robust Error Handling**: Enhanced timeout management and retry mechanisms
- **Mobile-Optimized**: Designed specifically for Termux environments
- **User-Friendly**: Interactive menus with color-coded interface

## ✨ Features

### 🎯 Core Features

- **📦 Multiple Server Types**
  - PaperMC - High-performance with optimizations
  - Purpur - Feature-rich Paper fork
  - Folia - Multi-threaded regionized server
  - Vanilla - Official Mojang server
  - PocketMine-MP - Bedrock Edition support

- **🔄 Version Management**
  - Paginated version browsing (10 per page)
  - Snapshot/pre-release toggle
  - Automatic latest version detection
  - Build number tracking for Paper/Purpur/Folia

- **🛡️ Reliability**
  - Enhanced HTTP session management
  - Automatic retry on failures
  - Timeout protection
  - File integrity verification (SHA256/SHA1)

- **📱 Mobile-First Design**
  - Optimized for Termux
  - Low memory footprint
  - Efficient resource usage
  - Screen session management

### 🔧 Advanced Features

- **Smart RAM Allocation**: Automatically detects system memory and suggests safe limits
- **Dependency Management**: Auto-installs required packages
- **Configuration Persistence**: JSON-based configuration storage
- **EULA Handling**: Automatic EULA acceptance for Java servers
- **Multi-Port Support**: Java (25565) and Bedrock (19132) default ports

## 📋 Requirements

- Android device with Termux installed
- Python 3.7 or higher
- Internet connection for downloading servers
- Minimum 2GB RAM (4GB+ recommended)
- 1GB+ free storage space

## 🚀 Installation

### Quick Install

```bash
# 1. Update and upgrade termux
pkg update && pkg upgrade -y

# 2. Install Python and Git
pkg install python git -y

# 3. Clone the repository
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

# 4. Make the script executable
chmod +x msm.py

# 5. Install required dependencies
pip install -r requirements.txt

# 6. Run MSM
./msm.py
```

### Manual Installation

1. **Install Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended) or Google Play Store

2. **Install required packages**:
   ```bash
   pkg update && pkg upgrade -y
   pkg install python wget curl screen tar -y
   ```

3. **Download MSM**:
   ```bash
   wget https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/msm.py
   chmod +x msm.py
   ```

## 📖 Usage

### Starting MSM

```bash
./msm.py
```

### Main Menu Options

1. **Start Server** - Launch your Minecraft server
2. **Stop Server** - Gracefully shutdown the server
3. **Install/Change Server** - Install new or switch server types
4. **Configure Server** - Modify server settings
5. **Server Console** - Access the server console
6. **Exit** - Close MSM

### Installing a Server

1. Select "Install/Change Server" from the main menu
2. Choose your preferred server flavor:
   - Paper (Recommended for performance)
   - Purpur (For extra features)
   - Folia (For large player counts)
   - Vanilla (Official Minecraft)
   - PocketMine-MP (For Bedrock Edition)
3. Browse available versions using:
   - Number keys (1-10) to select a version
   - `n`/`next` for next page
   - `p`/`prev` for previous page
   - `s`/`snap` to toggle snapshots
   - `latest` to select the newest version
4. Confirm installation

### Managing the Server

- **Start**: Launches server in a screen session
- **Stop**: Sends stop command to running server
- **Console**: Attach to server console (Ctrl+A, D to detach)

## 🎮 Supported Servers

### Java Edition Servers

| Server | Description | Performance | Features |
|--------|-------------|-------------|----------|
| **Paper** | Performance-focused fork | ⭐⭐⭐⭐⭐ | Optimizations, API |
| **Purpur** | Feature-rich Paper fork | ⭐⭐⭐⭐ | Extra config options |
| **Folia** | Multi-threaded Paper | ⭐⭐⭐⭐⭐ | Massive scalability |
| **Vanilla** | Official Mojang server | ⭐⭐⭐ | Pure Minecraft |

### Bedrock Edition

| Server | Description | Performance | Features |
|--------|-------------|-------------|----------|
| **PocketMine-MP** | PHP-based BE server | ⭐⭐⭐⭐ | Plugin support |

## ⚙️ Configuration

MSM stores configuration in `~/.config/msm/config.json`:

```json
{
    "server_flavor": "paper",
    "server_version": "1.20.4",
    "ram_mb": 2048,
    "ngrok_authtoken": null,
    "auto_backup": true,
    "backup_interval_hours": 24,
    "max_backups": 5,
    "include_snapshots": false,
    "server_settings": {
        "motd": "A Minecraft Server",
        "difficulty": "normal",
        "max-players": 20,
        "view-distance": 10,
        "port": 25565
    }
}
```

## 🔍 Troubleshooting

### Common Issues

**Server won't start**
- Check available RAM: `free -m`
- Verify Java installation: `java -version`
- Check server logs: `screen -r mcserver`

**Download failures**
- Check internet connection
- Try different server flavor
- Clear cache and retry

**Permission denied**
- Run `chmod +x msm.py`
- Check file ownership

### Debug Mode

Enable debug logging by modifying the script:
```python
DEBUG_MODE = True  # Add at top of script
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add comments for complex logic
- Test on actual Termux environment
- Update README for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [PaperMC Team](https://papermc.io/) for their excellent server software
- [Termux](https://termux.com/) for making this possible on Android
- [Mojang](https://minecraft.net/) for creating Minecraft
- All server software maintainers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/issues)
- **Discussions**: [GitHub Discussions](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/discussions)
- **Wiki**: [Documentation Wiki](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/wiki)

---

<div align="center">

**Made with ❤️ for the Minecraft Community**

![Minecraft](https://img.shields.io/badge/Minecraft-Server_Manager-green?style=flat-square&logo=minecraft)
![Android](https://img.shields.io/badge/Android-Termux-black?style=flat-square&logo=android)

</div>
