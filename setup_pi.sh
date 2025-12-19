#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

# ============================================================================
# PySB-App Setup Script for Raspberry Pi Zero 2W
# ============================================================================
# This script sets up a complete spectrometer application environment including:
# - System packages and Python virtual environment
# - Adafruit PiTFT 2.8" display driver
# - Seabreeze spectrometer library (from local lib/ folder)
# - MCP9808 temperature sensor support via I2C
# - Fan control via GPIO
# - DS3231 RTC module
# - Performance optimizations for fast boot
#
# Run with: sudo ./setup_pi.sh
# ============================================================================

# === Configuration ===
PROJECT_DIR_NAME="pysb-app"
APP_SRC_SUBDIR="pysb-app"  # Source files are in repo/pysb-app/
VENV_DIR_NAME="pysb_venv"
SWAP_SIZE="2G"  # 2GB swap for matplotlib compilation
PKG_MANAGER_TIMEOUT=180

# === Script Variables ===
ACTUAL_USER=""
ACTUAL_HOME=""
PROJECT_DIR_PATH=""
VENV_PATH=""
APP_SRC_DIR=""  # Will be set to script_dir/pysb-app/

# === Helper Functions ===
critical_error() {
    echo "" >&2; echo "ERROR: $1" >&2; echo "Setup failed." >&2; exit 1;
}
warning() {
    echo "" >&2; echo "WARNING: $1" >&2;
}
info() { # Added info function for consistency
    echo "[INFO] $1"
}
check_root() {
    if [ "$(id -u)" -ne 0 ]; then critical_error "This script must be run with sudo or as root."; fi
}
get_actual_user() {
    if [ -n "$SUDO_USER" ]; then ACTUAL_USER="$SUDO_USER"; else
        if [ "$(id -u)" -eq 0 ]; then
             ACTUAL_USER=$(awk -F: '($3 >= 1000) && ($7 !~ /nologin|false/) && ($6 != "") { print $1; exit }' /etc/passwd)
             if [ -z "$ACTUAL_USER" ]; then critical_error "Running as root, could not determine standard user."; fi
             info "Running as root. Assuming user: '$ACTUAL_USER'."
        else ACTUAL_USER=$(whoami); if [ "$(id -u)" -ne 0 ]; then critical_error "Needs root. Run with 'sudo'."; fi; fi
    fi
    ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)
    if [ -z "$ACTUAL_HOME" ] || [ ! -d "$ACTUAL_HOME" ]; then critical_error "No valid home dir for '$ACTUAL_USER'."; fi
    PROJECT_DIR_PATH="$ACTUAL_HOME/$PROJECT_DIR_NAME"; VENV_PATH="$PROJECT_DIR_PATH/$VENV_DIR_NAME"
    # Set source directory (where app files are in the repo)
    local script_src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    APP_SRC_DIR="$script_src_dir/$APP_SRC_SUBDIR"
    info "User: $ACTUAL_USER (home: $ACTUAL_HOME)"; info "Project dir: $PROJECT_DIR_PATH"; info "Venv: $VENV_PATH"
    info "App source: $APP_SRC_DIR"
}
check_internet() {
    info "Checking internet..."; if ping -c 1 8.8.8.8 >/dev/null 2>&1; then info "Internet OK."; else warning "No internet."; fi
}
wait_for_apt_lock() {
    info "Checking package manager locks..."; local locks=( "/var/lib/dpkg/lock*" "/var/lib/apt/lists/lock" "/var/cache/apt/archives/lock" ); local start=$(date +%s)
    while true; do local locked=0
        for lock in "${locks[@]}"; do if sudo fuser $lock >/dev/null 2>&1; then info "Lock: $lock. Waiting..."; locked=1; break; fi; done
        if pgrep -f "apt|dpkg" > /dev/null && [ $locked -eq 0 ]; then info "Waiting for apt/dpkg processes..."; locked=1; fi
        if [ $locked -eq 0 ]; then info "Package manager available."; return 0; fi
        if (( $(date +%s) - start > PKG_MANAGER_TIMEOUT )); then critical_error "Lock timeout. Investigate manually."; fi
        sleep 5; echo -n "."; done
}
check_date_time() {
    info "======================================"; info "Verifying System Date and Time"
    info "Current: $(date)"; read -p "Correct? (y/N): " choice
    if [[ "$choice" != "y" && "$choice" != "Y" ]]; then info "Syncing time via NTP..."
        if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
            sudo systemctl enable systemd-timesyncd --now > /dev/null 2>&1; sudo timedatectl set-ntp true
            info "Waiting for sync (30s max)..."; local synced=false
            for i in {1..15}; do sleep 2; echo -n "."; if timedatectl status | grep -q "System clock synchronized: yes"; then echo " Synced!"; synced=true; break; fi; done
            if $synced; then info "Time synced. New: $(date)"; else warning "Could not sync time."; fi
        else warning "No internet. Cannot sync time."; fi
        info "Manual: sudo timedatectl set-time 'YYYY-MM-DD HH:MM:SS'"
    fi
}
setup_rtc() {
    info "======================================"; info "Setting Up DS3231 RTC Module"
    local cfg="/boot/firmware/config.txt"; if [ ! -f $cfg ]; then cfg="/boot/config.txt"; fi
    if [ ! -f $cfg ]; then warning "config.txt not found. Cannot auto-config RTC."; return; fi
    info "Using config: $cfg"
    if grep -q "dtoverlay=i2c-rtc,ds3231" "$cfg"; then info "RTC overlay already enabled."; else
        info "Adding DS3231 RTC overlay to $cfg..."; echo -e "\n# Enable DS3231 RTC\ndtoverlay=i2c-rtc,ds3231" | sudo tee -a "$cfg" > /dev/null
        info "RTC overlay added. Effective after reboot."
    fi
    if dpkg -l | grep -q fake-hwclock; then info "Removing fake-hwclock..."; wait_for_apt_lock; sudo apt-get -y remove fake-hwclock; sudo update-rc.d -f fake-hwclock remove; else info "fake-hwclock not installed."; fi
    local hwset="/lib/udev/hwclock-set"; if [ -f "$hwset" ]; then
        if [ ! -f "${hwset}.backup_pysb" ]; then sudo cp "$hwset" "${hwset}.backup_pysb"; info "Backed up hwclock-set to ${hwset}.backup_pysb"; fi
        info "Modifying hwclock-set..."; sudo sed -i -E 's/^if \[ -e \/run\/(systemd\/system|udev\/hwclock-set) \] ; then/#&/' "$hwset"; sudo sed -i -E 's/^    exit 0/#&/' "$hwset"; sudo sed -i -E 's/^fi/#&/' "$hwset"
        info "hwclock-set configured."; else warning "hwclock-set not found. Manual config may be needed."; fi
    echo -e "\nNote: After system time is correct, run: sudo hwclock -w\nAfter reboot, verify with: sudo hwclock -r\n"
}
configure_swap() {
    info "======================================"; info "Configuring Swap (Target: ${SWAP_SIZE})"
    local current_total_kb=$(grep SwapTotal /proc/meminfo | awk '{print $2}')
    local target_bytes=$(numfmt --from=iec "$SWAP_SIZE")
    
    if [ -f /swapfile ]; then
        local current_file_bytes=$(sudo stat -c %s /swapfile 2>/dev/null || echo 0)
        info "Existing /swapfile (size: $(numfmt --to=iec $current_file_bytes)). Target: $(numfmt --to=iec $target_bytes)."
        if [ "$current_file_bytes" -lt "$target_bytes" ]; then
            info "Swap file too small. Recreating."; sudo swapoff /swapfile || true; sudo rm -f /swapfile
            sudo fallocate -l "${SWAP_SIZE}" /swapfile || { info "fallocate failed, using dd (slower)..."; sudo dd if=/dev/zero of=/swapfile bs=1M count=$(($(numfmt --from=iec $SWAP_SIZE)/1024/1024)) status=progress || critical_error "dd failed."; }
            sudo chmod 600 /swapfile; sudo mkswap /swapfile; sudo swapon /swapfile
        else info "Existing swap file sufficient."; if ! swapon --show | grep -q /swapfile; then sudo swapon /swapfile; fi; fi
    elif (( current_total_kb * 1024 < target_bytes / 2 )); then # If no /swapfile and total swap is very low
        info "No /swapfile, low total swap. Creating."; sudo fallocate -l "${SWAP_SIZE}" /swapfile || { info "fallocate failed, using dd..."; sudo dd if=/dev/zero of=/swapfile bs=1M count=$(($(numfmt --from=iec $SWAP_SIZE)/1024/1024)) status=progress || critical_error "dd failed."; }
        sudo chmod 600 /swapfile; sudo mkswap /swapfile; sudo swapon /swapfile
    else info "Sufficient swap or /swapfile not used. Skipping creation."; free -h; return 0; fi
    if ! grep -q '^[[:space:]]*/swapfile[[:space:]]' /etc/fstab; then echo "/swapfile none swap sw 0 0" | sudo tee -a /etc/fstab > /dev/null; fi
    info "Swap configured."; free -h
}
configure_needrestart() {
    info "======================================"; info "Configuring needrestart for auto restarts..."
    if [ -f /etc/needrestart/needrestart.conf ]; then
        if grep -q -E "^\s*#?\s*\$nrconf{restart}\s*=\s*'[il]'" /etc/needrestart/needrestart.conf; then
             info "Setting needrestart to auto mode..."; sudo sed -i "s:^\s*#\?\s*\$nrconf{restart}\s*=\s*'[il]':\$nrconf{restart} = 'a':" /etc/needrestart/needrestart.conf
        else info "Needrestart already configured or manually set."; fi
    else info "Needrestart config not found, creating with auto mode."; echo "\$nrconf{restart} = 'a';" | sudo tee /etc/needrestart/needrestart.conf > /dev/null; fi
    echo 'APT::Get::Assume-Yes "true";' | sudo tee /etc/apt/apt.conf.d/99assume-yes > /dev/null
    echo 'DPkg::Options { "--force-confdef"; "--force-confold"; }' | sudo tee /etc/apt/apt.conf.d/90local-dpkg-options > /dev/null
}
update_system() {
    info "======================================"; info "Updating System Packages"
    wait_for_apt_lock; info "Running apt update..."; if ! sudo apt-get update; then warning "apt update failed."; fi
    wait_for_apt_lock; info "Running apt upgrade..."; if ! sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y; then warning "apt upgrade failed."; fi
}
install_system_packages() {
    info "======================================"; info "Installing System Packages"
    local pkgs=( git build-essential pkg-config libusb-dev libudev-dev \
                 python3-pip python3-dev python3-venv vim feh screen wireless-tools i2c-tools \
                 libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
                 libportmidi-dev libfreetype6-dev libjpeg-dev libpng-dev libtiff5-dev \
                 cmake device-tree-compiler libraspberrypi-dev python3-evdev dphys-swapfile \
                 python3-rpi.gpio python3-spidev python3-smbus network-manager # System level for hardware access
    )
    info "Installing: ${pkgs[*]}"; wait_for_apt_lock
    if ! sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkgs[@]}"; then critical_error "Failed to install system packages."; fi
    info "System packages installed."
}
enable_spi_i2c() { # Combined SPI and I2C
    info "======================================"; info "Enabling SPI & I2C Interfaces"
    local cfg="/boot/firmware/config.txt"; if [ ! -f $cfg ]; then cfg="/boot/config.txt"; fi
    if [ ! -f $cfg ]; then warning "config.txt not found. Cannot auto-enable SPI/I2C."; return; fi
    info "Using config: $cfg"
    for iface_param in "dtparam=spi=on" "dtparam=i2c_arm=on"; do
        iface_name=$(echo "$iface_param" | cut -d'=' -f1 | cut -d'=' -f2 | sed 's/dtparam=//; s/_arm//' | tr '[:lower:]' '[:upper:]') # Extracts SPI or I2C
        if grep -q -E "^\s*${iface_param}" "$cfg"; then info "$iface_name interface already enabled."; else
            info "Enabling $iface_name interface..."; sudo sed -i -E "s:^\s*($(echo $iface_param | sed 's/=on/=off/')):#\1:" "$cfg" # Comment out "off" version
            if ! grep -q -E "^\s*${iface_param}" "$cfg"; then echo "$iface_param" | sudo tee -a "$cfg" > /dev/null; fi
            info "$iface_name interface enabled. Reboot required."
        fi
    done
}
setup_user_permissions() {
    info "======================================"; info "Setting User Permissions for Hardware"
    local groups=("video" "i2c" "gpio" "spi" "dialout" "input" "render" "plugdev") # Added input, render, plugdev
    for group in "${groups[@]}"; do
        if getent group "$group" >/dev/null; then
            if groups "$ACTUAL_USER" | grep -q -w "$group"; then info "User '$ACTUAL_USER' already in '$group'."; else
                info "Adding '$ACTUAL_USER' to '$group'..."; if ! sudo usermod -aG "$group" "$ACTUAL_USER"; then warning "Failed add to '$group'."; else info "User added to '$group'. Effective next login/reboot."; fi
            fi; else info "Group '$group' not found. Skipping."; fi
    done
}
configure_terminal() {
    info "======================================"; info "Configuring Terminal History Search"
    local rc="$ACTUAL_HOME/.inputrc"
    if [ -f "$rc" ] && grep -q "history-search-backward" "$rc"; then info "History search already configured."; else
        info "Setting up history search in $rc..."; { echo '$include /etc/inputrc'; echo '"\e[A": history-search-backward'; echo '"\e[B": history-search-forward'; } | sudo -u "$ACTUAL_USER" tee "$rc" > /dev/null
        sudo chown "$ACTUAL_USER:$ACTUAL_USER" "$rc"; info "Terminal history configured. Effective new shells."; fi
}

