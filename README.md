# MSM — Minecraft Server Manager for Termux

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%2F%20Android-green.svg)](https://termux.dev)
[![Version](https://img.shields.io/badge/Version-5.2-brightgreen.svg)](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/releases)

A Python TUI for running and managing Minecraft servers on Android via Termux. Supports 7 server flavors, multi-server configs, world backups, real-time monitoring, and SQLite session tracking — all from a menu-driven CLI built for low-end mobile hardware.

---

## What it does

- **Multi-server management** — create, configure, and switch between named server instances
- **7 server flavors** — Paper, Purpur, Folia, Vanilla, Fabric, Quilt, PocketMine-MP
- **Version browser** — paginated version selection with snapshot toggling
- **World backups** — ZIP-compressed backups with restore and delete
- **Session tracking** — SQLite database logs uptime, crashes, and restarts per server
- **Performance monitoring** — CPU and RAM sampled every 60 seconds via `psutil`
- **Auto-restart** — daemon thread watches screen session and relaunches on crash
- **Background running** — servers run inside GNU Screen sessions; MSM itself can be detached

---

## Requirements

**Device:**
- Android with [Termux](https://f-droid.org/packages/com.termux/) (install from F-Droid, not Play Store)
- 2 GB RAM minimum (4 GB recommended for Java servers)
- 1 GB free storage minimum

**Packages:**
```bash
pkg install python git wget screen openjdk-17 python-psutil -y
pip install requests
```

Java version per Minecraft version:
- Minecraft ≥ 1.21 → `openjdk-21`
- Minecraft 1.17–1.20 → `openjdk-17`
- Minecraft ≤ 1.16 → `openjdk-8`

PocketMine-MP requires PHP: `pkg install php -y`

---

## Installation

```bash
pkg update && pkg upgrade -y
pkg install python git wget screen openjdk-17 python-psutil -y
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux
pip install requests
chmod +x msm.py
python3 msm.py
```

Or use the installer script:

```bash
bash install.sh
```

---

## Usage

```bash
python3 msm.py
```

**First run:**
1. Option `8` — Create a new server (e.g., `survival`)
2. Option `3` — Install a server flavor and version
3. Option `4` — Configure RAM, port, MOTD (optional)
4. Option `1` — Start the server

**Console access:** Option `5` attaches to the GNU Screen session.  
Detach with `Ctrl+A` then `D`. Do not use `Ctrl+C` — that kills the server.

**Running multiple servers:** Each server gets its own screen session (`mc_<name>`). Create separate servers via Option `8`, configure different ports, start independently via Option `9` to switch + Option `1` to start.

---

## Data layout

```
~/.config/msm/
├── config.json       # Server configurations
├── msm.db            # SQLite: sessions, metrics, backups, errors
└── msm.log           # Rotating log (50 MB max, 30-day retention)

~/minecraft-<name>/
├── server.jar        # Server binary
├── eula.txt          # Auto-accepted
├── server.properties
├── world/            # Overworld
├── world_nether/
├── world_the_end/
└── backups/
    └── world_backup_YYYYMMDD_HHMMSS.zip
```

---

## Config reference

`~/.config/msm/config.json`:

```json
{
    "servers": {
        "survival": {
            "server_flavor": "paper",
            "server_version": "1.20.4",
            "server_build": 496,
            "ram_mb": 2048,
            "auto_restart": true,
            "server_settings": {
                "motd": "Survival Server",
                "port": 25565,
                "max-players": 20,
                "difficulty": "normal",
                "view-distance": 10
            }
        }
    },
    "current_server": "survival"
}
```

---

## Server flavors

| Flavor | Type | API Source | Notes |
|--------|------|------------|-------|
| Paper | Java | papermc.io | Best all-around; Bukkit/Spigot plugins |
| Purpur | Java | purpurmc.org | Paper fork with extra config knobs |
| Folia | Java | papermc.io | Multi-threaded; limited plugin support |
| Vanilla | Java | Mojang manifest | No plugins, no mods |
| Fabric | Java | fabricmc.net | Mod support; downloads server launcher JAR |
| Quilt | Java | quiltmc.org | Fabric-compatible mod loader |
| PocketMine-MP | PHP | GitHub releases | Bedrock edition; port 19132 |

---

## Known issues

- **Quilt download URL** — the installer version is hardcoded to `0.0.0` in the download path; some Quilt versions may fail. Workaround: install manually into the server directory.
- **PID discovery** — screen session PID is extracted via regex from `screen -ls` output. If Termux's screen version formats output differently, the monitoring thread won't attach (server still runs fine).
- **Auto-restart race condition** — the restart thread checks every 15 seconds; a manual stop followed by a quick restart may trigger an unintended relaunch before the stop event propagates.
- **PocketMine startup** — MSM launches PHAR files with the system `php` binary. If PHP isn't in PATH or the PHAR filename changed upstream, startup will fail silently.
- **SIGALRM on hardened kernels** — some Android ROMs with restrictive seccomp profiles block `SIGALRM`. If your server crashes immediately on start, check `dmesg` for seccomp denials.

---

## Troubleshooting

**Server won't start:**
```bash
# Check Java
java -version

# Check screen sessions
screen -ls

# Read logs
tail -50 ~/.config/msm/msm.log

# Attach directly to see server output
screen -r mc_<servername>
```

**Download fails:**
```bash
# Verify connectivity
ping -c 4 8.8.8.8

# Try wget manually
wget -O /tmp/test.jar "https://api.papermc.io/..."
```

**Database errors:**
```bash
sqlite3 ~/.config/msm/msm.db "PRAGMA integrity_check;"
# If not "ok", delete msm.db — MSM recreates it on next start
```

**Out of memory:**  
Reduce RAM allocation in Option `4`. Keep allocated RAM at least 500 MB below your device's available RAM. Java's `-Xmx` flag is a heap ceiling, not a reservation — actual process memory will be higher.

---

## Contributing

1. Fork and clone
2. Test changes on an actual Termux device (ARM64 behavior differs from desktop Linux)
3. Follow PEP 8; keep lines under 100 characters
4. Open a PR with a clear description of what changed and why

Bug reports: [GitHub Issues](https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux/issues)

---

## License

MIT — see [LICENSE](LICENSE).
