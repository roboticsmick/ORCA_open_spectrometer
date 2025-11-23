# pysb-app/ui/spectrometer_screen.py

"""
Spectrometer Screen - Live Spectral Data Visualization

This module provides the live spectrometer view screen that displays spectral plots
in real-time. It communicates with the spectrometer controller thread via queues
and uses session-based validity tracking to ensure only fresh data is displayed.

Screen States:
- LIVE_VIEW: Displays live spectral data
- FROZEN: Frozen plot for capture/save
- CAPTURE_DARK_REF: Capturing dark reference
- CAPTURE_WHITE_REF: Capturing white reference

Button Controls:
- ENTER: Freeze/unfreeze plot, or confirm capture
- BACK: Return to menu or cancel capture
- UP/DOWN: (Reserved for future features like zoom)
"""

import pygame
import queue
import datetime
import numpy as np
from typing import Optional

import config
from ui.plotting import FastSpectralRenderer, prepare_display_data
from hardware.spectrometer_controller import (
    SpectrometerCommand, SpectrometerResult,
    CMD_START_SESSION, CMD_STOP_SESSION, CMD_UPDATE_SETTINGS,
    CMD_CAPTURE_DARK_REF, CMD_CAPTURE_WHITE_REF, CMD_SET_COLLECTION_MODE
)

