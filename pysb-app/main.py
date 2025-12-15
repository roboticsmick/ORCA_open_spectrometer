## @file main.py
#  @brief Main entry point and application orchestrator for PySB-App spectrometer.
#
#  This module is the central coordinator for the spectrometer application.
#  It manages:
#  - Display initialization (framebuffer or windowed mode)
#  - Global threading events (shutdown_flag, leak_detected_flag)
#  - Shared data structures (SpectrometerSettings)
#  - Component lifecycle (hardware controllers, UI screens, data manager)
#  - Main UI state machine (MENU <-> SPECTROMETER states)
#
#  @details The application uses a multi-threaded architecture with
#  queue-based communication between components. The main loop runs
#  at ~30 FPS and handles state transitions based on user input.
#
#  Global Events:
#  - shutdown_flag: Signals all threads to terminate gracefully
#  - leak_detected_flag: Set by LeakSensor when leak is detected
#
#  State Machine:
#  - MENU: Main menu for settings and navigation
#  - SPECTROMETER: Live spectrometer view and capture workflow

import threading
from dataclasses import dataclass
import queue
import time
import os
import pygame

# Local imports
import config
from hardware import button_handler, leak_sensor, network_info, spectrometer_controller
from hardware import temp_sensor
from ui import (
    splash_screen,
    terms_screen,
    leak_warning,
    menu_system,
    display_utils,
    spectrometer_screen,
)
from data import data_manager

# Disable audio driver
os.environ["SDL_AUDIODRIVER"] = "dummy"

# ==============================================================================
# 1. SHARED STATE AND GLOBAL EVENTS
# ==============================================================================

# Threading events for global coordination
shutdown_flag = threading.Event()
leak_detected_flag = threading.Event()

# Flags to indicate if references need to be re-captured
dark_reference_required = True
white_reference_required = True

# ==============================================================================
# 2. SHARED DATA STRUCTURES (MODELS)
# ==============================================================================


## @brief Settings snapshot for spectrometer capture configuration.
#
#  Holds the current settings that control how the spectrometer captures data.
#  Passed between the menu system (for editing) and spectrometer controller
#  (for capture execution).
#
#  @var integration_time_ms Integration time in milliseconds (100-6000ms menu range).
#  @var collection_mode Data collection mode: "RAW" or "REFLECTANCE".
#  @var scans_to_average Number of scans to average (0-50, where 0 = no averaging).
@dataclass
class SpectrometerSettings:
    integration_time_ms: int = config.SPECTROMETER.DEFAULT_INTEGRATION_TIME_MS
    collection_mode: str = config.MODES.DEFAULT_COLLECTION_MODE
    scans_to_average: int = config.SPECTROMETER.DEFAULT_SCANS_TO_AVERAGE


# ==============================================================================
# 3. DISPLAY MANAGEMENT FUNCTIONS
# ==============================================================================


## @brief Initialize pygame display based on hardware configuration.
#
#  Creates either a framebuffer surface (for Adafruit PiTFT) or a
#  standard pygame window (for development/SSH). Disables mouse
#  cursor and console cursor blink in framebuffer mode.
#
#  @return pygame.Surface for rendering (SCREEN_WIDTH x SCREEN_HEIGHT).
#  @pre Pygame must not be initialized before calling this function.
#  @post Pygame is initialized and ready for rendering.
def initialize_display():
    if config.HARDWARE["USE_ADAFRUIT_PITFT"]:
        # Adafruit PiTFT Mode: Framebuffer rendering
        print("Configuring Pygame for Adafruit PiTFT (framebuffer mode)...")

        # Set SDL to dummy mode (no window, we'll write to framebuffer manually)
        os.environ["SDL_VIDEODRIVER"] = "dummy"

        # Disable console cursor blink
        try:
            with open("/sys/class/graphics/fbcon/cursor_blink", "w") as f:
                f.write("0")
            print("Console cursor blink disabled")
        except Exception as e:
            print(f"WARNING: Could not disable cursor blink: {e}")

        # Initialize pygame
        pygame.init()
        assert pygame.get_init(), "Pygame initialization failed"

        # Create a Surface (not a display window)
        screen = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.mouse.set_visible(False)

        print(
            f"Adafruit PiTFT: Pygame surface created ({config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT})"
        )
        return screen

    else:
        # Standard window mode (for SSH/development)
        print("Initializing standard Pygame display window...")

        # Make sure dummy mode is not set
        if "SDL_VIDEODRIVER" in os.environ and os.environ["SDL_VIDEODRIVER"] == "dummy":
            del os.environ["SDL_VIDEODRIVER"]

        pygame.init()
        assert pygame.get_init(), "Pygame initialization failed"

        screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption("PySB-App Spectrometer")

        print(
            f"Standard Pygame window initialized ({config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT})"
        )
        return screen


# ==============================================================================
# 4. MAIN APPLICATION ORCHESTRATOR
# ==============================================================================


