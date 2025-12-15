## @file leak_sensor.py
#  @brief Leak sensor monitoring using GPIO interrupt-based detection.
#
#  Monitors a leak sensor connected to a GPIO pin and triggers an alert
#  when liquid is detected. Uses interrupt-driven detection for efficiency.
#  Sets the leak_detected_flag event to trigger emergency shutdown.

import threading
import time

import config
# No longer importing from main, which removes the circular dependency.

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True  # Flag indicating if the RPi.GPIO library is available.
except (RuntimeError, ImportError):
    GPIO_AVAILABLE = False

##
# @class LeakSensor
# @brief Manages the leak sensor hardware using GPIO interrupt-based detection.
# @details This class sets up GPIO edge detection for the leak sensor. When the sensor
#          is triggered (pin transitions from HIGH to LOW), a callback is invoked that
#          sets the injected `leak_detected_flag` event to alert the main application.
#          Uses interrupt-driven detection rather than polling for efficiency and accuracy.
class LeakSensor(threading.Thread):

    ##
    # @brief Initializes the LeakSensor.
    # @param shutdown_flag A threading.Event to signal when the sensor should be disabled.
    # @param leak_detected_flag A threading.Event that will be set if a leak is detected.
    # @details Checks if the leak sensor is enabled in the config and if the GPIO
    #          library is available. If so, it sets up the GPIO pin with interrupt detection.
    def __init__(self, shutdown_flag, leak_detected_flag):
        super().__init__(name="LeakSensorThread")
        self.daemon = True

        self.shutdown_flag = shutdown_flag
        self.leak_detected_flag = leak_detected_flag

        ## @var enabled
        # @brief Boolean indicating if the leak sensor monitoring is active.
        self.enabled = False

        if not config.HARDWARE["USE_LEAK_SENSOR"] or not GPIO_AVAILABLE:
            self.enabled = False
            print("INFO: Leak sensor is disabled or RPi.GPIO is not available.")
        else:
            self.enabled = True
            ## @var pin
            # @brief The GPIO pin number (in BCM mode) connected to the leak sensor.
            self.pin = config.LEAK_SENSOR_PIN
            self._setup_gpio()

    ##
    # @brief Configures the GPIO pin for the leak sensor with interrupt detection.
    # @details Sets the GPIO mode to BCM and configures the sensor pin as an input
    #          with an internal pull-up resistor. Adds FALLING edge detection with
    #          a callback that triggers when the sensor detects a leak (pin goes LOW).
    #          Uses 1000ms bouncetime to prevent false triggers from electrical noise.
    def _setup_gpio(self):
        GPIO.setwarnings(False)  # Suppress warnings about GPIO already in use
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Remove existing edge detection if present (from previous run)
        try:
            GPIO.remove_event_detect(self.pin)
        except:
            pass  # Ignore if no edge detection was set

        # Add interrupt-based edge detection (triggers on HIGH->LOW transition)
        GPIO.add_event_detect(
            self.pin,
            GPIO.FALLING,
            callback=self._leak_callback,
            bouncetime=1000  # 1 second debounce time
        )
        print(f"INFO: Leak sensor initialized on GPIO pin {self.pin} (interrupt-based)")

    ##
    # @brief GPIO interrupt callback triggered when a leak is detected.
    # @param channel The GPIO channel number that triggered the interrupt.
    # @details This is called in a separate thread by RPi.GPIO when the pin transitions
    #          from HIGH to LOW. Sets the leak_detected_flag to alert the main application.
    def _leak_callback(self, channel):
        assert channel == self.pin, f"Leak callback triggered for unexpected channel {channel}"
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"!!! WATER LEAK DETECTED on GPIO {channel} !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.leak_detected_flag.set()

    ##
    # @brief The main execution method of the thread.
    # @details This thread simply waits for the shutdown_flag to be set. The actual
    #          leak detection is handled by the GPIO interrupt callback, not by polling.
    def run(self):
        if not self.enabled:
            return

        print("Leak sensor thread started (waiting for interrupts).")

        # Just wait for shutdown - leak detection is handled by GPIO interrupts
        while not self.shutdown_flag.is_set():
            time.sleep(1.0)  # Sleep to reduce CPU usage

        print("Leak sensor thread finished.")

    ##
    # @brief Stops the leak sensor and cleans up GPIO edge detection.
    # @details Removes the edge detection callback to prevent spurious triggers after shutdown.
    def stop(self):
        if self.enabled and GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.pin)
                print(f"INFO: Leak sensor edge detection removed from GPIO {self.pin}")
            except:
                pass  # Ignore errors during cleanup