class SpectrometerScreen:
    """
    Live spectrometer view screen.

    This screen:
    - Communicates with spectrometer controller via queues
    - Displays live spectral plots using FastSpectralRenderer
    - Implements session-based validity tracking (discards stale scans)
    - Supports freeze/capture functionality
    - Handles dark/white reference capture
    - Shows status information (integration time, mode, etc.)

    Queue Communication:
        request_queue → send commands to controller
        result_queue → receive results from controller

    Session Validity:
        Only displays scans where result.is_valid == True
        Controller marks scans as valid based on session_id matching
    """

    # Screen states
    STATE_LIVE_VIEW = "live_view"
    STATE_FROZEN = "frozen"
    STATE_CAPTURE_DARK_REF = "capture_dark_ref"
    STATE_CAPTURE_WHITE_REF = "capture_white_ref"

    def __init__(self, screen: pygame.Surface, button_handler,
                 settings, request_queue: queue.Queue,
                 result_queue: queue.Queue, save_queue: queue.Queue):
        """
        Initialize the spectrometer screen.

        Args:
            screen: Pygame surface for rendering
            button_handler: ButtonHandler instance
            settings: SpectrometerSettings instance (from main.py)
            request_queue: Queue for sending commands to controller
            result_queue: Queue for receiving results from controller
            save_queue: Queue for sending save requests to data manager
        """
        self.screen = screen
        self.button_handler = button_handler
        self.settings = settings
        self.request_queue = request_queue
        self.result_queue = result_queue
        self.save_queue = save_queue

        # Screen state
        self._state = self.STATE_LIVE_VIEW
        self._return_to_menu = False

        # Plot renderer
        plot_rect = pygame.Rect(10, 40, config.SCREEN_WIDTH - 20, config.SCREEN_HEIGHT - 80)
        self.renderer = FastSpectralRenderer(
            parent_surface=screen,
            plot_rect=plot_rect,
            target_fps=30,
            max_display_points=config.PLOTTING.TARGET_DISPLAY_POINTS
        )

        # Current data
        self._current_wavelengths: Optional[np.ndarray] = None
        self._current_intensities: Optional[np.ndarray] = None
        self._current_timestamp: Optional[datetime.datetime] = None
        self._current_integration_ms: int = config.SPECTROMETER.DEFAULT_INTEGRATION_TIME_MS

        # Frozen data (for capture)
        self._frozen_wavelengths: Optional[np.ndarray] = None
        self._frozen_intensities: Optional[np.ndarray] = None
        self._frozen_timestamp: Optional[datetime.datetime] = None
        self._frozen_integration_ms: Optional[int] = None
        self._frozen_spectra_type: str = config.MODES.SPECTRA_TYPE_RAW

        # Reference status
        self._has_dark_ref = False
        self._has_white_ref = False

        # Load fonts
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts for text rendering."""
        try:
            self.font_title = pygame.font.Font(config.FONTS.TITLE, config.FONT_SIZES.TITLE)
            self.font_info = pygame.font.Font(config.FONTS.SPECTRO, config.FONT_SIZES.SPECTRO)
            self.font_hint = pygame.font.Font(config.FONTS.HINT, config.FONT_SIZES.HINT)
        except:
            # Fallback to system fonts
            self.font_title = pygame.font.Font(None, config.FONT_SIZES.TITLE)
            self.font_info = pygame.font.Font(None, config.FONT_SIZES.SPECTRO)
            self.font_hint = pygame.font.Font(None, config.FONT_SIZES.HINT)

    def enter(self):
        """
        Called when entering the spectrometer screen.

        Sends START_SESSION command to controller to begin capturing.
        """
        print("SpectrometerScreen: Entering live view")
        self._state = self.STATE_LIVE_VIEW
        self._return_to_menu = False

        # Clear frozen data
        self._frozen_wavelengths = None
        self._frozen_intensities = None
        self._frozen_timestamp = None
        self._frozen_integration_ms = None

        # Start a new capture session
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

        # Update settings in controller
        self._sync_settings_to_controller()

    def exit(self):
        """
        Called when exiting the spectrometer screen.

        Sends STOP_SESSION command to controller to pause capturing.
        """
        print("SpectrometerScreen: Exiting live view")
        # Stop the capture session
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

    def _sync_settings_to_controller(self):
        """Send current settings to the spectrometer controller."""
        cmd = SpectrometerCommand(
            command_type=CMD_UPDATE_SETTINGS,
            integration_time_ms=self.settings.integration_time_ms,
            scans_to_average=self.settings.scans_to_average
        )
        self.request_queue.put(cmd)

        # Also update collection mode
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=self.settings.collection_mode
        )
        self.request_queue.put(mode_cmd)

    def handle_input(self) -> Optional[str]:
        """
        Handle button inputs.

        Returns:
            "MENU" if user wants to return to menu, None otherwise
        """
        if self._state == self.STATE_LIVE_VIEW:
            return self._handle_live_view_input()
        elif self._state == self.STATE_FROZEN:
            return self._handle_frozen_input()
        elif self._state == self.STATE_CAPTURE_DARK_REF:
            return self._handle_capture_dark_ref_input()
        elif self._state == self.STATE_CAPTURE_WHITE_REF:
            return self._handle_capture_white_ref_input()

        return None

    def _handle_live_view_input(self) -> Optional[str]:
        """Handle input in live view state."""
        # BACK: Return to menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            return "MENU"

        # ENTER: Freeze plot
        if self.button_handler.get_pressed(config.BTN_ENTER):
            if self._current_wavelengths is not None and self._current_intensities is not None:
                self._freeze_current_data()
            else:
                print("No data to freeze")

        # UP: Capture dark reference
        if self.button_handler.get_pressed(config.BTN_UP):
            self._start_dark_reference_capture()

        # DOWN: Capture white reference
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._start_white_reference_capture()

        return None

    def _handle_frozen_input(self) -> Optional[str]:
        """Handle input in frozen view state."""
        # BACK: Unfreeze and return to live view
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._unfreeze()
            return None

        # ENTER: Save captured data
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._save_frozen_data()
            self._unfreeze()
            return None

        return None

    def _handle_capture_dark_ref_input(self) -> Optional[str]:
        """Handle input during dark reference capture."""
        # BACK: Cancel
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._state = self.STATE_LIVE_VIEW
            self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))
            return None

        # ENTER: Confirm capture
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_DARK_REF))
            self._state = self.STATE_LIVE_VIEW
            self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))
            return None

        return None

    def _handle_capture_white_ref_input(self) -> Optional[str]:
        """Handle input during white reference capture."""
        # BACK: Cancel
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._state = self.STATE_LIVE_VIEW
            self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))
            return None

        # ENTER: Confirm capture
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_WHITE_REF))
            self._state = self.STATE_LIVE_VIEW
            self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))
            return None

        return None

    def _freeze_current_data(self):
        """Freeze the current spectral data for capture."""
        self._frozen_wavelengths = self._current_wavelengths.copy()
        self._frozen_intensities = self._current_intensities.copy()
        self._frozen_timestamp = self._current_timestamp
        self._frozen_integration_ms = self._current_integration_ms
        self._frozen_spectra_type = (
            config.MODES.SPECTRA_TYPE_REFLECTANCE
            if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE
            else config.MODES.SPECTRA_TYPE_RAW
        )
        self._state = self.STATE_FROZEN
        print("SpectrometerScreen: Data frozen for capture")

    def _unfreeze(self):
        """Unfreeze and return to live view."""
        self._state = self.STATE_LIVE_VIEW
        print("SpectrometerScreen: Returning to live view")

    def _save_frozen_data(self):
        """Save frozen data via the save queue."""
        if self._frozen_wavelengths is None or self._frozen_intensities is None:
            print("ERROR: No frozen data to save")
            return

        # TODO: Create SaveRequest and send to save_queue
        # For now, just print confirmation
        print(f"SpectrometerScreen: Saving {self._frozen_spectra_type} spectrum")
        print(f"  Timestamp: {self._frozen_timestamp}")
        print(f"  Integration: {self._frozen_integration_ms} ms")

    def _start_dark_reference_capture(self):
        """Start dark reference capture process."""
        print("SpectrometerScreen: Starting dark reference capture")
        self._state = self.STATE_CAPTURE_DARK_REF
        # Stop live session during reference capture
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

    def _start_white_reference_capture(self):
        """Start white reference capture process."""
        print("SpectrometerScreen: Starting white reference capture")
        self._state = self.STATE_CAPTURE_WHITE_REF
        # Stop live session during reference capture
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

    def update(self):
        """
        Update screen state and process results from controller.

        This method:
        - Reads results from the result queue
        - Validates session_id (only accept is_valid=True results)
        - Updates plot with new data
        - Updates reference status flags
        """
        # Process all pending results
        while True:
            try:
                result: SpectrometerResult = self.result_queue.get_nowait()
                self._process_result(result)
            except queue.Empty:
                break

    def _process_result(self, result: SpectrometerResult):
        """
        Process a result from the spectrometer controller.

        Args:
            result: SpectrometerResult from controller
        """
        # Session validity check - CRITICAL!
        if not result.is_valid:
            print(f"SpectrometerScreen: Discarding invalid scan (session_id={result.session_id})")
            return

        # Update reference status flags
        if result.spectra_type == config.MODES.SPECTRA_TYPE_DARK_REF:
            self._has_dark_ref = True
            print("SpectrometerScreen: Dark reference updated")
            return
        elif result.spectra_type == config.MODES.SPECTRA_TYPE_WHITE_REF:
            self._has_white_ref = True
            print("SpectrometerScreen: White reference updated")
            return

        # Update current data (for live view)
        self._current_wavelengths = result.wavelengths
        self._current_intensities = result.intensities
        self._current_timestamp = result.timestamp
        self._current_integration_ms = result.integration_time_ms

        # Update plot (only in live view)
        if self._state == self.STATE_LIVE_VIEW:
            # Set wavelengths if not already set
            if self.renderer.plotter.original_x_data is None:
                self.renderer.set_wavelengths(result.wavelengths)

            # Update spectrum
            self.renderer.update_spectrum(
                result.intensities,
                apply_smoothing=config.PLOTTING.USE_LIVE_SMOOTHING,
                force_update=False
            )

    def draw(self):
        """
        Draw the screen.

        This method:
        - Clears the screen
        - Draws the plot (live or frozen)
        - Draws status information
        - Draws hint text
        """
        self.screen.fill(config.COLORS.BLACK)

        # Draw plot
        if self._state == self.STATE_FROZEN:
            self._draw_frozen_plot()
        else:
            self._draw_live_plot()

        # Draw status bar
        self._draw_status_bar()

        # Draw hint text
        self._draw_hint_text()

    def _draw_live_plot(self):
        """Draw the live plot."""
        self.renderer.draw()

    def _draw_frozen_plot(self):
        """Draw the frozen plot."""
        if self._frozen_wavelengths is not None and self._frozen_intensities is not None:
            # Temporarily update renderer with frozen data
            self.renderer.set_wavelengths(self._frozen_wavelengths)
            self.renderer.update_spectrum(
                self._frozen_intensities,
                apply_smoothing=False,
                force_update=True
            )
            self.renderer.draw()

    def _draw_status_bar(self):
        """Draw status information at the top of the screen."""
        y_pos = 5

        # Mode and integration time
        mode_text = f"{self.settings.collection_mode} | {self._current_integration_ms}ms"
        if self.settings.scans_to_average > 1:
            mode_text += f" | Avg:{self.settings.scans_to_average}"

        mode_surface = self.font_info.render(mode_text, True, config.COLORS.CYAN)
        self.screen.blit(mode_surface, (10, y_pos))

        # Reference status
        ref_status = ""
        if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE:
            if self._has_dark_ref and self._has_white_ref:
                ref_status = "Refs: OK"
                ref_color = config.COLORS.GREEN
            else:
                ref_status = "Refs: Missing"
                ref_color = config.COLORS.RED

            ref_surface = self.font_info.render(ref_status, True, ref_color)
            ref_x = config.SCREEN_WIDTH - 10 - ref_surface.get_width()
            self.screen.blit(ref_surface, (ref_x, y_pos))

        # Frozen indicator
        if self._state == self.STATE_FROZEN:
            frozen_text = "FROZEN"
            frozen_surface = self.font_title.render(frozen_text, True, config.COLORS.YELLOW)
            frozen_x = (config.SCREEN_WIDTH - frozen_surface.get_width()) // 2
            self.screen.blit(frozen_surface, (frozen_x, y_pos))

    def _draw_hint_text(self):
        """Draw hint text at the bottom of the screen."""
        hint_text = self._get_hint_text()
        if hint_text:
            hint_surface = self.font_hint.render(hint_text, True, config.COLORS.YELLOW)
            hint_x = (config.SCREEN_WIDTH - hint_surface.get_width()) // 2
            hint_y = config.SCREEN_HEIGHT - 25
            self.screen.blit(hint_surface, (hint_x, hint_y))

    def _get_hint_text(self) -> str:
        """Get hint text based on current state."""
        if self._state == self.STATE_LIVE_VIEW:
            return "Enter:Freeze | Back:Menu | Up:Dark | Down:White"
        elif self._state == self.STATE_FROZEN:
            return "Enter:Save | Back:Cancel"
        elif self._state == self.STATE_CAPTURE_DARK_REF:
            return "Cover sensor | Enter:Capture | Back:Cancel"
        elif self._state == self.STATE_CAPTURE_WHITE_REF:
            return "Point at white reference | Enter:Capture | Back:Cancel"
        return ""
