# pysb-app/hardware/temp_sensor.py

##
# @file temp_sensor.py
# @brief Temperature sensor monitoring and fan control module.
# @details This module provides the TempSensorInfo class which manages:
#          - MCP9808 temperature sensor readings via I2C
#          - Automatic fan control based on temperature threshold
#          - Thread-safe access to temperature and fan state
#
#          The fan is controlled via a MOSFET on GPIO pin (configurable in config.py).
#          Fan turns ON when temperature >= threshold. Default threshold is 0C,
#          meaning the fan runs continuously when the spectrometer starts.
#
#          Library path on Raspberry Pi: /home/pi/pysb-app/lib/Adafruit_Python_MCP9808/MCP9808.py

import sys
import os
import threading
import time
import logging

import config

# Setup logging
logger = logging.getLogger(__name__)


##
# @class TempSensorInfo
# @brief Manages temperature sensor readings and automatic fan control.
# @details Runs a background thread that periodically:
#          1. Reads temperature from MCP9808 sensor
#          2. Controls fan based on temperature vs threshold
#          The class provides thread-safe access to temperature, fan state,
#          and allows runtime adjustment of the fan threshold.
#
# @pre config.HARDWARE["USE_TEMP_SENSOR_IF_AVAILABLE"] should be True to enable sensor.
# @pre config.FAN_ENABLE_PIN must be defined for fan control.
# @pre config.TEMP_UPDATE_INTERVAL_S defines the polling interval.
class TempSensorInfo:
    """Manages temperature sensor readings and automatic fan control."""

    ##
    # @brief Initializes the TempSensorInfo instance.
    # @param[in] shutdown_flag threading.Event used to signal thread termination.
    # @details Initializes the MCP9808 sensor (if available) and sets up GPIO for fan control.
    #          If sensor initialization fails, temperature will report "N/A".
    #          Fan control works independently even if sensor fails.
    def __init__(self, shutdown_flag):
        assert isinstance(shutdown_flag, threading.Event), "shutdown_flag must be threading.Event"

        ## @var _shutdown_flag
        # @brief Threading event to signal shutdown.
        self._shutdown_flag = shutdown_flag

        ## @var _temperature_c
        # @brief Current temperature in Celsius (float) or error string.
        self._temperature_c = "N/A"

        ## @var _fan_enabled
        # @brief Boolean indicating if fan is currently running.
        self._fan_enabled = False

        ## @var _fan_threshold_c
        # @brief Temperature threshold in Celsius above which fan turns on.
        self._fan_threshold_c = config.FAN_DEFAULT_THRESHOLD_C

        ## @var _lock
        # @brief Threading lock for thread-safe access to shared state.
        self._lock = threading.Lock()

        ## @var _update_thread
        # @brief Background thread for periodic updates.
        self._update_thread = None

        ## @var _sensor
        # @brief MCP9808 sensor instance (None if unavailable).
        self._sensor = None

        ## @var _gpio_available
        # @brief Boolean indicating if GPIO is available for fan control.
        self._gpio_available = False

        ## @var _GPIO
        # @brief Reference to RPi.GPIO module (None if unavailable).
        self._GPIO = None

        # Initialize sensor
        self._init_sensor()

        # Initialize GPIO for fan control
        self._init_gpio()

    ##
    # @brief Initializes the MCP9808 temperature sensor.
    # @details Attempts to import and initialize the Adafruit MCP9808 library.
    #          The library is expected at: lib/Adafruit_Python_MCP9808/Adafruit_MCP9808/
    #          If initialization fails, sensor remains None and temperature reports "N/A".
    def _init_sensor(self):
        """Initializes the MCP9808 temperature sensor."""
        if not config.HARDWARE.get("USE_TEMP_SENSOR_IF_AVAILABLE", False):
            logger.info("Temperature sensor disabled in config.")
            return

        try:
            # Add library path for Adafruit MCP9808
            lib_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "lib",
                "Adafruit_Python_MCP9808",
            )
            if lib_path not in sys.path:
                sys.path.insert(0, lib_path)
                logger.debug(f"Added library path: {lib_path}")

            # Import and initialize sensor
            from Adafruit_MCP9808 import MCP9808

            self._sensor = MCP9808.MCP9808()

            # Verify sensor is responding
            if self._sensor.begin():
                # Do an initial read to confirm sensor is working
                initial_temp = self._sensor.readTempC()
                if isinstance(initial_temp, (float, int)):
                    with self._lock:
                        self._temperature_c = float(initial_temp)
                    logger.info(f"MCP9808 sensor initialized. Initial temp: {initial_temp:.1f}C")
                else:
                    logger.warning(f"MCP9808 returned invalid data type: {type(initial_temp)}")
                    self._sensor = None
            else:
                logger.warning("MCP9808 sensor not detected (begin() returned False).")
                self._sensor = None

        except ImportError as e:
            logger.warning(f"MCP9808 library not available: {e}")
            self._sensor = None
        except Exception as e:
            logger.error(f"Failed to initialize MCP9808 sensor: {e}")
            self._sensor = None

    ##
    # @brief Initializes GPIO for fan control.
    # @details Sets up the fan enable pin as an output, starting with fan OFF.
    #          Fan will be turned on during the first update cycle if threshold is met.
    def _init_gpio(self):
        """Initializes GPIO for fan control."""
        try:
            import RPi.GPIO as GPIO

            self._GPIO = GPIO
            self._GPIO.setmode(GPIO.BCM)
            self._GPIO.setwarnings(False)

            # Setup fan enable pin as output, start with fan OFF
            self._GPIO.setup(config.FAN_ENABLE_PIN, GPIO.OUT, initial=GPIO.LOW)
            self._gpio_available = True
            logger.info(f"GPIO initialized for fan control on pin {config.FAN_ENABLE_PIN}")

        except ImportError:
            logger.warning("RPi.GPIO not available. Fan control disabled.")
            self._gpio_available = False
        except Exception as e:
            logger.error(f"Failed to initialize GPIO for fan: {e}")
            self._gpio_available = False

    ##
    # @brief Starts the background update thread.
    # @details The thread periodically reads temperature and controls the fan.
    #          Safe to call multiple times; will not start a second thread.
    def start(self):
        """Starts the background update thread."""
        if self._update_thread is not None and self._update_thread.is_alive():
            logger.warning("TempSensorInfo: Update thread already running.")
            return

        logger.info("Starting temperature sensor update thread.")
        self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self._update_thread.start()

    ##
    # @brief Stops the background update thread and cleans up resources.
    # @details Waits for the thread to terminate and cleans up GPIO.
    #          Fan is turned OFF during cleanup.
    def stop(self):
        """Stops the background update thread and cleans up."""
        if self._update_thread is not None and self._update_thread.is_alive():
            logger.info("Waiting for temperature update thread to stop...")
            self._update_thread.join(timeout=config.TEMP_UPDATE_INTERVAL_S + 1.0)
            if self._update_thread.is_alive():
                logger.warning("Temperature update thread did not terminate cleanly.")

        self._update_thread = None

        # Turn off fan and cleanup GPIO
        self._set_fan(False)
        if self._gpio_available and self._GPIO is not None:
            try:
                self._GPIO.cleanup(config.FAN_ENABLE_PIN)
                logger.info("Fan GPIO cleaned up.")
            except Exception as e:
                logger.error(f"Error cleaning up fan GPIO: {e}")

        logger.info("Temperature sensor stopped.")

    ##
    # @brief Background thread loop for temperature updates and fan control.
    # @details Runs until shutdown_flag is set. Each iteration:
    #          1. Reads temperature from sensor (if available)
    #          2. Updates fan state based on threshold
    #          3. Waits for the configured interval
    def _update_loop(self):
        """Background loop for temperature updates and fan control."""
        logger.info("Temperature update loop started.")

        while not self._shutdown_flag.is_set():
            start_time = time.monotonic()

            # Read temperature
            current_temp = self._read_temperature()

            with self._lock:
                self._temperature_c = current_temp

                # Control fan based on threshold
                if isinstance(current_temp, (float, int)):
                    should_fan_be_on = current_temp >= self._fan_threshold_c
                else:
                    # If temp reading failed, use current fan state (don't change)
                    # Or turn on fan as safety measure if threshold is 0 (always on)
                    should_fan_be_on = self._fan_threshold_c <= 0 or self._fan_enabled

            self._set_fan(should_fan_be_on)

            # Wait for next update
            elapsed = time.monotonic() - start_time
            wait_time = max(0, config.TEMP_UPDATE_INTERVAL_S - elapsed)
            self._shutdown_flag.wait(timeout=wait_time)

        logger.info("Temperature update loop finished.")

    ##
    # @brief Reads temperature from the MCP9808 sensor.
    # @return Temperature in Celsius (float) or error string if read fails.
    def _read_temperature(self):
        """Reads temperature from the sensor."""
        if self._sensor is None:
            return "No Sensor"

        try:
            raw_temp = self._sensor.readTempC()
            if isinstance(raw_temp, (float, int)):
                return float(raw_temp)
            else:
                logger.error(f"Invalid temperature data type: {type(raw_temp)}")
                return "Type Error"
        except AttributeError:
            logger.error("Sensor object missing or method not found.")
            self._sensor = None
            return "Sensor Error"
        except Exception as e:
            logger.error(f"Error reading temperature: {e}")
            return "Read Error"

    ##
    # @brief Sets the fan state (on or off).
    # @param[in] enable Boolean, True to turn fan on, False to turn off.
    def _set_fan(self, enable):
        """Sets the fan state."""
        if not self._gpio_available or self._GPIO is None:
            return

        try:
            if enable:
                self._GPIO.output(config.FAN_ENABLE_PIN, self._GPIO.HIGH)
            else:
                self._GPIO.output(config.FAN_ENABLE_PIN, self._GPIO.LOW)

            with self._lock:
                if self._fan_enabled != enable:
                    self._fan_enabled = enable
                    state_str = "ON" if enable else "OFF"
                    logger.debug(f"Fan turned {state_str}")

        except Exception as e:
            logger.error(f"Error setting fan state: {e}")

    ##
    # @brief Gets the current temperature.
    # @return Temperature in Celsius (float) or error string.
    # @details Thread-safe getter for current temperature reading.
    def get_temperature_c(self):
        """Returns the current temperature in Celsius."""
        with self._lock:
            return self._temperature_c

    ##
    # @brief Gets the current fan state.
    # @return Boolean, True if fan is running, False otherwise.
    def is_fan_enabled(self):
        """Returns True if fan is currently running."""
        with self._lock:
            return self._fan_enabled

    ##
    # @brief Gets the current fan threshold.
    # @return Temperature threshold in Celsius (int).
    def get_fan_threshold_c(self):
        """Returns the fan activation threshold in Celsius."""
        with self._lock:
            return self._fan_threshold_c

    ##
    # @brief Sets the fan activation threshold.
    # @param[in] threshold_c Temperature threshold in Celsius (int).
    # @details When temperature >= threshold, fan turns on.
    #          Setting threshold to 0 means fan is always on.
    #          Change takes effect on next temperature update cycle.
    def set_fan_threshold_c(self, threshold_c):
        """Sets the fan activation threshold in Celsius."""
        assert isinstance(threshold_c, (int, float)), "threshold_c must be numeric"

        with self._lock:
            old_threshold = self._fan_threshold_c
            self._fan_threshold_c = int(threshold_c)
            if old_threshold != self._fan_threshold_c:
                logger.info(f"Fan threshold changed from {old_threshold}C to {self._fan_threshold_c}C")

    ##
    # @brief Gets a formatted string for display in menu.
    # @return String like "Threshold 40C (Current 28C)" or "Disabled" if sensor unavailable.
    def get_display_string(self):
        """Returns a formatted string for menu display."""
        with self._lock:
            threshold = self._fan_threshold_c
            temp = self._temperature_c

        if isinstance(temp, (float, int)):
            return f"Threshold {threshold}C (Current {temp:.0f}C)"
        else:
            return f"Threshold {threshold}C (Temp: {temp})"