## @brief Main application entry point and orchestrator.
#
#  Initializes all hardware controllers, UI screens, and background threads.
#  Runs the main UI loop with state machine transitions between MENU and
#  SPECTROMETER screens. Handles graceful shutdown on keyboard interrupt
#  or leak detection.
#
#  @details Execution flow:
#  1. Initialize display (framebuffer or window)
#  2. Create shared queues for thread communication
#  3. Instantiate hardware controllers and UI screens
#  4. Start background threads (leak sensor, network, temp, spectrometer, data manager)
#  5. Show splash screen and terms screen
#  6. Enter main loop (state machine at ~30 FPS)
#  7. Cleanup all resources on exit
#
#  @pre No other instance of the application should be running.
#  @post All threads stopped, GPIO cleaned up, pygame quit.
def main():
    global dark_reference_required, white_reference_required

    # --- Display Initialization ---
    screen = initialize_display()
    clock = pygame.time.Clock()

    # --- Shared Data Instances ---
    spectrometer_settings = SpectrometerSettings()

    # Create thread-safe queues for communication
    spectrometer_request_queue = queue.Queue()
    spectrometer_result_queue = queue.Queue()
    data_manager_save_queue = queue.Queue()

    # --- Create Controller Instances ---
    button_handler_inst = button_handler.ButtonHandler()
    leak_sensor_inst = leak_sensor.LeakSensor(shutdown_flag, leak_detected_flag)
    network_info_inst = network_info.NetworkInfo(shutdown_flag)
    temp_sensor_inst = temp_sensor.TempSensorInfo(shutdown_flag)
    spec_controller_inst = spectrometer_controller.SpectrometerController(
        shutdown_flag=shutdown_flag,
        request_queue=spectrometer_request_queue,
        result_queue=spectrometer_result_queue,
    )
    data_manager_inst = data_manager.DataManager(
        shutdown_flag=shutdown_flag,
        save_queue=data_manager_save_queue,
    )

    # --- Create UI Screen Instances ---
    menu_screen = menu_system.MenuSystem(
        screen,
        button_handler_inst,
        spectrometer_settings,
        network_info_inst,
        temp_sensor_inst,
    )
    spectro_screen = spectrometer_screen.SpectrometerScreen(
        screen,
        button_handler_inst,
        spectrometer_settings,
        spectrometer_request_queue,
        spectrometer_result_queue,
        data_manager_save_queue,
    )

    # --- Start Background Threads ---
    leak_sensor_inst.start()
    network_info_inst.start()
    temp_sensor_inst.start()
    spec_controller_inst.start()
    data_manager_inst.start()

    # --- Main Application Logic ---
    print("Entering main application logic...")
    app_state = "MENU"  # Initial state
    try:
        # --- Initial Startup Sequence ---
        print("Showing splash screen...")
        splash_screen.show(screen, leak_detected_flag)
        print("Splash screen done.")

        if leak_detected_flag.is_set():
            leak_warning.show(screen)
            display_utils.update_display(screen)
            shutdown_flag.set()

        if not shutdown_flag.is_set():
            print("Showing terms screen...")
            terms_screen.show(screen, button_handler_inst, leak_detected_flag)
            print("Terms screen done.")

            if leak_detected_flag.is_set():
                leak_warning.show(screen)
                display_utils.update_display(screen)
                shutdown_flag.set()

        # --- Main Application Loop ---
        print("Entering main loop...")
        while not shutdown_flag.is_set():
            # --- Event Handling ---
            button_handler_inst.check_pygame_events()
            if button_handler_inst.get_pressed("shutdown"):
                shutdown_flag.set()

            if leak_detected_flag.is_set():
                leak_warning.show(screen)
                display_utils.update_display(screen)
                shutdown_flag.set()
                continue  # Skip the rest of the loop

            # --- State Machine ---
            if app_state == "MENU":
                menu_action = menu_screen.handle_input()
                if menu_action == "START_CAPTURE":
                    app_state = "SPECTROMETER"
                    spectro_screen.enter()  # Initialize spectrometer screen
                elif menu_action == "QUIT":
                    shutdown_flag.set()

                # Update flags if settings were changed in the menu
                if menu_screen.dark_reference_required:
                    dark_reference_required = True
                    menu_screen.dark_reference_required = False  # Reset flag
                if menu_screen.white_reference_required:
                    white_reference_required = True
                    menu_screen.white_reference_required = False  # Reset flag

                menu_screen.draw()

            elif app_state == "SPECTROMETER":
                # Update spectrometer screen (process new data from queue)
                spectro_screen.update()

                # Handle input
                screen_action = spectro_screen.handle_input()
                if screen_action == "MENU":
                    spectro_screen.exit()  # Cleanup spectrometer screen
                    app_state = "MENU"

                # Draw spectrometer screen
                spectro_screen.draw()

            # --- Screen Update ---
            display_utils.update_display(screen)  # Use hardware-aware display update
            clock.tick(30)  # Limit frame rate

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Shutting down.")
        shutdown_flag.set()
    finally:
        # --- Cleanup: Stop all threads and cleanup resources ---
        print("Initiating shutdown...")
        shutdown_flag.set()  # Ensure all threads see the flag
        leak_sensor_inst.stop()
        network_info_inst.stop()
        button_handler_inst.cleanup()
        temp_sensor_inst.stop()
        spec_controller_inst.stop()
        data_manager_inst.stop()
        pygame.quit()
        print("Application finished.")


if __name__ == "__main__":
    main()
