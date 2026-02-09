## @file spectrometer_screen.py
#  @brief Live spectrometer view screen with capture and calibration workflows.
#
#  This module provides the main spectrometer interface for real-time spectral
#  visualization at ~30 FPS. It implements a state machine for:
#  - Live view (RAW and REFLECTANCE modes)
#  - Freeze/capture workflow for saving spectra
#  - Dark/white reference calibration
#  - Auto-integration algorithm for optimal integration time
#
#  @details Uses queue-based communication with SpectrometerController thread.
#  Session-based validity tracking ensures only fresh scans are displayed.
#  Reference captures always use RAW mode regardless of collection mode setting.

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
    CMD_AUTO_INTEG_CAPTURE,
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
    STATE_AUTO_INTEG_SETUP = "auto_integ_setup"
    STATE_AUTO_INTEG_RUNNING = "auto_integ_running"
    STATE_AUTO_INTEG_CONFIRM = "auto_integ_confirm"

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
        self._frozen_raw_intensities: Optional[np.ndarray] = (
            None  # Raw data for reflectance saves
        )

        # Current raw intensities (for reflectance mode)
        self._current_raw_intensities: Optional[np.ndarray] = None

        # Reference status and integration time tracking
        self._has_dark_ref = False
        self._has_white_ref = False
        self._dark_ref_integration_ms: Optional[int] = None
        self._white_ref_integration_ms: Optional[int] = None

        # Reflectance mode validation flag
        self._refs_invalid_for_reflectance = False
        self._refs_invalid_reason = ""

        # Session scan counter (RAW and REFLECTANCE scans only, resets each app start)
        self._session_scan_count: int = 0

        # Scans since last calibration (for tracking when to recalibrate)
        self._scans_since_dark_ref: int = 0
        self._scans_since_white_ref: int = 0
        self._scans_since_auto_integ: int = 0

        # Auto-integration status
        self._auto_integ_completed: bool = False
        self._auto_integ_integration_ms: Optional[int] = None

        # Auto-integration algorithm state
        self._auto_integ_optimizing: bool = False
        self._auto_integ_current_us: int = 0  # Current test integration time (µs)
        self._auto_integ_pending_ms: Optional[int] = None  # Final result to apply
        self._auto_integ_iteration_count: int = 0
        self._auto_integ_status_msg: str = ""
        self._auto_integ_last_peak_adc: float = 0.0
        self._auto_integ_prev_direction: int = 0  # For oscillation detection
        self._auto_integ_waiting_for_result: bool = False  # Waiting for capture result
        self._original_y_max_before_auto_integ: Optional[float] = None

        # Hardware ADC limits for auto-integration targets
        self._hw_max_intensity_adc: int = config.SPECTROMETER.HW_MAX_ADC_COUNT
        self._hw_min_integration_us: int = config.SPECTROMETER.HW_INTEGRATION_TIME_MIN_US
        self._hw_max_integration_us: int = config.SPECTROMETER.HW_INTEGRATION_TIME_MAX_US

        # Calculate target ADC count range from config percentages
        self._auto_integ_target_low_counts: float = self._hw_max_intensity_adc * (
            config.AUTO_INTEGRATION.TARGET_LOW_PERCENT / 100.0
        )
        self._auto_integ_target_high_counts: float = self._hw_max_intensity_adc * (
            config.AUTO_INTEGRATION.TARGET_HIGH_PERCENT / 100.0
        )

        # Track settings for invalidation detection
        self._last_known_integration_ms: int = self.settings.integration_time_ms
        self._last_known_scans_to_average: int = self.settings.scans_to_average

        # Y-axis scaling
        self._current_y_max_for_plot: float = config.PLOTTING.Y_AXIS_DEFAULT_MAX
        self._stored_y_max_for_live_view: float = config.PLOTTING.Y_AXIS_DEFAULT_MAX

        # Calibration menu state
        self._calib_menu_index: int = 0
        self._first_scan_in_ref_capture: bool = False
        self._auto_rescale_on_next_scan: bool = False  # Trigger rescale after auto-integ

        # Stored collection mode for reference capture
        # When capturing references, we temporarily switch to RAW mode
        # This stores the original mode to restore after calibration
        self._stored_collection_mode: str = self.settings.collection_mode

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

    def _are_references_valid_for_reflectance(self) -> tuple[bool, str]:
        """
        Check if dark and white references are valid for reflectance mode.

        For reflectance mode to work, both references must:
        1. Exist (have been captured)
        2. Have matching integration times with current settings

        Returns:
            Tuple of (is_valid, reason_string)
            - is_valid: True if both references are valid
            - reason_string: Empty if valid, otherwise describes the issue
        """
        current_integ_ms = self.settings.integration_time_ms

        # Check if dark reference exists
        if not self._has_dark_ref or self._dark_ref_integration_ms is None:
            return False, "No Dark ref"

        # Check if white reference exists
        if not self._has_white_ref or self._white_ref_integration_ms is None:
            return False, "No White ref"

        # Check if integration times match
        dark_integ_ok = self._dark_ref_integration_ms == current_integ_ms
        white_integ_ok = self._white_ref_integration_ms == current_integ_ms

        if not dark_integ_ok and not white_integ_ok:
            return False, f"Integ mismatch D&W ({current_integ_ms}ms)"
        if not dark_integ_ok:
            return (
                False,
                f"Dark integ: {self._dark_ref_integration_ms}ms != {current_integ_ms}ms",
            )
        if not white_integ_ok:
            return (
                False,
                f"White integ: {self._white_ref_integration_ms}ms != {current_integ_ms}ms",
            )

        return True, ""

    def _check_and_handle_settings_changes(self):
        """
        Check if settings have changed and invalidate calibrations as needed.

        Called when entering live view to detect if user changed settings in menu.

        Invalidation rules:
        - Integration time change → ALL calibrations invalid
        - Scans to average change → Dark/White refs invalid (auto-integ unaffected)
        """
        current_integ_ms = self.settings.integration_time_ms
        current_avg = self.settings.scans_to_average

        # Check if integration time changed
        if current_integ_ms != self._last_known_integration_ms:
            print(
                f"SpectrometerScreen: Integration time changed "
                f"({self._last_known_integration_ms}ms → {current_integ_ms}ms)"
            )
            print("SpectrometerScreen: All calibrations invalidated")

            # Invalidate ALL calibrations
            self._has_dark_ref = False
            self._has_white_ref = False
            self._dark_ref_integration_ms = None
            self._white_ref_integration_ms = None
            self._auto_integ_completed = False
            self._auto_integ_integration_ms = None

            # Reset "scans since" counters
            self._scans_since_dark_ref = 0
            self._scans_since_white_ref = 0
            self._scans_since_auto_integ = 0

            self._last_known_integration_ms = current_integ_ms

        # Check if scans to average changed
        if current_avg != self._last_known_scans_to_average:
            print(
                f"SpectrometerScreen: Scans to average changed "
                f"({self._last_known_scans_to_average} → {current_avg})"
            )
            print("SpectrometerScreen: Dark/White references invalidated")

            # Invalidate dark/white refs only (auto-integ unaffected)
            self._has_dark_ref = False
            self._has_white_ref = False
            self._dark_ref_integration_ms = None
            self._white_ref_integration_ms = None

            # Reset dark/white "scans since" counters
            self._scans_since_dark_ref = 0
            self._scans_since_white_ref = 0

            self._last_known_scans_to_average = current_avg

    def enter(self):
        """
        Called when entering the spectrometer screen.

        For RAW mode: Immediately starts capturing
        For REFLECTANCE mode: Validates references first - if invalid,
            shows warning and does NOT start spectrometer until calibrated

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

        # Check for settings changes and invalidate calibrations if needed
        self._check_and_handle_settings_changes()

        # Update settings in controller FIRST (before starting session)
        # This ensures controller has correct settings before capturing
        self._sync_settings_to_controller()

        # Check reference validity for REFLECTANCE mode
        if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE:
            refs_valid, reason = self._are_references_valid_for_reflectance()
            if not refs_valid:
                self._refs_invalid_for_reflectance = True
                self._refs_invalid_reason = reason
                print(f"SpectrometerScreen: REFLECTANCE mode - refs invalid: {reason}")
                print(
                    "SpectrometerScreen: Spectrometer NOT started. Calibration required."
                )
                # Do NOT start the spectrometer - wait for calibration
                return
            else:
                self._refs_invalid_for_reflectance = False
                self._refs_invalid_reason = ""
        else:
            # RAW mode never requires reference validation
            self._refs_invalid_for_reflectance = False
            self._refs_invalid_reason = ""

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
        elif self._state == self.STATE_AUTO_INTEG_SETUP:
            return self._handle_auto_integ_setup_input()
        elif self._state == self.STATE_AUTO_INTEG_RUNNING:
            return self._handle_auto_integ_running_input()
        elif self._state == self.STATE_AUTO_INTEG_CONFIRM:
            return self._handle_auto_integ_confirm_input()

        return None

    def _handle_live_view_input(self) -> Optional[str]:
        """Handle input in live view state."""
        # BACK (B button): Return to menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            return "MENU"

        # UP (X button): Enter calibration menu
        # Always allowed - needed to calibrate when refs are invalid
        if self.button_handler.get_pressed(config.BTN_UP):
            self._enter_calibration_menu()
            return None

        # If references are invalid in REFLECTANCE mode, only X and B buttons work
        if self._refs_invalid_for_reflectance:
            # Freeze and rescale disabled - no data available
            return None

        # ENTER (A button): Freeze plot
        if self.button_handler.get_pressed(config.BTN_ENTER):
            if (
                self._current_wavelengths is not None
                and self._current_intensities is not None
            ):
                self._freeze_current_data()
            else:
                print("No data to freeze")

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
        """
        Handle input in calibration menu state.

        Direct button mapping (matches original code):
        - A (ENTER): Start white reference capture
        - X (UP): Start dark reference capture
        - Y (DOWN): Start auto-integration
        - B (BACK): Return to live view
        """
        # BACK (B button): Return to live view
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._exit_calibration_to_live_view()
            return None

        # ENTER (A button): Start white reference capture
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._start_live_white_reference()
            return None

        # UP (X button): Start dark reference capture
        if self.button_handler.get_pressed(config.BTN_UP):
            self._start_live_dark_reference()
            return None

        # DOWN (Y button): Start auto-integration
        if self.button_handler.get_pressed(config.BTN_DOWN):
            self._start_auto_integration_setup()
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

    def _handle_auto_integ_setup_input(self) -> Optional[str]:
        """
        Handle input in auto-integration setup state.

        User should aim at white reference before starting.
        - A (ENTER): Start auto-integration algorithm
        - B (BACK): Cancel and return to calibration menu
        """
        # BACK (B button): Cancel and return to calibration menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._cancel_auto_integration()
            self._state = self.STATE_CALIBRATION_MENU
            return None

        # ENTER (A button): Start auto-integration algorithm
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._auto_integ_optimizing = True
            self._auto_integ_iteration_count = 0
            self._auto_integ_status_msg = "Starting iteration 1..."
            self._state = self.STATE_AUTO_INTEG_RUNNING
            # Request first capture at current test integration time
            self._run_auto_integ_next_iteration()
            return None

        return None

    def _handle_auto_integ_running_input(self) -> Optional[str]:
        """
        Handle input while auto-integration is running.

        Only cancel is allowed during auto-integration.
        - B (BACK): Cancel auto-integration
        """
        # BACK (B button): Cancel auto-integration
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._cancel_auto_integration()
            self._state = self.STATE_CALIBRATION_MENU
            return None

        return None

    def _handle_auto_integ_confirm_input(self) -> Optional[str]:
        """
        Handle input in auto-integration confirmation state.

        User can accept or reject the calculated integration time.
        - A (ENTER): Apply the calculated integration time
        - B (BACK): Cancel and return to calibration menu
        """
        # BACK (B button): Cancel and return to calibration menu
        if self.button_handler.get_pressed(config.BTN_BACK):
            self._cancel_auto_integration()
            self._state = self.STATE_CALIBRATION_MENU
            return None

        # ENTER (A button): Apply the calculated integration time
        if self.button_handler.get_pressed(config.BTN_ENTER):
            self._apply_auto_integration_result()
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

            # Increment session scan counter (only for RAW and REFLECTANCE scans)
            # REFLECTANCE saves both RAW_REFLECTANCE and REFLECTANCE but only counts as 1
            if self._frozen_spectra_type in [
                config.MODES.SPECTRA_TYPE_RAW,
                config.MODES.SPECTRA_TYPE_REFLECTANCE,
            ]:
                self._session_scan_count += 1

                # Increment "scans since last calibration" counters
                self._scans_since_dark_ref += 1
                self._scans_since_white_ref += 1
                self._scans_since_auto_integ += 1

            print(
                f"SpectrometerScreen: Save request sent ({self._frozen_spectra_type})"
            )
            print(f"  Timestamp: {self._frozen_timestamp}")
            print(f"  Integration: {self._frozen_integration_ms} ms")
            print(f"  Scans averaged: {self._frozen_scans_to_average}")
            print(f"  Session scan count: {self._session_scan_count}")
        except queue.Full:
            print("ERROR: Save queue full. Data not saved.")

    def _enter_calibration_menu(self):
        """
        Enter calibration menu from live view.

        Stops spectrometer and stores current Y-axis scale and collection mode.
        """
        print("SpectrometerScreen: Entering calibration menu")

        # Store current Y-axis scale to restore when returning to live view
        self._stored_y_max_for_live_view = self._current_y_max_for_plot

        # Store current collection mode to restore after calibration
        # Reference captures always use RAW mode regardless of this setting
        self._stored_collection_mode = self.settings.collection_mode

        # Stop spectrometer while in calibration menu
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        # Reset menu index
        self._calib_menu_index = 0

        self._state = self.STATE_CALIBRATION_MENU

    def _exit_calibration_to_live_view(self):
        """
        Exit calibration and return to live view.

        Restores stored Y-axis scale, collection mode, and restarts spectrometer.
        For REFLECTANCE mode, validates references first - only starts
        spectrometer if references are valid.
        """
        print("SpectrometerScreen: Exiting calibration, returning to live view")

        # Restore Y-axis scale
        self._current_y_max_for_plot = self._stored_y_max_for_live_view
        self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)

        # Reset renderer wavelengths to force fresh data display
        self.renderer.plotter.original_x_data = None

        self._state = self.STATE_LIVE_VIEW

        # Restore collection mode in controller (was set to RAW during reference capture)
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=self._stored_collection_mode,
        )
        self.request_queue.put(mode_cmd)
        print(
            f"SpectrometerScreen: Restored collection mode to {self._stored_collection_mode}"
        )

        # Check reference validity for REFLECTANCE mode
        if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE:
            refs_valid, reason = self._are_references_valid_for_reflectance()
            if not refs_valid:
                self._refs_invalid_for_reflectance = True
                self._refs_invalid_reason = reason
                print(
                    f"SpectrometerScreen: REFLECTANCE mode - refs still invalid: {reason}"
                )
                print(
                    "SpectrometerScreen: Spectrometer NOT started. Calibration required."
                )
                # Do NOT start the spectrometer - wait for valid calibration
                return
            else:
                self._refs_invalid_for_reflectance = False
                self._refs_invalid_reason = ""
                print("SpectrometerScreen: References valid, starting spectrometer")
        else:
            # RAW mode never requires reference validation
            self._refs_invalid_for_reflectance = False
            self._refs_invalid_reason = ""

        # Start new session for fresh data
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _select_calibration_option(self):
        """Handle selection of calibration menu option."""
        if self._calib_menu_index == self.CALIB_MENU_DARK:
            self._start_live_dark_reference()
        elif self._calib_menu_index == self.CALIB_MENU_WHITE:
            self._start_live_white_reference()
        elif self._calib_menu_index == self.CALIB_MENU_AUTO_INT:
            self._start_auto_integration_setup()

    def _start_live_dark_reference(self):
        """
        Start live view for dark reference capture.

        IMPORTANT: Reference captures ALWAYS use RAW mode regardless of
        the current collection mode setting. This ensures we capture
        the actual sensor readings, not processed reflectance data.
        """
        print("SpectrometerScreen: Starting live dark reference capture")

        self._state = self.STATE_LIVE_DARK_REF
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Set collection mode to RAW for reference capture
        # This ensures we capture raw sensor data, not reflectance
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=config.MODES.MODE_RAW,
        )
        self.request_queue.put(mode_cmd)

        # Start new session for fresh scan
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

    def _start_live_white_reference(self):
        """
        Start live view for white reference capture.

        IMPORTANT: Reference captures ALWAYS use RAW mode regardless of
        the current collection mode setting. This ensures we capture
        the actual sensor readings, not processed reflectance data.
        """
        print("SpectrometerScreen: Starting live white reference capture")

        self._state = self.STATE_LIVE_WHITE_REF
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Set collection mode to RAW for reference capture
        # This ensures we capture raw sensor data, not reflectance
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=config.MODES.MODE_RAW,
        )
        self.request_queue.put(mode_cmd)

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
        print(
            f"SpectrometerScreen: Discarding frozen reference, returning to {return_state}"
        )

        self._state = return_state
        self._first_scan_in_ref_capture = True

        # Reset renderer for fresh data
        self.renderer.plotter.original_x_data = None

        # Ensure RAW mode is set (should already be RAW, but be explicit)
        mode_cmd = SpectrometerCommand(
            command_type=CMD_SET_COLLECTION_MODE,
            collection_mode=config.MODES.MODE_RAW,
        )
        self.request_queue.put(mode_cmd)

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
        # Also store the integration time used for this reference (for validation)
        if spectra_type == config.MODES.SPECTRA_TYPE_DARK_REF:
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_DARK_REF))
            self._has_dark_ref = True
            self._dark_ref_integration_ms = self._frozen_integration_ms
            self._scans_since_dark_ref = 0  # Reset counter
            print(
                f"SpectrometerScreen: Dark reference captured and stored "
                f"(integration: {self._dark_ref_integration_ms} ms)"
            )
        else:
            self.request_queue.put(SpectrometerCommand(CMD_CAPTURE_WHITE_REF))
            self._has_white_ref = True
            self._white_ref_integration_ms = self._frozen_integration_ms
            self._scans_since_white_ref = 0  # Reset counter
            print(
                f"SpectrometerScreen: White reference captured and stored "
                f"(integration: {self._white_ref_integration_ms} ms)"
            )

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

    def _start_auto_integration_setup(self):
        """
        Start auto-integration setup.

        Initializes the auto-integration algorithm state and transitions
        to the setup screen where user should aim at white reference.
        """
        print("SpectrometerScreen: Starting auto-integration setup")

        # Cancel any previous auto-integration state
        self._cancel_auto_integration()

        # Store current Y-axis scale to restore after auto-integration
        self._original_y_max_before_auto_integ = self._current_y_max_for_plot

        # Initialize test integration time from current menu setting
        current_integ_ms = self.settings.integration_time_ms
        self._auto_integ_current_us = int(current_integ_ms * 1000)

        # Clamp to hardware limits
        self._auto_integ_current_us = max(
            self._hw_min_integration_us,
            min(self._auto_integ_current_us, self._hw_max_integration_us),
        )

        self._auto_integ_status_msg = "Aim at white ref, then Start"
        self._state = self.STATE_AUTO_INTEG_SETUP

        print(
            f"SpectrometerScreen: Auto-integ initial test: {self._auto_integ_current_us} µs"
        )
        print(
            f"SpectrometerScreen: Target ADC range: "
            f"{self._auto_integ_target_low_counts:.0f} - {self._auto_integ_target_high_counts:.0f}"
        )

    def _cancel_auto_integration(self):
        """
        Cancel and reset auto-integration state.

        Restores Y-axis scaling if it was saved.
        """
        print("SpectrometerScreen: Cancelling auto-integration")

        # Restore original Y-axis scaling if we saved it
        if self._original_y_max_before_auto_integ is not None:
            self._current_y_max_for_plot = self._original_y_max_before_auto_integ
            self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)
            print(
                f"SpectrometerScreen: Restored Y-axis scaling: "
                f"{self._current_y_max_for_plot:.1f}"
            )
            self._original_y_max_before_auto_integ = None

        # Reset all auto-integration state
        self._auto_integ_optimizing = False
        self._auto_integ_current_us = 0
        self._auto_integ_pending_ms = None
        self._auto_integ_iteration_count = 0
        self._auto_integ_status_msg = ""
        self._auto_integ_last_peak_adc = 0.0
        self._auto_integ_prev_direction = 0
        self._auto_integ_waiting_for_result = False

        # Clear frozen data if it was from auto-integration
        if self._frozen_spectra_type == config.MODES.SPECTRA_TYPE_AUTO_INTEG:
            self._frozen_wavelengths = None
            self._frozen_intensities = None
            self._frozen_timestamp = None
            self._frozen_integration_ms = None

    def _run_auto_integ_next_iteration(self):
        """
        Request the next auto-integration capture.

        Sends CMD_AUTO_INTEG_CAPTURE command to controller with current
        test integration time.
        """
        if not self._auto_integ_optimizing:
            return

        # Start a new session to ensure valid results
        self.request_queue.put(SpectrometerCommand(CMD_START_SESSION))

        # Request capture at current test integration time
        cmd = SpectrometerCommand(
            command_type=CMD_AUTO_INTEG_CAPTURE,
            test_integration_us=self._auto_integ_current_us,
        )
        self.request_queue.put(cmd)

        self._auto_integ_waiting_for_result = True
        print(
            f"SpectrometerScreen: Auto-integ capture requested at "
            f"{self._auto_integ_current_us} µs"
        )

    def _process_auto_integ_result(self, result: SpectrometerResult):
        """
        Process an auto-integration capture result.

        Implements the proportional control algorithm with oscillation damping
        to find the optimal integration time for the target saturation range.

        Args:
            result: SpectrometerResult with peak_adc_value populated
        """
        if not self._auto_integ_optimizing:
            return

        self._auto_integ_waiting_for_result = False

        # Get peak ADC value from result
        if result.peak_adc_value is None:
            print("ERROR: Auto-integ result missing peak_adc_value")
            self._auto_integ_status_msg = "Error: No peak data"
            self._transition_to_auto_integ_confirm("Capture error. Aborting.")
            return

        peak_adc = result.peak_adc_value
        self._auto_integ_last_peak_adc = peak_adc

        # Store frozen data for display in confirm screen
        self._frozen_wavelengths = result.wavelengths.copy()
        self._frozen_intensities = result.intensities.copy()
        self._frozen_timestamp = result.timestamp
        self._frozen_integration_ms = result.integration_time_ms
        self._frozen_spectra_type = config.MODES.SPECTRA_TYPE_AUTO_INTEG
        self._frozen_scans_to_average = 1

        # Get the actual integration time used (may be clamped)
        clamped_current_us = result.test_integration_us or self._auto_integ_current_us

        # Check if max iterations reached
        if self._auto_integ_iteration_count >= config.AUTO_INTEGRATION.MAX_ITERATIONS:
            self._transition_to_auto_integ_confirm(
                f"Max iterations ({config.AUTO_INTEGRATION.MAX_ITERATIONS}) reached."
            )
            return

        self._auto_integ_iteration_count += 1

        # Check if peak is in target range
        if (
            self._auto_integ_target_low_counts
            <= peak_adc
            <= self._auto_integ_target_high_counts
        ):
            self._transition_to_auto_integ_confirm("Target range achieved!")
            return

        # Check if at hardware limits
        if (
            clamped_current_us <= self._hw_min_integration_us
            and peak_adc > self._auto_integ_target_high_counts
        ):
            self._transition_to_auto_integ_confirm(
                "At min integration, still saturated."
            )
            return

        if (
            clamped_current_us >= self._hw_max_integration_us
            and peak_adc < self._auto_integ_target_low_counts
        ):
            self._transition_to_auto_integ_confirm("At max integration, still low.")
            return

        # Calculate new integration time using proportional control
        target_adc = (
            self._auto_integ_target_low_counts + self._auto_integ_target_high_counts
        ) / 2.0

        # Avoid division by zero
        effective_max_peak_adc = max(peak_adc, 1.0)

        # Calculate adjustment ratio
        adjustment_ratio = target_adc / effective_max_peak_adc
        ideal_next_integ_us = clamped_current_us * adjustment_ratio
        change_us = ideal_next_integ_us - clamped_current_us

        # Apply proportional gain
        damped_change_us = change_us * config.AUTO_INTEGRATION.PROPORTIONAL_GAIN

        # Determine adjustment direction for oscillation detection
        current_adjustment_direction = 1 if damped_change_us > 0 else -1 if damped_change_us < 0 else 0

        # Apply oscillation damping if direction reversed
        if (
            self._auto_integ_prev_direction != 0
            and current_adjustment_direction != 0
            and current_adjustment_direction == -self._auto_integ_prev_direction
        ):
            damped_change_us *= config.AUTO_INTEGRATION.OSCILLATION_DAMPING_FACTOR

        # Enforce minimum adjustment
        min_adj = config.AUTO_INTEGRATION.MIN_ADJUSTMENT_US
        if abs(damped_change_us) < min_adj:
            if peak_adc < self._auto_integ_target_low_counts:
                damped_change_us = min_adj
            elif peak_adc > self._auto_integ_target_high_counts:
                damped_change_us = -min_adj

        # Calculate new test integration time
        new_test_integ_us = int(round(clamped_current_us + damped_change_us))

        # Clamp to hardware limits
        new_test_integ_us = max(
            self._hw_min_integration_us,
            min(new_test_integ_us, self._hw_max_integration_us),
        )

        # Check if no change possible (converged)
        if new_test_integ_us == clamped_current_us and not (
            self._auto_integ_target_low_counts
            <= peak_adc
            <= self._auto_integ_target_high_counts
        ):
            self._transition_to_auto_integ_confirm("Converged (no further adjustment).")
            return

        # Update state for next iteration
        self._auto_integ_current_us = new_test_integ_us
        self._auto_integ_prev_direction = current_adjustment_direction
        self._auto_integ_status_msg = (
            f"Iter {self._auto_integ_iteration_count}: "
            f"Peak={peak_adc:.0f} Next={new_test_integ_us / 1000.0:.1f}ms"
        )

        print(f"SpectrometerScreen: {self._auto_integ_status_msg}")

        # Request next iteration
        self._run_auto_integ_next_iteration()

    def _transition_to_auto_integ_confirm(self, status_msg: str):
        """
        Transition to auto-integration confirmation state.

        Args:
            status_msg: Status message to display
        """
        self._auto_integ_status_msg = status_msg
        self._auto_integ_pending_ms = int(round(self._auto_integ_current_us / 1000.0))
        self._auto_integ_optimizing = False
        self._auto_integ_waiting_for_result = False

        # Stop spectrometer session
        self.request_queue.put(SpectrometerCommand(CMD_STOP_SESSION))

        # Set Y-axis scaling based on frozen data if available
        if self._frozen_intensities is not None and len(self._frozen_intensities) > 0:
            max_intensity = float(np.max(self._frozen_intensities))
            self._current_y_max_for_plot = max(
                config.PLOTTING.Y_AXIS_MIN_CEILING,
                max_intensity * config.PLOTTING.Y_AXIS_RESCALE_FACTOR,
            )
            self.renderer.plotter.set_y_limits(0, self._current_y_max_for_plot)

        self._state = self.STATE_AUTO_INTEG_CONFIRM

        print(
            f"SpectrometerScreen: Auto-integ complete: {status_msg} "
            f"Proposed: {self._auto_integ_pending_ms} ms"
        )

    def _apply_auto_integration_result(self):
        """
        Apply the calculated auto-integration result.

        Updates the settings with the new integration time, sends the new
        integration time to the spectrometer controller, invalidates
        dark/white references (since integration time changed), and returns
        to live view.
        """
        print("SpectrometerScreen: Applying auto-integration result")

        if self._auto_integ_pending_ms is not None:
            new_integ_ms = self._auto_integ_pending_ms

            # Update settings with new integration time
            self.settings.integration_time_ms = new_integ_ms
            self._last_known_integration_ms = new_integ_ms

            # Send CMD_UPDATE_SETTINGS to controller so it uses the new integration time
            # This is CRITICAL - without this the controller keeps using the old value
            cmd = SpectrometerCommand(
                command_type=CMD_UPDATE_SETTINGS,
                integration_time_ms=new_integ_ms,
                scans_to_average=self.settings.scans_to_average,
            )
            self.request_queue.put(cmd)
            print(
                f"SpectrometerScreen: Sent CMD_UPDATE_SETTINGS with "
                f"integration_time_ms={new_integ_ms}"
            )

            # Invalidate dark/white references since integration time changed
            # References captured at a different integration time are not valid
            # for reflectance calculations
            if self._has_dark_ref or self._has_white_ref:
                print(
                    "SpectrometerScreen: Invalidating dark/white references "
                    "(integration time changed)"
                )
            self._has_dark_ref = False
            self._has_white_ref = False
            self._dark_ref_integration_ms = None
            self._white_ref_integration_ms = None
            self._scans_since_dark_ref = 0
            self._scans_since_white_ref = 0

            # Mark auto-integration as completed
            self._auto_integ_completed = True
            self._auto_integ_integration_ms = new_integ_ms
            self._scans_since_auto_integ = 0

            # Trigger auto-rescale on first scan back in live view
            # Integration time changed so signal levels will be different
            self._auto_rescale_on_next_scan = True

            print(
                f"SpectrometerScreen: New integration time: "
                f"{new_integ_ms} ms"
            )
        else:
            print("WARNING: No pending auto-integration time to apply")

        # Clear auto-integration state (but don't restore Y-axis - keep the new scale)
        self._original_y_max_before_auto_integ = None
        self._auto_integ_optimizing = False
        self._auto_integ_current_us = 0
        self._auto_integ_pending_ms = None
        self._auto_integ_iteration_count = 0
        self._auto_integ_status_msg = ""
        self._auto_integ_last_peak_adc = 0.0
        self._auto_integ_prev_direction = 0
        self._auto_integ_waiting_for_result = False

        # Clear frozen data
        self._frozen_wavelengths = None
        self._frozen_intensities = None
        self._frozen_timestamp = None
        self._frozen_integration_ms = None

        # Return to live view
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

        # Handle auto-integration results specially
        if result.spectra_type == config.MODES.SPECTRA_TYPE_AUTO_INTEG:
            if self._state == self.STATE_AUTO_INTEG_RUNNING:
                self._process_auto_integ_result(result)
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

            # Auto-rescale after auto-integration (integration time changed)
            if self._auto_rescale_on_next_scan and self._state == self.STATE_LIVE_VIEW:
                self._auto_rescale_on_next_scan = False
                self._rescale_y_axis()
                print("SpectrometerScreen: Auto-rescaled Y-axis after auto-integration")

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
        elif self._state == self.STATE_AUTO_INTEG_SETUP:
            self._draw_auto_integ_setup()
        elif self._state == self.STATE_AUTO_INTEG_RUNNING:
            self._draw_auto_integ_running()
        elif self._state == self.STATE_AUTO_INTEG_CONFIRM:
            self._draw_auto_integ_confirm()
        elif self._state in [
            self.STATE_FROZEN,
            self.STATE_FROZEN_DARK_REF,
            self.STATE_FROZEN_WHITE_REF,
        ]:
            self._draw_frozen_plot()
        elif self._state == self.STATE_LIVE_VIEW and self._refs_invalid_for_reflectance:
            # REFLECTANCE mode with invalid references - show warning
            self._draw_refs_invalid_warning()
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

    def _draw_refs_invalid_warning(self):
        """
        Draw warning message when REFLECTANCE mode requires calibration.

        Shown when in REFLECTANCE mode but dark/white references are
        missing or have mismatched integration times.
        """
        # Title - CALIBRATE REQUIRED
        title_text = "CALIBRATE REQUIRED"
        title_surface = self.font_title.render(title_text, True, config.COLORS.WHITE)
        title_x = (config.SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 70))

        # Reference status - centered
        status_y = 110

        # Dark reference status
        if self._has_dark_ref and self._dark_ref_integration_ms is not None:
            dark_text = "Dark Reference: Complete"
            dark_color = config.COLORS.YELLOW
        else:
            dark_text = "Dark Reference: Not set"
            dark_color = config.COLORS.WHITE
        dark_surface = self.font_info.render(dark_text, True, dark_color)
        dark_x = (config.SCREEN_WIDTH - dark_surface.get_width()) // 2
        self.screen.blit(dark_surface, (dark_x, status_y))

        # White reference status
        status_y += 30
        if self._has_white_ref and self._white_ref_integration_ms is not None:
            white_text = "White Reference: Complete"
            white_color = config.COLORS.YELLOW
        else:
            white_text = "White Reference: Not set"
            white_color = config.COLORS.WHITE
        white_surface = self.font_info.render(white_text, True, white_color)
        white_x = (config.SCREEN_WIDTH - white_surface.get_width()) // 2
        self.screen.blit(white_surface, (white_x, status_y))

    def _draw_calibration_menu(self):
        """
        Draw the calibration menu.

        Layout matches main menu style with left-aligned options and status info.

        Format:
        CALIBRATION MENU

        A: White Reference - Set/Not valid
           Scans since last set: ##
        X: Dark Reference - Set/Not valid
           Scans since last set: ##
        Y: Auto integration - Completed/Not complete
           Integration time: ####ms

        A:White | X:Dark | Y:Auto | B:Back
        """
        left_margin = 10
        y_pos = 5

        # Title at top (like main menu)
        title_text = "CALIBRATION MENU"
        title_surface = self.font_title.render(title_text, True, config.COLORS.YELLOW)
        self.screen.blit(title_surface, (left_margin, y_pos))

        # Menu items start below title
        y_pos = 35
        line_height = 18
        indent = 15  # Indent for sub-info lines

        # A: White Reference
        white_status = "Set" if self._has_white_ref else "Not valid"
        white_color = (
            config.COLORS.YELLOW if self._has_white_ref else config.COLORS.WHITE
        )
        white_text = f"A: White Reference - {white_status}"
        white_surface = self.font_info.render(white_text, True, white_color)
        self.screen.blit(white_surface, (left_margin, y_pos))

        y_pos += line_height
        if self._has_white_ref:
            white_scans_text = f"Scans since last set: {self._scans_since_white_ref}"
        else:
            white_scans_text = "Scans since last set: --"
        white_scans_surface = self.font_info.render(
            white_scans_text, True, config.COLORS.GRAY
        )
        self.screen.blit(white_scans_surface, (left_margin + indent, y_pos))

        # X: Dark Reference
        y_pos += line_height + 5
        dark_status = "Set" if self._has_dark_ref else "Not valid"
        dark_color = config.COLORS.YELLOW if self._has_dark_ref else config.COLORS.WHITE
        dark_text = f"X: Dark Reference - {dark_status}"
        dark_surface = self.font_info.render(dark_text, True, dark_color)
        self.screen.blit(dark_surface, (left_margin, y_pos))

        y_pos += line_height
        if self._has_dark_ref:
            dark_scans_text = f"Scans since last set: {self._scans_since_dark_ref}"
        else:
            dark_scans_text = "Scans since last set: --"
        dark_scans_surface = self.font_info.render(
            dark_scans_text, True, config.COLORS.GRAY
        )
        self.screen.blit(dark_scans_surface, (left_margin + indent, y_pos))

        # Y: Auto Integration
        y_pos += line_height + 5
        auto_status = "Completed" if self._auto_integ_completed else "Not complete"
        auto_color = (
            config.COLORS.YELLOW if self._auto_integ_completed else config.COLORS.WHITE
        )
        auto_text = f"Y: Auto integration - {auto_status}"
        auto_surface = self.font_info.render(auto_text, True, auto_color)
        self.screen.blit(auto_surface, (left_margin, y_pos))

        y_pos += line_height
        integ_text = f"Integration time: {self.settings.integration_time_ms}ms"
        integ_surface = self.font_info.render(integ_text, True, config.COLORS.GRAY)
        self.screen.blit(integ_surface, (left_margin + indent, y_pos))

        if self._auto_integ_completed:
            y_pos += line_height
            auto_scans_text = f"Scans since last set: {self._scans_since_auto_integ}"
            auto_scans_surface = self.font_info.render(
                auto_scans_text, True, config.COLORS.GRAY
            )
            self.screen.blit(auto_scans_surface, (left_margin + indent, y_pos))

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

    def _draw_auto_integ_setup(self):
        """
        Draw the auto-integration setup screen.

        Shows instructions and current settings before starting.
        """
        left_margin = 10
        y_pos = 40

        # Title
        title_text = "AUTO-INTEGRATION SETUP"
        title_surface = self.font_title.render(title_text, True, config.COLORS.YELLOW)
        self.screen.blit(title_surface, (left_margin, y_pos))

        # Instructions
        y_pos += 35
        line_height = 20

        instructions = [
            "Point spectrometer at white reference",
            "target for optimal results.",
            "",
            f"Starting integration: {self._auto_integ_current_us / 1000.0:.1f} ms",
            f"Target saturation: {config.AUTO_INTEGRATION.TARGET_LOW_PERCENT:.0f}%-{config.AUTO_INTEGRATION.TARGET_HIGH_PERCENT:.0f}%",
        ]

        for line in instructions:
            line_surface = self.font_info.render(line, True, config.COLORS.WHITE)
            self.screen.blit(line_surface, (left_margin, y_pos))
            y_pos += line_height

    def _draw_auto_integ_running(self):
        """
        Draw the auto-integration running screen.

        Shows current iteration status and progress.
        """
        left_margin = 10
        y_pos = 40

        # Title
        title_text = "AUTO-INTEGRATION RUNNING"
        title_surface = self.font_title.render(title_text, True, config.COLORS.YELLOW)
        self.screen.blit(title_surface, (left_margin, y_pos))

        # Progress info
        y_pos += 35
        line_height = 20

        progress_lines = [
            f"Iteration: {self._auto_integ_iteration_count} / {config.AUTO_INTEGRATION.MAX_ITERATIONS}",
            f"Current test: {self._auto_integ_current_us / 1000.0:.1f} ms",
            "",
            self._auto_integ_status_msg,
        ]

        if self._auto_integ_last_peak_adc > 0:
            progress_lines.append(f"Last peak ADC: {self._auto_integ_last_peak_adc:.0f}")
            progress_lines.append(
                f"Target range: {self._auto_integ_target_low_counts:.0f} - {self._auto_integ_target_high_counts:.0f}"
            )

        for line in progress_lines:
            line_surface = self.font_info.render(line, True, config.COLORS.WHITE)
            self.screen.blit(line_surface, (left_margin, y_pos))
            y_pos += line_height

    def _draw_auto_integ_confirm(self):
        """
        Draw the auto-integration confirmation screen.

        Shows the result with frozen plot and proposed integration time.
        """
        # Draw the frozen plot if available
        if (
            self._frozen_wavelengths is not None
            and self._frozen_intensities is not None
        ):
            self.renderer.set_wavelengths(self._frozen_wavelengths)
            self.renderer.update_spectrum(
                self._frozen_intensities, apply_smoothing=False, force_update=True
            )
            self.renderer.draw()

    def _draw_status_bar(self):
        """
        Draw status information at the top of the screen.

        Format: REFLECT | INT: ####ms | AVG: ## | SCANS: #### | Mode: Live
        """
        y_pos = 5

        # Skip status bar for calibration menu and auto-integ setup/running (they have their own layout)
        if self._state in [
            self.STATE_CALIBRATION_MENU,
            self.STATE_AUTO_INTEG_SETUP,
            self.STATE_AUTO_INTEG_RUNNING,
        ]:
            return

        # Build status text parts
        # Collection mode (RAW or REFLECT - abbreviated for space)
        mode_abbrev = (
            "REFLECT"
            if self.settings.collection_mode == config.MODES.MODE_REFLECTANCE
            else "RAW"
        )

        # Integration time
        integ_text = f"INT:{self._current_integration_ms}ms"

        # Scans to average
        avg_text = f"AVG:{self.settings.scans_to_average}"

        # Session scan count
        scans_text = f"SCANS:{self._session_scan_count}"

        # Combine left side status
        left_status = f"{mode_abbrev} | {integ_text} | {avg_text} | {scans_text}"

        mode_surface = self.font_info.render(left_status, True, config.COLORS.YELLOW)
        self.screen.blit(mode_surface, (5, y_pos))

        # Mode state display (top right corner)
        state_mode_text = ""
        state_mode_color = config.COLORS.YELLOW

        if self._state == self.STATE_LIVE_VIEW:
            state_mode_text = "LIVE"
        elif self._state == self.STATE_FROZEN:
            state_mode_text = "HOLD"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_LIVE_DARK_REF:
            state_mode_text = "DARK"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_LIVE_WHITE_REF:
            state_mode_text = "WHITE"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_FROZEN_DARK_REF:
            state_mode_text = "HOLD"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_FROZEN_WHITE_REF:
            state_mode_text = "HOLD"
            state_mode_color = config.COLORS.YELLOW
        elif self._state == self.STATE_AUTO_INTEG_CONFIRM:
            state_mode_text = "AUTO-INTEG"
            state_mode_color = config.COLORS.YELLOW

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
            # Special case: REFLECTANCE mode with invalid references
            if self._refs_invalid_for_reflectance:
                return "X: Calibrate | B: Menu"
            return "A:Freeze | X:Calib | Y:Rescale | B:Menu"
        elif self._state == self.STATE_FROZEN:
            return "A:Save | B:Discard"
        elif self._state == self.STATE_CALIBRATION_MENU:
            return "A:White | X:Dark | Y:Auto | B:Back"
        elif self._state == self.STATE_LIVE_DARK_REF:
            return "Cover sensor | A:Capture | Y:Rescale | B:Back"
        elif self._state == self.STATE_LIVE_WHITE_REF:
            return "Point at white | A:Capture | Y:Rescale | B:Back"
        elif self._state == self.STATE_FROZEN_DARK_REF:
            return "A:Save Dark Ref | B:Discard"
        elif self._state == self.STATE_FROZEN_WHITE_REF:
            return "A:Save White Ref | B:Discard"
        elif self._state == self.STATE_AUTO_INTEG_SETUP:
            return "A:Start | B:Cancel"
        elif self._state == self.STATE_AUTO_INTEG_RUNNING:
            return "B:Cancel"
        elif self._state == self.STATE_AUTO_INTEG_CONFIRM:
            pending_ms = self._auto_integ_pending_ms or 0
            return f"A:Apply {pending_ms}ms | B:Cancel"
        return ""
