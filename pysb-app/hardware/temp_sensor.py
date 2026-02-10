# pysb-app/hardware/temp_sensor.py

##
# @file temp_sensor.py
# @brief Temperature sensor monitoring and fan control module.
# @details This module provides the TempSensorInfo class which manages:
#          - MCP9808 temperature sensor readings via I2C using smbus2
#          - Automatic fan control based on temperature threshold
#          - Thread-safe access to temperature and fan state
#
#          The fan is controlled via a MOSFET on GPIO pin (configurable in config.py).
#          Fan turns ON when temperature >= threshold. Default threshold is 0C,
#          meaning the fan runs continuously when the spectrometer starts.
#
#          Requires: smbus2 (pip install smbus2)

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
    ## @var INIT_RETRY_COUNT
    # @brief Number of retries for sensor initialization during startup.
    INIT_RETRY_COUNT = 3

    ## @var INIT_RETRY_DELAY_S
    # @brief Delay between initialization retries in seconds.
    INIT_RETRY_DELAY_S = 1.0

    ## @var MAX_CONSECUTIVE_FAILURES
    # @brief After this many consecutive read failures, mark sensor unavailable.
    MAX_CONSECUTIVE_FAILURES = 5

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
        # @brief Flag indicating if sensor is available (True/None).
        self._sensor = None

        ## @var _i2c_bus
        # @brief SMBus instance for I2C communication (None if unavailable).
        self._i2c_bus = None

        ## @var _i2c_address
        # @brief I2C address of the MCP9808 sensor.
        self._i2c_address = 0x18

        ## @var _i2c_bus_num
        # @brief I2C bus number (typically 1 on Raspberry Pi).
        self._i2c_bus_num = 1

        ## @var _gpio_available
        # @brief Boolean indicating if GPIO is available for fan control.
        self._gpio_available = False

        ## @var _GPIO
        # @brief Reference to RPi.GPIO module (None if unavailable).
        self._GPIO = None

        ## @var _consecutive_failures
        # @brief Count of consecutive I2C read failures.
        self._consecutive_failures = 0

        ## @var _sensor_gave_up
        # @brief True when sensor is permanently marked unavailable after too many failures.
        self._sensor_gave_up = False

        ## @var _last_good_temp
        # @brief Last successfully read temperature, used as fallback during transient failures.
        self._last_good_temp = None

        # Initialize sensor (with retries for boot timing)
        self._init_sensor()

        # Initialize GPIO for fan control
        self._init_gpio()

    ##
    # @brief Initializes the MCP9808 temperature sensor.
    # @details Uses smbus2 directly to communicate with the MCP9808 sensor via I2C.
    #          No external Adafruit libraries required - just python3-smbus or smbus2.
    #          If initialization fails, sensor remains None and temperature reports "N/A".
    def _init_sensor(self):
        """Initializes the MCP9808 temperature sensor using smbus2.

        Retries up to INIT_RETRY_COUNT times with INIT_RETRY_DELAY_S between
        attempts to handle boot timing issues where I2C may be temporarily
        unavailable due to USB enumeration or other hardware initialization.
        """
        if not config.HARDWARE.get("USE_TEMP_SENSOR_IF_AVAILABLE", False):
            logger.info("Temperature sensor disabled in config.")
            return

        try:
            import smbus2
        except ImportError:
            logger.warning("smbus2 not available. Install with: pip install smbus2")
            self._sensor = None
            return

        self._i2c_address = getattr(config, "MCP9808_I2C_ADDRESS", 0x18)
        self._i2c_bus_num = getattr(config, "I2C_BUS_NUMBER", 1)

        for attempt in range(self.INIT_RETRY_COUNT):
            if self._shutdown_flag.is_set():
                return

            if attempt > 0:
                print(f"MCP9808: Retry {attempt + 1}/{self.INIT_RETRY_COUNT}...")
                time.sleep(self.INIT_RETRY_DELAY_S)

            try:
                # Open I2C bus (close previous attempt if any)
                if self._i2c_bus is not None:
                    try:
                        self._i2c_bus.close()
                    except Exception:
                        pass
                    self._i2c_bus = None

                self._i2c_bus = smbus2.SMBus(self._i2c_bus_num)

                # Verify sensor by reading manufacturer and device IDs
                REG_MANUF_ID = 0x06
                REG_DEVICE_ID = 0x07

                data = self._i2c_bus.read_i2c_block_data(self._i2c_address, REG_MANUF_ID, 2)
                manuf_id = (data[0] << 8) | data[1]

                data = self._i2c_bus.read_i2c_block_data(self._i2c_address, REG_DEVICE_ID, 2)
                device_id = (data[0] << 8) | data[1]

                if manuf_id == 0x0054 and device_id == 0x0400:
                    initial_temp = self._read_temperature_raw()
                    if isinstance(initial_temp, (float, int)):
                        with self._lock:
                            self._temperature_c = float(initial_temp)
                        self._sensor = True
                        self._last_good_temp = float(initial_temp)
                        print(f"MCP9808 sensor initialized (bus {self._i2c_bus_num}, "
                              f"addr 0x{self._i2c_address:02X}, temp: {initial_temp:.1f}C)")
                        return  # Success
                    else:
                        logger.warning(f"MCP9808 initial read failed: {initial_temp}")
                else:
                    logger.warning(f"MCP9808 not detected. Manuf: 0x{manuf_id:04X}, "
                                  f"Device: 0x{device_id:04X}")

            except FileNotFoundError:
                logger.warning(f"I2C bus {self._i2c_bus_num} not found. Is I2C enabled?")
                self._close_i2c_bus()
                self._sensor = None
                return  # Not recoverable with retries
            except PermissionError:
                logger.warning("Permission denied for I2C bus. Add user to 'i2c' group.")
                self._close_i2c_bus()
                self._sensor = None
                return  # Not recoverable with retries
            except OSError as e:
                if e.errno == 121:
                    print(f"MCP9808 not responding at 0x{self._i2c_address:02X} "
                          f"(attempt {attempt + 1}/{self.INIT_RETRY_COUNT})")
                else:
                    logger.warning(f"I2C error initializing MCP9808: {e}")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP9808 sensor: {e}")

        # All retries exhausted
        print("MCP9808: All init attempts failed. Sensor unavailable.")
        self._close_i2c_bus()
        self._sensor = None

    def _close_i2c_bus(self):
        """Safely close and release the I2C bus."""
        if self._i2c_bus is not None:
            try:
                self._i2c_bus.close()
            except Exception:
                pass
            self._i2c_bus = None

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
    # @details Waits for the thread to terminate and cleans up GPIO and I2C.
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

        # Close I2C bus
        self._close_i2c_bus()

        logger.info("Temperature sensor stopped.")

    ##
    # @brief Background thread loop for temperature updates and fan control.
    # @details Runs until shutdown_flag is set. Each iteration:
    #          1. Reads temperature from sensor (if available)
    #          2. Updates fan state based on threshold
    #          3. Waits for the configured interval
    def _update_loop(self):
        """Background loop for temperature updates and fan control.

        Tracks consecutive I2C failures. After MAX_CONSECUTIVE_FAILURES,
        marks sensor as permanently unavailable to stop error spam and
        prevent I2C timeouts from blocking the thread or printing over
        the framebuffer display.
        """
        logger.info("Temperature update loop started.")

        while not self._shutdown_flag.is_set():
            start_time = time.monotonic()

            # Read temperature (skip if sensor gave up)
            if self._sensor_gave_up:
                current_temp = "No Sensor"
            else:
                current_temp = self._read_temperature()

            # Track consecutive failures
            if isinstance(current_temp, (float, int)):
                self._consecutive_failures = 0
                self._last_good_temp = current_temp
            elif self._sensor is not None and not self._sensor_gave_up:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                    print(f"MCP9808: {self.MAX_CONSECUTIVE_FAILURES} consecutive "
                          f"failures. Sensor marked unavailable.")
                    self._sensor_gave_up = True
                    self._close_i2c_bus()
                    self._sensor = None
                    current_temp = "No Sensor"

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
    # @brief Reads temperature directly from MCP9808 via I2C.
    # @return Temperature in Celsius (float) or error string if read fails.
    # @details Reads the ambient temperature register and converts to Celsius.
    def _read_temperature_raw(self):
        """Reads temperature directly from MCP9808 via I2C.

        Only logs the first failure in a series of consecutive failures
        to prevent error messages from spamming the console/framebuffer.
        """
        if self._i2c_bus is None:
            return "No Bus"

        try:
            # MCP9808 ambient temperature register
            REG_AMBIENT_TEMP = 0x05

            # Read 2 bytes from temperature register
            data = self._i2c_bus.read_i2c_block_data(self._i2c_address, REG_AMBIENT_TEMP, 2)
            raw_temp = (data[0] << 8) | data[1]

            # Convert to Celsius (MCP9808 format)
            # Bits 0-11 contain the temperature in 1/16 degree increments
            # Bit 12 is the sign bit
            temp_c = (raw_temp & 0x0FFF) / 16.0
            if raw_temp & 0x1000:
                temp_c -= 256.0

            return temp_c

        except OSError as e:
            # Only log the first failure to avoid spamming the framebuffer console
            if self._consecutive_failures == 0:
                if e.errno == 121:
                    print("MCP9808: I2C read failed (remote I/O error)")
                else:
                    print(f"MCP9808: I2C read failed: {e}")
            return "I2C Error"
        except Exception as e:
            if self._consecutive_failures == 0:
                print(f"MCP9808: Read failed: {e}")
            return "Read Error"

    ##
    # @brief Reads temperature from the MCP9808 sensor.
    # @return Temperature in Celsius (float) or error string if read fails.
    def _read_temperature(self):
        """Reads temperature from the sensor."""
        if self._sensor_gave_up:
            return "No Sensor"

        if self._sensor is None and self._i2c_bus is None:
            return "No Sensor"

        return self._read_temperature_raw()

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