optimize_boot_performance() {
    info "======================================"; info "Optimizing Boot Performance"
    info "Disabling slow cloud-init services (keeping WiFi config)..."

    # Disable slow cloud-init services (keeps cloud-init.service and cloud-init-local.service for WiFi)
    for svc in cloud-config.service cloud-final.service; do
        if systemctl is-enabled "$svc" &>/dev/null 2>&1; then
            sudo systemctl disable "$svc" 2>/dev/null || true
            sudo systemctl mask "$svc" 2>/dev/null || true
            info "  Disabled: $svc"
        else
            info "  Already disabled: $svc"
        fi
    done

    # Disable snap services (not needed for spectrometer)
    info "Disabling snap services..."
    for svc in snapd.service snapd.socket snapd.seeded.service snap.lxd.activate.service; do
        if systemctl list-unit-files | grep -q "^$svc"; then
            sudo systemctl disable "$svc" 2>/dev/null || true
            sudo systemctl mask "$svc" 2>/dev/null || true
            info "  Disabled: $svc"
        fi
    done

    # Disable NetworkManager-wait-online (WiFi still connects, just doesn't block boot)
    info "Disabling network-wait service..."
    if systemctl is-enabled NetworkManager-wait-online.service &>/dev/null 2>&1; then
        sudo systemctl disable NetworkManager-wait-online.service 2>/dev/null || true
        sudo systemctl mask NetworkManager-wait-online.service 2>/dev/null || true
        info "  Disabled: NetworkManager-wait-online.service"
    else
        info "  Already disabled: NetworkManager-wait-online.service"
    fi

    info "Boot optimization complete. Expected boot time: ~20 seconds (down from 2+ minutes)"
}

