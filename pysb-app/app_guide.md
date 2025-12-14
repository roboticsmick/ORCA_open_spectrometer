# PySB-App Application Guide

This document provides a technical overview of the PySB-App, a Python-based spectrometer application designed for a Raspberry Pi with a touchscreen interface.

**Last Updated:** 2025-12-14
**Refactoring Status:** Phase 9 Complete (Temperature Sensor & Fan Control) ✅

---

## Coding Guidelines (Strictly Enforced)

**I. Core Principles (Safety & Simplicity):**

* **NASA-Inspired Rules:** All code must adhere to principles for safety-critical systems.
* **Simple Control Flow:** Use `if/elif/else` and bounded `for` or `while` loops. Avoid recursion and complex control structures.
* **Bounded Loops:** Ensure all loops are demonstrably terminable with clear exit conditions.
* **Memory Management:** Avoid creating large objects repeatedly in tight loops. Pre-allocate or reuse objects where possible.
* **Concise Functions:** Keep functions/methods short (under ~80 lines) and focused on a single task.
* **Assertions are Critical:** Do not remove existing assertions. Add new assertions to validate parameters, return values, and state.
* **Minimal Scope:** Declare variables in the smallest possible scope (local > class > global).
* **Robust Checks:** Rigorously validate all function inputs and outputs.
* **Clarity over Complexity:** Avoid complex metaprogramming or dynamic runtime modifications. Keep imports at the top of the file.
* **Traceable Calls:** Prefer direct method calls over passing functions as variables.
* **Linter Compliance:** Write clean code that would pass tools like `pylint` and `mypy` with no warnings.

**II. Code Modification & Integrity:**

* **No Deletions or Simplifications:** Never remove existing variables, functions, or configuration settings to simplify a response, especially from shared files like `config.py`. When adding to a file, integrate the new code without deleting existing code.
* **Provide Full Code Blocks:** Always rewrite the complete function, method, or class body. Do not provide snippets, diffs, or use placeholders like `...`.
* **Preserve Robustness:** Do not remove or simplify existing error handling (`try...except`), logging, or validation checks. Add new handling for any new error conditions introduced.

**III. Naming & Consistency:**

* **Consistent Naming:** Before creating a new variable or function, check the existing codebase for similar names. Reuse or adapt existing variables and adhere strictly to the established naming convention to prevent duplicates (e.g., `max_speed` vs. `maximum_speed`).
* **Clarity & Type Hinting:** Use clear, descriptive names. Maintain and add comments and type hints for all signatures and important variables.

***IV. Documentation Standards:***

**Doxygen Comments Required:** All files, classes, and public functions must include Doxygen documentation for clear parameter and function definitions.

**Format:**

```py
## @brief Brief description of the class/function.
#
#  Detailed description providing more context, usage examples,
#  and any important considerations.
#
#  @param parameter_name Description of the parameter.
#  @return Description of the return value.
class MyClass:
    # ...
```

**Key Requirements:**

* Use `@brief` for one-line summaries
* Document all parameters with `@param[in/out]`
* Include `@return` for non-void functions
* Add `@pre` tags matching code assertions (NASA principle compliance)

## 1. Application Overview

The application is built using `pygame` for the user interface and is structured around a multi-threaded architecture to ensure that the UI remains responsive while background tasks (like hardware monitoring and data processing) are running.

A central `main.py` module orchestrates the application, managing the overall state, user interface screens, and background worker threads.

## 2. Current File Structure & Refactoring Status

### ✅ Completed Components (Phase 1, 2 & 3)

```text
pysb-app/
├── main.py                      # ✅ Main entry point with dependency injection
├── config.py                    # ✅ Centralized configuration with asset paths
├── app_guide.md                 # ✅ This document (updated)
├── refactoring_goal.md          # ✅ Refactoring strategy document
│
├── assets/                      # ✅ Reorganized asset structure
│   ├── fonts/                   # ✅ All font files (.ttf)
│   │   ├── ChakraPetch-*.ttf
│   │   ├── Roboto-*.ttf
│   │   └── Segoe UI*.ttf
│   └── images/                  # ✅ Image files
│       ├── logo.png             # ✅ Main logo (formerly pysb-app.png)
│       └── Open spectro TEXT.png
│
├── lib/                         # ✅ Third-party libraries (vendored)
│   ├── Adafruit_Python_MCP9808/ # ✅ Temperature sensor library
│   └── pyseabreeze/             # ✅ Spectrometer library
│
├── hardware/                    # ✅ Hardware abstraction layer
│   ├── button_handler.py        # ✅ GPIO/Pygame input (⚠️ needs Doxygen docs)
│   ├── leak_sensor.py           # ✅ Leak detection thread (has Doxygen docs)
│   ├── network_info.py          # ✅ Network monitoring thread (has Doxygen docs)
│   ├── temp_sensor.py           # ✅ Temperature sensor & fan control thread (has Doxygen docs)
│   └── spectrometer_controller.py # ✅ Spectrometer control thread (has Doxygen docs)
│
├── ui/                          # ✅ User interface components
│   ├── display_utils.py         # ✅ Drawing utilities (has Doxygen docs)
│   ├── splash_screen.py         # ✅ Splash screen (has Doxygen docs)
│   ├── terms_screen.py          # ✅ Disclaimer screen (has Doxygen docs)
│   ├── leak_warning.py          # ✅ Leak warning display
│   ├── menu_system.py           # ✅ Menu system with datetime editing (has Doxygen docs)
│   ├── plotting.py              # ✅ Plotting & rendering classes (has Doxygen docs)
│   └── spectrometer_screen.py   # ✅ Live spectrometer view with save workflow
│
└── data/                        # ✅ Data management layer
    ├── __init__.py              # ✅ Package init
    └── data_manager.py          # ✅ File I/O, CSV operations, plot generation (has Doxygen docs)
```

**Legend:**

* ✅ = Completed and functional
* ⚠️ = Exists but needs updates/fixes
* ❌ = Not yet created

### 🎯 Target File Structure (Complete Vision)

This is the complete architecture we're working towards:

```text
pysb-app/
├── main.py                      # Main application entry point & UI loop
├── config.py                    # All constants, pins, file paths, fonts, etc.
├── app_guide.md                 # Technical documentation
├── refactoring_goal.md          # Refactoring strategy
│
├── assets/
│   ├── fonts/                   # All .ttf font files
│   └── images/                  # All .png image files
│
├── lib/                         # Third-party vendored libraries
│   ├── Adafruit_Python_MCP9808/
│   └── pyseabreeze/
│
├── hardware/                    # Hardware abstraction layer
│   ├── button_handler.py        # ButtonHandler class for GPIO/Pygame input
│   ├── leak_sensor.py           # LeakSensor thread for leak detection
│   ├── network_info.py          # NetworkInfo thread for WiFi/IP monitoring
│   ├── temp_sensor.py           # TempSensorInfo thread for temperature
│   └── spectrometer_controller.py # SpectrometerController thread
│
├── ui/                          # User interface components
│   ├── display_utils.py         # Shared drawing functions
│   ├── splash_screen.py         # Splash screen
│   ├── terms_screen.py          # Terms and conditions screen
│   ├── leak_warning.py          # Critical leak warning screen
│   ├── menu_system.py           # MenuSystem class for main menu
│   ├── plotting.py              # OptimizedPygamePlotter & FastSpectralRenderer
│   └── spectrometer_screen.py   # SpectrometerScreen for live view
│
└── data/                        # Data management layer
    └── data_manager.py          # DataManager thread for file I/O
```

## 3. Configuration Overview (`config.py`)

All static application-wide constants are stored in `config.py` to allow for easy tuning and management without altering the core application logic.

### 3.1 Asset Paths

* **`ASSETS_DIR`**: Base directory for all application assets
* **`FONTS_DIR`**: Directory containing all .ttf font files (`assets/fonts/`)
* **`IMAGES_DIR`**: Directory containing all image files (`assets/images/`)

