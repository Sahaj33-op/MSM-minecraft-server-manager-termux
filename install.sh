#!/usr/bin/env bash

set -euo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_CYAN='\033[96m'
C_RED='\033[91m'

log_info() {
    echo -e "${C_BOLD}${C_CYAN}[INFO]${C_RESET} $1"
}

log_success() {
    echo -e "${C_BOLD}${C_GREEN}[SUCCESS]${C_RESET} $1"
}

log_warning() {
    echo -e "${C_BOLD}${C_YELLOW}[WARNING]${C_RESET} $1"
}

log_error() {
    echo -e "${C_BOLD}${C_RED}[ERROR]${C_RESET} $1"
}

REPO_URL="https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git"
REPO_DIR="MSM-minecraft-server-manager-termux"

log_info "Starting MSM installation..."

# ── Dependency installation ───────────────────────────────────────────────────

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
    if [ "$(id -u)" -eq 0 ]; then
        apt-get update -y
        apt-get install -y git screen python3 python3-pip python3-venv \
            openjdk-17-jre-headless php-cli || true
    else
        sudo apt-get update -y
        sudo apt-get install -y git screen python3 python3-pip python3-venv \
            openjdk-17-jre-headless php-cli || true
    fi
    log_warning "Java 21 may not be in the default apt repos on older distros."
    log_warning "For Java 21: sudo apt-get install openjdk-21-jre-headless"
    log_warning "For playit: download from https://playit.gg/download"

elif command -v pacman >/dev/null 2>&1; then
    # ── Arch Linux ────────────────────────────────────────────────────────────
    log_info "Arch Linux detected. Updating packages..."
    if [ "$(id -u)" -eq 0 ]; then
        pacman -Sy --noconfirm git screen python python-pip jre17-openjdk php
    else
        sudo pacman -Sy --noconfirm git screen python python-pip jre17-openjdk php
    fi
    log_warning "For playit: download from https://playit.gg/download"

elif command -v dnf >/dev/null 2>&1; then
    # ── Fedora / RHEL ─────────────────────────────────────────────────────────
    log_info "Fedora/RHEL detected. Installing dependencies..."
    if [ "$(id -u)" -eq 0 ]; then
        dnf install -y git screen python3 python3-pip java-17-openjdk-headless php
    else
        sudo dnf install -y git screen python3 python3-pip java-17-openjdk-headless php
    fi
    log_warning "For playit: download from https://playit.gg/download"

else
    log_warning "Package manager not recognized. Please manually install:"
    log_warning "  git, screen, python3, pip3, python3-venv, Java 17+, php"
fi

# ── Clone or reuse repository ─────────────────────────────────────────────────

if [ -d "${REPO_DIR}" ]; then
    log_warning "${REPO_DIR} already exists. Reusing the existing checkout."
else
    log_info "Cloning the MSM repository..."
    git clone "${REPO_URL}"
fi

cd "${REPO_DIR}"

# ── Python virtual environment ────────────────────────────────────────────────

log_info "Creating a virtual environment..."
# Use python3 on Linux, python works on Termux
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
