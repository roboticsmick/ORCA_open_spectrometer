## @file button_handler.py
#  @brief Unified button input handler for GPIO and keyboard events.
#
#  Manages all button inputs from GPIO pins (Pimoroni Display HAT, Adafruit PiTFT,
#  or external Hall effect sensors) and Pygame keyboard events. Provides thread-safe
#  button state management with configurable debouncing.

import time
import threading

# Third-party imports
import pygame

# Local imports
import config

try:
    import RPi.GPIO as GPIO

    GPIO_AVAILABLE = True
except (RuntimeError, ImportError):
    GPIO_AVAILABLE = False


##
# @class ButtonHandler
# @brief Manages all button inputs from GPIO pins and Pygame keyboard events.
# @details This class provides a unified interface for button input, supporting:
#          - GPIO buttons (Pimoroni Display HAT or Adafruit PiTFT)
#          - External Hall effect sensors
#          - Keyboard input for development/testing
#          Thread-safe button state management with debouncing is implemented.
class ButtonHandler:
    """Manages all button inputs from GPIO and Pygame keyboard events."""

    ##
    # @brief Initializes the ButtonHandler.
    # @details Sets up button state dictionaries, threading locks, and configures GPIO
    #          if hardware is available and enabled. Falls back to keyboard-only mode
    #          if GPIO is unavailable.
    def __init__(self):
        """Initializes the button handler, setting up GPIO if available."""
        ## @var _button_states
        # @brief Dictionary mapping button names to their current state (True = pressed).
        self._button_states = {
            btn: False
            for btn in [
                config.BTN_UP,
                config.BTN_DOWN,
                config.BTN_ENTER,
                config.BTN_BACK,
            ]
        }

        ## @var _state_lock
        # @brief Threading lock for thread-safe access to button states.
        self._state_lock = threading.Lock()

        ## @var _last_press_time
        # @brief Dictionary tracking the last press time for each button (for debouncing).
        self._last_press_time = {btn: 0.0 for btn in self._button_states}

        ## @var _pin_to_button
        # @brief Mapping of GPIO pin numbers to logical button names.
        self._pin_to_button = {}

        ## @var _key_map
        # @brief Mapping of Pygame key codes to logical button names.
        self._key_map = {
            pygame.K_UP: config.BTN_UP,
            pygame.K_w: config.BTN_UP,
            pygame.K_DOWN: config.BTN_DOWN,
            pygame.K_s: config.BTN_DOWN,
            pygame.K_RETURN: config.BTN_ENTER,
            pygame.K_SPACE: config.BTN_ENTER,
            pygame.K_BACKSPACE: config.BTN_BACK,
            pygame.K_b: config.BTN_BACK,
        }

        if config.HARDWARE["USE_GPIO_BUTTONS"] and GPIO_AVAILABLE:
            self._setup_gpio_inputs()
        else:
            print(
                "INFO: GPIO buttons are disabled or RPi.GPIO is not available. Using keyboard only."
            )

    ##
    # @brief Sets up GPIO pins for button inputs and adds event detection.
    # @details Configures GPIO pins in BCM mode with pull-up resistors and FALLING edge detection.
    #          Sets up Hall effect sensors if enabled, AND Adafruit PiTFT buttons if enabled.
    #          Both can be active simultaneously. Display HAT buttons are used if no other buttons
    #          are configured. Includes hardware debouncing via bouncetime parameter.
    def _setup_gpio_inputs(self):
        """Sets up the GPIO pins for button inputs and adds event detection."""
        GPIO.setwarnings(False)  # Suppress warnings about GPIO already in use

        # Thorough cleanup of any existing GPIO configuration from previous runs
        try:
            # Try to cleanup all GPIO
            GPIO.cleanup()
        except:
            pass  # Ignore if GPIO wasn't initialized

        # Small delay to let kernel release pins
        time.sleep(0.1)

        GPIO.setmode(GPIO.BCM)

        # Convert debounce delay from seconds to milliseconds for GPIO bouncetime
        bouncetime_ms = int(config.DEBOUNCE_DELAY_S * 1000)

        pin_to_button = {}
        pins_used = set()

        # Setup Hall Effect sensors if enabled
        if config.HARDWARE["USE_HALL_EFFECT_BUTTONS"]:
            pin_to_button.update(
                {
                    config.HALL_EFFECT_PINS["UP"]: config.BTN_UP,
                    config.HALL_EFFECT_PINS["DOWN"]: config.BTN_DOWN,
                    config.HALL_EFFECT_PINS["ENTER"]: config.BTN_ENTER,
                    config.HALL_EFFECT_PINS["BACK"]: config.BTN_BACK,
                }
            )
            pins_used.update(pin_to_button.keys())

        # Setup Adafruit PiTFT tactile buttons if enabled
        if config.HARDWARE["USE_ADAFRUIT_PITFT"]:
            # Adafruit PiTFT button mapping (from original code)
            pitft_mapping = {
                config.BUTTON_PINS["A"]: config.BTN_ENTER,  # A -> Enter
                config.BUTTON_PINS["B"]: config.BTN_BACK,  # B -> Back
                config.BUTTON_PINS["X"]: config.BTN_UP,  # X -> Up
                config.BUTTON_PINS["Y"]: config.BTN_DOWN,  # Y -> Down
            }
            # Only add pins that aren't already used (avoid duplicates)
            for pin, button_name in pitft_mapping.items():
                if pin not in pins_used:
                    pin_to_button[pin] = button_name
                    pins_used.add(pin)

        # Setup Display HAT buttons if no other buttons configured
        if not pin_to_button and config.HARDWARE["USE_DISPLAY_HAT"]:
            pin_to_button.update(
                {
                    config.BUTTON_PINS["A"]: config.BTN_UP,
                    config.BUTTON_PINS["B"]: config.BTN_DOWN,
                    config.BUTTON_PINS["X"]: config.BTN_ENTER,
                    config.BUTTON_PINS["Y"]: config.BTN_BACK,
                }
            )

        # Store the mapping for callback lookup
        self._pin_to_button = pin_to_button.copy()

        for pin, button_name in pin_to_button.items():
            assert isinstance(pin, int), f"Pin {pin} must be an integer"
            assert (
                button_name in self._button_states
            ), f"Unknown button name: {button_name}"

            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            # Remove existing edge detection if present (from previous run)
            try:
                GPIO.remove_event_detect(pin)
                time.sleep(0.01)  # Small delay after removal
            except:
                pass  # Ignore if no edge detection was set

            # Add edge detection with hardware debouncing (with retry)
            # Use direct callback instead of lambda to avoid closure issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    GPIO.add_event_detect(
                        pin,
                        GPIO.FALLING,
                        callback=self._gpio_callback,
                        bouncetime=bouncetime_ms,
                    )
                    break  # Success, exit retry loop
                except RuntimeError as e:
                    if attempt < max_retries - 1:
                        # Try harder to clean up this specific pin
                        print(
                            f"WARNING: Failed to add edge detection on pin {pin}, attempt {attempt + 1}/{max_retries}"
                        )
                        try:
                            GPIO.cleanup(pin)
                            time.sleep(0.05)
                            # Re-setup the pin as input after cleanup
                            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                            time.sleep(0.01)
                        except:
                            pass
                    else:
                        # Final attempt failed
                        print(
                            f"ERROR: Could not add edge detection on pin {pin} after {max_retries} attempts"
                        )
                        raise
        print(f"INFO: GPIO buttons initialized for pins: {list(pin_to_button.keys())}")

    ##
    # @brief GPIO interrupt callback triggered when a button is pressed.
    # @param channel The GPIO pin number (BCM mode) that triggered the interrupt.
    # @details This is called in a separate thread by RPi.GPIO. Applies debouncing
    #          and sets the button state to True if the debounce period has elapsed.
    #          Looks up the logical button name from the pin number.
    def _gpio_callback(self, channel):
        """Callback triggered by a GPIO event. Sets the button state to True."""
        # Lookup button name from pin number
        button_name = self._pin_to_button.get(channel)
        if not button_name:
            print(f"WARNING: Unknown GPIO pin {channel} triggered callback")
            return

        assert button_name in self._button_states, f"Unknown button: {button_name}"

        # This is called in a separate thread by RPi.GPIO
        current_time = time.monotonic()
        if (
            current_time - self._last_press_time[button_name]
        ) > config.DEBOUNCE_DELAY_S:
            with self._state_lock:
                self._button_states[button_name] = True
            self._last_press_time[button_name] = current_time
            print(f"DEBUG: Button '{button_name}' pressed (GPIO {channel})")

    ##
    # @brief Polls Pygame for keyboard events and updates button states.
    # @details This should be called once per frame in the main loop. Handles:
    #          - Pygame QUIT event → sets "shutdown" flag
    #          - Escape key → sets "shutdown" flag
    #          - Mapped keyboard keys → sets corresponding button states with debouncing
    def check_pygame_events(self):
        """Polls Pygame for keyboard events and updates button states."""
        # This should be called once per frame in the main loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # This is a special case to signal shutdown
                with self._state_lock:
                    self._button_states["shutdown"] = True  # Special flag

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    with self._state_lock:
                        self._button_states["shutdown"] = True  # Special flag

                elif event.key in self._key_map:
                    button_name = self._key_map[event.key]
                    current_time = time.monotonic()
                    # Apply debounce for keyboard as well
                    if (
                        current_time - self._last_press_time[button_name]
                    ) > config.DEBOUNCE_DELAY_S:
                        with self._state_lock:
                            self._button_states[button_name] = True
                        self._last_press_time[button_name] = current_time

    ##
    # @brief Checks if a button was pressed and consumes the event.
    # @param button_name The logical name of the button to check (e.g., config.BTN_UP).
    # @return True if the button was pressed since the last check, False otherwise.
    # @details This is a thread-safe, non-blocking check that consumes the button press.
    #          Call this once per frame for each button you want to check.
    def get_pressed(self, button_name):
        """Checks if a button was pressed and consumes the event. Returns True if pressed."""
        with self._state_lock:
            if self._button_states.get(button_name, False):
                self._button_states[button_name] = False  # Consume the press
                return True
            return False

    ##
    # @brief Cleans up GPIO resources.
    # @details Calls GPIO.cleanup() if GPIO was initialized. Should be called during
    #          application shutdown to release GPIO pins.
    def cleanup(self):
        """Cleans up GPIO resources."""
        if config.HARDWARE["USE_GPIO_BUTTONS"] and GPIO_AVAILABLE:
            # First remove all edge detection
            for pin in self._pin_to_button.keys():
                try:
                    GPIO.remove_event_detect(pin)
                except:
                    pass  # Ignore errors during cleanup

            # Then cleanup all GPIO
            try:
                GPIO.cleanup()
                print("INFO: GPIO cleaned up.")
            except:
                print(
                    "WARNING: GPIO cleanup encountered errors (this is usually safe to ignore)"
                )