install_local_libraries() {
    info "======================================"; info "Installing Local Libraries from lib/ folder"
    # APP_SRC_DIR is set in get_actual_user() and points to repo/pysb-app/
    local lib_src_dir="$APP_SRC_DIR/lib"
    local venv_pip="$VENV_PATH/bin/pip"
    local venv_python="$VENV_PATH/bin/python"

    if [ ! -d "$lib_src_dir" ]; then
        warning "lib/ directory not found in $APP_SRC_DIR. Skipping local library installation."
        return
    fi

    # Install smbus2 for I2C communication (MCP9808 temperature sensor)
    info "Installing smbus2 for I2C temperature sensor..."
    if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir smbus2; then
        warning "Failed to install smbus2. Temperature sensor may not work."
    else
        info "smbus2 installed successfully."
    fi

    # Install pyseabreeze from local lib folder if it exists
    local pyseabreeze_dir="$lib_src_dir/pyseabreeze"
    if [ -d "$pyseabreeze_dir" ]; then
        info "Installing pyseabreeze from local lib/pyseabreeze..."
        if [ -f "$pyseabreeze_dir/setup.py" ] || [ -f "$pyseabreeze_dir/pyproject.toml" ]; then
            # Install in development mode so it uses the local source
            if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir -e "$pyseabreeze_dir"; then
                warning "Failed to install local pyseabreeze. Falling back to pip install..."
                sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir "seabreeze[pyseabreeze]" || warning "pip install seabreeze also failed"
            else
                info "Local pyseabreeze installed successfully."
            fi
        else
            # If no setup.py, just add to PYTHONPATH via .pth file
            info "No setup.py found, adding pyseabreeze to Python path..."
            local site_packages=$("$venv_python" -c "import site; print(site.getsitepackages()[0])")
            echo "$pyseabreeze_dir/src" | sudo -u "$ACTUAL_USER" tee "$site_packages/local_pyseabreeze.pth" > /dev/null
            info "Added pyseabreeze to Python path via .pth file"
        fi
    else
        info "Local pyseabreeze not found, installing from pip..."
        sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir "seabreeze[pyseabreeze]" || warning "Failed to install seabreeze from pip"
    fi

    # Note: Adafruit_Python_MCP9808 is not needed as we use smbus2 directly
    # The temp_sensor.py module handles I2C communication without external Adafruit libraries
    info "Local library installation complete."
}