### 3.2 Hardware Configuration

* **`HARDWARE`** (dict): Feature flags for optional hardware components
  * `USE_DISPLAY_HAT`: Enable Pimoroni Display HAT Mini support
  * `USE_ADAFRUIT_PITFT`: Enable Adafruit PiTFT 2.8" support
  * `USE_GPIO_BUTTONS`: Enable GPIO button inputs
  * `USE_HALL_EFFECT_BUTTONS`: Enable external Hall effect sensors
  * `USE_LEAK_SENSOR`: Enable leak detection hardware
  * `USE_SPECTROMETER`: Enable spectrometer hardware
  * `USE_TEMP_SENSOR_IF_AVAILABLE`: Enable MCP9808 temperature sensor

### 3.3 Pin Definitions (BCM Mode)

* **`BUTTON_PINS`** (dict): On-board button GPIO pins
  * Pimoroni Display HAT: A=5, B=6, X=16, Y=24 (default)
  * Adafruit PiTFT: A=27, B=23, X=22, Y=17
* **`HALL_EFFECT_PINS`** (dict): External Hall sensor GPIO pins
  * UP=20, DOWN=21, ENTER=19, BACK=12
* **`LEAK_SENSOR_PIN`**: GPIO pin 26 for leak detector
* **`LEAK_SENSOR_CHECK_S`**: Leak sensor polling interval (1.0 seconds)

### 3.4 Button Logical Names

* **`BTN_UP`**, **`BTN_DOWN`**, **`BTN_ENTER`**, **`BTN_BACK`**: Core button identifiers
* **`BTN_LEFT`**, **`BTN_RIGHT`**: Aliases mapped to UP/DOWN for menu value editing (4-button constraint)

### 3.5 Display Settings

* **`SCREEN_WIDTH`**, **`SCREEN_HEIGHT`**: Display dimensions (320x240 pixels)
* **`COLORS`** (class): Predefined color tuples (BLACK, WHITE, RED, GREEN, BLUE, YELLOW, GRAY, CYAN, MAGENTA)
* **`FONT_SIZES`** (class): Font sizes for different UI elements
  * TITLE=22, MENU_ITEM=18, MENU_VALUE=18, HINT=16, DISCLAIMER=14, INFO=14, SPECTRO=14, PLOTTER_TICK=12, PLOTTER_AXIS=14
* **`FONTS`** (class): Full paths to font files
  * TITLE, MAIN, HINT, SPECTRO, PLOTTER_AXIS_LABEL, PLOTTER_TICK_LABEL
* **`IMAGES`** (class): Full paths to image files
  * LOGO, SPLASH

### 3.6 Timing Constants

* **`SPLASH_DURATION_S`**: Splash screen display time (3.0 seconds)
* **`TERMS_DURATION_S`**: Terms screen timeout (0 = requires button press)
* **`DEBOUNCE_DELAY_S`**: Button debounce delay (0.2 seconds)
* **`NETWORK_UPDATE_INTERVAL_S`**: Network info refresh interval (10.0 seconds)
* **`TEMP_UPDATE_INTERVAL_S`**: Temperature sensor refresh interval (10.0 seconds)
* **`MAIN_LOOP_DELAY_S`**: Main UI loop delay (0.03 seconds)
* **`SPECTRO_LOOP_DELAY_S`**: Spectrometer loop delay (0.05 seconds)
* **`DIVISION_EPSILON`**: Small value to prevent division by zero (1e-9)

### 3.7 Data & File Paths

* **`DATA_BASE_DIR`**: Base directory for application data (`~/pysb-app`)
* **`DATA_DIR`**: Directory for spectra data (`~/pysb-app/spectra_data`)
* **`CSV_BASE_FILENAME`**: Base name for CSV log files (`spectra_log.csv`)
* **`DISCLAIMER_TEXT`**: Multi-line disclaimer text for terms screen

### 3.8 Spectrometer Settings

* **`SPECTROMETER`** (class): Spectrometer configuration constants
  * DEFAULT_INTEGRATION_TIME_MS=1000
  * MIN_INTEGRATION_TIME_MS=100
  * MAX_INTEGRATION_TIME_MS=6000
  * INTEGRATION_TIME_STEP_MS=50
  * HW_INTEGRATION_TIME_MIN_US=3800
  * HW_INTEGRATION_TIME_MAX_US=6000000
  * HW_INTEGRATION_TIME_BASE_US=10
  * HW_MAX_ADC_COUNT=16383

### 3.9 Auto-Integration Settings

* **`AUTO_INTEGRATION`** (class): Auto-integration algorithm parameters
  * TARGET_LOW_PERCENT=80.0
  * TARGET_HIGH_PERCENT=95.0
  * MAX_ITERATIONS=20
  * PROPORTIONAL_GAIN=0.8
  * MIN_ADJUSTMENT_US=50
  * OSCILLATION_DAMPING_FACTOR=0.5

### 3.10 Plotting Settings

* **`PLOTTING`** (class): Plot rendering configuration
  * USE_LIVE_SMOOTHING=True
  * LIVE_SMOOTHING_WINDOW_SIZE=9
  * Y_AXIS_DEFAULT_MAX=1000.0
  * Y_AXIS_RESCALE_FACTOR=1.2
  * Y_AXIS_MIN_CEILING=100.0
  * WAVELENGTH_RANGE_MIN_NM=400.0 (default minimum wavelength to display)
  * WAVELENGTH_RANGE_MAX_NM=620.0 (default maximum wavelength to display)
  * WAVELENGTH_EDIT_STEP_NM=20 (step size for menu adjustment)
  * WAVELENGTH_EDIT_MIN_LIMIT_NM=340 (hardware minimum)
  * WAVELENGTH_EDIT_MAX_LIMIT_NM=850 (hardware maximum)
  * WAVELENGTH_EDIT_MIN_GAP_NM=40 (minimum gap between min and max)

### 3.11 Mode Definitions

* **`MODES`** (class): Lens types, collection modes, and spectra types
  * Lens types: FIBER, CABLE, FIBER+CABLE
  * Collection modes: RAW, REFLECTANCE
  * Spectra types: RAW, REFLECTANCE, DARK, WHITE, RAW_REFLECTANCE

## 4. Application State Management (`main.py`)

The application's flow and state are managed by a set of global variables and threading events in `main.py`.

### Primary State Machine

- **`app_state` (string)**: This is the core state machine variable. It determines which UI screen is currently active and what logic should be executed in the main loop.
  - `"MENU"`: The main menu is active. The `MenuSystem` class handles input and drawing.
  - `"SPECTROMETER"`: The main data capture screen is active.

### Global Threading Events

These `threading.Event` objects are used to coordinate actions across all running threads safely.

- **`shutdown_flag`**: When set, all threads should clean up and terminate gracefully. This signals a complete application shutdown.
- **`leak_detected_flag`**: Set by the `LeakSensor` thread if the hardware detects a leak. The main loop and UI screens monitor this flag to display a warning and shut down immediately.
- **`stop_spectrometer_stream`**: Set to pause the spectrometer capture process. This is used when navigating away from the spectrometer screen (e.g., back to the menu) to prevent unnecessary background processing and to save power when the spectrometer is not in use.

### Reference Capture Flags

These boolean flags are used to signal to the spectrometer screen that new calibration captures are required.

- **`dark_reference_required`**: Set to `True` when a setting affecting the dark reference (like integration time) is changed.
- **`white_reference_required`**: Set to `True` when a setting affecting the white reference is changed.

### Shared Data Objects

* **`spectrometer_settings` (`SpectrometerSettings` dataclass)**: An instance of the dataclass that holds the current configuration for a spectrometer capture (e.g., integration time, mode). It is passed to the menu system to be modified and to the spectrometer system to be used for captures.

### Thread-Safe Communication Queues

