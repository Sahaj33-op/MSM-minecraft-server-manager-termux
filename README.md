<div align="center">

# ⛏️ MSM — Minecraft Server Manager

**Terminal-native server management for Termux and Linux.**  
Multi-server. Persistent SQLite tracking. Zero-GUI workflow.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux-orange?logo=android)](https://termux.dev)
[![Stars](https://img.shields.io/github/stars/Sahaj33-op/MSM-minecraft-server-manager-termux?style=flat&color=yellow)](https://github.com/Sahaj33-op/MSM-minecraft-server-manager-termux/stargazers)

</div>

-----

## What MSM Is

MSM manages multiple Minecraft server instances from a single TUI. It downloads server binaries, starts them inside `screen` sessions, records performance data in SQLite, handles world backups, and exposes a full CLI for routine administration — all from a phone running Termux, or a Linux box.

**This README describes what is implemented, not what is planned.**

-----

## Table of Contents

- [Features](#features)
- [Supported Server Flavors](#supported-server-flavors)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Quick Install (Termux)](#quick-install-termux)
  - [Manual Install (Termux)](#manual-install-termux)
  - [Manual Install (Linux)](#manual-install-linux)
- [Basic Workflow](#basic-workflow)
- [CLI Menu Reference](#cli-menu-reference)
- [Feature Details](#feature-details)
  - [Multi-Server Runtime Model](#multi-server-runtime-model)
  - [Process Management](#process-management)
  - [Monitoring & Statistics](#monitoring--statistics)
  - [Auto-Restart](#auto-restart)
  - [World Backups](#world-backups)
  - [Command Delivery](#command-delivery)
  - [Tunnel Support](#tunnel-support)
  - [Java Detection](#java-detection)
- [Files & Directories](#files--directories)
- [Configuration Format](#configuration-format)
- [Project Layout](#project-layout)
- [Security Notes](#security-notes)
- [Development](#development)
- [Known Limitations](#known-limitations)
- [License](#license)

-----

## Features

**What MSM does:**

- Manage multiple named server definitions from one CLI
- Download server binaries directly from upstream APIs (PaperMC, Mojang, Fabric, etc.)
- Start each server in its own `screen` session with PID tracking via `.msm.pid`
- Track sessions, crashes, restarts, backups, and CPU/RAM metrics in SQLite
- Optional per-server auto-restart while MSM is running
- Manual and scheduled world backups (ZIP archives)
- Edit `server.properties` and `eula.txt` from within the CLI
- RCON command delivery with `screen -X stuff` fallback
- `ngrok` and `playit` tunnel management

**What MSM does not do:**

- Keep backup scheduling or auto-restart alive after the MSM process exits
- Collect live player counts, TPS, or MSPT (schema exists, collection not implemented)
- Run natively on Windows (`screen` and POSIX behavior are hard dependencies)

-----

## Supported Server Flavors

|Flavor           |Runtime|Default Port|Binary Source                     |
|-----------------|-------|------------|----------------------------------|
|**PaperMC**      |Java   |25565       |PaperMC API (build metadata)      |
|**Purpur**       |Java   |25565       |Latest build per version          |
|**Folia**        |Java   |25565       |PaperMC API style                 |
|**Vanilla**      |Java   |25565       |Mojang version manifest           |
|**Fabric**       |Java   |25565       |Latest loader + installer metadata|
|**Quilt**        |Java   |25565       |Latest loader metadata            |
|**PocketMine-MP**|PHP    |19132       |`.phar` release assets            |

-----

## Requirements

### Always Required

|Dependency  |Purpose                          |
|------------|---------------------------------|
|Python 3.10+|MSM runtime                      |
|`screen`    |Server session isolation         |
|Internet    |Binary downloads and API metadata|

### Java Version Matrix

|Minecraft Version |Required Java|
|------------------|-------------|
|`1.16.x` and older|Java 8       |
|`1.17` – `1.20.4` |Java 17      |
|`1.20.5+`         |Java 21      |

### Optional

|Tool                   |Purpose             |
|-----------------------|--------------------|
|`ngrok`                |TCP tunnel via ngrok|
|`playit` / `playit-cli`|Tunnel via playit.gg|
|`php`                  |PocketMine-MP only  |

-----

## Installation

### Quick Install (Termux)

```bash
curl -fsSL https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/install.sh | bash
```

The installer handles:

- Termux package updates
- `python`, `git`, `screen`, `openjdk-17`, `openjdk-21`, `php`
- Repository clone, virtualenv setup, and `requirements.txt` install

**After install:**

```bash
cd MSM-minecraft-server-manager-termux
source .venv/bin/activate
python msm.py
```

**MSM data is stored at:**

```
~/.config/msm/
├── config.json     # server configurations
├── msm.db          # SQLite: sessions, metrics, backups, errors
└── msm.log         # rotating log (50 MB max, 30-day retention)
```

-----

### Manual Install (Termux)

```bash
pkg update && pkg upgrade -y
pkg install python git screen openjdk-17 openjdk-21 php -y

git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python msm.py
```

-----

### Manual Install (Linux)

Install platform equivalents of: `python3`, `python3-venv`, `screen`, Java runtimes, and `php` (if using PocketMine-MP).

```bash
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python msm.py
```

-----

## Basic Workflow

```
1. python msm.py          → launch MSM
2. Create server profile  → name, flavor, version
3. Install binary         → fetched from upstream API
4. Configure server       → RAM, port, RCON, tunnel, backups
5. Start server           → spawns in screen session
6. Manage live            → console attach, commands, stats, backups
```

-----

## CLI Menu Reference

|Action                 |Description                                   |
|-----------------------|----------------------------------------------|
|Start server           |Launches server in a `screen` session         |
|Stop server            |Sends stop signal; waits for clean exit       |
|Install / Update server|Downloads binary from upstream                |
|Configure server       |RAM, port, RCON, tunnel, backup settings      |
|Edit server.properties |In-TUI property editor                        |
|Edit eula.txt          |Accept EULA from the CLI                      |
|Attach to console      |Connects to the live `screen` session         |
|World manager          |Backup, restore, world switching              |
|Send command           |RCON or `screen -X stuff` delivery            |
|Statistics             |Session history, crash count, resource metrics|
|Create new server      |Add another server profile                    |
|Switch server          |Change active server context                  |
|Exit                   |Exits MSM (running servers stay in `screen`)  |

-----

## Feature Details

### Multi-Server Runtime Model

Each configured server gets its own `ServerInstance` object. No shared global session state.

Each running server owns:

- Its own `screen` session name
- Its own PID file and session ID file
- Its own monitoring thread
- Its own auto-restart thread
- Its own backup thread
- Its own optional tunnel process

Multiple servers run concurrently without session ID conflicts.

-----

### Process Management

MSM starts servers via a shell wrapper inside `screen` that writes the PID to `.msm.pid` before `exec`. Per-server state files in the server directory:

```
.msm.pid              # process ID
.msm.session          # screen session name
.msm.tunnel.pid       # tunnel process ID
.msm.ngrok.log        # ngrok output log
.msm.playit.log       # playit agent output log
.msm.playit.secret    # playit agent secret (after claim exchange)
```

-----

### Monitoring & Statistics

While MSM is running, each active server records:

|Metric                 |Interval               |
|-----------------------|-----------------------|
|RAM usage %            |Every 60 seconds       |
|CPU usage %            |Every 60 seconds       |
|Session start/end times|On start/stop events   |
|Crash count            |On unexpected exits    |
|Restart count          |On auto-restart trigger|
|Backup history         |On each backup creation|

All data is stored in SQLite with WAL mode enabled.

-----

### Auto-Restart

Auto-restart is configured per server. When enabled:

- MSM polls the server process every **15 seconds**
- Waits **5 seconds** before restarting after an unexpected exit
- Increments crash and restart counters in the database

> **Important:** Auto-restart only runs while the MSM process is alive. If you exit MSM while a server is running in `screen`, restart supervision stops until you re-launch MSM.

-----

### World Backups

Backups are ZIP archives stored under:

```
~/minecraft-<server-name>/backups/
```

|Behavior         |Detail                                                     |
|-----------------|-----------------------------------------------------------|
|Manual backups   |Available from world manager                               |
|Scheduled backups|Per-server, only while MSM is running and server is online |
|Backup threading |Offloaded to worker thread with a CLI spinner              |
|Restore guard    |Blocked while server is running                            |
|Path safety      |Symlink blocking + path validation against zip-slip attacks|

World discovery order:

1. `level-name` from `server.properties`
1. Fallback: directories starting with `world`

-----

### Command Delivery

|Method           |Condition                         |
|-----------------|----------------------------------|
|RCON             |Enabled + password set            |
|`screen -X stuff`|RCON disabled or connection failed|

RCON support covers command execution only — not console streaming.

-----

### Tunnel Support

MSM manages tunnel processes locally. Dashboard-side configuration (for playit) is still manual.

#### ngrok

```
MSM starts → ngrok tcp <port>
           → writes to .msm.ngrok.log
           → queries http://127.0.0.1:4040/api/tunnels for public URL
```

Store your authtoken:

```bash
ngrok config add-authtoken <your-token>
```

#### playit

```
MSM starts → playit start (background)
           → writes to .msm.playit.log
           → stores agent secret in .msm.playit.secret
           → attempts to extract public endpoint from agent log
```

The setup wizard drives: `claim generate` → `claim url` → `claim exchange`

**Termux install for playit:**

```bash
pkg update && pkg upgrade
pkg install tur-repo
pkg install playit
ln -s $PREFIX/bin/playit-cli $PREFIX/bin/playit
```

> `tmux` is not required when MSM manages the tunnel. Use it only if you want to run the playit agent independently.

-----

### Java Detection

MSM resolves Java in this order:

1. `java_homes` map in `config.json`
1. `java` on `PATH`
1. Common JVM directories:
- `$JAVA_HOME`
- `~/../usr/lib/jvm`
- `/usr/lib/jvm`
- `/usr/lib64/jvm`

The selected binary is validated with `java -version` before use.

-----

## Files & Directories

### Application Data

```
~/.config/msm/
├── config.json     # server configurations and global defaults
├── msm.db          # SQLite database
└── msm.log         # rotating application log
```

### Server Directories

```
~/minecraft-<sanitized-server-name>/
├── server.jar          # (or *.phar for PocketMine-MP)
├── server.properties
├── eula.txt
├── backups/
├── .msm.pid
├── .msm.session
├── .msm.tunnel.pid
├── .msm.ngrok.log
├── .msm.playit.log
└── .msm.playit.secret
```

-----

## Configuration Format

MSM creates and migrates `config.json` automatically.

```json
{
  "current_server": "survival",
  "java_homes": {
    "17": "/usr/lib/jvm/java-17-openjdk",
    "21": "/usr/lib/jvm/java-21-openjdk"
  },
  "tunnel_defaults": {
    "provider": "ngrok",
    "binary_path": "ngrok",
    "autostart": false
  },
  "servers": {
    "survival": {
      "server_flavor": "paper",
      "server_version": "1.21.1",
      "eula_accepted": true,
      "ram_mb": 2048,
      "auto_restart": true,
      "backup_settings": {
        "enabled": true,
        "interval_hours": 6
      },
      "tunnel": {
        "enabled": false,
        "provider": "ngrok",
        "binary_path": "ngrok",
        "autostart": false
      },
      "rcon": {
        "enabled": false,
        "host": "127.0.0.1",
        "port": 25575,
        "password": ""
      },
      "server_settings": {
        "motd": "survival Server",
        "port": 25565,
        "max-players": 20,
        "online-mode": "true",
        "enable-rcon": "false",
        "rcon.port": 25575
      }
    }
  }
}
```

-----

## Project Layout

```
msm.py          # entrypoint
core/           # config, runtime registry, per-server lifecycle
db/             # SQLite manager
ui/             # CLI flows and presentation
utils/          # networking, archive safety, properties, logging, system helpers
tests/          # regression tests
```

-----

## Security Notes

Hardening applied in the current codebase:

|Area             |Implementation                                                      |
|-----------------|--------------------------------------------------------------------|
|Session isolation|Per-server runtime state; no shared global session                  |
|PID tracking     |`.msm.pid` files instead of parsing `screen -ls`                    |
|Database safety  |SQLite WAL mode + busy timeout                                      |
|Archive safety   |ZIP restore path validation + symlink blocking (zip-slip prevention)|
|Subprocess safety|Argument-list calls; no `shell=True`                                |
|Java validation  |Runtime validated with `java -version` before use                   |
|Path sanitization|Server names sanitized before use in derived paths and screen names |

-----

## Development

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Checks (same as CI)

```bash
python -m flake8 --jobs=1 .
python -m black --check .
python -m pytest
python -m compileall msm.py core db ui utils tests
```

### CI Pipeline

GitHub Actions runs on every push:

```
flake8      → style and lint
black       → format enforcement
pytest      → test suite
compileall  → bytecode validation
```

-----

## Known Limitations

- **Thread lifetime:** Exiting MSM while servers are active stops the in-process monitor, auto-restart, and scheduled backup threads. Servers keep running in `screen`; supervision resumes when you relaunch MSM.
- **playit dashboard:** MSM manages the local agent only. Tunnel creation in the playit dashboard is still manual.
- **PocketMine-MP:** Binary download and process start work. The configuration UI is optimized around Java server fields.
- **Live metrics:** TPS, MSPT, and player counts are not yet collected despite schema placeholders existing.
- **Platform:** Actual hosting requires `screen` and POSIX behavior. Dev and tests can run elsewhere.

-----

## License

MIT — see [`LICENSE`](LICENSE).

-----

<div align="center">

Made for Termux. Built for control.

</div>
