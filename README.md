# Minecraft Server Manager (MSM) 6.0

MSM is a terminal-based manager for running multiple Minecraft servers from one machine, with a workflow aimed at Termux and Linux environments. It installs server binaries, starts them inside `screen`, tracks sessions and performance in SQLite, manages world backups, and exposes a CLI for routine server administration.

This README is written against the current codebase in this repository. It does not describe features that are not implemented.

## What MSM does

- Manages multiple named server definitions from one CLI.
- Supports Paper, Purpur, Folia, Vanilla, Fabric, Quilt, and PocketMine-MP.
- Downloads server binaries directly from upstream APIs.
- Starts each server in its own `screen` session and records its PID in a `.msm.pid` file.
- Tracks sessions, crashes, restarts, backups, and performance metrics in SQLite.
- Supports optional auto-restart per server while MSM is running.
- Supports manual backups and scheduled backups while MSM is running.
- Lets you edit `server.properties` and `eula.txt` from inside the CLI.
- Uses RCON for command delivery when enabled, and falls back to `screen -X stuff` otherwise.
- Can run `ngrok` or `playit` as a tunnel provider for a server.

## What MSM does not do

- It does not keep backup scheduling or auto-restart alive after the MSM process exits.
- It does not currently collect live player counts, TPS, or MSPT, even though the database schema has placeholders for them.
- It is not a Windows-native hosting workflow. The actual runtime depends on `screen` and POSIX shell behavior.

## Supported server flavors

| Flavor | Runtime | Default port | Notes |
| --- | --- | ---: | --- |
| PaperMC | Java | 25565 | Build metadata fetched from PaperMC API |
| Purpur | Java | 25565 | Latest build fetched per version |
| Folia | Java | 25565 | Uses PaperMC API style |
| Vanilla | Java | 25565 | Mojang version manifest |
| Fabric | Java | 25565 | Uses latest loader and installer metadata |
| Quilt | Java | 25565 | Uses latest loader metadata |
| PocketMine-MP | PHP | 19132 | Downloads `.phar` release assets |

## Runtime requirements

### Required

- Python 3.10 or newer
- `screen`
- Internet access for server downloads and metadata requests

### Required for some server types

- Java 8 for Minecraft `1.16.x` and older
- Java 17 for Minecraft `1.17` through `1.20.4`
- Java 21 for Minecraft `1.20.5+`
- PHP for PocketMine-MP

### Optional

- `ngrok` for TCP tunnel management
- `playit` or `playit-cli` for playit.gg agent management

## Installation

### Quick install on Termux

```bash
curl -fsSL https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/install.sh | bash
```

The installer:

- updates Termux packages
- installs `python`, `git`, `screen`, `openjdk-17`, `openjdk-21`, and `php`
- clones this repository
- creates `.venv`
- installs `requirements.txt`

After installation:

```bash
cd MSM-minecraft-server-manager-termux
source .venv/bin/activate
python msm.py
```

### Manual install on Termux

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

### Manual install on Linux

Install the platform equivalents of:

- `python3`
- `python3-venv`
- `screen`
- Java runtimes you need
- `php` if you want PocketMine-MP

Then:

```bash
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python msm.py
```

## Basic workflow

1. Launch MSM with `python msm.py`.
2. Create a server profile.
3. Install a server flavor and version.
4. Configure RAM, port, backups, tunnel provider, and optional RCON.
5. Start the server.
6. Use the world manager, console attach, command menu, and statistics view as needed.

## Main menu

The current CLI exposes these actions:

- Start server
- Stop server
- Install or update server
- Configure server
- Edit `server.properties` and `eula.txt`
- Attach to console
- World manager
- Send command
- Statistics
- Create new server
- Switch server
- Exit

## Current feature behavior

### Multi-server runtime model

Each configured server gets its own `ServerInstance`. Runtime state is not stored in module-level globals anymore.

Each running server owns:

- its own `screen` session name
- its own PID file
- its own session ID file
- its own monitoring thread
- its own auto-restart thread
- its own backup thread
- its own optional tunnel process

This means multiple servers can run concurrently without overwriting each other's session IDs or stop events.

### Process management

MSM starts servers inside `screen` using a small shell wrapper that writes the process PID to `.msm.pid` before `exec`.

Per-server files in the server directory:

- `.msm.pid`
- `.msm.session`
- `.msm.tunnel.pid`
- `.msm.ngrok.log` when ngrok is enabled
- `.msm.playit.log` when playit is enabled

### Monitoring and statistics

While MSM is running, each active server can record:

- RAM usage percent
- CPU usage percent
- session start and end times
- crash count
- restart count
- backup history

Metrics are sampled every 60 seconds and stored in SQLite with WAL mode enabled.

### Auto-restart

Auto-restart is controlled per server. When enabled:

- MSM checks the server every 15 seconds
- waits 5 seconds before restarting after an unexpected exit
- increments crash and restart counters in the database

Important:

- auto-restart only works while the MSM process is still running
- if you exit MSM and leave servers running in `screen`, restart supervision stops until you launch MSM again

### Backups

World backups are ZIP archives stored under:

```text
~/minecraft-<server-name>/backups/
```

Behavior:

- manual backups are available from the world manager
- scheduled backups are available per server
- scheduled backups only run while MSM is running and the server is online
- backup creation is offloaded to a worker thread with a spinner in the CLI
- restore is blocked while the server is running
- restore uses path validation and symlink checks to block zip-slip style archive attacks

World discovery uses:

- `level-name` from `server.properties` when available
- fallback matching for directories starting with `world`

### Command delivery

The command menu sends commands to the selected running server.

Behavior:

- if RCON is enabled and a password is set, MSM tries RCON first
- if RCON fails or is disabled, MSM falls back to `screen -X stuff`

RCON support is intentionally small and only covers command execution.

### Tunnels

MSM currently supports two tunnel providers:

- `ngrok`
- `playit`

For tunnel management:

- MSM stores the tunnel PID in `.msm.tunnel.pid`
- MSM shows localhost, LAN/Wi-Fi, and tunnel connection targets on the main screen
- MSM exposes a tunnel setup wizard from the server configuration menu

When `ngrok` is enabled:

- MSM starts `ngrok tcp <server-port>`
- writes output to `.msm.ngrok.log`
- queries the local ngrok API on `http://127.0.0.1:4040/api/tunnels` to discover the public URL
- the setup wizard can store your authtoken with `ngrok config add-authtoken`

When `playit` is enabled:

- MSM starts the `playit` or `playit-cli` agent in the background
- writes output to `.msm.playit.log`
- tries to extract the public endpoint or claim URL from the agent log
- expects you to link the agent to your playit account and create the tunnel mapping in the playit dashboard

Suggested Termux install flow for playit:

- `pkg update && pkg upgrade`
- `pkg install tur-repo`
- `pkg install playit`
- `ln -s $PREFIX/bin/playit-cli $PREFIX/bin/playit`
- `pkg install tmux`
- run `tmux`, then `playit-cli`, and detach with `Ctrl+B` then `D` if you want to keep it open outside MSM

Current limitation:

- playit tunnel creation is not automated through the playit API or website; MSM manages the local agent only

### Java detection

MSM resolves Java in this order:

1. `config.json` `java_homes`
2. `java` found on `PATH`
3. common JVM directories such as:
   - `$JAVA_HOME`
   - `~/../usr/lib/jvm`
   - `/usr/lib/jvm`
   - `/usr/lib64/jvm`

The selected binary is validated with `java -version`; MSM does not assume the default `java` matches the required version.

## Files and directories

### Application data

- Config: `~/.config/msm/config.json`
- Database: `~/.config/msm/msm.db`
- Log file: `~/.config/msm/msm.log`

### Server directories

Each server is stored under:

```text
~/minecraft-<sanitized-server-name>/
```

That directory typically contains:

```text
server.jar or *.phar
server.properties
eula.txt
backups/
.msm.pid
.msm.session
.msm.tunnel.pid
.msm.ngrok.log
.msm.playit.log
```

## Configuration format

MSM creates and migrates `config.json` automatically. The current structure looks like this:

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

## Project layout

```text
msm.py              # entrypoint
core/               # config, runtime registry, per-server lifecycle
db/                 # SQLite manager
ui/                 # CLI flows and presentation
utils/              # networking, archive safety, properties, logging, system helpers
tests/              # regression tests
```

## Security and reliability notes

The current codebase includes these hardening changes:

- per-server runtime state instead of shared global session state
- PID file tracking instead of parsing `screen -ls` output for PIDs
- SQLite WAL mode and busy timeout
- ZIP restore path validation and symlink blocking
- argument-list subprocess calls instead of `shell=True`
- Java runtime validation before startup
- sanitized server names for derived paths and screen names

## Development

### Install dev dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### Verification commands

These are the same checks used in CI:

```bash
python -m flake8 --jobs=1 .
python -m black --check .
python -m pytest
python -m compileall msm.py core db ui utils tests
```

### CI

GitHub Actions runs:

- `flake8`
- `black --check`
- `pytest`
- `compileall`

## Known limitations

- The runtime is designed for Termux/Linux. Development and tests can run elsewhere, but actual hosting depends on `screen`.
- Exiting MSM while leaving servers active also stops the in-process monitor, auto-restart, and scheduled backup threads.
- tunnel management supports `ngrok` and `playit`, but dashboard-side tunnel creation is still manual for playit.
- PocketMine-MP support covers binary download and process start, but the CLI is primarily optimized around Java server configuration fields.

## License

MIT. See [`LICENSE`](LICENSE).