verify_i2c_setup() {
    info "======================================"; info "Verifying I2C Setup"

    # Check if I2C device nodes exist
    if ls /dev/i2c-* &>/dev/null 2>&1; then
        info "I2C device nodes found:"
        ls -la /dev/i2c-* 2>/dev/null | while read line; do info "  $line"; done
    else
        warning "I2C device nodes not found. They will appear after reboot."
    fi

    # Check if i2c-tools are installed and scan for devices
    if command -v i2cdetect &>/dev/null; then
        info "Scanning I2C bus 1 for devices..."
        local scan_result=$(sudo i2cdetect -y 1 2>/dev/null || echo "scan_failed")
        if [ "$scan_result" != "scan_failed" ]; then
            echo "$scan_result" | while read line; do info "  $line"; done
            # Check for known devices
            if echo "$scan_result" | grep -q "18"; then
                info "  [OK] MCP9808 temperature sensor detected at 0x18"
            fi
            if echo "$scan_result" | grep -q "68"; then
                info "  [OK] DS3231 RTC detected at 0x68"
            fi
        else
            info "I2C scan not available yet. Run 'sudo i2cdetect -y 1' after reboot."
        fi
    else
        info "i2cdetect not available. Install with: sudo apt install i2c-tools"
    fi

    # Check user is in i2c group
    if groups "$ACTUAL_USER" | grep -q -w "i2c"; then
        info "User '$ACTUAL_USER' is in 'i2c' group."
    else
        warning "User '$ACTUAL_USER' is NOT in 'i2c' group. Adding..."
        sudo usermod -aG i2c "$ACTUAL_USER" || warning "Failed to add user to i2c group"
    fi
}

