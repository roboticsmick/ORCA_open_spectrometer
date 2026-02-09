## @file config.py
#  @brief Centralized configuration module for the PySB-App spectrometer application.
#
#  This module contains all static application-wide constants including:
#  - Asset paths (fonts, images)
#  - Hardware feature flags and GPIO pin definitions
#  - Display settings (screen dimensions, colors, fonts)
#  - Timing constants (debounce, update intervals)
#  - Spectrometer settings (integration time limits, scan averaging)
#  - Auto-integration algorithm parameters
#  - Plotting configuration (wavelength range, smoothing)
#  - Mode definitions (lens types, collection modes, spectra types)
#
#  All values can be tuned here without modifying core application logic.
#  Runtime-modifiable values (like wavelength range) are class attributes.

import os

# --- ASSET PATHS ---
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

# --- Configuration Flags ---
HARDWARE = {
    "USE_DISPLAY_HAT": False,
    "USE_ADAFRUIT_PITFT": False,
    "USE_GPIO_BUTTONS": True,
    "USE_HALL_EFFECT_BUTTONS": True,
    "USE_LEAK_SENSOR": True,
    "USE_SPECTROMETER": True,
    "USE_TEMP_SENSOR_IF_AVAILABLE": True,
}

# --- System ---
os.environ["ALSA_MIXER_CARD"] = "-1"
os.environ["ALSA_MIXER_DEVICE"] = "-1"

# --- PIN DEFINITIONS (BCM Mode) ---
BUTTON_PINS = {"A": 5, "B": 6, "X": 16, "Y": 24}  # Default: Pimoroni Display HAT Mini
if HARDWARE["USE_ADAFRUIT_PITFT"]:
    BUTTON_PINS = {"A": 27, "B": 23, "X": 22, "Y": 17}

HALL_EFFECT_PINS = {"UP": 20, "DOWN": 21, "ENTER": 5, "BACK": 12}

LEAK_SENSOR_PIN = 26
LEAK_SENSOR_CHECK_S = 1.0  # How often to check the leak sensor (seconds)

# Fan control pin (MOSFET gate control)
FAN_ENABLE_PIN = 4

# Fan threshold settings
# Default threshold of 0 means fan is always on when spectrometer starts
FAN_DEFAULT_THRESHOLD_C = 0
FAN_THRESHOLD_MIN_C = 0  # Minimum threshold (0 = always on)
FAN_THRESHOLD_MAX_C = 60  # Maximum threshold
FAN_THRESHOLD_STEP_C = 5  # Step size for menu adjustment

# Button Logical Names (used internally)
BTN_UP = "up"
BTN_DOWN = "down"
BTN_ENTER = "enter"
BTN_BACK = "back"

# Button aliases for menu navigation
# With only 4 physical buttons, LEFT/RIGHT are mapped to UP/DOWN for value editing
BTN_LEFT = "up"  # When editing values, UP acts as LEFT
BTN_RIGHT = "down"  # When editing values, DOWN acts as RIGHT

# --- DATA & FILE PATHS ---
DATA_BASE_DIR = os.path.expanduser("~/pysb-app")
DATA_DIR = os.path.join(DATA_BASE_DIR, "spectra_data")
CSV_BASE_FILENAME = "spectra_log.csv"

# --- UI & DISPLAY ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
SPLASH_DURATION_S = 3.0
TERMS_DURATION_S = 0

DISCLAIMER_TEXT = """\
This open-source software is freely provided
for marine conservation and scientific research.

It comes with ABSOLUTELY NO WARRANTY, no
technical support, and no guarantee of accuracy.

Always verify all data before using for research
purposes. Dive in at your own risk!
"""


## @brief Color definitions as RGB tuples for UI rendering.
#
#  All colors are defined as (R, G, B) tuples with values 0-255.
#  Used throughout the UI for consistent styling.
class COLORS:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    YELLOW = (255, 240, 31)
    GRAY = (128, 128, 128)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)


