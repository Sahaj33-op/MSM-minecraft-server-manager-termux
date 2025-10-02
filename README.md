# 🚀 Minecraft Server Manager (MSM) v2 - Termux

<div align="center">

![MSM Logo](https://img.shields.io/badge/MSM-v5.2-brightgreen?style=forblue?style=for-the-badge&logo=python&logoColor-Compatible-black?style=for-the-badgeimg.shields.io/badge/License-MIT-yellow?style=/badge/Size-120KB-orange?style=for-the-badge) **The Ultimate Multi-Server Minecraft Manager for Termux**

**90+ Features -  7 Server Types -  Real-Time Monitoring -  SQLite Database -  Professional Logging**

[Features](#-features) -  [Installation](#-installation) -  [Usage](#-usage) -  [Supported Servers](#-supported-servers) -  [Screenshots](#-screenshots) -  [Contributing](#-contributing)

</div>

---

## 🎮 Overview

Enhanced Minecraft Server Manager (MSM) v2 is a **professional, enterprise-grade** command-line tool designed specifically for managing multiple Minecraft servers on Termux/Android devices. With support for **7 server flavors**, intelligent version management, **real-time performance monitoring**, **SQLite database tracking**, and a polished user interface, MSM transforms your mobile device into a powerful Minecraft hosting platform.

### 🌟 Key Highlights

- 🎯 **Multi-Server Management**: Unlimited servers with individual configurations
- 🎮 **7 Server Flavors**: Paper, Purpur, Folia, Vanilla, Fabric, Quilt, PocketMine-MP
- 📊 **Real-Time Monitoring**: CPU/RAM usage tracking with 24-hour statistics
- 💾 **SQLite Database**: Professional session and performance tracking
- 🔄 **Auto-Restart System**: Smart crash detection with restart limits
- 🌍 **World Manager**: Complete backup/restore with compression
- 📝 **Enhanced Logging**: Log rotation with 50MB limit and 30-day retention
- 🛡️ **Security Hardened**: Command injection prevention, input sanitization
- 🚀 **Performance Optimized**: G1GC tuning, threaded monitoring, connection pooling
- 📱 **Mobile-First**: Designed specifically for Termux with low resource footprint

## ✨ Features

### 🎯 Core Features

#### **📦 7 Server Types (5 Java + 1 Bedrock + 1 Modded)**
- **PaperMC** - High-performance fork with optimizations and extensive API
- **Purpur** - Feature-rich Paper fork with 200+ configuration options
- **Folia** - Revolutionary multi-threaded Paper for massive player counts
- **Vanilla** - Official unmodified Minecraft server from Mojang
- **Fabric** 🆕 - Lightweight modding platform with excellent performance
- **Quilt** 🆕 - Modern Fabric fork with enhanced compatibility
- **PocketMine-MP** - High-performance Bedrock Edition server (PHP-based)

#### **🔄 Advanced Version Management**
- Paginated version browsing (15 versions per page)
- Snapshot/pre-release toggle with 📷 indicator
- Automatic latest version detection
- Build number tracking for Paper/Purpur/Folia
- SHA256/SHA1 integrity verification
- Download retry with exponential backoff (5 attempts)
- Connection pooling for faster downloads

#### **📊 Real-Time Performance Monitoring** 🆕
- CPU usage tracking per server
- RAM usage monitoring with MB precision
- Process monitoring via `psutil` with oneshot optimization
- 60-second interval metrics logging to SQLite
- 24-hour performance graphs and statistics
- Session history with crash/restart counts
- Player count tracking (future feature)

#### **💾 SQLite Database System** 🆕
- **4 Comprehensive Tables**:
  1. `server_sessions` - Runtime tracking with uptime/crashes
  2. `performance_metrics` - CPU/RAM/player metrics
  3. `backup_history` - Backup tracking with compression ratios
  4. `error_log` - Error tracking with stack traces
- Professional `DatabaseManager` class with context managers
- Thread-safe operations with proper connection handling
- Automatic schema creation and migration

#### **🛡️ Reliability & Error Handling**
- Enhanced HTTP session with retry strategies
- Automatic retry on 429, 500, 502, 503, 504 status codes
- Exponential backoff (1s → 2s → 4s → 8s → 16s)
- Timeout protection (15s connect, 45s read)
- File integrity verification (SHA256/SHA1)
- Comprehensive try-except coverage throughout
- Graceful degradation on failures
- Signal handling (SIGINT, SIGTERM) for clean exits

#### **📝 Enhanced Logging System** 🆕
- `EnhancedLogger` class with professional features
- Log rotation (50MB max file size, 30-day retention)
- 6 log levels: DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL
- Dual output (file + console) with color coding
- Thread-safe logging with proper locking
- Timestamp formatting: `YYYY-MM-DD HH:MM:SS`
- Log file location: `~/.config/msm/msm.log`

#### **📱 Mobile-Optimized Design**
- Low memory footprint (< 50MB when idle)
- Efficient resource usage with context managers
- Screen session management for background running
- Java version auto-detection (8, 17, 21)
- Automatic dependency installation via pkg
- Works on devices with 2GB+ RAM

### 🔧 Advanced Features

#### **🧠 Smart RAM Allocation**
- Automatic system memory detection via `psutil`
- Calculates safe maximum (75% of available RAM)
- Suggests optimal allocation based on server type
- Prevents OOM crashes with safety margins
- Displays total, available, and safe RAM in UI

#### **🎛️ Comprehensive Configuration**
- RAM allocation per server
- Port configuration (Java: 25565, Bedrock: 19132)
- Auto-restart toggle with smart restart limits
- MOTD (Message of the Day) customization
- Max players configuration
- Difficulty settings
- View distance settings
- Multi-server JSON config in `~/.config/msm/config.json`

#### **🌍 World Backup & Restore**
- ZIP compression with DEFLATED algorithm
- Timestamp naming: `world_backup_YYYYMMDD_HHMMSS.zip`
- Multi-dimension support (world, nether, end)
- Backup listing with file sizes
- One-click restore with confirmation
- Backup deletion with "type DELETE" safety
- Pre-backup disk space checking (1GB minimum)

#### **📈 Statistics Dashboard** 🆕
- Total server sessions count
- Total uptime formatted (X days, Y hours, Z minutes)
- Average session duration
- Total crash count
- Total restart count
- 24-hour average RAM usage (MB)
- 24-hour average CPU usage (%)
- 24-hour peak player count

#### **🔒 Security Features**
- Input sanitization with regex validation
- Path traversal prevention (blocks `../`, absolute paths)
- Command injection prevention (shell=False everywhere)
- Length limits (255 chars for filenames)
- UUID fallback for invalid names
- No shell=True usage (secure subprocess calls)
- ALLOWED_FILENAME_CHARS regex pattern

#### **🚀 Performance Optimizations**
- Java G1GC tuning with optimized arguments
- `-XX:+UseG1GC -XX:+ParallelRefProcEnabled`
- `-XX:MaxGCPauseMillis=200` for reduced lag
- Connection pooling (max 20 connections)
- Session reuse for HTTP requests
- Efficient ZIP compression
- Threaded monitoring (daemon threads)
- `psutil.oneshot()` for performance sampling

## 📋 Requirements

### Minimum Requirements
- Android device with Termux installed
- Python 3.7 or higher
- Internet connection for downloads
- **2GB RAM** (4GB+ recommended)
- **1GB free storage** (3GB+ recommended)
- ARMv7/ARMv8 or x86_64 architecture

### Recommended Requirements
- Android 8.0+ (for better stability)
- 4GB+ RAM
- 3GB+ free storage
- Stable WiFi connection (for downloads)

### Software Dependencies (Auto-installed)
- `python` (3.7+)
- `wget` (for downloading servers)
- `curl` (for API requests)
- `screen` (for background server running)
- `tar` (for backup compression)
- `openjdk-17` or `openjdk-21` (for Java servers)
- Python packages: `requests`, `psutil`

## 🚀 Installation

### Method 1: Quick Install (Recommended)

```bash
# 1. Update and upgrade Termux
pkg update && pkg upgrade -y

# 2. Install Python and Git
pkg install python git -y

# 3. Clone the repository
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

# 4. Install dependencies
pip install requests psutil
pkg install openjdk-17 -y
pkg install openjdk-21 -y

# 5. Make executable
chmod +x msm.py

# 6. Run MSM
python3 msm.py
```

### Method 2: Manual Installation

1. **Install Termux** from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended) or Google Play Store

2. **Install required packages**:
   ```bash
   pkg update && pkg upgrade -y
   pkg install python wget curl screen tar openjdk-17 -y
   ```

3. **Download MSM**:
   ```bash
   wget https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/msm.py
   chmod +x msm.py
   pip install requests psutil
   ```

4. **Verify installation**:
   ```bash
   python3 -m py_compile msm.py  # Check for syntax errors
   python3 msm.py --version       # Show version info
   ```

### Method 3: One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/install.sh | bash
```

## 📖 Usage

### Starting MSM

```bash
# Standard start
python3 msm.py

# Or if made executable
./msm.py

# Run in background
screen -dmS msm python3 msm.py
```

### Main Menu Overview

```
═══════════════════════════════════════════════════════════════════
         Enhanced Minecraft Server Manager v2
   Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine
═══════════════════════════════════════════════════════════════════

System Info: 4096MB RAM | 4 CPUs (15% usage) | Android

Current Server: survival
Flavor: PaperMC 1.20.4-build 496
Status: Server [ONLINE] ✅

Main Menu:
  1. 🚀 Start Server
  2. ⏹️  Stop Server
  3. 📦 Install/Update Server
  4. ⚙️  Configure Server
  5. 💻 Server Console
  6. 🌍 World Manager
  7. 📊 Statistics
  8. ➕ Create New Server
  9. 🔄 Switch Server
  0. 🚪 Exit

Choose option (1-9, 0):
```

### Menu Options Explained

#### **1. 🚀 Start Server**
- Launches server with optimized Java arguments
- Creates screen session: `mc_<servername>`
- Starts performance monitoring thread
- Logs session start to database
- Shows "Server started successfully!" message
- **Usage**: Detach with Ctrl+A then D

#### **2. ⏹️ Stop Server**
- Sends graceful shutdown command (`/stop`)
- Waits 10 seconds for clean shutdown
- Terminates screen session
- Logs session end to database
- Stops monitoring threads

#### **3. 📦 Install/Update Server**
- Select from 7 server flavors
- Browse versions (15 per page)
- Navigate: `n`/`next`, `p`/`prev`
- Toggle snapshots: `s`/`snap`
- Quick latest: `latest`
- Downloads with progress bar
- Verifies file integrity (SHA256/SHA1)
- Auto-accepts EULA

#### **4. ⚙️ Configure Server**
Interactive wizard to modify:
- RAM allocation (512MB - Max safe RAM)
- Port (1024-65535)
- Auto-restart (on/off)
- MOTD (Message of the Day)
- Max players (1-999)
- Saves to JSON config

#### **5. 💻 Server Console**
- Attaches to screen session
- Full console access
- Execute commands
- View live logs
- **Detach**: Ctrl+A then D
- **Kill session**: Ctrl+C (not recommended)

#### **6. 🌍 World Manager**
Submenu options:
- **Create Backup**: ZIP all world dimensions
- **List Backups**: Show all backups with sizes
- **Restore Backup**: Overwrite current world
- **Delete Backup**: Remove backup file
- **Return**: Back to main menu

#### **7. 📊 Statistics** 🆕
Displays comprehensive stats:
- Total sessions: X
- Total uptime: X days, Y hours, Z minutes
- Average session: X minutes
- Total crashes: X | Total restarts: Y
- 24h Avg RAM: X MB | 24h Avg CPU: Y%
- 24h Peak Players: Z

#### **8. ➕ Create New Server**
- Enter server name (alphanumeric, -, _)
- Creates directory: `~/minecraft-<name>/`
- Initializes config
- Automatically switches to new server

#### **9. 🔄 Switch Server**
- Lists all configured servers
- Shows flavor and version
- Select number to switch
- Updates current_server in config

#### **0. 🚪 Exit**
- Gracefully closes MSM
- Saves configuration
- Stops monitoring threads
- Returns to shell

### Quick Start Guide

#### First-Time Setup

```bash
# 1. Start MSM
python3 msm.py

# 2. Create your first server
# Choose option: 8 (Create New Server)
# Enter name: survival

# 3. Install a server
# Choose option: 3 (Install/Update Server)
# Select: 1 (PaperMC)
# Choose version: latest

# 4. Configure RAM (optional)
# Choose option: 4 (Configure Server)
# Set RAM: 2048 (for 2GB)

# 5. Start the server
# Choose option: 1 (Start Server)
# Wait 30-60 seconds for first-time setup

# 6. Access console
# Choose option: 5 (Server Console)
# Server ready when you see "Done!"
# Detach: Ctrl+A then D

# 7. Get your server IP
# In console, type: /whitelist add YourMinecraftName
# Connect from Minecraft: <your-phone-IP>:25565
```

#### Daily Operations

```bash
# Start server
Option 1 → Wait for "SUCCESS" message

# Stop server (before closing Termux)
Option 2 → Wait for "Server stopped successfully"

# Create backup before updates
Option 6 → 1 (Create Backup)

# Update server
Option 3 → Select flavor → Choose newer version → Confirm

# View performance
Option 7 → Check RAM/CPU usage and uptime
```

### Advanced Usage

#### **Managing Multiple Servers**

```bash
# Scenario: Run survival (Java) and creative (Bedrock) servers

# 1. Create survival server (Port 25565)
Option 8 → Name: survival

# 2. Install PaperMC
Option 3 → 1 (PaperMC) → latest

# 3. Configure survival
Option 4 → RAM: 2048, Port: 25565, MOTD: "Survival World"

# 4. Create creative server (Port 19132)
Option 8 → Name: creative

# 5. Install PocketMine
Option 3 → 7 (PocketMine-MP) → latest

# 6. Configure creative
Option 4 → RAM: 1024, Port: 19132, MOTD: "Creative Build"

# 7. Start both servers
Option 9 → Select survival → Option 1 (Start)
Option 9 → Select creative → Option 1 (Start)

# 8. Check both are running
screen -ls  # Should show mc_survival and mc_creative
```

#### **World Backup Rotation Strategy**

```bash
# Daily backup workflow
1. Option 6 (World Manager)
2. Option 1 (Create Backup)
   - Creates: world_backup_20251002_160000.zip
3. Keep last 7 backups, delete older ones:
   Option 4 (Delete Backup) → Select old backups

# Before major updates
1. Create backup
2. Option 3 (Install/Update Server) → Update
3. Test new version
4. If issues: Option 6 → 3 (Restore) → Select backup
```

#### **Performance Monitoring**

```bash
# Check real-time stats
Option 7 (Statistics)

# View detailed logs
tail -f ~/.config/msm/msm.log

# Monitor database directly
sqlite3 ~/.config/msm/msm.db
sqlite> SELECT * FROM performance_metrics ORDER BY timestamp DESC LIMIT 10;

# Check system resources
htop  # Install: pkg install htop
```

## 🎮 Supported Servers

### Java Edition Servers

| Server | Version | Performance | Plugins | Mods | Best For |
|--------|---------|-------------|---------|------|----------|
| **Paper** | 1.8-1.21+ | ⭐⭐⭐⭐⭐ | ✅ Bukkit/Spigot | ❌ | Survival, minigames |
| **Purpur** | 1.14-1.21+ | ⭐⭐⭐⭐ | ✅ Bukkit/Spigot | ❌ | Feature-rich servers |
| **Folia** | 1.19.4-1.21+ | ⭐⭐⭐⭐⭐ | ⚠️ Limited | ❌ | 100+ players |
| **Vanilla** | All versions | ⭐⭐⭐ | ❌ | ❌ | Pure Minecraft |
| **Fabric** 🆕 | 1.14-1.21+ | ⭐⭐⭐⭐ | ❌ | ✅ Fabric mods | Modded survival |
| **Quilt** 🆕 | 1.18-1.21+ | ⭐⭐⭐⭐ | ❌ | ✅ Quilt/Fabric | Modern modpacks |

### Bedrock Edition

| Server | Version | Performance | Plugins | Best For |
|--------|---------|-------------|---------|----------|
| **PocketMine-MP** | 1.20+ | ⭐⭐⭐⭐ | ✅ PocketMine | Mobile players |

### Feature Comparison

| Feature | Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PM-MP |
|---------|-------|--------|-------|---------|--------|-------|-------|
| **Plugin Support** | ✅ Full | ✅ Full | ⚠️ Limited | ❌ None | ❌ None | ❌ None | ✅ Full |
| **Mod Support** | ❌ | ❌ | ❌ | ❌ | ✅ Yes | ✅ Yes | ❌ |
| **Performance** | Excellent | Very Good | Outstanding | Good | Very Good | Very Good | Excellent |
| **Memory Usage** | Low | Medium | Low | High | Low | Low | Very Low |
| **Config Options** | Many | 200+ | Many | Few | Many | Many | Many |
| **Update Frequency** | Daily | Daily | Weekly | Official | Daily | Weekly | Weekly |
| **Stability** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### Recommended Server by Use Case

- **🏆 Best Overall**: PaperMC - Excellent performance + plugin support
- **🎨 Most Features**: Purpur - 200+ config options for customization
- **👥 Large Scale**: Folia - Revolutionary multi-threading for 100+ players
- **🔧 Modded**: Fabric/Quilt - Lightweight modding platforms
- **📱 Bedrock**: PocketMine-MP - For mobile/console cross-play
- **🎯 Pure Vanilla**: Vanilla - Official unmodified experience

## ⚙️ Configuration

### Configuration File

MSM stores settings in `~/.config/msm/config.json`:

```json
{
    "servers": {
        "survival": {
            "server_flavor": "paper",
            "server_version": "1.20.4",
            "server_build": 496,
            "ram_mb": 2048,
            "auto_restart": true,
            "auto_restart_delay": 5,
            "server_settings": {
                "motd": "§6Survival Server §7- §aWelcome!",
                "port": 25565,
                "max-players": 20,
                "difficulty": "normal",
                "view-distance": 10,
                "pvp": true,
                "online-mode": true,
                "white-list": false
            }
        },
        "creative": {
            "server_flavor": "purpur",
            "server_version": "1.20.4",
            "server_build": 2100,
            "ram_mb": 1024,
            "auto_restart": false,
            "server_settings": {
                "motd": "§bCreative Build Server",
                "port": 25566,
                "max-players": 10,
                "difficulty": "peaceful",
                "gamemode": "creative"
            }
        }
    },
    "current_server": "survival",
    "global_settings": {
        "check_updates": true,
        "log_level": "INFO",
        "backup_retention_days": 30
    }
}
```

### Database Schema

SQLite database at `~/.config/msm/msm.db`:

```sql
-- Server sessions table
CREATE TABLE server_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration INTEGER,
    peak_players INTEGER DEFAULT 0,
    crash_count INTEGER DEFAULT 0,
    restart_count INTEGER DEFAULT 0,
    ram_usage_avg REAL,
    cpu_usage_avg REAL
);