create_systemd_service() {
    info "======================================"; info "Creating Systemd Service for Auto-Start (Optional)"

    local service_file="/etc/systemd/system/pysb-app.service"

    if [ -f "$service_file" ]; then
        info "Systemd service already exists. Skipping."
        return
    fi

    read -p "Create systemd service for auto-start on boot? (y/N): " create_service
    if [[ "$create_service" != "y" && "$create_service" != "Y" ]]; then
        info "Skipping systemd service creation."
        return
    fi

    info "Creating systemd service file..."
    cat << EOF | sudo tee "$service_file" > /dev/null
[Unit]
Description=PySB-App Spectrometer Application
After=multi-user.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR_PATH
Environment="PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_PATH/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    info "Systemd service created. Enable with: sudo systemctl enable pysb-app.service"
    info "Start manually with: sudo systemctl start pysb-app.service"
}

setup_adafruit_pitft() { # New function for Adafruit PiTFT
    info "======================================"; info "Setting up Adafruit PiTFT 2.8c"
    local script_src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" # Directory where this setup_pi.sh is
    local adafruit_repo_dir="$script_src_dir/Raspberry-Pi-Installer-Scripts"

    if [ ! -d "$adafruit_repo_dir" ]; then
        info "Adafruit Installer Scripts repo not found locally. Cloning..."
        if ! git clone https://github.com/adafruit/Raspberry-Pi-Installer-Scripts.git "$adafruit_repo_dir"; then
            critical_error "Failed to clone Adafruit Installer Scripts."
        fi
        sudo chown -R "$ACTUAL_USER:$ACTUAL_USER" "$adafruit_repo_dir" # Own the clone
    else info "Adafruit Installer Scripts repo found at $adafruit_repo_dir"; fi

    if [ ! -f "$adafruit_repo_dir/adafruit-pitft.py" ]; then critical_error "adafruit-pitft.py not found."; fi

    info "Running Adafruit PiTFT Installer for 2.8c, console mode, no-reboot..."
    # Ensure script dependencies (click, adafruit-python-shell) are installed for system python3
    # The Adafruit script is run with `sudo python3`, so its dependencies need to be accessible to that.
    if ! python3 -c "import click; import adafruit_shell" &> /dev/null; then
        info "Installing click & adafruit-python-shell for Adafruit installer script (system-wide)..."
        sudo python3 -m pip install click adafruit-python-shell 
    fi
    
    cd "$adafruit_repo_dir"
    # Choose rotation: 90 for landscape (USB right), 270 for landscape (USB left)
    # Your main.py currently does its own 180 deg rotation. If Adafruit driver handles it, remove Pygame rotation.
    # Let's try --rotation=270 as an example to see if it matches your desired orientation.
    # If --install-type=console, then HDMI should be off and PiTFT is /dev/fb1
    if ! sudo -E env PATH="$PATH" python3 adafruit-pitft.py --display=28c --rotation=270 --install-type=console --reboot=no; then
        warning "Adafruit PiTFT installer script finished with warning/error. Check output. Manual config may be needed."
    else info "Adafruit PiTFT installer script completed."; fi
    cd "$script_src_dir" # Go back to original directory
    info "Adafruit PiTFT setup process finished. Reboot required for display changes."
}

