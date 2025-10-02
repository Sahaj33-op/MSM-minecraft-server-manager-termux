#!/bin/bash

# Enhanced MSM Installer v1.0
# This script automates the installation of the Minecraft Server Manager.

# --- ANSI Color Codes ---
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_CYAN='\033[96m'

# --- Helper Functions ---
log_info() {
    echo -e "${C_BOLD}${C_CYAN}[INFO]${C_RESET} $1"
}

log_success() {
    echo -e "${C_BOLD}${C_GREEN}[SUCCESS]${C_RESET} $1"
}

log_warning() {
    echo -e "${C_BOLD}${C_YELLOW}[WARNING]${C_RESET} $1"
}

# --- Installation Steps ---
log_info "Starting MSM installation..."

# 1. Update and upgrade Termux packages
log_info "Updating and upgrading Termux..."
pkg update && pkg upgrade -y

# 2. Install required system dependencies
log_info "Installing dependencies: python, git, wget, screen..."
pkg install python git wget screen -y

# 3. Clone the repository
log_info "Cloning the MSM repository..."
git clone https://github.com/sahaj33-op/MSM-minecraft-server-manager-termux.git
cd MSM-minecraft-server-manager-termux || exit

# 4. Install required Python packages
log_info "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# 5. Make the main script executable
log_info "Setting execute permissions for msm.py..."
chmod +x msm.py

# --- Final Instructions ---
log_success "MSM has been installed successfully!"
echo -e "\nTo run the server manager, use the following command:"
echo -e "${C_GREEN}./msm.py${C_RESET}"