## @brief Font size definitions in points for different UI elements.
#
#  Defines pixel sizes for text rendering in various UI contexts.
#  Smaller sizes used for info/tick labels, larger for titles.
class FONT_SIZES:
    TITLE = 22
    MENU_ITEM = 16
    MENU_VALUE = 16
    HINT = 16
    DISCLAIMER = 14
    INFO = 14
    SPECTRO = 14
    PLOTTER_TICK = 12
    PLOTTER_AXIS = 14


# Menu layout constants (from original code)
MENU_SPACING = 19
MENU_MARGIN_TOP = 38
MENU_MARGIN_LEFT = 12


## @brief Absolute file paths to TTF font files.
#
#  All paths are constructed from FONTS_DIR at module load time.
#  ChakraPetch used for titles, Segoe UI variants for body text.
class FONTS:
    TITLE = os.path.join(FONTS_DIR, "ChakraPetch-Medium.ttf")
    MAIN = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    HINT = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    SPECTRO = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    PLOTTER_AXIS_LABEL = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    PLOTTER_TICK_LABEL = os.path.join(FONTS_DIR, "Segoe UI Semilight.ttf")


## @brief Absolute file paths to image assets.
#
#  All paths are constructed from IMAGES_DIR at module load time.
#  Used for splash screen and logo display.
class IMAGES:
    LOGO = os.path.join(IMAGES_DIR, "logo.png")
    SPLASH = os.path.join(IMAGES_DIR, "logo.png")  # Same as logo for now


# --- TIMING & DELAYS ---
DEBOUNCE_DELAY_S = 0.2
NETWORK_UPDATE_INTERVAL_S = 10.0
TEMP_UPDATE_INTERVAL_S = 10.0
MAIN_LOOP_DELAY_S = 0.03
SPECTRO_LOOP_DELAY_S = 0.05
DIVISION_EPSILON = 1e-9


## @brief Spectrometer hardware configuration and limits.
#
#  Contains integration time limits (menu and hardware), ADC resolution,
#  and scan averaging parameters. HW_ prefixed values are device limits,
#  others are menu/UI limits.
#
#  @details Integration time is specified in milliseconds for UI and
#  microseconds for hardware communication. The spectrometer has a
#  14-bit ADC (16383 max count).
class SPECTROMETER:
    DEFAULT_INTEGRATION_TIME_MS = 1000
    MIN_INTEGRATION_TIME_MS = 100
    MAX_INTEGRATION_TIME_MS = 6000
    INTEGRATION_TIME_STEP_MS = 50
    HW_INTEGRATION_TIME_MIN_US = 3800
    HW_INTEGRATION_TIME_MAX_US = 6000000
    HW_INTEGRATION_TIME_BASE_US = 10
    HW_MAX_ADC_COUNT = 16383

    # Scan averaging settings
    DEFAULT_SCANS_TO_AVERAGE = 1
    MIN_SCANS_TO_AVERAGE = 0
    MAX_SCANS_TO_AVERAGE = 50
    SCANS_TO_AVERAGE_STEP = 1


## @brief Auto-integration algorithm parameters.
#
#  Controls the proportional feedback loop that automatically finds
#  the optimal integration time by targeting 80-95% ADC saturation.
#
#  @details The algorithm uses proportional control with oscillation
#  damping to converge on an integration time that produces peak
#  ADC values within the target range. Stops after MAX_ITERATIONS
#  or when at hardware limits.
class AUTO_INTEGRATION:
    TARGET_LOW_PERCENT = 80.0
    TARGET_HIGH_PERCENT = 95.0
    MAX_ITERATIONS = 20
    PROPORTIONAL_GAIN = 0.8
    MIN_ADJUSTMENT_US = SPECTROMETER.HW_INTEGRATION_TIME_BASE_US * 5
    OSCILLATION_DAMPING_FACTOR = 0.5


