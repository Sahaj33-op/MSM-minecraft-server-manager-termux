#!/usr/bin/env bash

set -euo pipefail

C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_CYAN='\033[96m'

log_info() {
    echo -e "${C_BOLD}${C_CYAN}[INFO]${C_RESET} $1"
}

log_success() {
    echo -e "${C_BOLD}${C_GREEN}[SUCCESS]${C_RESET} $1"
}

log_warning() {
    echo -e "${C_BOLD}${C_YELLOW}[WARNING]${C_RESET} $1"
}

REPO_URL="https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git"
REPO_DIR="MSM-minecraft-server-manager-termux"

log_info "Starting MSM installation..."

if command -v pkg >/dev/null 2>&1; then
    log_info "Updating Termux packages..."
    pkg update
    DEBIAN_FRONTEND=noninteractive
    apt-get upgrade -y -o
    Dpkg::Options::="--force-confdef" -o
    Dpkg::Options::="--force-confold"

    log_info "Installing system dependencies..."
    pkg install python git screen openjdk-17 openjdk-21 php python-psutil -y
else
    log_warning "pkg was not found. Install python3, git, screen, Java, and PHP manually."
fi

if [ -d "${REPO_DIR}" ]; then
    log_warning "${REPO_DIR} already exists. Reusing the existing checkout."
else
    log_info "Cloning the MSM repository..."
    git clone "${REPO_URL}"
fi

cd "${REPO_DIR}"

log_info "Creating a virtual environment..."
python -m venv --system-site-packages .venv

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