* **`spectrometer_request_queue`**: Queue for sending requests to the spectrometer controller
* **`spectrometer_result_queue`**: Queue for receiving capture results from the spectrometer
* **`data_manager_save_queue`**: Queue for sending save requests to the data manager

## 5. Completed Hardware Components

### 5.1 ButtonHandler (`hardware/button_handler.py`)

**Status:** ✅ Functional and tested with full Doxygen documentation and robust error recovery

Manages all button inputs from both GPIO pins and Pygame keyboard events, providing a unified interface.

**Features:**

* Supports both GPIO buttons (Pimoroni Display HAT or Adafruit PiTFT) and Hall effect sensors
* Multiple button sources active simultaneously (Hall Effect + PiTFT)
* Graceful fallback to keyboard-only mode if GPIO is unavailable
* Thread-safe button state management with debouncing
* Direct GPIO callback (not lambda) to avoid closure issues
* Pin-to-button mapping dictionary for reliable interrupt handling
* Keyboard mappings: Arrow keys, WASD, Enter, Space, Backspace, B, Escape
* **Robust GPIO error recovery with automatic retry logic (3 attempts)**
* **Automatic pin cleanup and re-initialization on edge detection failures**

**API:**

* `check_pygame_events()`: Poll Pygame events (call once per frame in main loop)
* `get_pressed(button_name)`: Check and consume a button press event
* `cleanup()`: Clean up GPIO resources

**Implementation Notes:**

* Uses direct callback method reference instead of lambda to avoid variable capture issues
* Stores pin-to-button mapping in instance variable for callback lookup
* Supports multiple GPIO button sources without pin conflicts
* Implements 3-attempt retry logic for edge detection failures with progressive cleanup
* Re-configures GPIO pins as INPUT after cleanup to prevent "channel not setup" errors
* Adds delays (100ms initial, 50ms between retries) to allow kernel to release pins
* Explicitly removes edge detection on all pins during cleanup for clean shutdown

### 5.2 LeakSensor (`hardware/leak_sensor.py`)

**Status:** ✅ Functional with Doxygen documentation

Monitors a GPIO pin for leak detection in a background thread using dependency injection.

**Features:**

* Runs as a daemon thread with configurable polling interval
* Sets `leak_detected_flag` event when leak is detected
* Gracefully shuts down when `shutdown_flag` is set
* Handles GPIO initialization and cleanup

**Dependency Injection:**

* `shutdown_flag`: Threading event to signal thread termination
* `leak_detected_flag`: Threading event to signal leak detection

### 5.3 NetworkInfo (`hardware/network_info.py`)

**Status:** ✅ Functional with Doxygen documentation

Fetches WiFi SSID and IP address in a background thread to prevent UI blocking.

**Features:**

* Periodically checks network interface status
* Uses system commands (`iwgetid`, `hostname -I`) for network info
* Thread-safe getters for cached network data
* Graceful error handling with fallback values

**API:**

* `start()`: Start the background update thread
* `stop()`: Stop the background thread
* `get_wifi_name()`: Get cached WiFi SSID
* `get_ip_address()`: Get cached IP address

### 5.4 TempSensorInfo (`hardware/temp_sensor.py`)

**Status:** ✅ Functional with Doxygen documentation

Manages MCP9808 temperature sensor readings and automatic fan control in a background thread.

**Features:**

* MCP9808 I2C temperature sensor support via Adafruit library
* Automatic fan control based on configurable temperature threshold
* MOSFET-controlled fan via GPIO pin (default: GPIO 4)
* Thread-safe temperature and fan state access
* Graceful degradation if sensor unavailable (fan still controllable)
* Runtime threshold adjustment via menu

**Fan Control Logic:**

* Fan turns ON when temperature >= threshold
* Default threshold is 0°C (fan always on when spectrometer starts)
* Higher thresholds (e.g., 40°C) save power by only cooling when needed
* Fan state preserved if temperature read fails

**Configuration (config.py):**

* `FAN_ENABLE_PIN`: GPIO pin for MOSFET gate control (default: 4)
* `FAN_DEFAULT_THRESHOLD_C`: Default threshold temperature (default: 0)
* `FAN_THRESHOLD_MIN_C`: Minimum threshold for menu (default: 0)
* `FAN_THRESHOLD_MAX_C`: Maximum threshold for menu (default: 60)
* `FAN_THRESHOLD_STEP_C`: Menu adjustment step size (default: 5)
* `TEMP_UPDATE_INTERVAL_S`: Sensor polling interval (default: 10.0 seconds)

**Dependency Injection:**

* `shutdown_flag`: Threading event to signal thread termination

**API:**

* `start()`: Start the background temperature/fan control thread
* `stop()`: Stop the thread and turn off fan, cleanup GPIO
* `get_temperature_c()`: Get current temperature (float) or error string
* `is_fan_enabled()`: Get current fan state (boolean)
* `get_fan_threshold_c()`: Get current fan threshold (int)
* `set_fan_threshold_c(threshold)`: Set new fan threshold (int)
* `get_display_string()`: Get formatted string for menu display

**Hardware Wiring:**

```text
Fan Red Wire    -> 5V through MOSFET drain
Fan Black Wire  -> Ground
Fan Yellow Wire -> Not connected (tachometer not used)
MOSFET Gate     -> GPIO 4 (configurable)
MCP9808 SDA     -> GPIO 2 (I2C data)
MCP9808 SCL     -> GPIO 3 (I2C clock)
MCP9808 VCC     -> 3.3V
MCP9808 GND     -> Ground
```

**Library Path (Raspberry Pi):**

```text
/home/pi/pysb-app/lib/Adafruit_Python_MCP9808/MCP9808.py
```

### 5.5 SpectrometerController (`hardware/spectrometer_controller.py`)

**Status:** ✅ Functional and tested with full Doxygen documentation

Background thread controller for USB spectrometer with session-based scan validity tracking.

**Key Features:**

* **Session-based validity tracking**: Automatically discards scans from previous sessions
  * Session ID increments when user enters live view or changes settings
  * Each scan captures session_id when it STARTS (not when it finishes)
  * UI only accepts scans where `scan.session_id == current_session_id`
  * Solves the "6-second integration time" problem - stale scans are automatically discarded
* **Queue-based command interface**: Thread-safe communication via request/result queues
* **Seabreeze integration**: Uses pyseabreeze library for Ocean Optics spectrometers
* **RAW and REFLECTANCE modes**: Automatic reflectance calculation using dark/white references
* **Scan averaging**: Average 0-50 scans to reduce noise
* **Hardware integration time clamping**: Respects device limits
* **Reference management**: Dark and white reference capture for reflectance mode

**Session Validity Example:**

User enters live view → `session_id = 42`
Scan starts (6-second integration) → `scan.session_id = 42`
User enters menu → `session_id = 43` (new session)
User returns to live view → `session_id = 44` (new session)
6-second scan finishes → `scan.session_id = 42` (old session)
UI receives scan → `42 != 44` → **Scan discarded automatically**
Fresh scan starts → `scan.session_id = 44` → **Valid scan displayed**

**Commands:**

* `CMD_START_SESSION`: Start new capture session (increments session_id)
* `CMD_STOP_SESSION`: Pause capturing
* `CMD_UPDATE_SETTINGS`: Update integration time or scan averaging (starts new session)
* `CMD_CAPTURE_DARK_REF`: Capture dark reference
* `CMD_CAPTURE_WHITE_REF`: Capture white reference
* `CMD_SET_COLLECTION_MODE`: Set RAW or REFLECTANCE mode (starts new session)
* `CMD_SHUTDOWN`: Terminate thread

**API:**

* `start()`: Start the spectrometer controller thread
* `stop()`: Stop the thread and close spectrometer
* Command interface via `request_queue` (put `SpectrometerCommand` objects)
* Results via `result_queue` (get `SpectrometerResult` objects)

**Data Structures:**