-- Performance metrics table
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ram_usage REAL,
    cpu_usage REAL,
    player_count INTEGER DEFAULT 0,
    tps REAL,
    mspt REAL
);

-- Backup history table
CREATE TABLE backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    backup_size INTEGER,
    compressed_size INTEGER,
    created_at TEXT NOT NULL,
    backup_type TEXT DEFAULT 'manual'
);

-- Error log table
CREATE TABLE error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    severity TEXT DEFAULT 'ERROR'
);
```

## 📁 File Structure

Complete directory layout:

```
~/
├── .config/msm/                    # MSM configuration directory
│   ├── config.json                 # Multi-server configuration
│   ├── msm.db                      # SQLite database (statistics)
│   └── msm.log                     # Rotating log file (50MB max)
│
├── minecraft-survival/             # Server files for "survival"
│   ├── server.jar                  # PaperMC server JAR
│   ├── eula.txt                    # EULA agreement (auto-accepted)
│   ├── server.properties           # Server configuration
│   ├── bukkit.yml                  # Bukkit settings (if applicable)
│   ├── spigot.yml                  # Spigot settings (if applicable)
│   ├── paper.yml                   # Paper settings (if applicable)
│   ├── config/                     # Paper configuration directory
│   ├── plugins/                    # Bukkit/Spigot plugins
│   ├── world/                      # Overworld dimension
│   ├── world_nether/               # Nether dimension
│   ├── world_the_end/              # End dimension
│   ├── logs/                       # Server logs
│   │   └── latest.log              # Current session log
│   └── backups/                    # World backups
│       ├── world_backup_20251002_120000.zip
│       └── world_backup_20251001_180000.zip
│
└── minecraft-creative/             # Server files for "creative"
    ├── server.jar                  # Purpur server JAR
    ├── eula.txt
    ├── server.properties
    ├── purpur.yml                  # Purpur-specific settings
    ├── world/
    ├── logs/
    └── backups/
