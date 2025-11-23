# OPEN SPECTROMETER

This library allows you to use the Ocean Optics ST-VIS range of spectrometers using a Raspberry Pi Zerro 2W and a LCD display to view spectra using the Seabreeze API. This allows for a very small low power package that can easily be integrated into a small handheld device for field work. 

Lots of love to the the people working on keeping the PySeabreeze API alive. This let me get the Ocena Optic Spectrometer working on an ARM device. 

## Installing Pyseabreeze on Ubuntu PC for testing the spectrometer

```sh
cd
mkdir pysb
cd pysb
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install seabreeze[pyseabreeze]
seabreeze_os_setup
```

## 2 inch RPi Display For RPi

Flash the Raspberry Pi Zeroe 2 W with Ubuntu 22.04 Server LTS

```sh
sudo apt install rpi-imager
```

Setup parameters:
1. Raspberry Pi Device: Raspberry Pi Zeroe 2 W
2. Operating System: Ubuntu 22.04 Server LTS (https://ubuntu.com/tutorials/how-to-install-ubuntu-on-your-raspberry-pi#1-overview)
3. Stoage - Use a Samsung 128GB PRO Plus microSD Card or high quality SD card. Get the best one you can afford from a reputable supplier. Don't be cheap here.
4. Select `Edit Settings`
  1. Set hostname: `rpi`
  2.Tick `Set username and password`
  3. Set username: `pi`
  4. Set password: `spectro`
  5. Tick `Configure wireless LAN`
  6. Enter known wifi name (I use my mobile hotspot name so I can access this easily in the field)
  7. Enter wifi password I use my mobile hotspot password so I can access this easily in the field)
  8. Set Wireless LAN country: `AU`
  9. Tick `Set locale settings`
  10. Timezone: `Australia/Brisbane`
  11. Keyboard Layout: `US`
  12. Select Services Tab
  13. Tick `Enable SSH - Use password authentication`
  14. Click Save
  15. Click Yes to apply OS customisation settings when you write the image to the storage device.

This will flash the OS to the SD card.

Enable your mobile phone hotspot so it can connect to the wifi.
Insert the SD card into the Raspberry Pi. 
Boot up the Raspberry Pi.
*Note: When first booting *
Check you mobile phone hotspot. 
When a connection is detected, you Raspberry Pi will have internet access. Check you mobile phone hotspot connections. The Raspberry Pi should show. Click on this and you should be able to see the IP address.
Connect you laptops wifi to your mobile phone hotspot. 
From a terminal on you PC SSH into the Raspberry Pi.

```sh
ping rpi.local
# Copy IP address from ping below into <IP>
ssh -X pi@<IP>
```
Enter password: spectro

### Add a new wifi connection

1. Insert the SD card into your computer.
2. Navigate to the root filesystem on the SD card. You should see a directory structure similar to a Linux system.
3. Find and edit the network configuration file. On Ubuntu 22.04 Server, this is typically located at /etc/netplan/50-cloud-init.yaml (or similar).
4. Open this file with a text editor. On Ubuntu: 

```sh
sudo vim 50-cloud-init.yaml
```

If you're on Windows, make sure to use an editor that preserves Linux line endings (like Notepad++, VS Code, etc.). 
5. Add your new WiFi network to the existing configuration. Here's an example of how to modify the file:

```sh
# This file is generated from information provided by the datasource.  Changes
# to it will not persist across an instance reboot.  To disable cloud-init's
# network configuration capabilities, write a file
# /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg with the following:
# network: {config: disabled}
network:
    version: 2
    wifis:
        renderer: networkd
        wlan0:
            access-points:
                wifi_name:
                    password: password
                new_wifi_name:
                    password: new_password
            dhcp4: true
            optional: true
```
Make sure the indentation is consistent.

6 If using the vim editor save (esc -> shift + : -> wq -> enter)
7. Insert the SD card back in the Pi and power it on. 
8. If you did it correctly it will show the new wifi connection and the IP address in the menu.

### Setting up the Raspberry Pi software for the LCD

```sh
cd
nano setup_pi.sh
```

