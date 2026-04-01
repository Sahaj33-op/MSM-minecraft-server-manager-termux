"""Interactive CLI for Minecraft Server Manager."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path

from core.config import ConfigManager
from core.constants import (
    CONFIG_FILE,
    DATABASE_FILE,
    DEFAULT_TUNNEL_BINARIES,
    EULA_FILE,
    LOG_FILE,
    LOG_RETENTION_DAYS,
    MAX_LOG_SIZE,
    SERVER_FLAVORS,
    SERVER_PROPERTIES_FILE,
    SUPPORTED_TUNNEL_PROVIDERS,
    VERSION,
    VERSIONS_PER_PAGE,
)
from core.runtime import RuntimeManager
from db.manager import DatabaseManager
from ui.colors import C
from utils.logging_utils import EnhancedLogger
from utils.network import get_versions_for_flavor
from utils.properties import load_properties
from utils.system import (
    check_base_dependencies,
    format_bytes,
    get_server_dir,
    get_system_info,
    read_text_file,
    run_command,
    running_on_termux,
    sanitize_input,
    write_text_file,
)
from utils.tunnels import (
    build_playit_claim_exchange_command,
    build_playit_claim_generate_command,
    build_playit_claim_url_command,
    extract_last_non_empty_line,
    extract_playit_claim_url,
)


def pause() -> None:
    input("\nPress Enter to continue...")


def clear_screen() -> None:
    print("\033[H\033[2J", end="", flush=True)


def format_duration(seconds: float | int | None) -> str:
    if not seconds:
        return "N/A"
    remaining = int(seconds)
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, _ = divmod(remaining, 60)
    return f"{days}d {hours}h {minutes}m"


def run_with_spinner(message: str, func, *args, **kwargs):
    state = {"done": False, "result": None, "error": None}

    def worker() -> None:
        try:
            state["result"] = func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - presentation glue
            state["error"] = exc
        finally:
            state["done"] = True

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    spinner = "|/-\\"
    index = 0
    while not state["done"]:
        print(f"\r{message} {spinner[index % len(spinner)]}", end="", flush=True)
        time.sleep(0.1)
        index += 1
    print("\r" + (" " * (len(message) + 4)) + "\r", end="", flush=True)

    if state["error"]:
        raise state["error"]
    return state["result"]


def create_services():
    logger = EnhancedLogger(LOG_FILE, MAX_LOG_SIZE, LOG_RETENTION_DAYS)
    config_manager = ConfigManager(CONFIG_FILE, logger)
    db_manager = DatabaseManager(DATABASE_FILE)
    runtime = RuntimeManager(config_manager, db_manager, logger)
    return logger, config_manager, db_manager, runtime


def ensure_current_server(config_manager: ConfigManager) -> dict:
    config = config_manager.load()
    if not config.get("current_server") and config.get("servers"):
        config["current_server"] = next(iter(config["servers"]))
        config = config_manager.save(config)
    return config


def print_header(current_server: str | None, runtime: RuntimeManager) -> None:
    clear_screen()
    system_info = get_system_info()
    running_servers = runtime.running_servers()
    ram_usage = f"{system_info['available_ram_mb']}MB/{system_info['total_ram_mb']}MB"
    cpu_info = f"{system_info['cpu_count']} cores @ {system_info['cpu_usage']:.1f}%"
    print(f"{C.BOLD}{C.CYAN}{'=' * 72}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}Minecraft Server Manager v{VERSION}{C.RESET}")
    print(
        f"{C.DIM}RAM: {ram_usage} | CPU: {cpu_info} "
        f"| Platform: {system_info['platform']}{C.RESET}"
    )
    print(f"{C.DIM}Running servers: {len(running_servers)}{C.RESET}")
    if current_server:
        print(f"{C.DIM}Current server: {current_server}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * 72}{C.RESET}\n")


def print_connection_summary(instance) -> None:
    info = instance.get_connection_info()
    lan_endpoints = info["lan_endpoints"]
    if lan_endpoints:
        lan_display = ", ".join(lan_endpoints[:2])
        if len(lan_endpoints) > 2:
            lan_display += f" (+{len(lan_endpoints) - 2} more)"
    else:
        lan_display = "Not detected"

    tunnel_display = info["tunnel_url"] or info["tunnel_status"]

    print(f"{C.DIM}Localhost: {info['loopback_endpoint']}{C.RESET}")
    print(f"{C.DIM}LAN/Wi-Fi: {lan_display}{C.RESET}")
    print(f"{C.DIM}Tunnel: {tunnel_display}{C.RESET}")
    if info.get("tunnel_setup_url"):
        print(f"{C.DIM}Tunnel setup: {info['tunnel_setup_url']}{C.RESET}")


def resolve_tunnel_binary(binary_path: str) -> str | None:
    resolved = shutil.which(binary_path)
    if resolved:
        return resolved
    file_path = Path(binary_path).expanduser()
    if file_path.exists():
        return str(file_path)
    return None


def save_tunnel_config(
    instance,
    config_manager: ConfigManager,
    current_server: str,
    provider: str,
    binary_path: str,
    enabled: bool,
    logger,
) -> None:
    def updater(saved_config: dict) -> None:
        tunnel = saved_config["servers"][current_server].setdefault("tunnel", {})
        tunnel["provider"] = provider
        tunnel["binary_path"] = binary_path
        tunnel["enabled"] = enabled
        tunnel["autostart"] = enabled

    config_manager.mutate(updater)
    if instance.is_running():
        if enabled:
            instance.restart_tunnel()
        else:
            instance.stop_tunnel()
    logger.log(
        "SUCCESS",
        f"Tunnel settings saved for {current_server}.",
        provider=provider,
        enabled=enabled,
    )


def ngrok_setup_wizard(
    runtime: RuntimeManager,
    config_manager: ConfigManager,
    current_server: str,
    logger,
) -> None:
    instance = runtime.get_instance(current_server)
    config = config_manager.load()
    tunnel = config["servers"][current_server].setdefault("tunnel", {})
    current_binary = tunnel.get("binary_path") or DEFAULT_TUNNEL_BINARIES["ngrok"]
    default_binary = resolve_tunnel_binary(current_binary) or current_binary

    print_header(current_server, runtime)
    print(f"{C.BOLD}Ngrok Setup Wizard{C.RESET}")
    print_connection_summary(instance)
    print()
    print("Ngrok requirements:")
    print(" - The ngrok agent must be installed and reachable by MSM.")
    print(" - Your ngrok account must be configured with an authtoken.")
    print(" - TCP endpoints may require billing details on ngrok.")
    if running_on_termux():
        print(" - If you installed ngrok through a wrapper, set the binary path to that wrapper.")

    binary_path = input(f"\nNgrok binary path [{default_binary}]: ").strip() or default_binary
    resolved_binary = resolve_tunnel_binary(binary_path)
    if resolved_binary:
        logger.log("INFO", f"Using ngrok binary at {resolved_binary}")
    else:
        logger.log("WARNING", f"Ngrok binary '{binary_path}' was not found on this device.")

    authtoken = input("Ngrok authtoken (leave blank to keep the existing config): ").strip()
    if authtoken:
        if not resolved_binary:
            logger.log(
                "ERROR",
                "Cannot configure ngrok authtoken because the binary was not found.",
            )
        else:
            result = run_command(
                [resolved_binary, "config", "add-authtoken", authtoken],
                logger=logger,
                check=False,
                capture_output=True,
            )
            if result and result.returncode == 0:
                logger.log("SUCCESS", "Stored ngrok authtoken successfully.")
            else:
                stderr = ""
                if result:
                    stderr = (result.stderr or result.stdout or "").strip()
                logger.log("ERROR", f"Failed to store ngrok authtoken. {stderr}".strip())

    enable_tunnel = input("Enable ngrok for this server? (Y/n): ").strip().lower() != "n"
    save_tunnel_config(
        instance,
        config_manager,
        current_server,
        provider="ngrok",
        binary_path=binary_path,
        enabled=enable_tunnel,
        logger=logger,
    )
    pause()


def playit_setup_wizard(
    runtime: RuntimeManager,
    config_manager: ConfigManager,
    current_server: str,
    logger,
) -> None:
    instance = runtime.get_instance(current_server)
    config = config_manager.load()
    tunnel = config["servers"][current_server].setdefault("tunnel", {})
    current_binary = tunnel.get("binary_path")
    if not current_binary or current_binary == DEFAULT_TUNNEL_BINARIES["ngrok"]:
        current_binary = (
            resolve_tunnel_binary("playit")
            or resolve_tunnel_binary(DEFAULT_TUNNEL_BINARIES["playit"])
            or DEFAULT_TUNNEL_BINARIES["playit"]
        )

    print_header(current_server, runtime)
    print(f"{C.BOLD}Playit Setup Wizard{C.RESET}")
    print_connection_summary(instance)
    print()
    print("Playit notes:")
    print(" - MSM uses `claim generate`, `claim url`, and `claim exchange` for setup.")
    print(" - MSM uses `playit-cli start` for the managed background agent.")
    print(" - You still need to link the agent to your playit account.")
    print(f" - Create a playit TCP tunnel that forwards to 127.0.0.1:{instance.get_server_port()}.")
    if running_on_termux():
        print("\nInstall playit on Termux:")
        print(" pkg update && pkg upgrade")
        print(" pkg install tur-repo")
        print(" pkg install playit")
        print(" ln -s $PREFIX/bin/playit-cli $PREFIX/bin/playit")
        print(" MSM does not need tmux when it manages playit for this server.")

    binary_path = input(f"\nPlayit binary path [{current_binary}]: ").strip() or str(current_binary)
    resolved_binary = resolve_tunnel_binary(binary_path)
    if resolved_binary:
        logger.log("INFO", f"Using playit binary at {resolved_binary}")
    else:
        logger.log("WARNING", f"Playit binary '{binary_path}' was not found on this device.")

    if resolved_binary:
        run_guided_claim = input(
            "Run the guided playit claim flow now? (Y/n): "
        ).strip().lower() != "n"
        if run_guided_claim:
            claim_generate = run_command(
                build_playit_claim_generate_command(resolved_binary),
                logger=logger,
                check=False,
                capture_output=True,
                cwd=instance.server_dir,
            )
            generate_output = ""
            if claim_generate:
                generate_output = (
                    f"{claim_generate.stdout or ''}\n{claim_generate.stderr or ''}".strip()
                )
            claim_code = extract_last_non_empty_line(generate_output)
            if not claim_generate or claim_generate.returncode != 0 or not claim_code:
                logger.log(
                    "ERROR",
                    "Failed to generate a playit claim code.",
                )
                if generate_output:
                    logger.log("INFO", generate_output)
            else:
                logger.log("INFO", f"Playit claim code: {claim_code}")
                claim_url_result = run_command(
                    build_playit_claim_url_command(resolved_binary, claim_code),
                    logger=logger,
                    check=False,
                    capture_output=True,
                    cwd=instance.server_dir,
                )
                url_output = ""
                if claim_url_result:
                    url_output = (
                        f"{claim_url_result.stdout or ''}\n{claim_url_result.stderr or ''}".strip()
                    )
                claim_url = extract_playit_claim_url(url_output) or extract_last_non_empty_line(
                    url_output
                )
                if claim_url:
                    logger.log("INFO", f"Open this playit claim URL: {claim_url}")
                    print()
                    print(f"Claim URL: {claim_url}")
                else:
                    logger.log(
                        "WARNING",
                        "MSM could not derive a playit claim URL automatically.",
                    )
                step = input(
                    "Press Enter after linking the device in your browser, or type 'skip': "
                ).strip()
                if step.lower() != "skip":
                    exchange_result = run_command(
                        build_playit_claim_exchange_command(
                            resolved_binary,
                            claim_code,
                            secret_path=instance.playit_secret_file,
                        ),
                        logger=logger,
                        check=False,
                        capture_output=True,
                        cwd=instance.server_dir,
                    )
                    exchange_output = ""
                    if exchange_result:
                        exchange_output = f"{exchange_result.stdout or ''}\n"
                        exchange_output += exchange_result.stderr or ""
                        exchange_output = exchange_output.strip()
                    stored_secret = read_text_file(instance.playit_secret_file)
                    if not stored_secret:
                        fallback_secret = extract_last_non_empty_line(exchange_output)
                        if fallback_secret:
                            write_text_file(instance.playit_secret_file, fallback_secret)
                            stored_secret = fallback_secret
                    if exchange_result and exchange_result.returncode == 0 and stored_secret:
                        logger.log(
                            "SUCCESS",
                            (
                                f"Stored playit secret for {current_server} "
                                f"at {instance.playit_secret_file}"
                            ),
                        )
                    else:
                        logger.log(
                            "ERROR",
                            "Playit claim exchange did not produce a usable secret.",
                        )
                        if exchange_output:
                            logger.log("INFO", exchange_output)

    enable_tunnel = input("Enable playit for this server? (Y/n): ").strip().lower() != "n"
    save_tunnel_config(
        instance,
        config_manager,
        current_server,
        provider="playit",
        binary_path=binary_path,
        enabled=enable_tunnel,
        logger=logger,
    )
    pause()


def tunnel_setup_wizard(
    runtime: RuntimeManager,
    config_manager: ConfigManager,
    current_server: str,
    logger,
) -> None:
    instance = runtime.get_instance(current_server)

    while True:
        config = config_manager.load()
        tunnel = config["servers"][current_server].setdefault("tunnel", {})
        print_header(current_server, runtime)
        print(f"{C.BOLD}Tunnel Setup Wizard{C.RESET}")
        print(f"Current provider: {tunnel.get('provider', 'ngrok')}")
        print(f"Enabled: {tunnel.get('enabled', False)}")
        print(f"Binary: {tunnel.get('binary_path', DEFAULT_TUNNEL_BINARIES['ngrok'])}")
        print_connection_summary(instance)
        print()
        print(" 1. Setup ngrok")
        print(" 2. Setup playit")
        print(" 3. Disable tunnel for this server")
        print(" 0. Back")

        choice = input(f"\n{C.BOLD}Choose action: {C.RESET}").strip()
        if choice == "0":
            return
        if choice == "1":
            ngrok_setup_wizard(runtime, config_manager, current_server, logger)
            continue
        if choice == "2":
            playit_setup_wizard(runtime, config_manager, current_server, logger)
            continue
        if choice == "3":
            binary_path = tunnel.get(
                "binary_path",
                DEFAULT_TUNNEL_BINARIES.get(tunnel.get("provider", "ngrok"), "ngrok"),
            )
            save_tunnel_config(
                instance,
                config_manager,
                current_server,
                provider=tunnel.get("provider", "ngrok"),
                binary_path=binary_path,
                enabled=False,
                logger=logger,
            )
            pause()
            continue
        logger.log("ERROR", "Invalid tunnel wizard selection.")
        pause()


def create_new_server(config_manager: ConfigManager, logger) -> None:
    name = input(f"{C.BOLD}Enter a new server name: {C.RESET}").strip()
    if not name:
        logger.log("ERROR", "Server name cannot be empty.")
        return
    sanitized_name = sanitize_input(name)
    config = config_manager.load()
    if sanitized_name in config.get("servers", {}):
        logger.log("ERROR", f"Server '{sanitized_name}' already exists.")
        return
    config["servers"][sanitized_name] = {
        "server_flavor": None,
        "server_version": None,
        "eula_accepted": True,
        "ram_mb": 2048,
        "auto_restart": False,
        "backup_settings": {"enabled": False, "interval_hours": 6},
        "tunnel": {
            "enabled": False,
            "provider": "ngrok",
            "binary_path": "ngrok",
            "autostart": False,
        },
        "rcon": {"enabled": False, "host": "127.0.0.1", "port": 25575, "password": ""},
        "server_settings": {
            "motd": f"{sanitized_name} Server",
            "port": 25565,
            "max-players": 20,
            "online-mode": "true",
            "enable-rcon": "false",
            "rcon.port": 25575,
        },
    }
    config["current_server"] = sanitized_name
    config_manager.save(config)
    get_server_dir(sanitized_name).mkdir(parents=True, exist_ok=True)
    logger.log("SUCCESS", f"Created server '{sanitized_name}'.")


def select_current_server(config_manager: ConfigManager, logger) -> None:
    config = config_manager.load()
    servers = list(config.get("servers", {}))
    if not servers:
        logger.log("ERROR", "No servers are configured.")
        return
    print(f"{C.BOLD}Configured servers:{C.RESET}")
    for index, server_name in enumerate(servers, start=1):
        print(f" {index}. {server_name}")
    choice = input(f"\n{C.BOLD}Choose server: {C.RESET}").strip()
    if not choice.isdigit():
        logger.log("ERROR", "Selection must be a number.")
        return
    selection = int(choice) - 1
    if selection < 0 or selection >= len(servers):
        logger.log("ERROR", "Invalid server selection.")
        return
    config["current_server"] = servers[selection]
    config_manager.save(config)
    logger.log("SUCCESS", f"Switched to server '{servers[selection]}'.")


def select_server_flavor() -> str | None:
    flavors = list(SERVER_FLAVORS)
    print(f"{C.BOLD}Server flavors:{C.RESET}")
    for index, flavor in enumerate(flavors, start=1):
        details = SERVER_FLAVORS[flavor]
        print(f" {index}. {details['name']} - {details['description']}")
    choice = input(f"\n{C.BOLD}Choose flavor: {C.RESET}").strip()
    if not choice.isdigit():
        return None
    selection = int(choice) - 1
    if selection < 0 or selection >= len(flavors):
        return None
    return flavors[selection]


def select_server_version(flavor: str, logger) -> tuple[str | None, dict | None]:
    include_snapshots = False
    page = 0
    while True:
        versions_data = get_versions_for_flavor(
            flavor,
            include_snapshots=include_snapshots,
            logger=logger,
        )
        versions = list(versions_data.keys())
        if not versions:
            logger.log("ERROR", f"No versions were returned for {flavor}.")
            return None, None
        total_pages = max(1, ((len(versions) - 1) // VERSIONS_PER_PAGE) + 1)
        page = min(page, total_pages - 1)
        start = page * VERSIONS_PER_PAGE
        end = start + VERSIONS_PER_PAGE
        page_versions = versions[start:end]
        print(f"\n{C.BOLD}{SERVER_FLAVORS[flavor]['name']} versions{C.RESET}")
        print(
            f"{C.DIM}Snapshots: {'on' if include_snapshots else 'off'} "
            f"| Page {page + 1}/{total_pages}{C.RESET}"
        )
        for index, version in enumerate(page_versions, start=1):
            marker = " [snapshot]" if versions_data[version].get("is_snapshot") else ""
            print(f" {index}. {version}{marker}")
        print("\n n = next page | p = previous page | s = toggle snapshots | 0 = cancel")
        choice = input(f"{C.BOLD}Choose version: {C.RESET}").strip().lower()
        if choice == "0":
            return None, None
        if choice == "n":
            if page < total_pages - 1:
                page += 1
            continue
        if choice == "p":
            if page > 0:
                page -= 1
            continue
        if choice == "s":
            include_snapshots = not include_snapshots
            page = 0
            continue
        if not choice.isdigit():
            logger.log("ERROR", "Invalid version selection.")
            continue
        selection = int(choice) - 1
        if selection < 0 or selection >= len(page_versions):
            logger.log("ERROR", "Invalid version selection.")
            continue
        version = page_versions[selection]
        return version, versions_data[version]


def install_server(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        logger.log("ERROR", "No server is selected.")
        return
    flavor = select_server_flavor()
    if not flavor:
        logger.log("ERROR", "Invalid flavor selection.")
        return
    version, version_info = select_server_version(flavor, logger)
    if not version or not version_info:
        return
    instance = runtime.get_instance(current_server)
    artifact = run_with_spinner(
        f"Downloading {SERVER_FLAVORS[flavor]['name']} {version}",
        instance.install_binary,
        flavor,
        version,
        version_info,
    )

    def updater(saved_config: dict) -> None:
        server_config = saved_config["servers"][current_server]
        server_config["server_flavor"] = flavor
        server_config["server_version"] = version
        server_config["server_settings"]["port"] = SERVER_FLAVORS[flavor]["default_port"]

    config_manager.mutate(updater)
    instance.apply_server_files()
    logger.log("SUCCESS", f"Installed {artifact.name} for '{current_server}'.")


def configure_server(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        logger.log("ERROR", "No server is selected.")
        return
    instance = runtime.get_instance(current_server)

    while True:
        config = config_manager.load()
        server_config = config["servers"][current_server]
        print_header(current_server, runtime)
        print(f"{C.BOLD}Configure {current_server}{C.RESET}")
        print(f" 1. RAM MB: {server_config['ram_mb']}")
        print(f" 2. Port: {server_config['server_settings']['port']}")
        print(f" 3. Auto restart: {server_config['auto_restart']}")
        print(f" 4. MOTD: {server_config['server_settings']['motd']}")
        print(f" 5. Max players: {server_config['server_settings']['max-players']}")
        print(f" 6. Online mode: {server_config['server_settings']['online-mode']}")
        print(f" 7. Scheduled backups: {server_config['backup_settings']['enabled']}")
        print(f" 8. Backup interval hours: {server_config['backup_settings']['interval_hours']}")
        print(f" 9. Tunnel enabled: {server_config['tunnel']['enabled']}")
        print(f"10. Tunnel provider: {server_config['tunnel']['provider']}")
        print(f"11. Tunnel binary: {server_config['tunnel']['binary_path']}")
        print("12. Tunnel setup wizard")
        print(f"13. RCON enabled: {server_config['rcon']['enabled']}")
        print(f"14. RCON password set: {bool(server_config['rcon']['password'])}")
        print(" 0. Back")

        choice = input(f"\n{C.BOLD}Choose setting: {C.RESET}").strip()
        if choice == "0":
            return
        try:
            if choice == "1":
                value = int(input("RAM in MB: ").strip())

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["ram_mb"] = value

            elif choice == "2":
                value = int(input("Server port: ").strip())

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["server_settings"]["port"] = value

            elif choice == "3":
                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    server["auto_restart"] = not server["auto_restart"]

            elif choice == "4":
                value = input("MOTD: ").strip()

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["server_settings"]["motd"] = value

            elif choice == "5":
                value = int(input("Max players: ").strip())

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["server_settings"][
                        "max-players"
                    ] = value

            elif choice == "6":
                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    current_value = str(
                        server["server_settings"].get("online-mode", "true")
                    ).lower()
                    server["server_settings"]["online-mode"] = (
                        "false" if current_value == "true" else "true"
                    )

            elif choice == "7":
                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    backup_settings = server.setdefault("backup_settings", {})
                    backup_settings["enabled"] = not backup_settings.get("enabled", False)

            elif choice == "8":
                value = float(input("Backup interval in hours: ").strip())

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["backup_settings"][
                        "interval_hours"
                    ] = value

            elif choice == "9":
                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    tunnel = server.setdefault("tunnel", {})
                    tunnel["enabled"] = not tunnel.get("enabled", False)

            elif choice == "10":
                provider_options = ", ".join(SUPPORTED_TUNNEL_PROVIDERS)
                current_provider = server_config["tunnel"].get("provider", "ngrok")
                value = (
                    input(
                        f"Tunnel provider ({provider_options}) [{current_provider}]: "
                    ).strip().lower()
                    or current_provider
                )
                if value not in SUPPORTED_TUNNEL_PROVIDERS:
                    logger.log("ERROR", f"Tunnel provider must be one of: {provider_options}")
                    pause()
                    continue

                def updater(saved_config: dict) -> None:
                    tunnel = saved_config["servers"][current_server].setdefault("tunnel", {})
                    previous_provider = tunnel.get("provider", "ngrok")
                    previous_binary = tunnel.get("binary_path", DEFAULT_TUNNEL_BINARIES["ngrok"])
                    tunnel["provider"] = value
                    if previous_binary == DEFAULT_TUNNEL_BINARIES.get(
                        previous_provider,
                        previous_binary,
                    ):
                        tunnel["binary_path"] = DEFAULT_TUNNEL_BINARIES.get(value, value)

            elif choice == "11":
                current_provider = server_config["tunnel"].get("provider", "ngrok")
                default_binary = server_config["tunnel"].get(
                    "binary_path",
                    DEFAULT_TUNNEL_BINARIES.get(current_provider, current_provider),
                )
                value = (
                    input(f"Tunnel binary path [{default_binary}]: ").strip()
                    or default_binary
                )

                def updater(saved_config: dict) -> None:
                    saved_config["servers"][current_server]["tunnel"]["binary_path"] = value

            elif choice == "12":
                tunnel_setup_wizard(runtime, config_manager, current_server, logger)
                continue

            elif choice == "13":
                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    rcon = server.setdefault("rcon", {})
                    settings = server.setdefault("server_settings", {})
                    enabled = not rcon.get("enabled", False)
                    rcon["enabled"] = enabled
                    settings["enable-rcon"] = str(enabled).lower()

            elif choice == "14":
                value = input("RCON password: ").strip()

                def updater(saved_config: dict) -> None:
                    server = saved_config["servers"][current_server]
                    server["rcon"]["password"] = value
                    server["server_settings"]["rcon.password"] = value

            else:
                logger.log("ERROR", "Invalid configuration selection.")
                pause()
                continue

            saved_config = config_manager.mutate(updater)
            instance.apply_server_files()
            if choice in {"9", "10", "11"} and instance.is_running():
                tunnel_settings = saved_config["servers"][current_server]["tunnel"]
                if tunnel_settings.get("enabled"):
                    instance.restart_tunnel()
                else:
                    instance.stop_tunnel()
        except ValueError:
            logger.log("ERROR", "A numeric value was required.")
            pause()


def edit_server_files(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        logger.log("ERROR", "No server is selected.")
        return
    instance = runtime.get_instance(current_server)
    instance.ensure_server_files()

    while True:
        properties_path = instance.server_dir / SERVER_PROPERTIES_FILE
        eula_path = instance.server_dir / EULA_FILE
        properties = load_properties(properties_path)
        eula_status = load_properties(eula_path).get("eula", "false")

        print_header(current_server, runtime)
        print(f"{C.BOLD}Server file editor{C.RESET}")
        print(f" server.properties: {properties_path}")
        print(f" eula.txt: {eula_path}")
        print(f" EULA accepted: {eula_status}")
        print("\n 1. Show current properties")
        print(" 2. Set or update a property")
        print(" 3. Delete a property")
        print(" 4. Toggle EULA")
        print(" 0. Back")

        choice = input(f"\n{C.BOLD}Choose action: {C.RESET}").strip()
        if choice == "0":
            return
        if choice == "1":
            if not properties:
                print("No server.properties entries found.")
            else:
                for key, value in properties.items():
                    print(f" {key}={value}")
            pause()
            continue
        if choice == "2":
            key = input("Property key: ").strip()
            if not key:
                logger.log("ERROR", "Property key cannot be empty.")
                pause()
                continue
            value = input("Property value: ").strip()
            properties[key] = value
            instance.save_server_properties(properties)
            logger.log("SUCCESS", f"Updated {key} in {SERVER_PROPERTIES_FILE}.")
            pause()
            continue
        if choice == "3":
            key = input("Property key to delete: ").strip()
            if key not in properties:
                logger.log("ERROR", f"Property '{key}' does not exist.")
                pause()
                continue
            properties.pop(key, None)
            instance.save_server_properties(properties)
            logger.log("SUCCESS", f"Deleted {key} from {SERVER_PROPERTIES_FILE}.")
            pause()
            continue
        if choice == "4":
            instance.set_eula(eula_status.lower() != "true")
            logger.log("SUCCESS", "Updated EULA flag.")
            pause()
            continue
        logger.log("ERROR", "Invalid file editor selection.")
        pause()


def choose_backup(instance, logger) -> Path | None:
    backups = instance.list_backups()
    if not backups:
        logger.log("INFO", "No backups are available.")
        return None
    for index, backup in enumerate(backups, start=1):
        print(f" {index}. {backup.name} ({format_bytes(backup.stat().st_size)})")
    choice = input(f"\n{C.BOLD}Choose backup: {C.RESET}").strip()
    if not choice.isdigit():
        logger.log("ERROR", "Backup selection must be numeric.")
        return None
    selection = int(choice) - 1
    if selection < 0 or selection >= len(backups):
        logger.log("ERROR", "Invalid backup selection.")
        return None
    return backups[selection]


def world_manager(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        logger.log("ERROR", "No server is selected.")
        return
    instance = runtime.get_instance(current_server)

    while True:
        print_header(current_server, runtime)
        print(f"{C.BOLD}World manager{C.RESET}")
        print(" 1. Create backup")
        print(" 2. List backups")
        print(" 3. Restore backup")
        print(" 4. Delete backup")
        print(" 0. Back")

        choice = input(f"\n{C.BOLD}Choose action: {C.RESET}").strip()
        if choice == "0":
            return
        if choice == "1":
            try:
                backup_path = run_with_spinner("Creating backup", instance.create_backup)
                logger.log("SUCCESS", f"Backup saved to {backup_path}")
            except Exception as exc:
                logger.log("ERROR", f"Backup failed: {exc}")
            pause()
            continue
        if choice == "2":
            backups = instance.list_backups()
            if not backups:
                logger.log("INFO", "No backups are available.")
            else:
                for backup in backups:
                    print(f" {backup.name} ({format_bytes(backup.stat().st_size)})")
            pause()
            continue
        if choice == "3":
            backup_path = choose_backup(instance, logger)
            if not backup_path:
                pause()
                continue
            confirmation = input(
                "This will overwrite world data. Type RESTORE to continue: "
            ).strip()
            if confirmation != "RESTORE":
                logger.log("INFO", "Restore cancelled.")
                pause()
                continue
            try:
                run_with_spinner("Restoring backup", instance.restore_backup, backup_path.name)
            except Exception as exc:
                logger.log("ERROR", f"Restore failed: {exc}")
            pause()
            continue
        if choice == "4":
            backup_path = choose_backup(instance, logger)
            if not backup_path:
                pause()
                continue
            confirmation = input(f"Type DELETE to remove {backup_path.name}: ").strip()
            if confirmation != "DELETE":
                logger.log("INFO", "Deletion cancelled.")
                pause()
                continue
            try:
                instance.delete_backup(backup_path.name)
            except Exception as exc:
                logger.log("ERROR", f"Deletion failed: {exc}")
            pause()
            continue
        logger.log("ERROR", "Invalid world manager selection.")
        pause()


def show_statistics(
    runtime: RuntimeManager,
    config_manager: ConfigManager,
    db_manager: DatabaseManager,
) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        return
    stats = db_manager.get_server_statistics(current_server)
    print_header(current_server, runtime)
    print(f"{C.BOLD}Statistics for {current_server}{C.RESET}")
    print(f" Total sessions: {stats['total_sessions']}")
    print(f" Total uptime: {format_duration(stats['total_uptime'])}")
    print(f" Average session: {format_duration(stats['avg_duration'])}")
    print(f" Total crashes: {stats['total_crashes']}")
    print(f" Total restarts: {stats['total_restarts']}")
    print(f" Avg RAM usage (24h): {stats['avg_ram_usage_24h'] or 0:.2f}%")
    print(f" Avg CPU usage (24h): {stats['avg_cpu_usage_24h'] or 0:.2f}%")
    print(f" Peak players (24h): {stats['peak_players_24h'] or 0}")
    pause()


def show_console(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        return
    instance = runtime.get_instance(current_server)
    if not instance.is_running():
        logger.log("ERROR", f"{current_server} is not running.")
        pause()
        return
    print(f"{C.CYAN}Attaching to {current_server}. Detach with Ctrl+A then D.{C.RESET}")
    time.sleep(1)
    try:
        subprocess.run(["screen", "-r", instance.screen_name], check=False)
    except FileNotFoundError:
        logger.log("ERROR", "screen is not installed.")
        pause()


def send_command_menu(runtime: RuntimeManager, config_manager: ConfigManager, logger) -> None:
    config = ensure_current_server(config_manager)
    current_server = config.get("current_server")
    if not current_server:
        return
    instance = runtime.get_instance(current_server)
    if not instance.is_running():
        logger.log("ERROR", f"{current_server} is not running.")
        pause()
        return
    while True:
        print_header(current_server, runtime)
        print(f"{C.BOLD}Send command to {current_server}{C.RESET}")
        print(" Leave blank to return.")
        command = input("> ").strip()
        if not command:
            return
        success = instance.send_command(command)
        if not success:
            logger.log("ERROR", "Command delivery failed.")
        time.sleep(1)


def main() -> None:
    logger, config_manager, db_manager, runtime = create_services()
    if not check_base_dependencies(logger):
        raise SystemExit(1)

    while True:
        config = ensure_current_server(config_manager)
        if not config.get("servers"):
            print_header(None, runtime)
            logger.log("INFO", "No servers found. Create one to begin.")
            create_new_server(config_manager, logger)
            pause()
            continue

        current_server = config.get("current_server")
        if not current_server:
            logger.log("ERROR", "No current server is selected.")
            pause()
            continue

        instance = runtime.get_instance(current_server)
        server_config = config["servers"][current_server]
        flavor = server_config.get("server_flavor")
        flavor_name = SERVER_FLAVORS.get(flavor, {}).get("name", "Not installed")
        version = server_config.get("server_version") or "N/A"
        status = (
            f"{C.GREEN}ONLINE{C.RESET}"
            if instance.is_running()
            else f"{C.RED}OFFLINE{C.RESET}"
        )

        print_header(current_server, runtime)
        print(f"{C.BOLD}{current_server}{C.RESET} | Status: {status}")
        print(f"{C.DIM}{flavor_name} {version}{C.RESET}")
        print_connection_summary(instance)
        print()
        print(" 1. Start server")
        print(" 2. Stop server")
        print(" 3. Install or update server")
        print(" 4. Configure server")
        print(" 5. Edit server.properties and eula.txt")
        print(" 6. Attach to console")
        print(" 7. World manager")
        print(" 8. Send command")
        print(" 9. Statistics")
        print("10. Create new server")
        print("11. Switch server")
        print(" 0. Exit")

        choice = input(f"\n{C.BOLD}Choose action: {C.RESET}").strip()
        try:
            if choice == "1":
                started = instance.start()
                if started:
                    instance.print_connection_details()
                pause()
            elif choice == "2":
                force = input("Force stop? (y/N): ").strip().lower() == "y"
                instance.stop(force=force)
                pause()
            elif choice == "3":
                install_server(runtime, config_manager, logger)
                pause()
            elif choice == "4":
                configure_server(runtime, config_manager, logger)
            elif choice == "5":
                edit_server_files(runtime, config_manager, logger)
            elif choice == "6":
                show_console(runtime, config_manager, logger)
            elif choice == "7":
                world_manager(runtime, config_manager, logger)
            elif choice == "8":
                send_command_menu(runtime, config_manager, logger)
            elif choice == "9":
                show_statistics(runtime, config_manager, db_manager)
            elif choice == "10":
                create_new_server(config_manager, logger)
                pause()
            elif choice == "11":
                select_current_server(config_manager, logger)
                pause()
            elif choice == "0":
                if runtime.running_servers():
                    leave_running = input(
                        "Leave running servers active in screen after exit? (Y/n): "
                    ).strip().lower()
                    if leave_running == "n":
                        for server_name in runtime.running_servers():
                            runtime.get_instance(server_name).stop()
                raise SystemExit(0)
            else:
                logger.log("ERROR", "Invalid menu selection.")
                pause()
        except KeyboardInterrupt as exc:
            raise SystemExit(0) from exc
        except Exception as exc:
            logger.log("CRITICAL", f"Unexpected error: {exc}")
            pause()


if __name__ == "__main__":
    main()