setup_python_venv() {
    info "======================================"; info "Setting Up Python Environment in $PROJECT_DIR_PATH"
    info "Ensuring project directory exists: $PROJECT_DIR_PATH"
    if ! sudo -u "$ACTUAL_USER" mkdir -p "$PROJECT_DIR_PATH"; then critical_error "Failed create project dir."; fi
    info "Checking/Creating venv at: $VENV_PATH"
    if [ ! -d "$VENV_PATH" ]; then info "Creating venv..."; if ! sudo -u "$ACTUAL_USER" python3 -m venv "$VENV_PATH"; then critical_error "Failed create venv."; fi; info "Venv created."; else info "Venv exists."; fi
    
    local venv_python="$VENV_PATH/bin/python"; local venv_pip="$VENV_PATH/bin/pip"
    info "Upgrading pip, setuptools, wheel in venv..."
    sudo -u "$ACTUAL_USER" "$venv_python" -m pip install --no-cache-dir --upgrade pip setuptools wheel

    # APP_SRC_DIR is set in get_actual_user() and points to repo/pysb-app/
    local req_file="$APP_SRC_DIR/requirements.txt"

    if [ -f "$req_file" ]; then
        info "Copying requirements.txt to project directory..."
        sudo -u "$ACTUAL_USER" cp "$req_file" "$PROJECT_DIR_PATH/requirements.txt"
        info "Installing packages from requirements.txt into venv..."
        # Modify requirements.txt on the fly if displayhatmini is there and we don't want it
        local temp_req_file=$(mktemp)
        if grep -q "displayhatmini" "$PROJECT_DIR_PATH/requirements.txt"; then
            info "Temporarily removing 'displayhatmini' from requirements for Adafruit PiTFT setup."
            grep -v "displayhatmini" "$PROJECT_DIR_PATH/requirements.txt" > "$temp_req_file"
            if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir -r "$temp_req_file"; then warning "Failed to install some packages from modified requirements.txt."; fi
            rm "$temp_req_file"
        else
            if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir -r "$PROJECT_DIR_PATH/requirements.txt"; then warning "Failed to install some packages from requirements.txt."; fi
        fi
    else
        warning "requirements.txt not found in script directory. Python packages (except Seabreeze) must be manually specified or installed."
        # Example of direct install if no requirements.txt - customize this list!
        # local python_packages=("matplotlib" "pygame" "pygame-menu" "spidev" "RPi.GPIO" "numpy" "pyusb" "rpi-lgpio" "wheel" "setuptools")
        # for package in "${python_packages[@]}"; do
        #     info "Installing $package into venv..."
        #     if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir "$package"; then
        #         warning "Failed to install Python package '$package'."
        #     fi
        # done
    fi

    info "Python packages installation process finished."
    info "To use the environment: cd $PROJECT_DIR_PATH && source $VENV_DIR_NAME/bin/activate"
    local bashrc="$ACTUAL_HOME/.bashrc"; local hint="echo 'Project env: cd ${PROJECT_DIR_PATH} && source ${VENV_DIR_NAME}/bin/activate'"
    if [ -f "$bashrc" ] && ! grep -Fq "$PROJECT_DIR_PATH" "$bashrc"; then info "Adding venv hint to $bashrc..."
         { echo ""; echo "# Hint for ${PROJECT_DIR_NAME} venv"; echo "$hint"; } | sudo -u "$ACTUAL_USER" tee -a "$bashrc" > /dev/null; sudo chown "$ACTUAL_USER:$ACTUAL_USER" "$bashrc"; fi
}
install_seabreeze() { # Using your original function for Seabreeze
    info "======================================"; info "Installing Seabreeze (Special Handling)"
    local venv_pip="$VENV_PATH/bin/pip"
    info "Installing seabreeze[pyseabreeze] (can take several minutes)..."
    if ! sudo -u "$ACTUAL_USER" "$venv_pip" install --no-cache-dir "seabreeze[pyseabreeze]"; then
        warning "Failed to install seabreeze[pyseabreeze]."; echo "Manual install: cd $PROJECT_DIR_PATH && source $VENV_DIR_NAME/bin/activate && pip install seabreeze[pyseabreeze]"
    else info "Seabreeze installation successful."; fi
}
setup_seabreeze_udev() { # Using your original function
    info "======================================"; info "Setting Seabreeze udev Rules"
    local rules="/etc/udev/rules.d/10-oceanoptics.rules"; local setup_cmd="$VENV_PATH/bin/seabreeze_os_setup"
    if [ -f "$rules" ]; then info "Seabreeze udev rules exist. Skipping."; echo "If needed, remove $rules and re-run, or run manually: sudo $setup_cmd"; return; fi
    if [ ! -x "$setup_cmd" ]; then warning "seabreeze_os_setup not found/executable in venv. Manual setup needed."; return; fi
    info "Running seabreeze_os_setup..."; if ! sudo "$setup_cmd"; then
        warning "seabreeze_os_setup failed."; echo "Manual: cd $PROJECT_DIR_PATH && source $VENV_DIR_NAME/bin/activate && sudo seabreeze_os_setup"
    else info "Seabreeze udev rules installed. Reloading..."; sudo udevadm control --reload-rules && sudo udevadm trigger; info "udev reloaded."; fi
}