* `SpectrometerCommand`: Command packet (command_type, integration_time_ms, scans_to_average, collection_mode)
* `SpectrometerResult`: Result packet (wavelengths, intensities, timestamp, integration_time_ms, collection_mode, scans_to_average, session_id, spectra_type, is_valid, raw_intensities)
* `SaveRequest` (in `data/data_manager.py`): Save packet (wavelengths, intensities, timestamp, integration_time_ms, scans_to_average, spectra_type, collection_mode, lens_type, temperature_c, raw_intensities_for_reflectance)

**Thread Safety:**

* All communication via thread-safe queues
* Shutdown coordinated via global `shutdown_flag` event
* No shared mutable state between threads

## 6. Completed UI Components

### 6.1 display_utils.py (`ui/display_utils.py`)

**Status:** ✅ Functional with Doxygen documentation

Provides reusable drawing functions for text and images.

**Functions:**

* `draw_text()`: Renders wrapped text within a rectangle with auto-centering
* `draw_image_centered()`: Loads and centers an image with optional fallback text

### 6.2 splash_screen.py (`ui/splash_screen.py`)

**Status:** ✅ Functional with Doxygen documentation

Displays the application logo for a configured duration.

**Features:**

* Uses dependency injection for `leak_detected_flag`
* Exits immediately if leak is detected
* Configurable duration via `config.SPLASH_DURATION_S`

### 6.3 terms_screen.py (`ui/terms_screen.py`)

**Status:** ✅ Functional with Doxygen documentation

Displays disclaimer text with optional timeout or button press to continue.

**Features:**

* Auto-advance after timeout or wait for ENTER button
* Monitors leak detection flag for emergency exit
* Displays hint text when button press is required

### 6.4 leak_warning.py (`ui/leak_warning.py`)

**Status:** ✅ Functional

Displays critical leak warning message.

### 6.5 menu_system.py (`ui/menu_system.py`)

**Status:** ✅ Functional with full datetime editing and network display

Main menu for navigating settings and starting capture.

**Current Implementation:**

* Menu navigation with UP/DOWN buttons
* Value editing with UP/DOWN (adjusts selected value)
* Settings: Integration time, collection mode, scans to average
* Field-by-field date/time editing with time offset tracking
* Network information display (WiFi SSID, IP address)
* Start capture action
* Context-sensitive hint text at bottom

**Features:**

* **Date/Time Editing**: Field-by-field editing (year→month→day, hour→minute)
  * Uses time offset (datetime.timedelta) to preserve user-set time
  * ENTER advances through fields and saves when complete
  * BACK cancels edits and restores original offset
  * Green highlight during editing, yellow when selected
  * Hint text shows current field being edited
* **Network Display**: Shows WiFi SSID and IP (greyed out when not connected)
* **Reference Tracking**: Sets dark_reference_required and white_reference_required flags when settings change

**Public Methods:**

* `handle_input()`: Process button presses and return actions
* `draw()`: Render menu to screen
* `get_current_display_time()`: Get current time with offset (for CSV timestamps)

### 6.6 plotting.py (`ui/plotting.py`)

**Status:** ✅ Functional and tested with full Doxygen documentation

High-performance plotting library for spectral data visualization with optimized data flow.

**Classes:**

* **OptimizedPygamePlotter**: Core plotter with data decimation and numpy vectorization
  * Separate static/plot surfaces for efficient rendering
  * Pre-computed screen coordinates
  * NaN/inf safe rendering
  * Axes, labels, ticks, and grid support
  * Dynamic Y-axis scaling

* **FastSpectralRenderer**: Wrapper with caching and performance monitoring
  * MD5-based data caching
  * FPS and frame time monitoring
  * Configurable smoothing
  * Automatic wavelength update detection
  * **Preserves original wavelength data separately from display data to prevent overwrite bugs**

**Helper Functions:**

* `crop_wavelength_range()`: Crop spectral data to wavelength range (400-620nm)
* `decimate_spectral_data_for_display()`: Reduce points using block averaging
* `apply_fast_smoothing()`: Fast numpy convolution smoothing
* `prepare_display_data()`: Complete 3-stage pipeline (crop → smooth → decimate)

**Performance:**

* Reduces 2048 points to 300 display points
* Maintains 30+ FPS rendering
* <50ms frame times
* Handles long scans without blocking

### 6.7 spectrometer_screen.py (`ui/spectrometer_screen.py`)

**Status:** ✅ Functional and tested with queue-based controller integration

Live spectrometer view screen for displaying spectral plots in real-time at ~30 FPS.

**Key Features:**

* **Session-based validity tracking**: Only displays scans where `result.is_valid == True`
  * Automatically discards stale scans from previous sessions
  * Works seamlessly with SpectrometerController's session tracking
* **Queue-based communication**: Thread-safe communication with controller
  * `request_queue`: Send commands (START_SESSION, STOP_SESSION, etc.)
  * `result_queue`: Receive scan results with validity flags
  * `save_queue`: Send save requests to data manager
* **Live plotting**: Uses FastSpectralRenderer for high-performance visualization
* **Freeze/capture**: Freeze current plot and save to CSV
  * **Thread control in review state**: Spectrometer thread stops when reviewing frozen scan
  * **Fresh data on unfreeze**: New session starts when returning to live view
  * Prevents stale data and saves power during review
* **Reference capture**: Dark and white reference capture workflows
* **Status display**: Shows integration time, mode, scan averaging, reference status
* **Optimized initialization**: Settings synced before session start to prevent rapid session cycling
* **Renderer reset on entry**: Clears previous wavelength data for fresh initialization

**Screen States:**

* `STATE_LIVE_VIEW`: Displays live spectral data
* `STATE_FROZEN`: Frozen plot for capture/save
* `STATE_CAPTURE_DARK_REF`: Capturing dark reference (cover sensor)
* `STATE_CAPTURE_WHITE_REF`: Capturing white reference (point at white target)

**Button Controls by State:**

**Live View (Mode: LIVE):**

* **A (ENTER)**: Freeze current spectrum for capture
* **X (UP)**: Enter calibration menu
* **Y (DOWN)**: Rescale Y-axis based on current data
* **B (BACK)**: Return to main menu
* Hint: `A:Freeze | X:Calib | Y:Rescale | B:Menu`

**Calibration Menu:**

* **A (ENTER)**: Start white reference capture
* **X (UP)**: Start dark reference capture
* **Y (DOWN)**: Start auto-integration (placeholder)
* **B (BACK)**: Return to live view
* Hint: `A:White | X:Dark | Y:Auto | B:Back`

**Dark/White Reference Live Capture:**

* **A (ENTER)**: Freeze current spectrum
* **Y (DOWN)**: Rescale Y-axis
* **B (BACK)**: Return to calibration menu
* Hint: `Cover sensor | A:Capture | Y:Rescale | B:Back` (dark)
* Hint: `Point at white | A:Capture | Y:Rescale | B:Back` (white)

**Frozen View (capture review):**

* **A (ENTER)**: Save frozen data
* **B (BACK)**: Discard and return to live view

**On-Screen Display:**

* **Top Left**: Collection mode, integration time, scan averaging (e.g., "RAW | 1000ms | Avg:10")
* **Top Right**: Current screen state mode (e.g., "Mode: LIVE", "Mode: REVIEW", "Mode: DARK REF")
* **Bottom Center**: Context-sensitive hint text

**Y-Axis Scaling:**

* **Initial defaults**: Set when entering screen based on collection mode
  * RAW mode: 1000.0 (max ADC counts)
  * REFLECTANCE mode: 10.0 (reflectance ratio)
* **Manual rescale**: Press Y button to rescale based on current maximum intensity
  * Applies 1.2x scaling factor with mode-specific min/max limits
  * RAW limits: 100.0 to (HW_MAX_ADC_COUNT * 1.2)
  * REFLECTANCE limits: 0.2 to 200.0

