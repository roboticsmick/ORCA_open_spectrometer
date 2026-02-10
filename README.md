# ORCA Open Spectrometer

A one handed underwater spectrometer system using Ocean Optics ST-VIS spectrometers with a Raspberry Pi Zero 2W and Adafruit 2.8LCD display. Designed for field work in a compact, low-power package.

![ORCA Open Spectrometer](pysb-app/assets/images/ORCA_open_spectro_testing.jpeg)
![ORCA Open Spectrometer](pysb-app/assets/images/demo.png)

## Changelog

### 2025-DEC-18

* Version 1.0 released

---

## Table of Contents

1. [Hardware Requirements](#1-hardware-requirements)
2. [Installing Ubuntu on the Raspberry Pi](#2-installing-ubuntu-on-the-raspberry-pi)
3. [Setting Up WiFi](#3-setting-up-wifi)
4. [Installing the Software](#4-installing-the-software)
5. [Running the App](#5-running-the-app)
6. [App Settings Reference](#6-app-settings-reference)
7. [Capturing Reference Spectra (Calibration)](#7-capturing-reference-spectra-calibration)
8. [Capturing Spectra](#8-capturing-spectra)
9. [Downloading Data to Your Computer](#9-downloading-data-to-your-computer)
10. [Advanced: Editing config.py](#10-advanced-editing-configpy)
11. [Data Format & Storage](#11-data-format--storage)
12. [Hardware Information](#12-hardware-information)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Hardware

### 1.1 ORCA Open Spectrometer Hardware

* **Raspberry Pi Zero 2W**
* **PiTFT Plus Assembled 320x240 2.8" TFT + Resistive/Capacitive Touchscreen**
* **Ocean Optics ST-VIS spectrometer**
* **High-quality microSD card if flashing software (Samsung 128/256GB PRO Plus recommended)**
* **Adafruit MCP9808 High Accuracy I2C Temperature Sensor Breakout**
* **Hydrocean M10 Magnetic USB Penetrator**
* **FEX Heat Sink with Fan FEX40-40-21/T710/M2**
* **Blue Robotics leak sensor SOS Probes**
* **ORCA Open Spectro Pi Hat**
* **4 x ORCA Magnetic Hal Effect Trigger Switches**

### 1.1 Disassembly

**WARNING: You can easily damage the hardware or cables if you are not very careful opening the housing.**

The device is very carefully assembled. Read all three guides from Blue Robotics on enclosure assembley before attempting to open the case as these outline how their parts work. Take note of where the ports and cables are located in the payload.

* [Watertight Enclosure (WTE) User Guide](https://bluerobotics.com/learn/watertight-enclosure-wte-assembly-new/)

To disassemble the device, both end caps need to carefully released, and all ports need to be unplugged in order to prevent damage.

1. Completely unscrew the pressure relief valve. **Ensure no dust or sand gets on any of the parts or O-rings.**
2. Remove both plastic locking cords on each end of the housing.
3. Carefully open the penetrator bulkhead housing end of the tube (the side with all the cables). Open this just enough to access the battery bank plugs.
4. Carefully reach into the housing to unplug both USB-C battery connections carefully.
5. Carefully open the fibre optics bulkhead housing end of the tube just enough to access the spectrometer plug.
6. Unplug the spectrometer USB-C port.
7. Carefully reach into the housing and unplug the fan and temperature sensor from the Pi Hat (it helps if you have the housing rotated so the battery is parallel to the ground so it stays out of the way so you can access the plug).
8. Unscrew the 2 x M3 bolts holding the battery USB cable plate.
9. Unscrew the M3 bolts holding the Pi Hat cover. Carefully remove the plate being careful not to damage the leak sensor port.
10. Carefully remove the Pi Hat being sure not to damage the P. Carefully remove the plate being careful not to damage the leak sensor power switch plug, and trigger plugs.
11. Take note of the orientation of the USB-C plug on the Pi hat. Carefully remove the USB-C port of the Pi hat. **Note: Orientation of this USB-C port is critical. Plugging it in in reverse will stop break the power switch working.**.
12. Unplug the leak sensor, triggers, and power switch ports. **Note: The triggers plugs are labelled and correspond to the labelled ports on the Pi hat PCB.**

### 1.2 Waterproof Blue Robotics Housing and Pressure Testing

The enclosures uses Blue Robotics enclosures. All O-rings, seals, and components need to be maintained and checked regularly.

1. [Watertight Enclosure (WTE) User Guide](https://bluerobotics.com/learn/watertight-enclosure-wte-assembly-new/)

The Vacuum Plug allows you to vacuum test enclosures ensuring a watertight seal.

1. [Pressure Relief Valve Installation and Usage](https://bluerobotics.com/learn/pressure-relief-valve-installation-and-usage/)
2. [Using the Vacuum Plug and Hand Pump](https://bluerobotics.com/learn/using-the-vacuum-test-plug/)

---

## 2. Installing Ubuntu on the Raspberry Pi

### 2.1 Download Raspberry Pi Imager

```bash
# Ubuntu/Debian
sudo apt install rpi-imager

# Or download from: https://www.raspberrypi.com/software/
```

### 2.2 Flash the SD Card

1. Open **Raspberry Pi Imager**
2. **Choose Device**: Raspberry Pi Zero 2W
3. **Choose OS**: Ubuntu 22.04 Server LTS
4. **Choose Storage**: Select your SD card
5. Click **Edit Settings** and configure:

| Setting | Value |
|---------|-------|
| Hostname | `rpi` |
| Username | `pi` |
| Password | `spectro` (or your choice) |
| Configure WiFi | Yes (see section 3 for adding additional wifi networks) |
| WiFi Country | Your country code (e.g., `AU`) |
| Timezone | Your timezone (e.g., `Australia/Brisbane`) |
| Enable SSH | Yes, with password authentication |

1. Click **Save**, then **Yes** to apply settings
2. Flash the image to the SD card

### 2.3 First Boot

1. Insert the SD card into the Raspberry Pi
2. Connect power
3. Wait 3-5 minutes for first boot (the Pi expands the filesystem)
4. The Pi should automatically connect to your configured WiFi

---

## 3. Setting Up WiFi (Using Ubuntu)

### 3.1 Initial WiFi (During Imaging)

Configure your primary WiFi during the imaging process (section 2.2). You should also add your mobile hotspot for easy field access to the data of configuration settings, along with any other WiFi networks you plan on connecting to at this stage.

### 3.2 Adding Additional WiFi Networks

#### Method A: Edit SD card directly (before boot)

1. Insert the SD card into your computer
2. Navigate to the root filesystem
3. Edit `/etc/netplan/50-cloud-init.yaml`

#### Method B: Edit via SSH (after boot)

```bash
# See section 3.3 if you don't know how to find your Raspberry Pi IP_ADDRESS
ssh pi@<IP_ADDRESS>
sudo vim /etc/netplan/50-cloud-init.yaml
```

**Example configuration:**

```yaml
network:
    version: 2
    wifis:
        renderer: networkd
        wlan0:
            access-points:
                "Your_Hotspot_Name":
                    password: "hotspot_password"
                "Home_WiFi":
                    password: "home_password"
                "Office_WiFi":
                    password: "office_password"
            dhcp4: true
            optional: true
```

> **Important:** YAML requires consistent indentation (use spaces, not tabs).

**Apply changes:**

```bash
sudo netplan apply
```

### 3.3 Finding the Pi's IP Address

An **IP address** is a unique number assigned to each device on a network (like `192.168.1.105` or `10.154.83.52`). You need the Pi's IP address to connect to it remotely via SSH.

**Ways to find the IP address:**

* **From the app**: The IP is displayed in the spectrometer app menu under "IP". This is only visible after the complete installation and setup of the Open Spectro app.
* **From your router**: Check the connected devices list in your router or hotspot settings (see section 3.4 for details on how to do this).
* **Using ping**: From another computer on the same network, run `ping rpi.local`. This is an easy way, but can sometimes be unreliable.

### 3.4 Finding the Pi's IP Address via Mobile Hotspot

When connecting to your Pi through a mobile hotspot (useful for field work), you may need to find its IP address manually using `nmap` - a network scanning tool.

#### Prerequisites

1. Your mobile hotspot WiFi credentials are configured in the Pi's `/etc/netplan/50-cloud-init.yaml` file
2. Your laptop is connected to the same mobile hotspot
3. The Pi is powered on and connected (check your phone shows 2+ devices connected)

#### Step 1: Install nmap (if not already installed)

```bash
sudo apt install nmap
```

#### Step 2: Find your laptop's IP address

```bash
ip addr show | grep "inet "      # Search for local IP addresses
ifconfig                         # Alternative search option
```

Look for the IP address on your wireless interface (usually `wlan0` or `wlp...`):

```text
inet 10.154.83.49/24 brd 10.154.83.255 scope global dynamic wlp3s0
```

In this example, your laptop's IP is `10.154.83.49`.

#### Step 3: Scan the network for other devices

Use nmap to scan all devices on the same subnet. Replace the IP with yours, keeping `.0/24` at the end:

```bash
sudo nmap -sn 10.154.83.0/24
```

This scans all addresses from `10.154.83.1` to `10.154.83.254`. Example output:

```text
Nmap scan report for 10.154.83.1
Host is up (0.0050s latency).

Nmap scan report for 10.154.83.49
Host is up (0.00010s latency).

Nmap scan report for 10.154.83.52
Host is up (0.045s latency).
```

#### Step 4: Identify and connect to the Pi

One of the IP addresses (not your laptop's, not `.1` which is usually the hotspot) will be the Pi. Try connecting:

```bash
ssh -Y pi@10.154.83.52
```

**Tip:** If you have multiple unknown devices, try each one until you find the Pi. The Pi will respond with a password prompt for user `pi`.

---

## 4. Installing the Software

### 4.1 Connect to the Pi via SSH

```bash
ssh pi@<IP_ADDRESS>
# Password: spectro (or your password)
```

### 4.2 Download and Run the Setup Script

```bash
cd ~
git clone https://github.com/roboticsmick/ORCA_open_spectrometer.git
cd ORCA_open_spectrometer
chmod +x setup_pi.sh
sudo ./setup_pi.sh
```

The setup script:

* Installs all system dependencies
* Creates a Python virtual environment
* Installs Python packages (pygame, seabreeze, etc.)
* Configures the display
* Sets up the app to run as a systemd service on boot

### 4.3 Reboot

```bash
sudo reboot
```

After reboot, the app should start automatically.

---

## 5. Running the App

### 5.1 Automatic Startup (Default)

The app runs automatically as a systemd service when the Pi boots. No action required.

### 5.2 Service Commands

```bash
ssh pi@<IP_ADDRESS>
# Password: spectro (or your password)

# Check if the app is running
sudo systemctl status pysb-app.service

# Stop the app
sudo systemctl stop pysb-app.service

# Start the app
sudo systemctl start pysb-app.service

# Restart the app
sudo systemctl restart pysb-app.service

# View live logs
journalctl -u pysb-app.service -f
```

### 5.3 Manual Execution (For Testing)

```bash
# Stop the service first
sudo systemctl stop pysb-app.service

# Activate virtual environment and run
cd ~/ORCA_open_spectrometer/pysb-app
source pysb_venv/bin/activate
python3 main.py
```

---

## 6. App Settings Reference

### 6.1 Button Controls

The app uses 4 buttons:

| Button | Menu Action | Live View Action |
|--------|-------------|------------------|
| **UP (X)** | Previous item / Increase value | Open calibration menu |
| **DOWN (Y)** | Next item / Decrease value | Rescale Y-axis |
| **A (ENTER)** | Select / Confirm | Freeze spectrum |
| **B (BACK)** | Cancel / Go back | Return to menu |

### 6.2 Integration Time

Controls how long the sensor collects light per measurement.

![ORCA Open Spectrometer](pysb-app/assets/images/menu.png)

| Parameter | Value |
|-----------|-------|
| Default | 1000 ms |
| Minimum | 100 ms |
| Maximum | 6000 ms |
| Step | 50 ms |

**General guidelines:**

* **Low light conditions**: Increase integration time
* **Bright light / saturation**: Decrease integration time
* Use **Auto-Integration** (Section 7.4) to find the optimal value

### 6.3 Collection Mode

| Mode | Description |
|------|-------------|
| **RAW** | Direct sensor readings as ADC counts (0-16383) |
| **REFLECTANCE** | Calibrated reflectance ratio (requires calibration) |

#### RAW Mode

* Shows direct sensor values
* No calibration required
* Best for: testing, alignment, troubleshooting

#### Reflectance Mode

* Calculates relative reflectance using dark and white references
* **Requires calibration** before use (see Section 7)

**Reflectance Formula:**

```text
Reflectance = (Target - Dark) / (White - Dark)
```

Where:

* **Target** = Raw spectrum of your sample
* **Dark** = Raw spectrum with sensor covered (no light)
* **White** = Raw spectrum of a white reference standard (e.g., Spectralon or white PTFE panel)

**Interpreting Values:**

| Value | Meaning |
|-------|---------|
| 0.0 | No reflectance (absorbs all light) |
| 1.0 | Same reflectance as white reference (100%) |

### 6.4 Scans to Average

Averages multiple scans to reduce noise.

![ORCA Open Spectrometer](pysb-app/assets/images/scans_to_average.png)

| Parameter | Value |
|-----------|-------|
| Default | 1 |
| Minimum | 0 |
| Maximum | 50 |
| Step | 1 |

> **Trade-off:** Higher values = smoother data, but slower live updates.

### 6.5 Display Wavelength Range

Controls the X-axis range shown on the plot.

| Parameter | Value |
|-----------|-------|
| Default Min | 400 nm |
| Default Max | 620 nm |
| Minimum Limit | 340 nm |
| Maximum Limit | 850 nm |
| Step | 20 nm |

> **Important:** This only affects the **display**. The full spectrum is always saved to CSV.

**Editing:**

1. Press A to start editing (MIN field highlighted in blue)
2. Use UP/DOWN to adjust value
3. Press A to move to MAX field
4. Press A again to save
5. Press B anytime to cancel

### 6.6 Date/Time

Sets the timestamp used in saved filenames. This creates a temporary offset from system time (not a permanent clock change).

**Editing fields:** Year → Month → Day → Hour → Minute

### 6.7 Fan Threshold

Controls the cooling fan activation temperature.

| Parameter | Value |
|-----------|-------|
| Default | 0°C (always on) |
| Minimum | 0°C |
| Maximum | 60°C |
| Step | 5°C |

**Display format:** `Fan: Threshold 40C (Current 32C)`

| Setting | Behavior |
|---------|----------|
| 0°C | Fan always runs (maximum cooling) |
| 40°C | Fan runs only when temperature >= 40°C |

### 6.8 Network Info (Read-Only)

* **WiFi**: Current network name
* **IP**: Current IP address (use this for SSH)

---

## 7. Capturing Reference Spectra (Calibration)

Calibration is **required** for Reflectance mode. Both references must be captured at the **same integration time and averaging settings**.

![ORCA Open Spectrometer](pysb-app/assets/images/calibrate.png)

### 7.1 Access Calibration Menu

1. Enter live view (Menu → Start Capture)
2. Press **X (UP)** to open calibration menu

```text
CALIBRATION MENU

A: White Reference - Not set
X: Dark Reference - Not set
Y: Auto integration - Not complete

A:White | X:Dark | Y:Auto | B:Back
```

### 7.2 Capture Dark Reference

The dark reference captures sensor noise when no light reaches the sensor.

1. Press **X** to start dark reference capture
2. **Cover the sensor completely** (or close the shutter)
3. The live view shows raw sensor data
4. Press **A** to freeze when ready
5. Press **A** to save, or **B** to discard and retake

### 7.3 Capture White Reference

The white reference captures maximum expected reflectance.

1. Press **A** to start white reference capture
2. **Point at a white reference target** (e.g., Spectralon, white tile)
3. The live view shows raw sensor data
4. Press **A** to freeze when ready
5. Press **A** to save, or **B** to discard and retake

### 7.4 Auto-Integration

Automatically finds the optimal integration time by targeting 80-95% sensor saturation.

![ORCA Open Spectrometer](pysb-app/assets/images/auto_integration.png)

1. Press **Y** to start auto-integration setup
2. **Point at your brightest expected sample** (usually white reference)
3. Press **A** to begin the algorithm
4. Wait for iterations to complete (max 20)
5. Review the proposed integration time
6. Press **A** to apply, or **B** to cancel

> **Note:** Applying auto-integration **invalidates** existing dark and white references. You must recapture them.

### 7.5 When References Become Invalid

References are invalidated when you change:

* **Integration time** → Both dark and white invalidated
* **Scans to average** → Both dark and white invalidated

The app will display "CALIBRATE REQUIRED" if you try to use Reflectance mode with invalid references.

---

## 8. Capturing Spectra

![ORCA Open Spectrometer](pysb-app/assets/images/capture.png)

### 8.1 Live View

1. From menu, select **Start Capture**
2. Live spectrum updates at ~30 FPS
3. Status bar shows: `RAW | INT:1000ms | AVG:1 | SCANS:0 | LIVE`

### 8.2 Freeze and Save

1. Press **A** to freeze the current spectrum
2. Review the frozen plot (spectrometer pauses)
3. Press **A** to save to file
4. Press **B** to discard and return to live view

### 8.3 Saved File Location

Files are saved to: `~/pysb-app/spectra_data/YYYY-MM-DD/`

Each day creates a new folder with:

* CSV file containing all spectra
* PNG plot images for each capture

### 8.4 Rescale Y-Axis

Press **Y** in live view to auto-scale the Y-axis based on current data.

---

## 9. Downloading Data to Your Computer

### 9.1 Prerequisites

| Platform | Requirements |
|----------|--------------|
| **Ubuntu/Linux** | Terminal (built-in) |
| **macOS** | Terminal (built-in) |
| **Windows** | WSL (Windows Subsystem for Linux) |

**Installing WSL on Windows:**

WSL lets you open a Linux terminal you can use in Windows. This allows you to use the Ubuntu linux commands on your Windows PC.

Read the guidelines for installing WSL on windows here (How to install Linux on Windows with WSL
)[https://learn.microsoft.com/en-us/windows/wsl/install].

### 9.2 Using rsync (Recommended)

rsync (remote sync) is a powerful command-line utility for efficiently transferring files and directories locally or over a network.

**Download all data:**

```bash
# Create local folder
mkdir -p ~/spectra_data

# Sync all data from Pi
rsync -av --progress pi@<IP_ADDRESS>:~/pysb-app/spectra_data/ ~/spectra_data/
```

**Download specific date:**

```bash
rsync -av --progress pi@<IP_ADDRESS>:~/pysb-app/spectra_data/2025-12-15/ ~/spectra_data/2025-12-15/
```

**Resume interrupted transfer:**

```bash
rsync -av --progress --partial pi@<IP_ADDRESS>:~/pysb-app/spectra_data/ ~/spectra_data/
```

### 9.3 Using scp

scp is simpler for one-off file copies.

**Download single file:**

```bash
scp pi@<IP_ADDRESS>:~/pysb-app/spectra_data/2025-12-15/2025-12-15_spectra_log.csv ./
```

**Download entire folder:**

```bash
scp -r pi@<IP_ADDRESS>:~/pysb-app/spectra_data/2025-12-15/ ./2025-12-15/
```

### 9.4 Windows: Accessing WSL Files

After downloading to WSL, access files in Windows Explorer:

```text
\\wsl$\Ubuntu\home\yourusername\spectra_data
```

Or copy to Windows filesystem:

```bash
cp -r ~/spectra_data /mnt/c/Users/YourName/Desktop/
```

### 9.5 macOS: Using Finder

```text
Go menu → Connect to Server → sftp://pi@<IP_ADDRESS>
```

---

## 10. Advanced: Editing config.py

To customize default values or enable/disable hardware features, edit the `config.py` file.

### 10.1 Stop the Service

```bash
ssh pi@<IP_ADDRESS>
sudo systemctl stop pysb-app.service
```

### 10.2 Edit config.py

```bash
cd ~/ORCA_open_spectrometer/pysb-app
source pysb_venv/bin/activate
nano config.py  # or vim config.py
```

### 10.3 Key Configuration Sections

#### Hardware Flags

```python
HARDWARE = {
    "USE_DISPLAY_HAT": False,         # Pimoroni Display HAT. No longer used.
    "USE_ADAFRUIT_PITFT": True,       # Adafruit PiTFT 2.8"
    "USE_GPIO_BUTTONS": False,        # On-board GPIO buttons
    "USE_HALL_EFFECT_BUTTONS": True,  # External Hall effect buttons
    "USE_LEAK_SENSOR": True,          # Leak detection hardware
    "USE_SPECTROMETER": True,         # Ocean Optics spectrometer
    "USE_TEMP_SENSOR_IF_AVAILABLE": True  # MCP9808 sensor
}
```

#### Spectrometer Defaults

```python
class SPECTROMETER:
    DEFAULT_INTEGRATION_TIME_MS = 1000
    MIN_INTEGRATION_TIME_MS = 100
    MAX_INTEGRATION_TIME_MS = 6000
    INTEGRATION_TIME_STEP_MS = 50
    HW_MAX_ADC_COUNT = 16383  # 14-bit ADC
```

#### Fan Control

```python
FAN_ENABLE_PIN = 4           # GPIO pin for MOSFET gate
FAN_DEFAULT_THRESHOLD_C = 0  # 0 = always on
FAN_THRESHOLD_MIN_C = 0
FAN_THRESHOLD_MAX_C = 60
FAN_THRESHOLD_STEP_C = 5
```

#### Plotting Defaults

```python
class PLOTTING:
    USE_LIVE_SMOOTHING = True
    LIVE_SMOOTHING_WINDOW_SIZE = 9
    WAVELENGTH_RANGE_MIN_NM = 400.0  # Default display min
    WAVELENGTH_RANGE_MAX_NM = 620.0  # Default display max
    TARGET_DISPLAY_POINTS = 300      # Decimation for 30+ FPS
```

#### Auto-Integration Parameters

```python
class AUTO_INTEGRATION:
    TARGET_LOW_PERCENT = 80.0   # Lower saturation target
    TARGET_HIGH_PERCENT = 95.0  # Upper saturation target
    MAX_ITERATIONS = 20
    PROPORTIONAL_GAIN = 0.8
```

### 10.4 Test Changes

```bash
# Run manually to test
python3 main.py

# If working, restart service
sudo systemctl start pysb-app.service
```

### 10.5 Make Changes Permanent

Changes to `config.py` persist across reboots. The service reads the config on startup.

---

## 11. Data Format & Storage

### 11.1 Folder Structure

```text
~/pysb-app/spectra_data/
├── 2025-12-14/
│   ├── 2025-12-14_spectra_log.csv
│   ├── spectrum_RAW_FIBER_2025-12-14-103000.png
│   └── spectrum_REFLECTANCE_FIBER_2025-12-14-104500.png
└── 2025-12-15/
    ├── 2025-12-15_spectra_log.csv
    └── spectrum_RAW_FIBER_2025-12-15-091500.png
```

### 11.2 CSV Format

Each row contains one spectrum:

| Column | Description |
|--------|-------------|
| timestamp_utc | ISO format timestamp |
| spectra_type | RAW, REFLECTANCE, DARK, WHITE, RAW_REFLECTANCE |
| lens_type | FIBER, CABLE, or FIBER+CABLE |
| integration_time_ms | Integration time used |
| scans_to_average | Number of averaged scans |
| temperature_c | Housing temperature (if sensor available) |
| 340.12, 340.24, ... | Wavelength columns with intensity values |

### 11.3 Spectra Types

| Type | Description |
|------|-------------|
| RAW | Direct sensor measurement in ADC counts |
| REFLECTANCE | Calibrated reflectance ratio |
| DARK | Dark reference capture |
| WHITE | White reference capture |
| RAW_REFLECTANCE | Raw target data saved alongside reflectance |

### 11.4 PNG Plots

* Generated automatically for RAW and REFLECTANCE captures
* Calibration captures (DARK, WHITE) do not generate plots
* High resolution suitable for publications

---

## 12. Hardware Information

### 12.1 Custom Breakout PCB

The optional breakout PCB provides:

* USB-C power input
* Blue Robotics waterproof power switch
* Real-time clock (DS3231) with battery backup
* Leak sensor input (Blue Robotics SOS probes)
* External button inputs
* I2C and UART breakouts

See the `/PCB` folder for schematics and board files.

### 12.2 Wiring Reference

```text
Fan Red Wire    → 5V through MOSFET drain
Fan Black Wire  → Ground
MOSFET Gate     → GPIO 4
MCP9808 SDA     → GPIO 2 (I2C data)
MCP9808 SCL     → GPIO 3 (I2C clock)
MCP9808 VCC     → 3.3V
MCP9808 GND     → Ground
Leak Sensor     → GPIO 26
```

### 12.3 Power Consumption

With a 10,000mAh battery:

| Measurement | Value |
|-------------|-------|
| Current (live capture) | ~0.6A |
| Voltage | 5.1V |
| Power | 3.06W |
| Expected runtime | ~10 hours (85% efficiency) |

---

## 13. Troubleshooting

### 13.1 App Won't Start

```bash
# Check service status
sudo systemctl status pysb-app.service

# View detailed logs
journalctl -u pysb-app.service -n 50

# Restart service
sudo systemctl restart pysb-app.service
```

### 13.2 No Spectrometer Detected

```bash
# Check USB devices
lsusb | grep -i ocean

# Try unplugging and reconnecting the spectrometer
# Check cable connection
```

### 13.3 Display Not Working

* Check display ribbon cable connection
* Verify `USE_ADAFRUIT_PITFT: True` in config.py
* Check framebuffer exists: `ls /dev/fb1`

### 13.4 References Invalid Error

* Recapture dark and white references after changing integration time or averaging
* Both references must use the same settings

### 13.5 WiFi Not Connecting

* Check `/etc/netplan/50-cloud-init.yaml` syntax
* Verify SSID and password are correct
* Check WiFi country code matches your location

### 13.6 Debug printouts

The app prints the status and processes out for easy debugging when connected via ssh. This should allow for easy detecting of errors.

```sh
# Stop the app service
sudo systemctl stop pysb-app.service

# Run manually to test
cd ~/pysb-app
python3 main.py

# Remember to restart the service after debugging has been complete
sudo systemctl start pysb-app.service
```

Example debug printouts:

```sh
(pysb_venv) pi@ada:~/pysb-app$ python3 main.py
/home/pi/pysb-app/pysb_venv/lib/python3.10/site-packages/pygame/pkgdata.py:25: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import resource_stream, resource_exists
pygame 2.6.1 (SDL 2.28.4, Python 3.10.12)
Hello from the pygame community. https://www.pygame.org/contribute.html
Seabreeze libraries loaded successfully.
DataManager: Matplotlib loaded successfully (Agg backend).
Initializing standard Pygame display window...
Standard Pygame window initialized (320x240)
INFO: GPIO buttons initialized for pins: [20, 21, 19, 12]
INFO: Leak sensor initialized on GPIO pin 26 (interrupt-based)
Leak sensor thread started (waiting for interrupts).
NetworkInfo thread started.
SpectrometerController: Thread loop started
SpectrometerController thread started
DataManager: Thread loop started
DataManager thread started
Entering main application logic...
Showing splash screen...
DataManager: Data directory ready: /home/pi/pysb-app/spectra_data
Splash screen done.
Showing terms screen...
DEBUG: Button 'enter' pressed (GPIO 5)
Terms screen done.
Entering main loop...
Spectrometer initialized: ST
  Serial: ST02348
  Wavelength range: 348.3 - 809.2 nm
  Pixels: 1516
  Integration time limits: 3800 - 6000000 µs
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Entering live view
SpectrometerScreen: Set Y-axis for RAW mode: 1000.0
SpectrometerController: New session started (ID: 1)
SpectrometerScreen: Setting wavelengths (length: 1516)
DEBUG: Button 'up' pressed (GPIO 20)
SpectrometerScreen: Entering calibration menu
SpectrometerController: Session stopped (ID: 1)
DEBUG: Button 'down' pressed (GPIO 21)
SpectrometerScreen: Starting auto-integration setup
SpectrometerScreen: Cancelling auto-integration
SpectrometerScreen: Auto-integ initial test: 1000000 µs
SpectrometerScreen: Target ADC range: 13106 - 15564
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Auto-integ capture requested at 1000000 µs
SpectrometerController: New session started (ID: 2)
SpectrometerScreen: Iter 1: Peak=1125 Next=6000.0ms
SpectrometerScreen: Auto-integ capture requested at 6000000 µs
SpectrometerController: New session started (ID: 3)
SpectrometerScreen: Auto-integ complete: At max integration, still low. Proposed: 6000 ms
SpectrometerController: Session stopped (ID: 3)
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Applying auto-integration result
SpectrometerScreen: Sent CMD_UPDATE_SETTINGS with integration_time_ms=6000
SpectrometerScreen: New integration time: 6000 ms
SpectrometerScreen: Exiting calibration, returning to live view
SpectrometerScreen: Restored collection mode to RAW
SpectrometerController: Integration time updated to 6000 ms
SpectrometerController: New session started (ID: 4)
SpectrometerScreen: Setting wavelengths (length: 1516)
SpectrometerScreen: Rescaling Y-axis...
SpectrometerScreen: Y-axis rescaled to 9962.84
SpectrometerScreen: Auto-rescaled Y-axis after auto-integration
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Data frozen for capture
SpectrometerController: Session stopped (ID: 4)
DEBUG: Button 'back' pressed (GPIO 12)
SpectrometerScreen: Returning to live view
SpectrometerController: New session started (ID: 5)
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Data frozen for capture
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Save request sent (RAW)
DataManager: Processing save request (RAW)...
  Timestamp: 2025-12-19 11:27:50.461775
  Integration: 6000 ms
  Scans averaged: 1
  Session scan count: 1
SpectrometerScreen: Returning to live view
DataManager: Found 6 existing scans in today's log
DataManager: Saved RAW to CSV successfully
DataManager: Plot saved: /home/pi/pysb-app/spectra_data/2025-12-19/spectrum_RAW_FIBER_2025-12-19-112750.png
SpectrometerController: Session stopped (ID: 5)
SpectrometerController: New session started (ID: 6)
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Data frozen for capture
SpectrometerController: Session stopped (ID: 6)
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Save request sent (RAW)
DataManager: Processing save request (RAW)...
  Timestamp: 2025-12-19 11:27:56.572918
  Integration: 6000 ms
  Scans averaged: 1
  Session scan count: 2
SpectrometerScreen: Returning to live view
DataManager: Saved RAW to CSV successfully
SpectrometerController: New session started (ID: 7)
DataManager: Plot saved: /home/pi/pysb-app/spectra_data/2025-12-19/spectrum_RAW_FIBER_2025-12-19-112756.png
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Data frozen for capture
DEBUG: Button 'enter' pressed (GPIO 5)
SpectrometerScreen: Save request sent (RAW)
DataManager: Processing save request (RAW)...
  Timestamp: 2025-12-19 11:28:22.606372
  Integration: 6000 ms
  Scans averaged: 1
  Session scan count: 3
SpectrometerScreen: Returning to live view
DataManager: Saved RAW to CSV successfully
DataManager: Plot saved: /home/pi/pysb-app/spectra_data/2025-12-19/spectrum_RAW_FIBER_2025-12-19-112822.png
SpectrometerController: Session stopped (ID: 7)
SpectrometerController: New session started (ID: 8)

```

---

## Credits

Special thanks to the [PySeabreeze](https://github.com/ap--/python-seabreeze) project for enabling Ocean Optics spectrometer support on ARM devices.

---

## Support

* Technical documentation: See [pysb-app/app_guide.md](pysb-app/app_guide.md)
