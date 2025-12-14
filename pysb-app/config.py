# pysb-app/config.py

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
    "USE_TEMP_SENSOR_IF_AVAILABLE": False,
}

# --- System ---
os.environ["ALSA_MIXER_CARD"] = "-1"
os.environ["ALSA_MIXER_DEVICE"] = "-1"

# --- PIN DEFINITIONS (BCM Mode) ---
BUTTON_PINS = {"A": 5, "B": 6, "X": 16, "Y": 24}  # Default: Pimoroni Display HAT Mini
if HARDWARE["USE_ADAFRUIT_PITFT"]:
    BUTTON_PINS = {"A": 27, "B": 23, "X": 22, "Y": 17}

HALL_EFFECT_PINS = {"UP": 20, "DOWN": 21, "ENTER": 19, "BACK": 12}

LEAK_SENSOR_PIN = 26
LEAK_SENSOR_CHECK_S = 1.0  # How often to check the leak sensor (seconds)

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


class FONT_SIZES:
    TITLE = 22
    MENU_ITEM = 16  # Original MENU_FONT_SIZE
    MENU_VALUE = 16  # Original MENU_FONT_SIZE
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


class FONTS:
    """Font file paths relative to the fonts directory."""

    TITLE = os.path.join(FONTS_DIR, "ChakraPetch-Medium.ttf")
    MAIN = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    HINT = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    SPECTRO = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    PLOTTER_AXIS_LABEL = os.path.join(FONTS_DIR, "Segoe UI This.ttf")
    PLOTTER_TICK_LABEL = os.path.join(FONTS_DIR, "Segoe UI Semilight.ttf")


class IMAGES:
    """Image file paths relative to the images directory."""

    LOGO = os.path.join(IMAGES_DIR, "logo.png")
    SPLASH = os.path.join(IMAGES_DIR, "logo.png")  # Same as logo for now


# --- TIMING & DELAYS ---
DEBOUNCE_DELAY_S = 0.2
NETWORK_UPDATE_INTERVAL_S = 10.0
TEMP_UPDATE_INTERVAL_S = 10.0
MAIN_LOOP_DELAY_S = 0.03
SPECTRO_LOOP_DELAY_S = 0.05
DIVISION_EPSILON = 1e-9


# --- SPECTROMETER ---
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


# --- AUTO_INTEGRATION ---
class AUTO_INTEGRATION:
    TARGET_LOW_PERCENT = 80.0
    TARGET_HIGH_PERCENT = 95.0
    MAX_ITERATIONS = 20
    PROPORTIONAL_GAIN = 0.8
    MIN_ADJUSTMENT_US = SPECTROMETER.HW_INTEGRATION_TIME_BASE_US * 5
    OSCILLATION_DAMPING_FACTOR = 0.5


# --- PLOTTING ---
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


# --- MODES ---
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