**Public Methods:**

* `enter()`: Called when entering screen (sends START_SESSION)
* `exit()`: Called when exiting screen (sends STOP_SESSION)
* `handle_input()`: Process button presses, returns "MENU" to exit
* `update()`: Process results from queue, update plot
* `draw()`: Render screen (plot, status, hints)

**Integration with Controller:**

```python
# Enter screen → start new session
spectro_screen.enter()
  → request_queue.put(SpectrometerCommand(CMD_START_SESSION))

# Update screen → process results
spectro_screen.update()
  → result = result_queue.get_nowait()
  → if result.is_valid: update_plot(result)
  → else: discard_stale_scan()

# Freeze scan (enter review) → stop session
spectro_screen._freeze_current_data()
  → request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))
  → Thread pauses, no background captures

# Unfreeze (exit review) → start new session
spectro_screen._unfreeze()
  → request_queue.put(SpectrometerCommand(CMD_START_SESSION))
  → Fresh scans begin from current spectrometer position

# Exit screen → stop session
spectro_screen.exit()
  → request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))
```

## 7. Pending Components (To Be Migrated)

### 7.1 temp_sensor.py ✅ COMPLETED

**Source:** `archive/Adafruit_pitft/main.py` lines 752-863 (TempSensorInfo class)

**Status:** Completed 2025-12-14

**Implementation:**

* ✅ Created `hardware/temp_sensor.py` with TempSensorInfo class
* ✅ Background thread for temperature monitoring and fan control
* ✅ MCP9808 sensor via Adafruit library
* ✅ MOSFET-controlled fan with configurable threshold
* ✅ Thread-safe temperature, fan state, and threshold access
* ✅ Menu integration for fan threshold adjustment
* ✅ Full Doxygen documentation

See Section 5.4 for complete documentation.

### 7.2 data_manager.py ✅ COMPLETED

**Source:** `archive/Adafruit_pitft/main.py` (CSV writing and file I/O logic)

**Status:** Completed 2025-12-03

**Implementation:**

* ✅ Created `data/data_manager.py` with DataManager class
* ✅ Background thread processes save requests from queue
* ✅ Daily folder organization (`DATA_DIR/YYYY-MM-DD/`)
* ✅ CSV file with headers including wavelengths as columns
* ✅ Matplotlib plot generation (PNG) for RAW and REFLECTANCE spectra
* ✅ Saves raw intensities alongside reflectance data (RAW_REFLECTANCE type)
* ✅ Thread-safe file I/O with queue-based communication
* ✅ Full Doxygen documentation

## 8. Refactoring Achievements

### ✅ Phase 1 Complete: Foundation & Core Architecture

**Completed:**

1. ✅ Fixed circular import issues (splash_screen, terms_screen)
2. ✅ Reorganized assets directory structure (fonts/, images/)
3. ✅ Added missing config values (LEAK_SENSOR_CHECK_S, BTN_LEFT, BTN_RIGHT)
4. ✅ Implemented dependency injection pattern throughout
5. ✅ Created hardware abstraction layer (button_handler, leak_sensor, network_info)
6. ✅ Implemented core UI utilities (display_utils, splash, terms, leak_warning, menu_system)
7. ✅ Established thread-safe communication patterns
8. ✅ Added Doxygen documentation to all new modules
9. ✅ Implemented field-by-field date/time editing with offset tracking

### ✅ Phase 2 Complete: Spectrometer Integration

**Completed:**

1. ✅ Created high-performance plotting library (`ui/plotting.py`)
   * OptimizedPygamePlotter with pre-computed screen coordinates
   * FastSpectralRenderer with MD5 caching
   * Helper functions: crop, decimate, smooth, prepare_display_data
   * Maintains 30+ FPS with 2048→300 point decimation
   * **Fixed: Prevents original_x_data overwrite during display updates**
2. ✅ Implemented spectrometer controller thread (`hardware/spectrometer_controller.py`)
   * Session-based scan validity tracking (solves 6-second integration problem)
   * Queue-based command/result interface
   * RAW and REFLECTANCE mode support
   * Dark/white reference management
   * Scan averaging (0-50 scans)
   * Seabreeze integration with hardware limit clamping
3. ✅ Created live spectrometer screen (`ui/spectrometer_screen.py`)
   * Real-time spectral plot display at ~30 FPS
   * Session validity checking (automatic stale scan discard)
   * Freeze/capture workflow
   * Dark/white reference capture UI
   * Status display (mode, integration, references)
   * **Fixed: Optimized command sequencing to prevent session cycling**
4. ✅ Integrated spectrometer components into main.py
   * Queue-based communication between screen and controller
   * State machine integration (MENU ↔ SPECTROMETER)
   * Thread lifecycle management (start/stop)
   * Clean separation of concerns
   * **Fixed: Default settings now match between dataclass and config**
5. ✅ Enhanced ButtonHandler reliability
   * 3-attempt retry logic for GPIO edge detection failures
   * Automatic pin cleanup and re-initialization
   * Robust error recovery for reliable startup

**Critical Bug Fixes:**

1. **Integration Time Conflict (main.py)**
   * **Problem**: SpectrometerSettings defaulted to 100ms but config.py specified 1000ms
   * **Symptom**: Integration time flashing between values, settings conflicts
   * **Solution**: Changed dataclass defaults to use config values
   * **File**: `main.py:48-50`

2. **Array Length Mismatch (plotting.py)**
   * **Problem**: `update_spectrum` called `set_x_data_static()` which overwrote `original_x_data` with decimated display data
   * **Symptom**: "Wavelengths and intensities must have same length" errors after first update
   * **Solution**: Directly update `display_x_data` without touching `original_x_data`
   * **File**: `ui/plotting.py:830-840`

3. **Session Cycling (spectrometer_screen.py)**
   * **Problem**: Commands sent in rapid succession (START_SESSION → UPDATE_SETTINGS → SET_MODE) caused multiple session increments
   * **Symptom**: Rapid session ID changes, discarded scans
   * **Solution**: Sync settings BEFORE starting session, reorder command sequence
   * **File**: `ui/spectrometer_screen.py:145-153`

4. **GPIO Edge Detection Failures (button_handler.py)**
   * **Problem**: GPIO pins from previous run not properly cleaned up, edge detection already set
   * **Symptom**: "Failed to add edge detection" error on startup, requiring restart
   * **Solution**: 3-attempt retry with cleanup, re-setup as INPUT, proper delays
   * **File**: `hardware/button_handler.py:82-90, 159-197`

5. **Review State Thread Control (spectrometer_screen.py)** ✅ **FIXED 2025-11-23**
   * **Problem**: Spectrometer thread continued capturing when reviewing frozen scans, and didn't restart fresh when returning to live view
   * **Symptom**: Wasted battery/processing during review, stale data displayed when unfreezing
   * **Solution**: Added `CMD_STOP_SESSION` in `_freeze_current_data()` and `CMD_START_SESSION` in `_unfreeze()`
   * **File**: `ui/spectrometer_screen.py:334, 344`
   * **Benefit**: Thread now properly pauses during review and always provides fresh data representative of current spectrometer position

6. **Reflectance Clipping Too Aggressive (spectrometer_controller.py)** ✅ **FIXED 2025-12-14**
   * **Problem**: Reflectance values were clipped to [0.0, 1.0] range
   * **Symptom**: Saved reflectance data capped at 1.0, losing legitimate high values
   * **Solution**: Changed `np.clip(reflectance, 0.0, 1.0)` to `np.maximum(reflectance, 0.0)`
   * **File**: `hardware/spectrometer_controller.py:717`
   * **Benefit**: Values > 1.0 now preserved (valid for fluorescence, specular reflection, etc.)

