# ORCA Open Spectrometer

A portable, low-power spectrometer system using Ocean Optics ST-VIS spectrometers with a Raspberry Pi Zero 2W and touchscreen display. Designed for field work and scientific research.

Built on the [PySeabreeze](https://github.com/ap--/python-seabreeze) library.

---

## Quick Start Guide

This guide will help you set up a Raspberry Pi Zero 2W from scratch. Follow each step in order.

**Estimated time:** 30-45 minutes (mostly waiting for installations)

---

## Step 1: What You Need

### Hardware

- Raspberry Pi Zero 2W
- Adafruit PiTFT 2.8" Resistive Touchscreen (Product ID: 1601)
- High-quality microSD card (32GB or larger, Class 10 or better)
- Ocean Optics compatible spectrometer (ST-VIS series)
- USB power supply (2.5A recommended)
- A computer with an SD card reader

### Optional Hardware

- DS3231 RTC module (keeps time when powered off)
- MCP9808 temperature sensor
- Cooling fan with MOSFET control
- Custom PCB (see Hardware section below)

### Software (on your computer)

- Raspberry Pi Imager - [Download here](https://www.raspberrypi.com/software/)
- SSH client (built into Mac/Linux, use PuTTY on Windows)

---

## Step 2: Flash Ubuntu to the SD Card

### 2.1 Install Raspberry Pi Imager

**On Ubuntu/Debian:**

```bash
sudo apt install rpi-imager
```

**On other systems:** Download from <https://www.raspberrypi.com/software/>

### 2.2 Flash the Operating System

1. Insert your microSD card into your computer
2. Open **Raspberry Pi Imager**
3. Click **"Choose Device"** → Select **Raspberry Pi Zero 2 W**
4. Click **"Choose OS"** → Select **Other general-purpose OS** → **Ubuntu** → **Ubuntu Server 22.04 LTS (64-bit)**
5. Click **"Choose Storage"** → Select your microSD card
6. Click **"Next"**

### 2.3 Configure Settings (Important!)

When prompted "Would you like to apply OS customization settings?", click **"Edit Settings"**

**General Tab:**

| Setting | Value |
|---------|-------|
| Set hostname | `rpi` |
| Set username and password | Username: `pi`, Password: `spectro` |
| Configure wireless LAN | Check this box |
| SSID | Your WiFi network name |
| Password | Your WiFi password |
| Wireless LAN country | Your country code (e.g., `AU`, `US`, `GB`) |
| Set locale settings | Check this box |
| Time zone | Your timezone (e.g., `Australia/Brisbane`) |
| Keyboard layout | `us` |

**Services Tab:**

| Setting | Value |
|---------|-------|
| Enable SSH | Check this box |
| Use password authentication | Select this option |

1. Click **"Save"**
2. Click **"Yes"** to apply OS customization
3. Click **"Yes"** to confirm and start writing
4. Wait for the write and verification to complete
5. Remove the SD card when prompted

---

## Step 3: First Boot

1. Insert the microSD card into the Raspberry Pi
2. Connect the PiTFT display (if not already connected)
3. Make sure your WiFi network is available (turn on your phone hotspot if using that)
4. Connect power to the Raspberry Pi
5. Wait 2-3 minutes for the first boot to complete

---

## Step 4: Connect via SSH

You need to connect to the Pi from your computer to run the setup.

### 4.1 Find the Pi's IP Address

**Option A - Try the hostname first:**

```bash
ping rpi.local
```

If you see replies with an IP address, use that IP.

**Option B - Scan your network:**

On Linux/Mac:

```bash
# First, find your network range
ip addr show | grep "inet "
# Look for something like: inet 192.168.1.50/24
# Your network is 192.168.1.0/24

# Scan for devices
nmap -sn 192.168.1.0/24
# Look for "Raspberry Pi" in the results
```

**Option C - Check your router's admin page:**
Log into your router and look for connected devices named "rpi"

### 4.2 Connect via SSH

```bash
ssh pi@<IP_ADDRESS>
```

Replace `<IP_ADDRESS>` with the actual IP (e.g., `ssh pi@192.168.1.100`)

When prompted:

- Type `yes` to accept the host key (first time only)
- Enter password: `spectro`

**You should now see a command prompt like:** `pi@rpi:~$`

---

## Step 5: Download the Spectrometer Software

Run these commands on the Raspberry Pi (via SSH):

```bash
# Install git (if not already installed)
sudo apt update && sudo apt install -y git

# Download the spectrometer software
cd ~
git clone https://github.com/USER/ORCA_open_spectrometer.git

# Navigate to the application folder
cd ORCA_open_spectrometer/pysb-app
```

> **Note:** Replace `USER` with the actual GitHub username/organization for this repository.

---

## Step 6: Run the Setup Script

This script will install everything automatically. It takes about 20-30 minutes.

```bash
# Make the script executable
chmod +x setup_pi.sh

# Run the setup script
sudo ./setup_pi.sh
```

**What the setup script does:**

- Updates the system packages
- Installs the PiTFT display driver
- Sets up the Python environment
- Installs the spectrometer libraries
- Configures I2C for temperature sensor
- Optimizes boot time (reduces from 2+ minutes to ~20 seconds)
- Sets up user permissions for hardware access

**During setup:**

- The script will ask a few questions - just press Enter for defaults
- If asked about creating a systemd service, type `n` (unless you want auto-start)
- The display driver installation may show warnings - this is normal

---

## Step 7: Reboot

After the setup script completes, you must reboot:

```bash
sudo reboot
```

Wait about 30 seconds, then reconnect via SSH:

```bash
ssh pi@<IP_ADDRESS>
```

---

## Step 8: Run the Spectrometer Application

```bash
# Navigate to the project folder
cd ~/pysb-app

# Activate the Python environment
source pysb_venv/bin/activate

# Run the application
python3 main.py
```

The application should now start and display on the PiTFT screen!

---

## Using the Spectrometer

### Button Controls

| Button | Function |
|--------|----------|
| **X** (top) | Navigate up / Increase value |
| **Y** (bottom) | Navigate down / Decrease value |
| **A** | Select / Confirm / Start capture |
| **B** | Back / Cancel |

### Menu Options

- **Integration Time:** How long the sensor collects light (longer = more signal)
- **Scans to Average:** Number of readings to average (more = smoother data)
- **Collection Mode:** RAW (raw counts) or REFLECTANCE (calibrated %)
- **Plot Range:** Wavelength range to display
- **Fan:** Temperature threshold for cooling fan

### Taking Measurements

1. Select **"Start Capture"** from the menu
2. For reflectance mode, you'll be prompted to capture:
   - **Dark reference** (cover the sensor)
   - **White reference** (measure a white standard)
3. Press **A** to capture spectra
4. Data is automatically saved to the SD card

---

## Troubleshooting

### Can't connect via SSH

- Make sure both devices are on the same WiFi network
- Wait a full 3 minutes after powering on for first boot
- Try using the IP address instead of `rpi.local`
- Check that WiFi credentials in Step 2.3 are correct

### Display not working after reboot

- Ensure the display ribbon cable is firmly connected
- Re-run the setup script if needed
- Check that you completed the full reboot

### Spectrometer not detected

- Unplug and replug the spectrometer USB cable
- Run: `lsusb` to check if it appears
- Try a different USB cable or port

### Temperature sensor shows "N/A"

- Check I2C wiring (SDA→GPIO2, SCL→GPIO3)
- Run the diagnostic: `python3 test_temp_sensor.py`
- Verify I2C is enabled: `sudo i2cdetect -y 1`

### Application crashes or errors

- Make sure the virtual environment is activated: `source pysb_venv/bin/activate`
- Check you're in the correct directory: `cd ~/pysb-app`
- View error logs for details

---

## Testing Hardware Components

### Test Temperature Sensor (MCP9808)

```bash
cd ~/pysb-app
source pysb_venv/bin/activate
python3 test_temp_sensor.py
```

### Test I2C Devices

```bash
sudo i2cdetect -y 1
```

You should see:

- `18` = MCP9808 temperature sensor
- `68` = DS3231 RTC

### Test Spectrometer

```bash
cd ~/pysb-app
source pysb_venv/bin/activate
python -m seabreeze.cseabreeze_backend ListDevices
```

### Test RTC

```bash
sudo hwclock -r
```

---

## File Locations

After setup, files are located at:

```text
~/pysb-app/
├── main.py              # Main application
├── config.py            # Configuration settings
├── pysb_venv/           # Python virtual environment
├── hardware/            # Hardware control modules
├── ui/                  # User interface modules
├── data/                # Data management modules
├── assets/              # Fonts and images
└── lib/                 # Additional libraries
```

Captured spectra are saved to: `~/pysb-app/data/` (or as configured)

---

## Adding Additional WiFi Networks

If you need to add more WiFi networks later:

1. SSH into the Pi
2. Edit the network configuration:

   ```bash
   sudo nano /etc/netplan/50-cloud-init.yaml
   ```

3. Add your network under `access-points`:

   ```yaml
   network:
       version: 2
       wifis:
           wlan0:
               access-points:
                   "Existing_Network":
                       password: "existing_password"
                   "New_Network":
                       password: "new_password"
               dhcp4: true
   ```

4. Save (Ctrl+O, Enter) and exit (Ctrl+X)
5. Apply changes: `sudo netplan apply`

---

## Hardware Documentation

### Custom PCB

A custom PCB was designed to add:

- USB-C power input
- Blue Robotics waterproof power switch
- Real-time clock (DS3231) with battery backup
- Leak sensor input
- Button inputs
- I2C and UART breakouts

The complete schematic and board design can be found in the `PCB/` folder.

![PCB Front](https://github.com/user-attachments/assets/a64ad8f9-ed21-4b6f-b43d-9462d401118d)

![PCB Back](https://github.com/user-attachments/assets/7c0f146f-47bb-43a3-b808-453892763aac)

### Leak Sensor

Based on the Blue Robotics leak sensor design, using Blue Robotics SOS leak sensor probes.

![Leak Sensor](https://github.com/user-attachments/assets/3c34cd6f-63d9-44bc-a1fa-a32ff59414d8)

### RTC Module

Based on Adafruit's I2C DS3231 module design.

![RTC Module](https://github.com/user-attachments/assets/7edfee91-a727-4598-ba51-139883b82f8c)

### Wiring Reference

| Component | Raspberry Pi Pin |
|-----------|------------------|
| **I2C SDA** | GPIO 2 (Pin 3) |
| **I2C SCL** | GPIO 3 (Pin 5) |
| **Fan Control** | GPIO 4 (Pin 7) |
| **Button A** | GPIO 27 |
| **Button B** | GPIO 23 |
| **Button X** | GPIO 22 |
| **Button Y** | GPIO 17 |
| **Leak Sensor** | GPIO 26 |

---

## Power Consumption

Using a 10000mAh battery pack, the system runs for approximately **10 hours** under typical use.

| Measurement | Value |
|-------------|-------|
| Current (live feed) | ~0.6A |
| Voltage | 5.1V |
| Power consumption | 3.06W |
| Battery capacity | 37Wh (10000mAh × 3.7V) |
| Efficiency | ~85% |
| Runtime | ~10.3 hours |

---

## Testing on Ubuntu PC (Development)

To test the spectrometer on a regular Ubuntu PC (without the Pi):

```bash
cd ~
mkdir pysb-dev
cd pysb-dev
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install seabreeze[pyseabreeze]
seabreeze_os_setup
```

---

## License

This project is designed for educational and research purposes. Please ensure compliance with all applicable licenses for the software components used.

---

## Acknowledgments

Thanks to the [python-seabreeze](https://github.com/ap--/python-seabreeze) team for maintaining the PySeabreeze API, which makes this project possible on ARM devices.