```

### Log File Format

Example `msm.log` entries:

```
2025-10-02 16:30:15 [INFO] Starting Minecraft Server Manager v5.2
2025-10-02 16:30:16 [INFO] Checking system dependencies...
2025-10-02 16:30:16 [DEBUG] wget found at /data/data/com.termux/files/usr/bin/wget
2025-10-02 16:30:17 [SUCCESS] All essential dependencies are installed.
2025-10-02 16:30:20 [INFO] Loaded configuration for server: survival
2025-10-02 16:30:25 [INFO] Starting server 'survival' (PaperMC 1.20.4)
2025-10-02 16:30:26 [DEBUG] Java 17 found, required: 17
2025-10-02 16:30:27 [INFO] Server started in screen session: mc_survival
2025-10-02 16:30:29 [SUCCESS] Server 'survival' started successfully!
2025-10-02 16:31:30 [DEBUG] Performance: RAM=1847MB, CPU=23%, Players=0
```

## 🔍 Troubleshooting

### Common Issues & Solutions

#### **Server won't start**

**Symptoms**: Error message after selecting "Start Server"

**Solutions**:
```bash
# 1. Check available RAM
free -m
# Need at least 512MB free

# 2. Verify Java installation
java -version
# Should show Java 17 or 21

# 3. Check if port is in use
netstat -tuln | grep 25565
# If occupied, change port in Configure Server