Copy the code into the text file editor.

```sh
chmod +x setup_pi.sh
sudo ./setup_pi.sh
```
## Run the main script

```sh
cd pysb-app/
vim main.py
```

Copy the main.py script

```sh
mkdir assets
```

From whereever I have saved the fonts and images:

```sh
scp -r . pi@rpi.local:~/pysb-app/assets/
```

Now run the script:

```py
source venv/bin/activate
python3 main.py
```

## Editing the codebase

ORCA Open Spectro runs by default at startup. To disable this so you can test the code, stop the service.

```bash
sudo systemctl stop pysb-app.service # password: spectro
pi@ada:~$ cd pysb-app/
pi@ada:~/pysb-app$ source pysb_venv/bin/activate
(pysb_venv) pi@ada:~/pysb-app$ vim main.py 
(pysb_venv) pi@ada:~/pysb-app$ python3 main.py 
```




## Underwater Spectrometer Data Download Guide

This guide explains how to download spectral data (CSV files and PNG images) from your Raspberry Pi-based underwater spectrometer to your computer.

### 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Method 1: Using the Download Script (Recommended)](#method-1-using-the-download-script-recommended)
- [Method 2: Manual Download with rsync](#method-2-manual-download-with-rsync)
- [Method 3: Using SCP for Single Files](#method-3-using-scp-for-single-files)
- [Troubleshooting](#troubleshooting)
- [Data Organization](#data-organization)
- [Additional Tips](#additional-tips)

### 🔍 Overview

The spectrometer automatically saves data in date-organized folders on the Raspberry Pi:
```
~/pysb-app/spectra_data/
├── 2025-05-31/
│   ├── spectra_log.csv
│   ├── spectrum_001.png
│   └── spectrum_002.png
├── 2025-06-01/
│   ├── spectra_log.csv
│   └── spectrum_001.png
└── 2025-07-16/
    ├── spectra_log.csv
    ├── spectrum_001.png
    └── spectrum_002.png
```

### 🛠️ Prerequisites

#### For Ubuntu Users
- Ubuntu 18.04 or later
- Terminal access
- Network connection to the Raspberry Pi

#### For Windows Users (WSL)
- Windows 10 version 2004 or later, or Windows 11
- Windows Subsystem for Linux (WSL) installed
- Ubuntu distribution installed in WSL

##### Installing WSL on Windows:
1. **Enable WSL** (Run as Administrator in PowerShell):
   ```powershell
   wsl --install
   ```

2. **Install Ubuntu** (if not automatically installed):
   ```powershell
   wsl --install -d Ubuntu
   ```

3. **Launch WSL**:
   - Press `Windows Key + R`, type `wsl`, press Enter
   - Or search for "Ubuntu" in Start Menu

#### Required Information
- **Raspberry Pi IP Address**: Find this in the spectrometer menu under "IP"
- **Username**: Usually `pi` (check with your system administrator)
- **Password**: Set during initial setup

### 🚀 Quick Start

1. **Connect to your Raspberry Pi**:
   ```bash
   ssh pi@YOUR_PI_IP_ADDRESS
   ```

2. **Download and run the script**:
   ```bash
   curl -O https://raw.githubusercontent.com/yourusername/yourrepository/main/download_spectra_data.sh
   chmod +x download_spectra_data.sh
   ./download_spectra_data.sh
   ```

3. **Follow the interactive prompts** to select and download your data.

### 📥 Method 1: Using the Download Script (Recommended)

#### Step 1: Connect to the Raspberry Pi

**Ubuntu/WSL Terminal:**
```bash
ssh pi@192.168.1.100
# Replace 192.168.1.100 with your Pi's actual IP address
```

**First time connection**: You'll see a security prompt. Type `yes` and press Enter.

#### Step 2: Install the Download Script

**Option A: Download directly (if you have internet on the Pi):**
```bash
wget https://raw.githubusercontent.com/yourusername/yourrepository/main/download_spectra_data.sh
chmod +x download_spectra_data.sh
```

**Option B: Create the script manually:**
```bash
nano download_spectra_data.sh
# Copy and paste the script content, then save with Ctrl+X, Y, Enter
chmod +x download_spectra_data.sh
```

#### Step 3: Run the Script

**Basic usage:**
```bash
./download_spectra_data.sh
```

**Download to custom location:**
```bash
./download_spectra_data.sh ~/Desktop/my_spectra_data
```

#### Step 4: Follow Interactive Prompts

The script will:
1. Show available data collection dates
2. Let you select which date to download
3. Choose download location
4. Download all files for that date
5. Show a summary of downloaded files

**Example interaction:**

```
Available data collection dates:
=================================
 1) 2025-05-31 (45 files)
 2) 2025-06-01 (23 files)
 3) 2025-07-16 (67 files)

Enter the number of the date you want to download (or 'q' to quit): 3

✓ Selected date: 2025-07-16
ℹ Starting download of data from 2025-07-16...
```

#### Step 5: Transfer to Your Computer

**From Pi to your computer:**
```bash
# Exit the Pi connection
exit

# Download from Pi to your computer
scp -r pi@192.168.1.100:~/Downloads/spectra_download/2025-07-16 ./
```

### 📦 Method 2: Manual Download with rsync

#### Step 1: Direct Download from Pi to Computer

**Ubuntu/WSL:**
```bash
# Create local directory
mkdir -p ~/spectra_data

# Download specific date
rsync -av --progress pi@192.168.1.100:~/pysb-app/spectra_data/2025-07-16/ ~/spectra_data/2025-07-16/

# Download all data
rsync -av --progress pi@192.168.1.100:~/pysb-app/spectra_data/ ~/spectra_data/
```

#### Step 2: List Available Dates First

```bash
# List available dates on Pi
ssh pi@192.168.1.100 'ls -la ~/pysb-app/spectra_data/'

# Count files in each date folder
ssh pi@192.168.1.100 'for dir in ~/pysb-app/spectra_data/*/; do echo "$(basename "$dir"): $(find "$dir" -type f | wc -l) files"; done'
```

### 📄 Method 3: Using SCP for Single Files

#### Download Specific Files

**Download single CSV file:**
```bash
scp pi@192.168.1.100:~/pysb-app/spectra_data/2025-07-16/spectra_log.csv ./
```

**Download all PNG files from a date:**
```bash
scp pi@192.168.1.100:~/pysb-app/spectra_data/2025-07-16/*.png ./images/
```

**Download entire folder:**
```bash
scp -r pi@192.168.1.100:~/pysb-app/spectra_data/2025-07-16/ ./2025-07-16/
```

### 🔧 Troubleshooting

#### Common Issues

**"Permission denied" error:**
```bash
# Make sure you have the correct username and password
ssh pi@192.168.1.100

# Check if the data directory exists
ls -la ~/pysb-app/spectra_data/
```

**"Connection refused" error:**
```bash
# Check if SSH is enabled on Pi
sudo systemctl status ssh

# Enable SSH if needed
sudo systemctl enable ssh
sudo systemctl start ssh
```

**"No such file or directory":**
```bash
# Check if spectrometer has been run and data collected
ssh pi@192.168.1.100 'ls -la ~/pysb-app/spectra_data/'
```

**Large file transfer interrupted:**
```bash
# Resume with rsync
rsync -av --progress --partial pi@192.168.1.100:~/pysb-app/spectra_data/2025-07-16/ ~/spectra_data/2025-07-16/
```

#### Windows WSL Specific Issues

**Can't access downloaded files in Windows:**
```bash
# Files are in WSL, access them via:
# \\wsl$\Ubuntu\home\yourusername\spectra_data

# Or copy to Windows directory:
cp -r ~/spectra_data /mnt/c/Users/YourUsername/Desktop/
```

**WSL Ubuntu not found:**
```powershell
# List installed distributions
wsl --list

# Install Ubuntu if needed
wsl --install -d Ubuntu
```

### 📊 Data Organization

#### CSV Files
- **spectra_log.csv**: Contains all spectral measurements with metadata
- **Columns**: Timestamp, Wavelength, Intensity, Collection Mode, Lens Type, etc.

#### PNG Files
- **spectrum_001.png, spectrum_002.png**: Individual spectrum plots
- **High-resolution images** suitable for publications
- **Automatically generated** for each measurement

#### Folder Structure After Download
```
~/spectra_data/
├── 2025-07-16/
│   ├── spectra_log.csv          # All measurements from this date
│   ├── spectrum_001.png         # First spectrum plot
│   ├── spectrum_002.png         # Second spectrum plot
│   └── ...
└── 2025-06-01/
    ├── spectra_log.csv
    └── spectrum_001.png
```

### 💡 Additional Tips

#### 1. Automated Backup Script
Create a scheduled download script:
```bash
#!/bin/bash
# backup_spectra.sh
DATE=$(date +%Y-%m-%d)
rsync -av --progress pi@192.168.1.100:~/pysb-app/spectra_data/ ~/spectra_backup/$DATE/
```

#### 2. Monitoring Data Collection
```bash
# Check if new data is being collected
ssh pi@192.168.1.100 'ls -lt ~/pysb-app/spectra_data/*/spectra_log.csv | head -5'

# Monitor file sizes
ssh pi@192.168.1.100 'du -sh ~/pysb-app/spectra_data/*/'
```

#### 3. Data Validation
```bash
# Check CSV file integrity
head -n 5 spectra_log.csv
wc -l spectra_log.csv

# Verify PNG files can be opened
file *.png
```

#### 4. Network Configuration
If you can't connect to the Pi:
```bash
# Find Pi on network
nmap -sn 192.168.1.0/24 | grep -B 2 -A 2 "Raspberry"

# Or use the Pi's hostname
ssh pi@raspberrypi.local
```

#### 5. Using SSH Keys (Optional)
Set up passwordless access:
```bash
# Generate SSH key (on your computer)
ssh-keygen -t rsa -b 4096

# Copy to Pi
ssh-copy-id pi@192.168.1.100
```

### 🆘 Support

If you encounter issues:

1. **Check the Pi's IP address** in the spectrometer menu
2. **Ensure SSH is enabled** on the Raspberry Pi
3. **Verify network connectivity** with `ping 192.168.1.100`
4. **Check if data directory exists** with `ls ~/pysb-app/spectra_data/`

### 📝 Script Options

The download script supports several options:

```bash
# Show help
./download_spectra_data.sh --help

# Download to custom location
./download_spectra_data.sh ~/Desktop/my_data

# Default download location
./download_spectra_data.sh
# Downloads to ~/Downloads/spectra_download/
```

## Raspberry Pi breakout PCB

A custom PCB was built to add a USB-C power input, Blue Robotics waterproof power switch, real time clock (RTC) and battery, leak sensor and button inputs. An I2C and UART breakout was also added just for fun.

This complete schematic and board design can be found in the PCB folder. 

![image](https://github.com/user-attachments/assets/a64ad8f9-ed21-4b6f-b43d-9462d401118d)

![image](https://github.com/user-attachments/assets/7c0f146f-47bb-43a3-b808-453892763aac)

Leak sensor is based on the Blue Robotics leak sensor and uses Blue Robotics SOS leak sensor probes.

![image](https://github.com/user-attachments/assets/3c34cd6f-63d9-44bc-a1fa-a32ff59414d8)

RTC is based on Adafruit's I2C DS3231 module.

![image](https://github.com/user-attachments/assets/7edfee91-a727-4598-ba51-139883b82f8c)

## Power Usage:

Using a 10000mAh battery pack, the Raspberry Pi and spectrometer setup for approximately 10 hours and 18 minutes under the current load conditions.

Current during spectrometer live feed: ~0.6A 
Voltage: 5.099V
Power consumption = Voltage × Current
Power consumption = 5.099V × 0.6A = 3.06W
Energy capacity = 10000mAh × 3.7V ÷ 1000 = 37Wh
Assuming a typical efficiency rate: 85%
Actual available energy = 37Wh × 0.85 = 31.45Wh
Runtime = Available energy ÷ Power consumption
Runtime = 31.45Wh ÷ 3.06W ≈ 10.3 hours