copy_project_files_custom() {
    info "======================================"; info "Copying Project Files to $PROJECT_DIR_PATH"
    # APP_SRC_DIR is set in get_actual_user() and points to repo/pysb-app/

    if [ ! -d "$APP_SRC_DIR" ]; then
        critical_error "App source directory not found: $APP_SRC_DIR"
    fi

    # Create necessary directories
    sudo -u "$ACTUAL_USER" mkdir -p "$PROJECT_DIR_PATH/hardware"
    sudo -u "$ACTUAL_USER" mkdir -p "$PROJECT_DIR_PATH/ui"
    sudo -u "$ACTUAL_USER" mkdir -p "$PROJECT_DIR_PATH/data"

    # Copy main application files
    for file in main.py config.py; do
        if [ -f "$APP_SRC_DIR/$file" ]; then
            info "Copying $file..."
            sudo -u "$ACTUAL_USER" cp "$APP_SRC_DIR/$file" "$PROJECT_DIR_PATH/"
        else
            warning "$file not found in $APP_SRC_DIR"
        fi
    done

    # Copy test scripts
    if [ -f "$APP_SRC_DIR/test_temp_sensor.py" ]; then
        info "Copying test_temp_sensor.py..."
        sudo -u "$ACTUAL_USER" cp "$APP_SRC_DIR/test_temp_sensor.py" "$PROJECT_DIR_PATH/"
    fi

    # Copy hardware module
    if [ -d "$APP_SRC_DIR/hardware" ]; then
        info "Copying hardware/ directory..."
        sudo -u "$ACTUAL_USER" cp -r "$APP_SRC_DIR/hardware" "$PROJECT_DIR_PATH/"
    else
        warning "hardware/ directory not found in $APP_SRC_DIR"
    fi

    # Copy UI module
    if [ -d "$APP_SRC_DIR/ui" ]; then
        info "Copying ui/ directory..."
        sudo -u "$ACTUAL_USER" cp -r "$APP_SRC_DIR/ui" "$PROJECT_DIR_PATH/"
    else
        warning "ui/ directory not found in $APP_SRC_DIR"
    fi

    # Copy data module
    if [ -d "$APP_SRC_DIR/data" ]; then
        info "Copying data/ directory..."
        sudo -u "$ACTUAL_USER" cp -r "$APP_SRC_DIR/data" "$PROJECT_DIR_PATH/"
    else
        warning "data/ directory not found in $APP_SRC_DIR"
    fi

    # Copy assets directory
    if [ -d "$APP_SRC_DIR/assets" ]; then
        info "Copying assets/ directory..."
        sudo -u "$ACTUAL_USER" cp -r "$APP_SRC_DIR/assets" "$PROJECT_DIR_PATH/"
    else
        warning "assets/ directory not found in $APP_SRC_DIR"
    fi

    # Copy lib directory (for local pyseabreeze and other vendored libraries)
    if [ -d "$APP_SRC_DIR/lib" ]; then
        info "Copying lib/ directory..."
        sudo -u "$ACTUAL_USER" cp -r "$APP_SRC_DIR/lib" "$PROJECT_DIR_PATH/"
    fi

    # Copy requirements.txt if exists
    if [ -f "$APP_SRC_DIR/requirements.txt" ]; then
        info "Copying requirements.txt..."
        sudo -u "$ACTUAL_USER" cp "$APP_SRC_DIR/requirements.txt" "$PROJECT_DIR_PATH/"
    fi

    sudo chown -R "$ACTUAL_USER:$ACTUAL_USER" "$PROJECT_DIR_PATH"
    info "Project files copied successfully."
}