7. **Reference Captures Using Reflectance Mode (spectrometer_screen.py)** ✅ **FIXED 2025-12-14**
   * **Problem**: When in REFLECTANCE mode, dark/white reference captures were showing reflectance-processed data instead of raw sensor data
   * **Symptom**: White reference live feed and frozen data showed clipped/processed values, not raw ADC counts
   * **Solution**: Added `CMD_SET_COLLECTION_MODE` with `MODE_RAW` in `_start_live_dark_reference()` and `_start_live_white_reference()`, stored original mode in `_stored_collection_mode`, restored mode in `_exit_calibration_to_live_view()`
   * **Files**: `ui/spectrometer_screen.py:587-639, 679-722`
   * **Benefit**: References now always capture raw sensor data, which is correct for the reflectance formula

8. **Auto-Integration Not Updating Controller (spectrometer_screen.py)** ✅ **FIXED 2025-12-14**
   * **Problem**: Auto-integration calculated new integration time but controller kept using old value
   * **Symptom**: After auto-integration completed and applied (e.g., 6000ms), live view showed old integration time (e.g., 1000ms)
   * **Root Cause**: `_apply_auto_integration_result()` updated `self.settings.integration_time_ms` but did NOT send `CMD_UPDATE_SETTINGS` to the controller. The controller has its own internal `_integration_time_ms` variable.
   * **Solution**: Added `CMD_UPDATE_SETTINGS` command in `_apply_auto_integration_result()` to sync the new integration time to the controller
   * **File**: `ui/spectrometer_screen.py:1292-1380`
   * **Additional Fixes**:
     * Invalidate dark/white references when auto-integration changes integration time (references at different integration time not valid for reflectance)
     * Added `_auto_rescale_on_next_scan` flag to trigger Y-axis rescale on first scan after auto-integration (signal levels change with integration time in RAW mode)

### ✅ Phase 3 Complete: Data Storage & Save Workflow

**Completed 2025-12-03:**

1. ✅ Created data management module (`data/data_manager.py`)
   * DataManager class with background thread for file I/O
   * Queue-based save request processing
   * Daily folder organization (`~/pysb-app/spectra_data/YYYY-MM-DD/`)
   * CSV file with wavelengths as column headers
   * Matplotlib plot generation for RAW and REFLECTANCE spectra
   * Automatic raw intensity saving alongside reflectance (RAW_REFLECTANCE type)
   * Daily scan counter with persistence across sessions
   * Full Doxygen documentation

2. ✅ Extended SpectrometerResult dataclass
   * Added optional `raw_intensities` field for reflectance mode
   * Controller populates raw intensities when calculating reflectance
   * Enables saving both reflectance and raw target data

3. ✅ Implemented save workflow in spectrometer_screen.py
   * `_save_frozen_data()` creates SaveRequest with all capture metadata
   * Sends to data_manager_save_queue for async file I/O
   * Stores raw intensities for reflectance mode saves
   * Tracks scans_to_average in frozen data

4. ✅ Integrated DataManager into main.py
   * Thread starts on application launch
   * Graceful shutdown on application exit
   * Queue-based communication with spectrometer screen

**CSV Format:**

```text
timestamp_utc, spectra_type, lens_type, integration_time_ms, scans_to_average, temperature_c, [wavelengths...]
2025-12-03T10:30:00Z, RAW, FIBER, 1000, 5, , 400.12, 400.24, ...
```

**File Organization:**

```text
~/pysb-app/spectra_data/
└── 2025-12-03/
    ├── 2025-12-03_spectra_log.csv
    ├── spectrum_RAW_FIBER_2025-12-03-103000.png
    └── spectrum_REFLECTANCE_FIBER_2025-12-03-104500.png
```

**Key Features:**

* Lens type defaults to FIBER (original used variable lens types)
* Scans to average now included in CSV (was not used in original)
* Temperature column reserved for future temp_sensor integration
* Raw target intensities saved with RAW_REFLECTANCE type when in reflectance mode
* Plot generation only for OOI scans (RAW and REFLECTANCE), not for references

### ✅ Phase 4 Complete: Calibration Workflow

**Completed 2025-12-03:**

1. ✅ New screen states for calibration workflow
   * `STATE_CALIBRATION_MENU` - Select calibration type
   * `STATE_LIVE_DARK_REF` - Live view for dark reference capture
   * `STATE_LIVE_WHITE_REF` - Live view for white reference capture
   * `STATE_FROZEN_DARK_REF` - Frozen dark reference for save/discard
   * `STATE_FROZEN_WHITE_REF` - Frozen white reference for save/discard

2. ✅ Y-axis scale persistence
   * Store Y-axis scale when entering calibration menu
   * Restore Y-axis scale when returning to live view
   * Auto-rescale on first scan in reference capture mode

3. ✅ Calibration menu implementation
   * Direct button mapping: A=White, X=Dark, Y=Auto, B=Back
   * Shows button options and current reference status (OK/Not Set)

4. ✅ Reference capture live feed
   * Spectrometer starts fresh session when entering reference capture
   * Shows live feed of spectrometer with averaging
   * User can rescale Y-axis during capture
   * First scan triggers automatic Y-axis rescale

5. ✅ Freeze/Save/Discard for references
   * A button freezes current averaged scan
   * Frozen view shows "DARK REVIEW" or "WHITE REVIEW" status
   * A button saves to CSV and stores reference in controller
   * B button discards and returns to live reference capture with fresh scan

6. ✅ Reference saves
   * Saved to CSV with spectra_type DARK or WHITE
   * No PNG plot generation for calibration scans
   * Reference stored in controller for reflectance calculations

**Calibration Workflow:**

```text
Live View (RAW/REFLECTANCE)
    │  Hint: "A:Freeze | X:Calib | Y:Rescale | B:Menu"
    │
    ├── [X] Enter Calibration Menu
    │         ├── Spectrometer stops
    │         └── Y-axis scale stored
    │
    ▼
Calibration Menu
    │  Hint: "A:White | X:Dark | Y:Auto | B:Back"
    │
    ├── [A] Start White Reference capture
    ├── [X] Start Dark Reference capture
    ├── [Y] Start Auto-Integration (placeholder)
    │         ├── Spectrometer starts fresh session
    │         ├── Y-axis auto-rescales on first scan
    │         └── Live feed displayed
    │
    └── [B] Return to Live View
              └── Y-axis scale restored
    │
    ▼
Live Dark/White Reference
    │  Hint: "Cover sensor | A:Capture | Y:Rescale | B:Back" (dark)
    │  Hint: "Point at white | A:Capture | Y:Rescale | B:Back" (white)
    │
    ├── [Y] Rescale Y-axis
    ├── [A] Freeze for capture
    │         └── Spectrometer stops
    │
    └── [B] Return to Calibration Menu
    │
    ▼
Frozen Dark/White Reference
    │  Hint: "A:Save Dark/White Ref | B:Discard"
    │
    ├── [A] Save
    │         ├── Save to CSV (no PNG)
    │         ├── Store in controller
    │         └── Return to Live View
    │
    └── [B] Discard
              ├── Spectrometer restarts
              └── Return to Live Reference Capture
```

**Benefits Achieved:**

* No circular dependencies - all modules are now standalone
* Clear separation of concerns across hardware, UI, and data layers
* Thread-safe architecture with proper event coordination
* Centralized configuration for easy maintenance
* Improved code documentation and maintainability
* **Live spectrometer plotting at 30 FPS with 1516-pixel sensor**
* **Reliable startup even after unclean shutdown**

## 9. Next Steps (Remaining Work)

### Phase 3: Data Management ✅ COMPLETE

See Section 8 "Phase 3 Complete" for full implementation details.

**Summary:**

* ✅ DataManager class with background thread
* ✅ CSV file writing with daily folders
* ✅ Matplotlib plot generation
* ✅ Save workflow in spectrometer_screen.py
* ✅ Integration with main.py

### Phase 4: Calibration & Reflectance ✅ COMPLETE

See Section 8 "Phase 4 Complete" for full implementation details.

**Summary:**

