# pysb-app/main.py

import threading
from dataclasses import dataclass
import numpy as np
import datetime
import queue
import time
import os
import pygame

# Local imports
import config
from hardware import button_handler, leak_sensor, network_info, spectrometer_controller
# from hardware import temp_sensor
from ui import splash_screen, terms_screen, leak_warning, menu_system, display_utils, spectrometer_screen
# from data import data_manager

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

@dataclass
class SpectrometerSettings:
    """
    A snapshot of the settings used for a specific capture.

    Attributes:
        integration_time_ms: Integration time in milliseconds (range: 10-10000)
        collection_mode: Data collection mode ("RAW" or "REFLECTANCE")
        scans_to_average: Number of scans to average (0-50, where 0 means no averaging)
    """
    integration_time_ms: int = 100
    collection_mode: str = "RAW"
    scans_to_average: int = 1

@dataclass
class CaptureResult:
    """Data packet sent FROM the Spectrometer thread TO the main UI thread."""
    wavelengths: np.ndarray
    intensities: np.ndarray
    settings: SpectrometerSettings
    timestamp: datetime.datetime

@dataclass
class SaveRequest:
    """Data packet sent FROM the main UI thread TO the Data Manager thread."""
    result_data: CaptureResult
    spectra_type: str  # e.g., "RAW", "REFLECTANCE", "DARK", "WHITE"

# ==============================================================================
# 3. DISPLAY MANAGEMENT FUNCTIONS
# ==============================================================================

def initialize_display():
    """
    Initializes the display based on hardware configuration.

    Returns:
        screen: pygame.Surface for rendering
    """
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

        print(f"Adafruit PiTFT: Pygame surface created ({config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT})")
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

        print(f"Standard Pygame window initialized ({config.SCREEN_WIDTH}x{config.SCREEN_HEIGHT})")
        return screen

# ==============================================================================
# 4. MAIN APPLICATION ORCHESTRATOR
# ==============================================================================

def main():
    """Initializes all components, starts threads, and runs the main UI loop."""
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
    # temp_sensor_inst = temp_sensor.TempSensorInfo(shutdown_flag)
    spec_controller_inst = spectrometer_controller.SpectrometerController(
        shutdown_flag=shutdown_flag,
        request_queue=spectrometer_request_queue,
        result_queue=spectrometer_result_queue
    )
    # data_manager_inst = data_manager.DataManager(shutdown_flag, data_manager_save_queue)

    # --- Create UI Screen Instances ---
    menu_screen = menu_system.MenuSystem(screen, button_handler_inst, spectrometer_settings, network_info_inst)
    spectro_screen = spectrometer_screen.SpectrometerScreen(
        screen,
        button_handler_inst,
        spectrometer_settings,
        spectrometer_request_queue,
        spectrometer_result_queue,
        data_manager_save_queue
    )

    # --- Start Background Threads ---
    leak_sensor_inst.start()
    network_info_inst.start()
    # temp_sensor_inst.start()
    spec_controller_inst.start()
    # data_manager_inst.start()

    # --- Main Application Logic ---
    app_state = "MENU" # Initial state
    try:
        # --- Initial Startup Sequence ---
        splash_screen.show(screen, leak_detected_flag)

        if leak_detected_flag.is_set():
            leak_warning.show(screen)
            display_utils.update_display(screen)
            shutdown_flag.set()

        if not shutdown_flag.is_set():
            terms_screen.show(screen, button_handler_inst, leak_detected_flag)

            if leak_detected_flag.is_set():
                leak_warning.show(screen)
                display_utils.update_display(screen)
                shutdown_flag.set()

        # --- Main Application Loop ---
        while not shutdown_flag.is_set():
            # --- Event Handling ---
            button_handler_inst.check_pygame_events()
            if button_handler_inst.get_pressed("shutdown"):
                shutdown_flag.set()

            if leak_detected_flag.is_set():
                leak_warning.show(screen)
                display_utils.update_display(screen)
                shutdown_flag.set()
                continue # Skip the rest of the loop

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
                    menu_screen.dark_reference_required = False # Reset flag
                if menu_screen.white_reference_required:
                    white_reference_required = True
                    menu_screen.white_reference_required = False # Reset flag

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
            clock.tick(30) # Limit frame rate

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Shutting down.")
        shutdown_flag.set()
    finally:
        # --- Cleanup: Stop all threads and cleanup resources ---
        print("Initiating shutdown...")
        shutdown_flag.set() # Ensure all threads see the flag
        leak_sensor_inst.stop()
        network_info_inst.stop()
        button_handler_inst.cleanup()
        # temp_sensor_inst.stop()
        spec_controller_inst.stop()
        # data_manager_inst.stop()
        pygame.quit()
        print("Application finished.")

if __name__ == "__main__":
    main()