# 4. View detailed logs
tail -n 50 ~/.config/msm/msm.log

# 5. Attach to screen to see server console
screen -r mc_<servername>
```

#### **Download failures**

**Symptoms**: "Download failed" or timeout errors

**Solutions**:
```bash
# 1. Check internet connection
ping -c 4 8.8.8.8

# 2. Try different server flavor
# Paper → try Vanilla instead

# 3. Clear cache
rm -rf /data/data/com.termux/files/usr/tmp/*

# 4. Increase timeout (edit msm.py)
DOWNLOAD_TIMEOUT = 1800  # 30 minutes instead of 15

# 5. Use mobile data instead of WiFi
# Or vice versa
```

#### **Permission denied**

**Symptoms**: `Permission denied` when running script

**Solutions**:
```bash
# Make script executable
chmod +x msm.py

# Check file ownership
ls -l msm.py
# Should show your username

# If needed, take ownership
chown $USER:$USER msm.py

# Run with explicit Python
python3 msm.py
```

#### **Java version issues**

**Symptoms**: "Required Java X not installed"

**Solutions**:
```bash
# 1. Check installed Java versions
ls /data/data/com.termux/files/usr/lib/jvm/

# 2. Install required version
pkg install openjdk-17  # For Minecraft 1.17+
pkg install openjdk-8   # For Minecraft 1.12-1.16

# 3. MSM auto-detects, but you can verify
java -version

# 4. For Minecraft 1.20.5+, Java 21 is ideal
pkg install openjdk-21
```

#### **Database errors**

**Symptoms**: "Database locked" or statistics not showing

**Solutions**:
```bash
# 1. Check database integrity
sqlite3 ~/.config/msm/msm.db "PRAGMA integrity_check;"
# Should output: ok

# 2. Backup and rebuild database
mv ~/.config/msm/msm.db ~/.config/msm/msm.db.backup
# MSM will create new database on next start

# 3. Check file permissions
ls -l ~/.config/msm/msm.db
chmod 644 ~/.config/msm/msm.db
```

#### **Screen session issues**

**Symptoms**: Can't attach to console or session not found

**Solutions**:
```bash
# 1. List all screen sessions
screen -ls

# 2. Kill zombie sessions
screen -wipe

# 3. Create new session manually
screen -dmS mc_test

# 4. If screen isn't installed
pkg install screen

# 5. Reattach to detached session
screen -r mc_<servername>
```

#### **Out of Memory (OOM)**

**Symptoms**: Server crashes with "Out of memory" or device freezes

**Solutions**:
```bash
# 1. Check current RAM allocation
Option 4 → View current RAM setting

# 2. Reduce RAM allocation
# If set to 3000MB, try 2048MB or 1536MB

# 3. Close other apps
# Free up RAM before starting server

# 4. Check system RAM
free -m
# Available should be > allocated + 500MB

# 5. Use swap file (advanced)
# Create 2GB swap on external SD card
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Edit msm.py
nano msm.py

# Find and change (near top of file)
LOG_LEVEL = "INFO"
# Change to:
LOG_LEVEL = "DEBUG"

# Save and run
python3 msm.py

# View debug logs
tail -f ~/.config/msm/msm.log | grep DEBUG
```

### Getting Help

If issues persist:

1. **Check logs first**:
   ```bash
   tail -n 100 ~/.config/msm/msm.log
   ```

2. **Capture error output**:
   ```bash
   python3 msm.py 2>&1 | tee msm_error.log
   ```

3. **System information**:
   ```bash
   # Create debug report
   echo "=== System Info ===" > debug_report.txt
   uname -a >> debug_report.txt
   free -m >> debug_report.txt
   df -h >> debug_report.txt
   python3 --version >> debug_report.txt
   java -version 2>> debug_report.txt
   echo "=== MSM Log ===" >> debug_report.txt
   tail -n 50 ~/.config/msm/msm.log >> debug_report.txt
   ```

4. **Open GitHub Issue** with debug_report.txt attached

## 📊 Screenshots

### Main Menu
```
═══════════════════════════════════════════════════════════════════
         Enhanced Minecraft Server Manager v5.2
   Paper | Purpur | Folia | Vanilla | Fabric | Quilt | PocketMine
═══════════════════════════════════════════════════════════════════

System: 4096MB RAM (2340MB free) | 8 CPUs (12%) | Android 12
```

### Statistics Dashboard
```
╔═══════════════════════════════════════════════════════════════╗
║              Server Statistics - survival                      ║
╚═══════════════════════════════════════════════════════════════╝

Total Sessions: 47
Total Uptime: 12 days, 8 hours, 34 minutes
Average Session: 6 hours, 15 minutes

Total Crashes: 2
Total Restarts: 5

24-Hour Performance:
  Average RAM Usage: 1847 MB
  Average CPU Usage: 18%
  Peak Players: 8
```

### Version Selection
```
Available PaperMC Versions (Page 1/8):
─────────────────────────────────────────────────────────────────
1. 1.20.4 - Build 496 (Latest)
2. 1.20.4 - Build 495
3. 1.20.4 - Build 494
...
15. 1.20.2 - Build 318

Navigation: [n]ext, [p]rev, [s]napshots, [latest], or number
```

## 🤝 Contributing

Contributions are welcome! Whether it's bug reports, feature requests, or code contributions, we appreciate your help.

### How to Contribute

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub
   git clone https://github.com/YOUR_USERNAME/MSM-minecraft-server-manager-termux.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/AmazingFeature
   ```

3. **Make your changes**
   - Follow PEP 8 style guide
   - Add comments for complex logic
   - Update documentation if needed

4. **Test on Termux**
   ```bash
   python3 -m py_compile msm.py  # Check syntax
   python3 msm.py                 # Test functionality
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m 'Add some AmazingFeature'
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/AmazingFeature
   ```

7. **Open a Pull Request**
   - Go to GitHub and click "New Pull Request"
   - Describe your changes clearly

### Development Guidelines

- **Code Style**: Follow PEP 8 (max 100 chars/line)
- **Comments**: Explain "why", not "what"
- **Testing**: Test on actual Termux device (ARMv7/v8)
- **Documentation**: Update README for new features
- **Commits**: Use meaningful commit messages
- **Backwards Compatibility**: Don't break existing configs

### Areas Needing Help

- 🌐 Translations (i18n)
- 📝 Documentation improvements
- 🐛 Bug fixes
- 🎨 UI enhancements
- 🚀 Performance optimizations
- 🧪 Unit tests

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Sahaj33

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

## 🙏 Acknowledgments

Special thanks to:

- **[PaperMC Team](https://papermc.io/)** - For the excellent Paper, Folia, and API
- **[Purpur Team](https://purpurmc.org/)** - For the feature-rich Purpur fork
- **[Fabric Team](https://fabricmc.net/)** - For the lightweight modding platform
- **[Quilt Team](https://quiltmc.org/)** - For the modern modding framework
- **[PocketMine Team](https://pmmp.io/)** - For PHP Bedrock server software
- **[Mojang Studios](https://minecraft.net/)** - For creating Minecraft
- **[Termux Team](https://termux.com/)** - For making Linux on Android possible
- **All Contributors** - For bug reports, feature suggestions, and code contributions

### Built With

- [Python 3](https://python.org/) - Programming language
- [Requests](https://requests.readthedocs.io/) - HTTP library
- [psutil](https://github.com/giampaolo/psutil) - System monitoring
- [SQLite](https://sqlite.org/) - Database engine
- Love ❤️ and lots of ☕

## 📞 Support & Community

### Get Help

- **📖 Documentation**: [Wiki](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/wiki)
- **🐛 Bug Reports**: [GitHub Issues](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/issues)
- **💬 Discussions**: [GitHub Discussions](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/discussions)
- **❓ FAQ**: [Frequently Asked Questions](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/wiki/FAQ)

### Stay Updated

- ⭐ Star this repository for updates
- 👀 Watch for new releases
- 🍴 Fork to contribute

---

<div align="center">

**🎮 Made with ❤️ for the Minecraft Community 🎮**

![Minecraft](https://img.shields.io/badge/Minecraft-Server_Manager-green?style=flat-square&logo=minecraft&logo/badge/Android-Termux-black?style=flat-square&logo_Ready-brightgreen?style=flat/github/downloads/sahaj33-op/MSM-minecraft-server-manager-termux/total?style/github/stars/sahaj33-op/MSM-minecraft-server-manager-termux?styled-minecraft-server-manager-msm-v52---termux)

</div>
