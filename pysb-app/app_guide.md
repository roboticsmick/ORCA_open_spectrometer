# PySB-App Application Guide

This document provides a technical overview of the PySB-App, a Python-based spectrometer application designed for a Raspberry Pi with a touchscreen interface.

**Last Updated:** 2025-12-03
**Refactoring Status:** Phase 4 Complete (Calibration Workflow) ✅

---

## AI Coding Guidelines (Strictly Enforced)

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
│   ├── temp_sensor.py           # ❌ TODO: Temperature sensor thread
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

### 5.4 SpectrometerController (`hardware/spectrometer_controller.py`)

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

**Button Controls (Physical Button → Logical Name):**

* **A (ENTER)**: Freeze/unfreeze plot, save frozen data, or confirm capture
* **B (BACK)**: Return to menu, discard frozen data, or cancel capture
* **X (UP)**: Start dark reference capture
* **Y (DOWN)**: Rescale Y-axis based on current data (in live view and white setup)

**On-Screen Display:**

* **Top Left**: Collection mode, integration time, scan averaging (e.g., "RAW | 1000ms | Avg:10")
* **Top Right**: Current screen state mode (e.g., "Mode: LIVE", "Mode: REVIEW", "Mode: DARK SETUP")
* **Bottom Center**: Context-sensitive hint text (e.g., "A:Freeze | X:Dark | Y:Rescale | B:Menu")

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

### 7.1 temp_sensor.py (High Priority)

**Source:** `archive/Adafruit_pitft/main.py` lines 752-863 (TempSensorInfo class)

**Requirements:**

* Create `hardware/temp_sensor.py`
* Implement TempSensorInfo class with background thread
* Use dependency injection for `shutdown_flag`
* Handle MCP9808 sensor via SMBus2
* Provide thread-safe temperature getter
* Add full Doxygen documentation

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
   * Navigate with X/Y buttons (up/down)
   * Select with A button
   * Options: Dark Reference, White Reference, Auto Integration (placeholder)
   * Shows current reference status (OK/Not Set)

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
    │
    ├── [X] Enter Calibration Menu
    │         ├── Spectrometer stops
    │         └── Y-axis scale stored
    │
    ▼
Calibration Menu
    │
    ├── [X/Y] Navigate options
    ├── [A] Select Dark/White Reference
    │         ├── Spectrometer starts fresh session
    │         ├── Y-axis auto-rescales on first scan
    │         └── Live feed displayed
    │
    └── [B] Return to Live View
              └── Y-axis scale restored
    │
    ▼
Live Dark/White Reference
    │
    ├── [Y] Rescale Y-axis
    ├── [A] Freeze for capture
    │         └── Spectrometer stops
    │
    └── [B] Return to Calibration Menu
    │
    ▼
Frozen Dark/White Reference
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

### Phase 5: Reflectance Testing & Auto-Integration (Next Priority)

1. **Reflectance Mode End-to-End Testing**
   * Verify reflectance calculation: (Raw - Dark) / (White - Dark)
   * Test saving both reflectance and raw target data
   * Verify plot generation for reflectance spectra
   * **Status**: Controller calculates, needs end-to-end testing

2. **Auto-Integration Feature**
   * Implement algorithm from config.AUTO_INTEGRATION
   * Auto-adjust integration time for optimal signal (80-95% saturation)
   * Add to calibration menu (currently placeholder)
   * **Status**: Config exists, menu placeholder exists, not implemented

### Phase 6: Optional Enhancements

1. **Create temp_sensor.py** - Temperature monitoring (optional feature)
   * Implement TempSensorInfo class with background thread
   * MCP9808 sensor via SMBus2
   * Display temperature in menu or status bar
   * Include temperature in CSV saves
   * **Status**: Not started (low priority)

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
* [ ] Reflectance mode end-to-end testing
* [ ] Auto-integration algorithm

---

## End of Application Guide
