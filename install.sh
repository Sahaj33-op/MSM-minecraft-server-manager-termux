#!/usr/bin/env bash

set -euo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_CYAN='\033[96m'
C_RED='\033[91m'

log_info()    { echo -e "${C_BOLD}${C_CYAN}[INFO]${C_RESET} $*"; }
log_success() { echo -e "${C_BOLD}${C_GREEN}[SUCCESS]${C_RESET} $*"; }
log_warning() { echo -e "${C_BOLD}${C_YELLOW}[WARNING]${C_RESET} $*"; }
log_error()   { echo -e "${C_BOLD}${C_RED}[ERROR]${C_RESET} $*"; }

REPO_URL="https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git"
REPO_DIR="MSM-minecraft-server-manager-termux"

log_info "Starting MSM installation..."

# ---------------------------------------------------------------------------
# Privilege escalation
#
# When the script is piped from curl (`curl ... | bash`) stdin is the pipe,
# so 'sudo' cannot prompt for a password interactively.  We handle three
# cases:
#
#   1. Already running as root            -> use commands directly
#   2. Passwordless / cached sudo works   -> prefix commands with sudo
#   3. Neither                            -> print instructions and exit
#
# The recommended one-liner for non-root users is therefore:
#   curl -fsSL <URL> | sudo bash
# ---------------------------------------------------------------------------

if [ "$(id -u)" -eq 0 ]; then
    _SUDO=""
elif command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    _SUDO="sudo"
else
    log_error "Root privileges are required to install system dependencies."
    log_info  "Please re-run using one of these commands:"
    log_info  "  curl -fsSL https://raw.githubusercontent.com/sahaj33-op/MSM-minecraft-server-manager-termux/main/install.sh | sudo bash"
    log_info  "  -- OR log in as root and re-run --"
    exit 1
fi

# Wrapper: prepends sudo only when needed
priv() {
    if [ -n "$_SUDO" ]; then
        sudo "$@"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# apt Java helper: tries multiple candidate package names in order and
# installs the first one that exists in the local apt cache.
# ---------------------------------------------------------------------------
install_java_apt() {
    # Try newest-first so Debian Trixie (Java 21 only) and older LTS
    # (Java 17 preferred) both work automatically.
    local -a candidates=(
        "openjdk-21-jre-headless"
        "openjdk-17-jre-headless"
        "openjdk-21-jre"
        "default-jre-headless"
    )
    for pkg in "${candidates[@]}"; do
        if apt-cache show "$pkg" >/dev/null 2>&1; then
            log_info "Installing Java ($pkg)..."
            priv apt-get install -y "$pkg"
            return 0
        fi
    done
    log_warning "No Java package found in apt repos."
    log_warning "Please install Java 17 or 21 manually before starting a server."
}

# ---------------------------------------------------------------------------
# Dependency installation
# ---------------------------------------------------------------------------

if command -v pkg >/dev/null 2>&1; then
    # ── Termux ────────────────────────────────────────────────────────────────
    log_info "Termux detected. Updating packages..."
    pkg update -y
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold"

    log_info "Installing system dependencies..."
    pkg install python git screen openjdk-17 openjdk-21 php python-psutil -y

    log_info "Installing playit tunnel support via tur-repo..."
    if ! pkg list-installed tur-repo >/dev/null 2>&1; then
        pkg install tur-repo -y
    fi
    if ! command -v playit >/dev/null 2>&1; then
        pkg install playit -y || log_warning "playit installation failed; install manually later."
    fi
    if command -v playit >/dev/null 2>&1 && ! command -v playit-cli >/dev/null 2>&1; then
        ln -sf "$(command -v playit)" "$PREFIX/bin/playit-cli" 2>/dev/null || true
    fi

elif command -v apt-get >/dev/null 2>&1; then
    # ── Debian / Ubuntu / WSL ─────────────────────────────────────────────────
    log_info "Debian/Ubuntu detected. Updating packages..."
    priv apt-get update -y

    # Install base tools first — these are always available
    log_info "Installing base dependencies..."
    priv apt-get install -y git screen python3 python3-pip python3-venv

    # Java — use the helper so we pick whichever version is in this distro's repos
    install_java_apt

    # php-cli is only needed for PocketMine/Bedrock; skip gracefully if absent
    log_info "Installing php-cli (optional, for Bedrock/PocketMine servers)..."
    priv apt-get install -y php-cli 2>/dev/null \
        || log_warning "php-cli not available; PocketMine/Bedrock servers will not work."

    log_warning "For playit tunnel support: download from https://playit.gg/download"

elif command -v pacman >/dev/null 2>&1; then
    # ── Arch Linux ────────────────────────────────────────────────────────────
    log_info "Arch Linux detected."
    priv pacman -Sy --noconfirm git screen python python-pip jre21-openjdk php
    log_warning "For playit: download from https://playit.gg/download"

elif command -v dnf >/dev/null 2>&1; then
    # ── Fedora / RHEL ─────────────────────────────────────────────────────────
    log_info "Fedora/RHEL detected."
    priv dnf install -y git screen python3 python3-pip java-21-openjdk-headless php
    log_warning "For playit: download from https://playit.gg/download"

else
    log_warning "Package manager not recognized."
    log_warning "Please manually install: git, screen, python3, pip3, python3-venv, Java 17+, php"
fi

# ---------------------------------------------------------------------------
# Clone or reuse repository
# ---------------------------------------------------------------------------

if [ -d "${REPO_DIR}" ]; then
    log_warning "${REPO_DIR} already exists. Reusing the existing checkout."
else
    log_info "Cloning the MSM repository..."
    git clone "${REPO_URL}"
fi

cd "${REPO_DIR}"

# ---------------------------------------------------------------------------
# Python virtual environment
# ---------------------------------------------------------------------------

log_info "Creating a virtual environment..."
PYTHON_BIN="python3"
if ! command -v python3 >/dev/null 2>&1 && command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

"$PYTHON_BIN" -m venv --system-site-packages .venv

log_info "Installing Python dependencies inside .venv..."
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

log_info "Setting execute permissions for msm.py..."
chmod +x msm.py

log_success "MSM has been installed successfully."
echo -e "\nRun MSM with:"
echo -e "${C_GREEN}source .venv/bin/activate && python msm.py${C_RESET}"
