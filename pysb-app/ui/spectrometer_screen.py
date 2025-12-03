# pysb-app/ui/spectrometer_screen.py

"""
Spectrometer Screen - Live Spectral Data Visualization

This module provides the live spectrometer view screen that displays spectral plots
in real-time. It communicates with the spectrometer controller thread via queues
and uses session-based validity tracking to ensure only fresh data is displayed.

Screen States:
- LIVE_VIEW: Displays live spectral data (RAW or REFLECTANCE mode)
- FROZEN: Frozen plot for capture/save
- CALIBRATION_MENU: Select calibration type (Dark/White/Auto-Integration)
- LIVE_DARK_REF: Live view for dark reference capture
- LIVE_WHITE_REF: Live view for white reference capture
- FROZEN_DARK_REF: Frozen dark reference for save/discard
- FROZEN_WHITE_REF: Frozen white reference for save/discard

Button Controls:
- ENTER (A): Freeze/unfreeze plot, confirm capture, or select menu item
- BACK (B): Return to menu or cancel capture
- UP (X): Dark reference / navigate menu
- DOWN (Y): Rescale Y-axis / navigate menu
"""

import pygame
import queue
import datetime
import numpy as np
from typing import Optional

import config
from ui.plotting import FastSpectralRenderer, prepare_display_data
from hardware.spectrometer_controller import (
    SpectrometerCommand,
    SpectrometerResult,
    CMD_START_SESSION,
    CMD_STOP_SESSION,
    CMD_UPDATE_SETTINGS,
    CMD_CAPTURE_DARK_REF,
    CMD_CAPTURE_WHITE_REF,
    CMD_SET_COLLECTION_MODE,
)
from data.data_manager import SaveRequest


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
    STATE_CALIBRATION_MENU = "calibration_menu"
    STATE_LIVE_DARK_REF = "live_dark_ref"
    STATE_LIVE_WHITE_REF = "live_white_ref"
    STATE_FROZEN_DARK_REF = "frozen_dark_ref"
    STATE_FROZEN_WHITE_REF = "frozen_white_ref"

    # Legacy state aliases (for compatibility)
    STATE_CAPTURE_DARK_REF = STATE_LIVE_DARK_REF
    STATE_CAPTURE_WHITE_REF = STATE_LIVE_WHITE_REF

    # Calibration menu options
    CALIB_MENU_DARK = 0
    CALIB_MENU_WHITE = 1
    CALIB_MENU_AUTO_INT = 2
    CALIB_MENU_OPTIONS = ["Dark Reference", "White Reference", "Auto Integration"]

    def __init__(
        self,
        screen: pygame.Surface,
        button_handler,
        settings,
        request_queue: queue.Queue,
        result_queue: queue.Queue,
        save_queue: queue.Queue,
    ):
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
        plot_rect = pygame.Rect(
            10, 40, config.SCREEN_WIDTH - 20, config.SCREEN_HEIGHT - 80
        )
        self.renderer = FastSpectralRenderer(
            parent_surface=screen,
            plot_rect=plot_rect,
            target_fps=30,
            max_display_points=config.PLOTTING.TARGET_DISPLAY_POINTS,
        )

        # Current data
        self._current_wavelengths: Optional[np.ndarray] = None
        self._current_intensities: Optional[np.ndarray] = None
        self._current_timestamp: Optional[datetime.datetime] = None
        self._current_integration_ms: int = (
            config.SPECTROMETER.DEFAULT_INTEGRATION_TIME_MS
        )

        # Frozen data (for capture)
        self._frozen_wavelengths: Optional[np.ndarray] = None
        self._frozen_intensities: Optional[np.ndarray] = None
        self._frozen_timestamp: Optional[datetime.datetime] = None
        self._frozen_integration_ms: Optional[int] = None
        self._frozen_scans_to_average: int = 1
        self._frozen_spectra_type: str = config.MODES.SPECTRA_TYPE_RAW
        self._frozen_raw_intensities: Optional[np.ndarray] = None  # Raw data for reflectance saves

        # Current raw intensities (for reflectance mode)
        self._current_raw_intensities: Optional[np.ndarray] = None

        # Reference status
        self._has_dark_ref = False
        self._has_white_ref = False

        # Y-axis scaling
        self._current_y_max_for_plot: float = config.PLOTTING.Y_AXIS_DEFAULT_MAX
        self._stored_y_max_for_live_view: float = config.PLOTTING.Y_AXIS_DEFAULT_MAX

        # Calibration menu state
        self._calib_menu_index: int = 0
        self._first_scan_in_ref_capture: bool = False

        # Load fonts
        self._load_fonts()

    def _load_fonts(self):
        """Load fonts for text rendering."""
        try:
            self.font_title = pygame.font.Font(
                config.FONTS.TITLE, config.FONT_SIZES.TITLE
            )
            self.font_info = pygame.font.Font(
                config.FONTS.SPECTRO, config.FONT_SIZES.SPECTRO
            )
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
        Sets initial Y-axis scaling based on collection mode.
        """
        print("SpectrometerScreen: Entering live view")
        self._state = self.STATE_LIVE_VIEW
        self._return_to_menu = False

        # Clear frozen data
        self._frozen_wavelengths = None
        self._frozen_intensities = None
        self._frozen_timestamp = None
        self._frozen_integration_ms = None
        self._frozen_scans_to_average = 1
        self._frozen_raw_intensities = None

        # Clear current raw intensities
        self._current_raw_intensities = None

        # Reset renderer wavelengths to force re-initialization with fresh data
        self.renderer.plotter.original_x_data = None

        # Set initial Y-axis defaults based on collection mode
        if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE:
            self._current_y_max_for_plot = (
                config.PLOTTING.Y_AXIS_REFLECTANCE_DEFAULT_MAX
            )
            print(
                f"SpectrometerScreen: Set Y-axis for REFLECTANCE mode: {self._current_y_max_for_plot}"
            )
        else:
            self._current_y_max_for_plot = config.PLOTTING.Y_AXIS_DEFAULT_MAX
            print(
                f"SpectrometerScreen: Set Y-axis for RAW mode: {self._current_y_max_for_plot}"
            )

        # Apply Y-axis limits to renderer
        self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)

        # Update settings in controller FIRST (before starting session)
        # This ensures controller has correct settings before capturing
        self._sync_settings_to_controller()

        # Start a new capture session with updated settings
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

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
            scans_to_average=self.settings.scans_to_average,
        )
        self.request_queue.put(cmd)

        # Also update collection mode
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=self.settings.collection_mode,
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
        elif self._state == self.STATE_CALIBRATION_MENU:
            return self._handle_calibration_menu_input()
        elif self._state == self.STATE_LIVE_DARK_REF:
            return self._handle_live_dark_ref_input()
        elif self._state == self.STATE_LIVE_WHITE_REF:
            return self._handle_live_white_ref_input()
        elif self._state == self.STATE_FROZEN_DARK_REF:
            return self._handle_frozen_dark_ref_input()
        elif self._state == self.STATE_FROZEN_WHITE_REF:
            return self._handle_frozen_white_ref_input()

        return None

    def _handle_live_view_input(self) -> Optional[str]:
        """Handle input in live view state."""
        # BACK (B button): Return to menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            return "MENU"

        # ENTER (A button): Freeze plot
        if self.button_handler.get_pressed(config.BTN_ENTER):
            if (
                self._current_wavelengths is not None
                and self._current_intensities is not None
            ):
                self._freeze_current_data()
            else:
                print("No data to freeze")

        # UP (X button): Enter calibration menu
        if self.button_handler.get_pressed(config.BTN_UP):
            self._enter_calibration_menu()

        # DOWN (Y button): Rescale Y-axis
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._rescale_y_axis()

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

    def _handle_calibration_menu_input(self) -> Optional[str]:
        """Handle input in calibration menu state."""
        # BACK (B button): Return to live view
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._exit_calibration_to_live_view()
            return None

        # ENTER (A button): Select current option
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._select_calibration_option()
            return None

        # UP (X button): Navigate up
        if self.button_handler.get_pressed(config.BTN_UP):
            self._calib_menu_index = (self._calib_menu_index - 1) % len(
                self.CALIB_MENU_OPTIONS
            )
            return None

        # DOWN (Y button): Navigate down
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._calib_menu_index = (self._calib_menu_index + 1) % len(
                self.CALIB_MENU_OPTIONS
            )
            return None

        return None

    def _handle_live_dark_ref_input(self) -> Optional[str]:
        """Handle input during live dark reference capture."""
        # BACK (B button): Return to calibration menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._return_to_calibration_menu()
            return None

        # ENTER (A button): Freeze for capture
        if self.button_handler.get_pressed(config.BTN_ENTER):
            if (
                self._current_wavelengths is not None
                and self._current_intensities is not None
            ):
                self._freeze_reference_data(config.MODES.SPECTRA_TYPE_DARK_REF)
            else:
                print("No data to freeze for dark reference")
            return None

        # DOWN (Y button): Rescale Y-axis
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._rescale_y_axis()

        return None

    def _handle_live_white_ref_input(self) -> Optional[str]:
        """Handle input during live white reference capture."""
        # BACK (B button): Return to calibration menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._return_to_calibration_menu()
            return None

        # ENTER (A button): Freeze for capture
        if self.button_handler.get_pressed(config.BTN_ENTER):
            if (
                self._current_wavelengths is not None
                and self._current_intensities is not None
            ):
                self._freeze_reference_data(config.MODES.SPECTRA_TYPE_WHITE_REF)
            else:
                print("No data to freeze for white reference")
            return None

        # DOWN (Y button): Rescale Y-axis
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._rescale_y_axis()

        return None

    def _handle_frozen_dark_ref_input(self) -> Optional[str]:
        """Handle input when dark reference is frozen for save/discard."""
        # BACK (B button): Discard and return to live dark ref capture
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._discard_frozen_reference(self.STATE_LIVE_DARK_REF)
            return None

        # ENTER (A button): Save dark reference
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._save_frozen_reference(config.MODES.SPECTRA_TYPE_DARK_REF)
            return None

        return None

    def _handle_frozen_white_ref_input(self) -> Optional[str]:
        """Handle input when white reference is frozen for save/discard."""
        # BACK (B button): Discard and return to live white ref capture
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._discard_frozen_reference(self.STATE_LIVE_WHITE_REF)
            return None

        # ENTER (A button): Save white reference
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._save_frozen_reference(config.MODES.SPECTRA_TYPE_WHITE_REF)
            return None

        return None

    def _freeze_current_data(self):
        """Freeze the current spectral data for capture."""
        self._frozen_wavelengths = self._current_wavelengths.copy()
        self._frozen_intensities = self._current_intensities.copy()
        self._frozen_timestamp = self._current_timestamp
        self._frozen_integration_ms = self._current_integration_ms
        self._frozen_scans_to_average = self.settings.scans_to_average
        self._frozen_spectra_type = (
            config.MODES.SPECTRA_TYPE_REFLECTANCE
            if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE
            else config.MODES.SPECTRA_TYPE_RAW
        )
        # Store raw intensities for reflectance mode saves
        if self._current_raw_intensities is not None:
            self._frozen_raw_intensities = self._current_raw_intensities.copy()
        else:
            self._frozen_raw_intensities = None

        self._state = self.STATE_FROZEN

        # Stop the spectrometer thread while reviewing frozen data
        # This prevents unnecessary background captures and saves power
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        print("SpectrometerScreen: Data frozen for capture")

    def _unfreeze(self):
        """Unfreeze and return to live view."""
        self._state = self.STATE_LIVE_VIEW

        # Start a new session to get fresh data representative of when user returned to live view
        # This ensures the scan is from the current spectrometer position, not stale data
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

        print("SpectrometerScreen: Returning to live view")

    def _save_frozen_data(self):
        """Save frozen data via the save queue."""
        if self._frozen_wavelengths is None or self._frozen_intensities is None:
            print("ERROR: No frozen data to save")
            return

        if self._frozen_timestamp is None or self._frozen_integration_ms is None:
            print("ERROR: Incomplete frozen data (missing timestamp or integration)")
            return

        # Create SaveRequest
        save_request = SaveRequest(
            wavelengths=self._frozen_wavelengths.copy(),
            intensities=self._frozen_intensities.copy(),
            timestamp=self._frozen_timestamp,
            integration_time_ms=self._frozen_integration_ms,
            scans_to_average=self._frozen_scans_to_average,
            spectra_type=self._frozen_spectra_type,
            collection_mode=self.settings.collection_mode,
            lens_type=config.MODES.DEFAULT_LENS_TYPE,  # Default to FIBER
            temperature_c=None,  # Temperature sensor not implemented yet
            raw_intensities_for_reflectance=self._frozen_raw_intensities,
        )

        # Send to save queue
        try:
            self.save_queue.put_nowait(save_request)
            print(f"SpectrometerScreen: Save request sent ({self._frozen_spectra_type})")
            print(f"  Timestamp: {self._frozen_timestamp}")
            print(f"  Integration: {self._frozen_integration_ms} ms")
            print(f"  Scans averaged: {self._frozen_scans_to_average}")
        except queue.Full:
            print("ERROR: Save queue full. Data not saved.")

    def _enter_calibration_menu(self):
        """
        Enter calibration menu from live view.

        Stops spectrometer and stores current Y-axis scale.
        """
        print("SpectrometerScreen: Entering calibration menu")

        # Store current Y-axis scale to restore when returning to live view
        self._stored_y_max_for_live_view = self._current_y_max_for_plot

        # Stop spectrometer while in calibration menu
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        # Reset menu index
        self._calib_menu_index = 0

        self._state = self.STATE_CALIBRATION_MENU

    def _exit_calibration_to_live_view(self):
        """
        Exit calibration and return to live view.

        Restores stored Y-axis scale and restarts spectrometer.
        """
        print("SpectrometerScreen: Exiting calibration, returning to live view")

        # Restore Y-axis scale
        self._current_y_max_for_plot = self._stored_y_max_for_live_view
        self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)

        # Reset renderer wavelengths to force fresh data display
        self.renderer.plotter.original_x_data = None

        self._state = self.STATE_LIVE_VIEW

        # Start new session for fresh data
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _select_calibration_option(self):
        """Handle selection of calibration menu option."""
        if self._calib_menu_index == self.CALIB_MENU_DARK:
            self._start_live_dark_reference()
        elif self._calib_menu_index == self.CALIB_MENU_WHITE:
            self._start_live_white_reference()
        elif self._calib_menu_index == self.CALIB_MENU_AUTO_INT:
            # TODO: Implement auto-integration
            print("SpectrometerScreen: Auto-integration not yet implemented")

    def _start_live_dark_reference(self):
        """Start live view for dark reference capture."""
        print("SpectrometerScreen: Starting live dark reference capture")

        self._state = self.STATE_LIVE_DARK_REF
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Start new session for fresh scan
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _start_live_white_reference(self):
        """Start live view for white reference capture."""
        print("SpectrometerScreen: Starting live white reference capture")

        self._state = self.STATE_LIVE_WHITE_REF
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Start new session for fresh scan
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _return_to_calibration_menu(self):
        """Return to calibration menu from reference capture."""
        print("SpectrometerScreen: Returning to calibration menu")

        # Stop spectrometer
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        self._state = self.STATE_CALIBRATION_MENU

    def _freeze_reference_data(self, spectra_type: str):
        """
        Freeze current data for reference capture.

        Args:
            spectra_type: SPECTRA_TYPE_DARK_REF or SPECTRA_TYPE_WHITE_REF
        """
        self._frozen_wavelengths = self._current_wavelengths.copy()
        self._frozen_intensities = self._current_intensities.copy()
        self._frozen_timestamp = self._current_timestamp
        self._frozen_integration_ms = self._current_integration_ms
        self._frozen_scans_to_average = self.settings.scans_to_average
        self._frozen_spectra_type = spectra_type
        self._frozen_raw_intensities = None  # No raw intensities for references

        # Stop spectrometer while reviewing frozen reference
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        # Set appropriate frozen state
        if spectra_type == config.MODES.SPECTRA_TYPE_DARK_REF:
            self._state = self.STATE_FROZEN_DARK_REF
            print("SpectrometerScreen: Dark reference frozen for review")
        else:
            self._state = self.STATE_FROZEN_WHITE_REF
            print("SpectrometerScreen: White reference frozen for review")

    def _discard_frozen_reference(self, return_state: str):
        """
        Discard frozen reference and return to live capture.

        Args:
            return_state: State to return to (STATE_LIVE_DARK_REF or STATE_LIVE_WHITE_REF)
        """
        print(f"SpectrometerScreen: Discarding frozen reference, returning to {return_state}")

        self._state = return_state
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Restart spectrometer with fresh session
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _save_frozen_reference(self, spectra_type: str):
        """
        Save frozen reference data and send capture command to controller.

        Args:
            spectra_type: SPECTRA_TYPE_DARK_REF or SPECTRA_TYPE_WHITE_REF
        """
        if self._frozen_wavelengths is None or self._frozen_intensities is None:
            print("ERROR: No frozen reference data to save")
            self._exit_calibration_to_live_view()
            return

        if self._frozen_timestamp is None or self._frozen_integration_ms is None:
            print("ERROR: Incomplete frozen reference data")
            self._exit_calibration_to_live_view()
            return

        # Send capture command to controller to store reference internally
        if spectra_type == config.MODES.SPECTRA_TYPE_DARK_REF:
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_DARK_REF))
            self._has_dark_ref = True
            print("SpectrometerScreen: Dark reference captured and stored")
        else:
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_WHITE_REF))
            self._has_white_ref = True
            print("SpectrometerScreen: White reference captured and stored")

        # Save to CSV (no PNG for calibration scans)
        save_request = SaveRequest(
            wavelengths=self._frozen_wavelengths.copy(),
            intensities=self._frozen_intensities.copy(),
            timestamp=self._frozen_timestamp,
            integration_time_ms=self._frozen_integration_ms,
            scans_to_average=self._frozen_scans_to_average,
            spectra_type=spectra_type,
            collection_mode=self.settings.collection_mode,
            lens_type=config.MODES.DEFAULT_LENS_TYPE,
            temperature_c=None,
            raw_intensities_for_reflectance=None,
        )

        try:
            self.save_queue.put_nowait(save_request)
            print(f"SpectrometerScreen: Reference save request sent ({spectra_type})")
        except queue.Full:
            print("ERROR: Save queue full. Reference not saved to CSV.")

        # Return to live view with stored Y-axis scale
        self._exit_calibration_to_live_view()

    def _rescale_y_axis(self):
        """
        Perform manual Y-axis rescale based on current spectral data.

        This method:
        - Uses current intensities to calculate max value
        - Applies smoothing if enabled in config
        - Calculates new Y-axis max based on collection mode (RAW vs REFLECTANCE)
        - Updates renderer Y-axis limits
        """
        # Check if we have current data to rescale from
        if self._current_intensities is None or len(self._current_intensities) == 0:
            print("SpectrometerScreen: No data available for rescaling")
            return

        print("SpectrometerScreen: Rescaling Y-axis...")

        # Get data to find max from
        data_to_find_max_from = self._current_intensities

        # Apply smoothing if enabled
        if (
            config.PLOTTING.USE_LIVE_SMOOTHING
            and config.PLOTTING.LIVE_SMOOTHING_WINDOW_SIZE > 1
            and len(self._current_intensities)
            >= config.PLOTTING.LIVE_SMOOTHING_WINDOW_SIZE
        ):
            # Import smoothing function from plotting module
            from ui.plotting import apply_fast_smoothing

            data_to_find_max_from = apply_fast_smoothing(
                self._current_intensities, config.PLOTTING.LIVE_SMOOTHING_WINDOW_SIZE
            )

        # Find max value
        max_val_for_scaling = (
            np.max(data_to_find_max_from) if len(data_to_find_max_from) > 0 else 0.0
        )

        # Calculate new Y-axis max based on collection mode
        is_reflectance = self.settings.collection_mode == config.MODES.MODE_REFLECTANCE

        if is_reflectance:
            # Reflectance mode: use reflectance-specific limits
            new_y_max_val = max(
                float(config.PLOTTING.Y_AXIS_REFLECTANCE_RESCALE_MIN_CEILING),
                float(max_val_for_scaling * config.PLOTTING.Y_AXIS_RESCALE_FACTOR),
            )
            new_y_max_val = min(
                new_y_max_val,
                float(config.PLOTTING.Y_AXIS_REFLECTANCE_RESCALE_MAX_CEILING),
            )
        else:
            # RAW mode: use RAW-specific limits
            new_y_max_val = max(
                float(config.PLOTTING.Y_AXIS_MIN_CEILING),
                float(max_val_for_scaling * config.PLOTTING.Y_AXIS_RESCALE_FACTOR),
            )
            # For RAW mode, cap at hardware max (if available)
            hw_max = config.SPECTROMETER.HW_MAX_ADC_COUNT
            new_y_max_val = min(
                new_y_max_val,
                float(hw_max * config.PLOTTING.Y_AXIS_RESCALE_FACTOR),
            )

        # Update internal tracking variable
        self._current_y_max_for_plot = new_y_max_val

        # Apply to renderer
        self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)

        print(
            f"SpectrometerScreen: Y-axis rescaled to {self._current_y_max_for_plot:.2f}"
        )

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
            print(
                f"SpectrometerScreen: Discarding invalid scan (session_id={result.session_id})"
            )
            return

        # Update reference status flags (from controller captures)
        if result.spectra_type == config.MODES.SPECTRA_TYPE_DARK_REF:
            self._has_dark_ref = True
            print("SpectrometerScreen: Dark reference updated (from controller)")
            return
        elif result.spectra_type == config.MODES.SPECTRA_TYPE_WHITE_REF:
            self._has_white_ref = True
            print("SpectrometerScreen: White reference updated (from controller)")
            return

        # Update current data (for live view and reference capture)
        self._current_wavelengths = result.wavelengths
        self._current_intensities = result.intensities
        self._current_timestamp = result.timestamp
        self._current_integration_ms = result.integration_time_ms
        self._current_raw_intensities = result.raw_intensities  # For reflectance saves

        # Determine if we should update the plot
        is_live_state = self._state in [
            self.STATE_LIVE_VIEW,
            self.STATE_LIVE_DARK_REF,
            self.STATE_LIVE_WHITE_REF,
        ]

        if is_live_state:
            # Set wavelengths if not already set
            if self.renderer.plotter.original_x_data is None:
                print(
                    f"SpectrometerScreen: Setting wavelengths (length: {len(result.wavelengths)})"
                )
                self.renderer.set_wavelengths(result.wavelengths)

            # Verify array lengths match before updating
            if len(result.intensities) != len(result.wavelengths):
                print(
                    f"ERROR: Array length mismatch! Wavelengths: {len(result.wavelengths)}, "
                    f"Intensities: {len(result.intensities)}"
                )
                return

            # Auto-rescale on first scan in reference capture mode
            if self._first_scan_in_ref_capture and self._state in [
                self.STATE_LIVE_DARK_REF,
                self.STATE_LIVE_WHITE_REF,
            ]:
                self._first_scan_in_ref_capture = False
                self._rescale_y_axis()
                print("SpectrometerScreen: Auto-rescaled Y-axis for reference capture")

            # Update spectrum
            self.renderer.update_spectrum(
                result.intensities,
                apply_smoothing=config.PLOTTING.USE_LIVE_SMOOTHING,
                force_update=False,
            )

    def draw(self):
        """
        Draw the screen.

        This method:
        - Clears the screen
        - Draws the plot (live or frozen) or calibration menu
        - Draws status information
        - Draws hint text
        """
        self.screen.fill(config.COLORS.BLACK)

        # Draw based on state
        if self._state == self.STATE_CALIBRATION_MENU:
            self._draw_calibration_menu()
        elif self._state in [self.STATE_FROZEN, self.STATE_FROZEN_DARK_REF, self.STATE_FROZEN_WHITE_REF]:
            self._draw_frozen_plot()
        else:
            # Live states: LIVE_VIEW, LIVE_DARK_REF, LIVE_WHITE_REF
            self._draw_live_plot()

        # Draw status bar
        self._draw_status_bar()

        # Draw hint text
        self._draw_hint_text()

    def _draw_live_plot(self):
        """Draw the live plot."""
        self.renderer.draw()

    def _draw_calibration_menu(self):
        """Draw the calibration menu."""
        # Title
        title_text = "Calibration"
        title_surface = self.font_title.render(title_text, True, config.COLORS.CYAN)
        title_x = (config.SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 50))

        # Menu options
        menu_y_start = 100
        menu_spacing = 35

        for i, option in enumerate(self.CALIB_MENU_OPTIONS):
            is_selected = i == self._calib_menu_index

            # Highlight selected option
            if is_selected:
                color = config.COLORS.YELLOW
                prefix = "> "
            else:
                color = config.COLORS.WHITE
                prefix = "  "

            option_text = f"{prefix}{option}"
            option_surface = self.font_info.render(option_text, True, color)
            option_x = (config.SCREEN_WIDTH - option_surface.get_width()) // 2
            option_y = menu_y_start + i * menu_spacing
            self.screen.blit(option_surface, (option_x, option_y))

        # Reference status
        status_y = menu_y_start + len(self.CALIB_MENU_OPTIONS) * menu_spacing + 30
        dark_status = "Dark: " + ("OK" if self._has_dark_ref else "Not Set")
        white_status = "White: " + ("OK" if self._has_white_ref else "Not Set")

        dark_color = config.COLORS.GREEN if self._has_dark_ref else config.COLORS.RED
        white_color = config.COLORS.GREEN if self._has_white_ref else config.COLORS.RED

        dark_surface = self.font_info.render(dark_status, True, dark_color)
        white_surface = self.font_info.render(white_status, True, white_color)

        self.screen.blit(dark_surface, (80, status_y))
        self.screen.blit(white_surface, (180, status_y))

    def _draw_frozen_plot(self):
        """Draw the frozen plot."""
        if (
            self._frozen_wavelengths is not None
            and self._frozen_intensities is not None
        ):
            # Temporarily update renderer with frozen data
            self.renderer.set_wavelengths(self._frozen_wavelengths)
            self.renderer.update_spectrum(
                self._frozen_intensities, apply_smoothing=False, force_update=True
            )
            self.renderer.draw()

    def _draw_status_bar(self):
        """Draw status information at the top of the screen."""
        y_pos = 5

        # Skip status bar for calibration menu (it has its own layout)
        if self._state == self.STATE_CALIBRATION_MENU:
            return

        # Mode and integration time (left side)
        mode_text = (
            f"{self.settings.collection_mode} | {self._current_integration_ms}ms"
        )
        if self.settings.scans_to_average > 1:
            mode_text += f" | Avg:{self.settings.scans_to_average}"

        mode_surface = self.font_info.render(mode_text, True, config.COLORS.CYAN)
        self.screen.blit(mode_surface, (10, y_pos))

        # Mode state display (top right corner)
        state_mode_text = ""
        state_mode_color = config.COLORS.CYAN

        if self._state == self.STATE_LIVE_VIEW:
            state_mode_text = "Mode: LIVE"
        elif self._state == self.STATE_FROZEN:
            state_mode_text = "Mode: REVIEW"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_LIVE_DARK_REF:
            state_mode_text = "Mode: DARK REF"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_LIVE_WHITE_REF:
            state_mode_text = "Mode: WHITE REF"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_FROZEN_DARK_REF:
            state_mode_text = "Mode: DARK REVIEW"
            state_mode_color = config.COLORS.GREEN
        elif self._state == self.STATE_FROZEN_WHITE_REF:
            state_mode_text = "Mode: WHITE REVIEW"
            state_mode_color = config.COLORS.GREEN

        if state_mode_text:
            state_surface = self.font_info.render(
                state_mode_text, True, state_mode_color
            )
            state_x = config.SCREEN_WIDTH - 10 - state_surface.get_width()
            self.screen.blit(state_surface, (state_x, y_pos))

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
            return "A:Freeze | X:Calibration | Y:Rescale | B:Menu"
        elif self._state == self.STATE_FROZEN:
            return "A:Save | B:Discard"
        elif self._state == self.STATE_CALIBRATION_MENU:
            return "A:Select | X/Y:Navigate | B:Back"
        elif self._state == self.STATE_LIVE_DARK_REF:
            return "Cover sensor | A:Capture | Y:Rescale | B:Back"
        elif self._state == self.STATE_LIVE_WHITE_REF:
            return "Point at white | A:Capture | Y:Rescale | B:Back"
        elif self._state == self.STATE_FROZEN_DARK_REF:
            return "A:Save Dark Ref | B:Discard"
        elif self._state == self.STATE_FROZEN_WHITE_REF:
            return "A:Save White Ref | B:Discard"
        return ""