* ✅ Calibration menu (Dark/White/Auto-Integration selection)
* ✅ Live feed for reference capture with fresh scan guarantee
* ✅ Auto-rescale Y-axis on first scan in reference mode
* ✅ Freeze/Save/Discard workflow for references
* ✅ Y-axis scale persistence across calibration

### Phase 5: Reflectance Mode & Scan Tracking ✅ COMPLETE

**Reflectance Mode Implementation (2025-12-14):**

1. **Reference Validation**

   * Dark and white references must exist before REFLECTANCE mode starts
   * References must have matching integration times with current settings
   * Validation checks: existence + integration time match
   * If invalid: spectrometer does NOT start, warning displayed

2. **Reference Integration Time Tracking**

   * `_dark_ref_integration_ms` - stored when dark reference is saved
   * `_white_ref_integration_ms` - stored when white reference is saved
   * Validation compares against `settings.integration_time_ms`

3. **Reflectance Calculation**

   * Formula: `Reflectance = (Raw - Dark) / (White - Dark)`
   * Division-by-zero protection using `config.DIVISION_EPSILON`
   * Only negative values clipped to 0.0 (no upper bound)
   * Values > 1.0 are valid (fluorescence, specular reflection, etc.)
   * Calculation performed in SpectrometerController thread

4. **Reference Capture Mode**

   * Dark/White reference captures ALWAYS use RAW mode
   * Collection mode temporarily set to RAW when entering reference capture
   * Original collection mode stored in `_stored_collection_mode`
   * Mode restored when exiting calibration back to live view
   * Ensures references contain raw sensor data, not processed reflectance

5. **Invalid References Warning Screen**

   * Title: "CALIBRATE REQUIRED" (white, centered)
   * Shows simplified reference status:
     * "Dark Reference: Not set" (white) or "Dark Reference: Complete" (yellow)
     * "White Reference: Not set" (white) or "White Reference: Complete" (yellow)
   * Hint: "X: Calibrate | B: Menu"
   * Only X and B buttons functional (A and Y disabled)

**Session Scan Counter (2025-12-14):**

1. **Session Scan Count**

   * `_session_scan_count` - counts RAW and REFLECTANCE scans only
   * Resets each app start (not daily)
   * REFLECTANCE saves both RAW_REFLECTANCE and REFLECTANCE but counts as 1
   * Calibration scans (DARK, WHITE) are NOT counted

2. **Scans Since Last Calibration**

   * `_scans_since_dark_ref` - resets to 0 when dark ref saved
   * `_scans_since_white_ref` - resets to 0 when white ref saved
   * `_scans_since_auto_integ` - resets to 0 when auto-integ completes
   * Incremented on each RAW/REFLECTANCE save

3. **Calibration Invalidation Rules**

   * Integration time change → ALL calibrations invalidated
   * Scans to average change → Dark/White refs invalidated (auto-integ unaffected)
   * Checked on screen entry via `_check_and_handle_settings_changes()`

4. **Status Bar Format**

   ```text
   RAW | INT:1000ms | AVG:1 | SCANS:0 | LIVE
   REFLECT | INT:1000ms | AVG:10 | SCANS:5 | LIVE
   ```

**Calibration Menu Redesign (2025-12-14):**

```text
CALIBRATION MENU

A: White Reference - Set/Not valid
   Scans since last set: ##
X: Dark Reference - Set/Not valid
   Scans since last set: ##
Y: Auto integration - Completed/Not complete
   Integration time: ####ms
   Scans since last set: ##

A:White | X:Dark | Y:Auto | B:Back
```

### Phase 6: Auto-Integration ✅ COMPLETE

**Completed 2025-12-14:**

1. **Command & Result Extensions (spectrometer_controller.py)**
   * Added `CMD_AUTO_INTEG_CAPTURE` command type
   * Added `test_integration_us` parameter to `SpectrometerCommand`
   * Added `peak_adc_value` and `test_integration_us` fields to `SpectrometerResult`
   * Added `SPECTRA_TYPE_AUTO_INTEG` to config.MODES
   * Implemented `_capture_for_auto_integration()` method:
     * Captures single scan at specified integration time (no averaging)
     * Returns result with peak ADC value for algorithm evaluation
     * Uses RAW mode for accurate sensor readings

2. **Auto-Integration States (spectrometer_screen.py)**
   * `STATE_AUTO_INTEG_SETUP` - Setup screen with instructions
   * `STATE_AUTO_INTEG_RUNNING` - Algorithm running iteratively
   * `STATE_AUTO_INTEG_CONFIRM` - Confirm or discard result

3. **Algorithm Implementation**
   * **Proportional Control**: Adjusts integration time based on peak ADC vs target range
   * **Target Range**: 80-95% of max ADC count (configurable in `config.AUTO_INTEGRATION`)
   * **Oscillation Damping**: Detects direction reversals and applies damping factor
   * **Minimum Adjustment**: Enforces minimum step size to prevent stalling
   * **Convergence Detection**: Stops when no further adjustment possible
   * **Hardware Limits**: Respects min/max integration time from device

4. **Configuration Parameters (config.AUTO_INTEGRATION)**

   ```python
   TARGET_LOW_PERCENT = 80.0      # Lower bound of target saturation
   TARGET_HIGH_PERCENT = 95.0     # Upper bound of target saturation
   MAX_ITERATIONS = 20            # Maximum algorithm iterations
   PROPORTIONAL_GAIN = 0.8        # Control loop gain
   MIN_ADJUSTMENT_US = 50         # Minimum integration time step (µs)
   OSCILLATION_DAMPING_FACTOR = 0.5  # Damping when direction reverses
   ```

5. **Algorithm Flow**

   ```text
   Start with current menu integration time
   ↓
   For each iteration (max 20):
     1. Capture single scan at test integration time
     2. Get peak ADC value from result
     3. Check conditions:
        - In target range (80-95%) → CONFIRM with "Target achieved"
        - At min integ & saturated → CONFIRM with "At min, still saturated"
        - At max integ & low → CONFIRM with "At max, still low"
        - Max iterations reached → CONFIRM with "Max iterations"
     4. Calculate new integration time:
        - ratio = target_adc / peak_adc
        - change = (ideal_next - current) * PROPORTIONAL_GAIN
        - Apply oscillation damping if direction reversed
        - Enforce minimum adjustment
        - Clamp to hardware limits
     5. Request next capture
   ↓
   Confirm screen shows result and proposed integration time
   User accepts (A) or cancels (B)
   ```

6. **User Interface**
   * **Setup Screen**: Instructions to aim at white reference, shows starting integration time and target range
   * **Running Screen**: Shows iteration count, current test integration, last peak ADC, target range
   * **Confirm Screen**: Shows frozen spectrum plot with proposed integration time
   * **Hint Text**:
     * Setup: `A:Start | B:Cancel`
     * Running: `B:Cancel`
     * Confirm: `A:Apply {ms}ms | B:Cancel`

7. **Workflow from Calibration Menu**

   ```text
   Calibration Menu
       ↓ [Y button]
   Auto-Integration Setup
       ↓ [A button]
   Auto-Integration Running (iterates automatically)
       ↓ (algorithm completes)
   Auto-Integration Confirm
       ↓ [A button]
   Settings updated, return to Live View
   ```

8. **Integration with Settings**
   * On apply: Updates `settings.integration_time_ms` with new value
   * Marks `_auto_integ_completed = True`
   * Resets `_scans_since_auto_integ = 0`
   * Integration time change also invalidates dark/white references (existing behavior)

### Phase 8: Plot Wavelength Range Menu ✅ COMPLETE

**Completed 2025-12-14:**

1. **Menu Item Implementation**
   * New menu item type: `wavelength_range`
   * Dual-field editing similar to datetime (min → max)
   * Format displayed: `400nm - 620nm`
   * Blue box highlights current field being edited