## @brief Plotting and visualization configuration.
#
#  Controls live plot rendering including smoothing, Y-axis scaling,
#  wavelength range cropping, and data decimation for performance.
#
#  @details WAVELENGTH_RANGE_*_NM values are runtime-modifiable via menu.
#  Display cropping only affects visualization; saved data contains
#  full spectrum. TARGET_DISPLAY_POINTS reduces 2048 sensor pixels
#  to 300 for smooth 30+ FPS rendering.
class PLOTTING:
    USE_LIVE_SMOOTHING = True
    LIVE_SMOOTHING_WINDOW_SIZE = 9
    Y_AXIS_DEFAULT_MAX = 1000.0
    Y_AXIS_REFLECTANCE_DEFAULT_MAX = 10.0  # Default Y max for reflectance plots
    Y_AXIS_RESCALE_FACTOR = 1.2
    Y_AXIS_MIN_CEILING = 100.0
    Y_AXIS_REFLECTANCE_RESCALE_MIN_CEILING = (
        0.2  # Min Y-axis ceiling after rescale for reflectance
    )
    Y_AXIS_REFLECTANCE_RESCALE_MAX_CEILING = (
        200.0  # Max Y-axis ceiling after rescale for reflectance
    )
    WAVELENGTH_RANGE_MIN_NM = 400.0  # Minimum wavelength to display (nm)
    WAVELENGTH_RANGE_MAX_NM = 620.0  # Maximum wavelength to display (nm)
    TARGET_DISPLAY_POINTS = 300  # Number of points to display after decimation

    # Wavelength range editing limits (for menu)
    WAVELENGTH_EDIT_STEP_NM = 20  # Step size for wavelength range adjustment
    WAVELENGTH_EDIT_MIN_LIMIT_NM = 340  # Minimum allowed wavelength (hardware limit)
    WAVELENGTH_EDIT_MAX_LIMIT_NM = 850  # Maximum allowed wavelength (hardware limit)
    WAVELENGTH_EDIT_MIN_GAP_NM = 40  # Minimum gap between min and max wavelength


## @brief Mode definitions for lens types, collection modes, and spectra types.
#
#  Defines string constants used throughout the application for:
#  - Lens types: FIBER, CABLE, FIBER+CABLE (optical input configuration)
#  - Collection modes: RAW (direct ADC counts), REFLECTANCE (calibrated ratio)
#  - Spectra types: RAW, REFLECTANCE, DARK, WHITE, RAW_REFLECTANCE, AUTO_INTEG
#
#  @details RAW_REFLECTANCE is the raw target scan saved alongside reflectance
#  data for scientific reproducibility. AUTO_INTEG marks test scans during
#  auto-integration algorithm execution.
class MODES:
    LENS_TYPE_FIBER = "FIBER"
    LENS_TYPE_CABLE = "CABLE"
    LENS_TYPE_FIBER_CABLE = "FIBER+CABLE"
    LENS_TYPES = (LENS_TYPE_FIBER, LENS_TYPE_CABLE, LENS_TYPE_FIBER_CABLE)
    DEFAULT_LENS_TYPE = LENS_TYPE_FIBER
    MODE_RAW = "RAW"
    MODE_REFLECTANCE = "REFLECTANCE"
    AVAILABLE_COLLECTION_MODES = (MODE_RAW, MODE_REFLECTANCE)
    DEFAULT_COLLECTION_MODE = MODE_RAW
    SPECTRA_TYPE_RAW = "RAW"
    SPECTRA_TYPE_REFLECTANCE = "REFLECTANCE"
    SPECTRA_TYPE_DARK_REF = "DARK"
    SPECTRA_TYPE_WHITE_REF = "WHITE"
    SPECTRA_TYPE_RAW_TARGET_FOR_REFLECTANCE = "RAW_REFLECTANCE"
    SPECTRA_TYPE_AUTO_INTEG = "AUTO_INTEG"