verify_setup() {
    info "======================================"; info "Verifying Setup (Comprehensive Checks)"

    local venv_py="$VENV_PATH/bin/python"
    if [ ! -x "$venv_py" ]; then
        warning "Venv Python not found. Skipping package check."
        return
    fi

    # Check SPI device nodes
    info "Checking for SPI device nodes..."
    if ls /dev/spidev* >/dev/null 2>&1; then
        info "  SPI devices found:"
        ls -l /dev/spidev* 2>/dev/null | while read line; do info "    $line"; done
    else
        info "  SPI device nodes not found (expected until reboot)."
    fi

    # Check I2C device nodes
    info "Checking for I2C device nodes..."
    if ls /dev/i2c-* >/dev/null 2>&1; then
        info "  I2C devices found:"
        ls -l /dev/i2c-* 2>/dev/null | while read line; do info "    $line"; done
    else
        info "  I2C device nodes not found (expected until reboot)."
    fi

    # Check Python packages
    info "Checking Python packages in venv..."
    local pkgs_check=("matplotlib" "pygame" "pygame_menu" "spidev" "RPi.GPIO" "numpy" "pyusb" "smbus2")
    local failed=()

    for pkg in "${pkgs_check[@]}"; do
        if sudo -u "$ACTUAL_USER" "$venv_py" -c "import $pkg" >/dev/null 2>&1; then
            echo "    [OK] $pkg"
        else
            echo "    [FAILED] $pkg"
            failed+=("$pkg")
        fi
    done

    # Check seabreeze specifically
    info "Checking seabreeze:"
    if sudo -u "$ACTUAL_USER" "$venv_py" -c "import seabreeze" >/dev/null 2>&1; then
        echo "    [OK] seabreeze"
    else
        echo "    [FAILED] seabreeze (check install)"
    fi

    # Summary
    if [ ${#failed[@]} -gt 0 ]; then
        warning "Python packages failed import: ${failed[*]}"
        info "You can install missing packages with:"
        info "  cd $PROJECT_DIR_PATH && source $VENV_DIR_NAME/bin/activate"
        for pkg in "${failed[@]}"; do
            info "  pip install $pkg"
        done
    else
        info "All checked Python packages imported successfully."
    fi

    # Check project files
    info "Checking project files..."
    local required_files=("main.py" "config.py" "hardware/temp_sensor.py" "ui/menu_system.py")
    for file in "${required_files[@]}"; do
        if [ -f "$PROJECT_DIR_PATH/$file" ]; then
            echo "    [OK] $file"
        else
            echo "    [MISSING] $file"
        fi
    done
}

# === Main Script Logic ===
main() {
    info "====================================="
    info "PySB-App Setup Script for Raspberry Pi Zero 2W"
    info "====================================="
    info "Target OS: Ubuntu 22.04 LTS Server"
    info "Project: ~/$PROJECT_DIR_NAME"
    info "Venv: $VENV_DIR_NAME"
    echo "====================================="

    # Initial checks
    check_root
    get_actual_user
    check_date_time
    check_internet

    # System configuration
    configure_swap              # 2GB swap for matplotlib compilation
    configure_needrestart       # Auto-restart services during updates
    update_system               # apt update && upgrade
    install_system_packages     # Build tools, I2C tools, pygame dependencies

    # Hardware interfaces
    enable_spi_i2c              # Enable SPI and I2C in boot config
    setup_rtc                   # DS3231 RTC module setup
    setup_adafruit_pitft        # PiTFT 2.8" display driver
    setup_user_permissions      # Add user to hardware groups (i2c, gpio, spi, etc.)
    configure_terminal          # Bash history search

    # Performance optimization (faster boot)
    optimize_boot_performance   # Disable slow cloud-init, snap, network-wait services

    # Python environment and application
    setup_python_venv           # Create venv, install from requirements.txt
    copy_project_files_custom   # Copy main.py, config.py, hardware/, ui/, data/, assets/, lib/
    install_local_libraries     # Install smbus2, pyseabreeze from lib/
    install_seabreeze           # Fallback: install seabreeze from pip if local install failed
    setup_seabreeze_udev        # udev rules for spectrometer USB access

    # Verification
    verify_i2c_setup            # Check I2C bus and devices
    verify_setup                # Check all packages and files

    # Optional: Create systemd service for auto-start
    create_systemd_service

    # Set RTC from system time
    info "Attempting to set hardware RTC from system time..."
    if sudo hwclock -w 2>/dev/null; then
        info "Hardware RTC set to: $(sudo hwclock -r 2>/dev/null || echo 'unknown')"
    else
        warning "Failed to write to hardware clock. Ensure RTC is connected and time is correct."
    fi

    # Final summary
    echo ""
    info "====================================="
    info "Setup Complete!"
    info "====================================="
    echo ""
    info "IMPORTANT: A REBOOT is REQUIRED for:"
    info "  - Display drivers to take effect"
    info "  - I2C/SPI interfaces to be available"
    info "  - User group permissions to be active"
    info "  - Boot optimizations to be applied"
    echo ""
    info "Run: sudo reboot"
    echo ""
    info "After reboot, SSH back in and run:"
    info "  cd $PROJECT_DIR_PATH"
    info "  source $VENV_DIR_NAME/bin/activate"
    info "  python3 main.py"
    echo ""
    info "Useful test commands:"
    info "  # Test temperature sensor"
    info "  python3 test_temp_sensor.py"
    echo ""
    info "  # Test I2C devices"
    info "  sudo i2cdetect -y 1"
    echo ""
    info "  # Test spectrometer"
    info "  python -m seabreeze.cseabreeze_backend ListDevices"
    echo ""
    info "  # Test RTC"
    info "  sudo hwclock -r"
    echo ""
    info "====================================="
}

main # Execute