2. **Configuration Constants (config.PLOTTING)**
   * `WAVELENGTH_RANGE_MIN_NM` - Current minimum wavelength (runtime modifiable)
   * `WAVELENGTH_RANGE_MAX_NM` - Current maximum wavelength (runtime modifiable)
   * `WAVELENGTH_EDIT_STEP_NM = 20` - Adjustment step size
   * `WAVELENGTH_EDIT_MIN_LIMIT_NM = 340` - Hardware lower bound
   * `WAVELENGTH_EDIT_MAX_LIMIT_NM = 850` - Hardware upper bound
   * `WAVELENGTH_EDIT_MIN_GAP_NM = 40` - Minimum gap between min and max

3. **Editing Workflow**
   * Press A to enter edit mode (starts with MIN field)
   * Use X/Y to adjust value by ±20nm steps
   * Press A to advance to MAX field
   * Press A again to save and exit
   * Press B at any time to cancel and restore original values

4. **Validation Rules**
   * MIN cannot go below 340nm (hardware limit)
   * MAX cannot exceed 850nm (hardware limit)
   * MIN must be at least 40nm less than MAX
   * MAX must be at least 40nm greater than MIN

5. **Display vs Save Behavior**
   * Wavelength range ONLY affects plot display cropping
   * Saved CSV files contain FULL wavelength spectrum
   * Reflectance calculations use full wavelength arrays (no data quality impact)
   * Scientists can filter noisy regions (e.g., >700nm) from display while preserving complete data

6. **Technical Implementation**
   * Menu modifies `config.PLOTTING.WAVELENGTH_RANGE_*_NM` at runtime
   * `prepare_display_data()` in `plotting.py` reads config values automatically
   * X-axis ticks auto-adjust using `np.linspace()` for any range
   * No changes needed to plotting.py or spectrometer_screen.py

**Files Modified:**

* `config.py` - Added wavelength editing constants
* `ui/menu_system.py` - Added `wavelength_range` menu item type with dual-field editing

### Phase 9: Temperature Sensor & Fan Control ✅ COMPLETE

**Completed 2025-12-14:**

1. **TempSensorInfo Class (`hardware/temp_sensor.py`)**
   * Background thread for temperature monitoring (10-second interval)
   * MCP9808 I2C temperature sensor via Adafruit library
   * MOSFET-controlled fan on GPIO 4
   * Automatic fan activation when temp >= threshold
   * Thread-safe access to temperature, fan state, threshold
   * Graceful degradation if sensor unavailable

2. **Fan Control Configuration (`config.py`)**
   * `FAN_ENABLE_PIN = 4` - MOSFET gate GPIO pin
   * `FAN_DEFAULT_THRESHOLD_C = 0` - Default: always on
   * `FAN_THRESHOLD_MIN_C = 0` - Minimum threshold
   * `FAN_THRESHOLD_MAX_C = 60` - Maximum threshold
   * `FAN_THRESHOLD_STEP_C = 5` - Menu adjustment step

3. **Menu Integration (`ui/menu_system.py`)**
   * New `fan_threshold` menu item type
   * Display format: `Fan: Threshold ##C (Current ##C)`
   * Real-time temperature display from sensor
   * Threshold adjustment with UP/DOWN buttons (±5°C steps)
   * Fan threshold changes do not invalidate spectrometer references

4. **Integration with main.py**
   * TempSensorInfo instantiated with shutdown_flag
   * Passed to MenuSystem for temperature display and fan control
   * Background thread started/stopped with application lifecycle
   * Fan turned off and GPIO cleaned up on shutdown

**Fan Control Behavior:**

```text
Threshold = 0°C  → Fan always ON (default, maximum cooling)
Threshold = 40°C → Fan ON when temp >= 40°C (power saving)
Threshold = 60°C → Fan ON when temp >= 60°C (minimal cooling)
```

**Menu Display Examples:**

```text
Fan: Threshold 0C (Current 28C)    # Fan always on, current temp 28°C
Fan: Threshold 40C (Current 35C)   # Fan off, waiting for 40°C
Fan: Threshold 40C (Current 42C)   # Fan on, temp above threshold
Fan: Threshold 0C (Temp: N/A)      # Fan on, sensor unavailable
```

**Files Modified:**

* `hardware/temp_sensor.py` - New file with TempSensorInfo class
* `config.py` - Added fan control settings
* `ui/menu_system.py` - Added fan_threshold menu item type
* `main.py` - Integrated TempSensorInfo

### Phase 10: Optional Enhancements

1. **Include temperature in CSV saves**
   * Add temperature column to saved spectra data
   * Pass TempSensorInfo to SpectrometerScreen
   * **Status**: Not implemented

2. **Enhanced error handling**
   * More detailed error messages
   * Recovery strategies for hardware failures
   * **Status**: Basic error handling in place

3. **Save confirmation feedback**
   * Visual feedback when save completes
   * Error indication if save fails
   * **Status**: Not implemented

## 10. Development Guidelines Reminder

When implementing new components, always follow these principles:

* **Dependency Injection:** Pass dependencies via constructors, never import main.py
* **Thread Safety:** Use threading.Lock() for shared state, use Queue for communication
* **Documentation:** Add full Doxygen comments to all classes and functions
* **Error Handling:** Add proper try/except blocks with logging
* **Assertions:** Validate inputs and state transitions
* **Bounded Loops:** Ensure all loops have clear termination conditions
* **No Deletions:** Never remove existing functionality when adding new code

## 11. Testing Checklist

Current Component Status:

* [x] No circular imports (check with import graph)
* [x] All functions have Doxygen documentation
* [x] Thread-safe access to shared state
* [x] Graceful shutdown when shutdown_flag is set
* [x] Proper error handling and logging
* [x] Input validation with assertions
* [x] Code follows NASA-inspired safety principles
* [x] Linter compliance (verified with automatic formatting)
* [x] Live spectrometer plotting functional
* [x] Button handler startup reliability
* [x] Data saving to CSV (implemented 2025-12-03)
* [x] Matplotlib plot generation (implemented 2025-12-03)
* [x] Dark/white reference capture workflow (implemented 2025-12-03)
* [x] Calibration menu navigation
* [x] Reference freeze/save/discard workflow
* [x] Y-axis scale persistence across calibration
* [x] Reflectance mode reference validation (2025-12-14)
* [x] Reflectance mode warning screen when refs invalid (2025-12-14)
* [x] Reference integration time tracking (2025-12-14)
* [x] Session scan counter (2025-12-14)
* [x] Scans-since-calibration counters (2025-12-14)
* [x] Calibration invalidation on settings change (2025-12-14)
* [x] Status bar redesign with scan count (2025-12-14)
* [x] Calibration menu redesign with status info (2025-12-14)
* [x] Reflectance clipping fix - no upper bound (2025-12-14)
* [x] Reference captures always use RAW mode (2025-12-14)
* [x] Auto-integration algorithm (2025-12-14)
* [x] Auto-integration updates controller integration time (2025-12-14)
* [x] Auto-integration invalidates dark/white references (2025-12-14)
* [x] Auto-integration triggers Y-axis rescale on first scan (2025-12-14)
* [x] Plot wavelength range menu item (2025-12-14)
* [x] Wavelength range dual-field editing (min/max) (2025-12-14)
* [x] Wavelength range validation (limits and gap) (2025-12-14)
* [ ] Reflectance mode live feed testing (needs hardware)
* [ ] Auto-integration hardware testing (needs hardware)
* [ ] Plot wavelength range hardware testing (needs hardware)
* [x] Temperature sensor integration (2025-12-14)
* [x] Fan control GPIO setup (2025-12-14)
* [x] Fan threshold menu item (2025-12-14)
* [ ] MCP9808 sensor hardware testing (needs hardware)
* [ ] Fan MOSFET control hardware testing (needs hardware)
* [ ] Fan threshold adjustment hardware testing (needs hardware)

---

## End of Application Guide
