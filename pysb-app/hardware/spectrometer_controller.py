## @file spectrometer_controller.py
#  @brief Background thread for USB spectrometer control via Seabreeze library.
#
#  Provides continuous spectral data capture with session-based validity tracking.
#  Implements queue-based command interface for integration time, scan averaging,
#  collection mode, and reference capture. Supports RAW and REFLECTANCE modes.
#
#  @details Session validity tracking ensures stale scans (from before the current
#  session) are discarded. This prevents displaying old data when returning from
#  menu or after settings changes.

"""
Spectrometer Controller Thread

This module provides a background thread that continuously captures spectral data
from a USB spectrometer using the Seabreeze library. It implements session-based
scan validity tracking to ensure only fresh, valid scans are processed.

Key Features:
- Session-based validity tracking (scans from old sessions are discarded)
- Queue-based command interface (START_SESSION, UPDATE_SETTINGS, etc.)
- Support for RAW and REFLECTANCE collection modes
- Dark and white reference management
- Scan averaging (0-50 scans)
- Thread-safe communication
- Hardware integration time clamping

Session Validity:
    When the user enters the live view or changes settings, a new session starts
    (session_id increments). Scans that started before the new session are
    automatically discarded. This prevents stale data from being displayed.

    Example: With 6-second integration time, if user enters menu and returns
    before scan finishes, that scan is discarded and a fresh scan starts.
"""

import threading
import queue
import time
import datetime
import numpy as np
from dataclasses import dataclass
from typing import Optional

import config

# ==============================================================================
# SEABREEZE LIBRARY IMPORT
# ==============================================================================

Spectrometer = None  # Type annotation
sb = None

try:
    import seabreeze

    seabreeze.use("pyseabreeze")  # Use pure Python implementation
    import seabreeze.spectrometers as sb
    from seabreeze.spectrometers import Spectrometer

    print("Seabreeze libraries loaded successfully.")
except ImportError as e:
    print(f"WARNING: Seabreeze library not available: {e}")
    print("Spectrometer functionality will be disabled.")

# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass
class SpectrometerCommand:
    """Command sent to the spectrometer controller thread."""

    command_type: str  # Command type (see COMMAND constants below)
    integration_time_ms: Optional[int] = None
    scans_to_average: Optional[int] = None
    collection_mode: Optional[str] = None
    test_integration_us: Optional[int] = None  # For auto-integration captures


# Command types
CMD_START_SESSION = "START_SESSION"  # Start new capture session
CMD_STOP_SESSION = "STOP_SESSION"  # Stop capturing (pause)
CMD_UPDATE_SETTINGS = "UPDATE_SETTINGS"  # Update integration time or scan averaging
CMD_CAPTURE_DARK_REF = "CAPTURE_DARK_REF"  # Capture dark reference
CMD_CAPTURE_WHITE_REF = "CAPTURE_WHITE_REF"  # Capture white reference
CMD_SET_COLLECTION_MODE = "SET_COLLECTION_MODE"  # Set RAW or REFLECTANCE mode
CMD_AUTO_INTEG_CAPTURE = "AUTO_INTEG_CAPTURE"  # Capture for auto-integration (single scan at test integration time)
CMD_SHUTDOWN = "SHUTDOWN"  # Terminate thread


@dataclass
class SpectrometerResult:
    """
    Result sent from the spectrometer controller thread.

    Attributes:
        wavelengths: Wavelength array (nm)
        intensities: Intensity array (ADC counts or reflectance)
        timestamp: When the scan was captured
        integration_time_ms: Integration time used for this scan
        collection_mode: Collection mode (RAW or REFLECTANCE)
        scans_to_average: Number of scans averaged
        session_id: Session ID when scan STARTED (for validity checking)
        spectra_type: Type of spectra (RAW, REFLECTANCE, DARK, WHITE, AUTO_INTEG)
        is_valid: Whether this scan is valid for the current session
        raw_intensities: Raw intensities before reflectance calculation (only in REFLECTANCE mode)
        peak_adc_value: Peak ADC value from scan (for auto-integration, otherwise None)
        test_integration_us: Integration time in µs used for auto-integ capture (otherwise None)
    """

    wavelengths: np.ndarray
    intensities: np.ndarray
    timestamp: datetime.datetime
    integration_time_ms: int
    collection_mode: str
    scans_to_average: int
    session_id: int
    spectra_type: str
    is_valid: bool
    raw_intensities: Optional[np.ndarray] = None
    peak_adc_value: Optional[float] = None
    test_integration_us: Optional[int] = None


# ==============================================================================
# SPECTROMETER CONTROLLER THREAD
# ==============================================================================


class SpectrometerController:
    """
    Background thread controller for USB spectrometer.

    This class manages a background thread that continuously captures spectral
    data from a USB spectrometer. It uses session-based validity tracking to
    ensure only fresh scans are processed by the UI.

    Session Validity:
        - Each time START_SESSION is called, session_id increments
        - Each scan captures the current session_id when it STARTS
        - UI only accepts scans where scan.session_id == current_session_id
        - This automatically discards scans from previous sessions

    Queue Communication:
        - Commands sent via request_queue
        - Results sent via result_queue
        - All communication is thread-safe

    Example:
        >>> request_queue = queue.Queue()
        >>> result_queue = queue.Queue()
        >>> controller = SpectrometerController(shutdown_flag, request_queue, result_queue)
        >>> controller.start()
        >>> # Start capturing
        >>> request_queue.put(SpectrometerCommand(CMD_START_SESSION))
        >>> # Get results
        >>> result = result_queue.get(timeout=1.0)
        >>> if result.is_valid:
        >>>     plot(result.wavelengths, result.intensities)
    """

    def __init__(
        self,
        shutdown_flag: threading.Event,
        request_queue: queue.Queue,
        result_queue: queue.Queue,
    ):
        """
        Initialize the spectrometer controller.

        Args:
            shutdown_flag: Global shutdown event (set to terminate thread)
            request_queue: Queue for receiving commands
            result_queue: Queue for sending results
        """
        self.shutdown_flag = shutdown_flag
        self.request_queue = request_queue
        self.result_queue = result_queue

        # Thread management
        self._thread: Optional[threading.Thread] = None

        # Spectrometer hardware
        self.spectrometer: Optional[Spectrometer] = None
        self.wavelengths: Optional[np.ndarray] = None

        # Hardware limits (will be read from device)
        self._hw_min_integration_us = config.SPECTROMETER.HW_INTEGRATION_TIME_MIN_US
        self._hw_max_integration_us = config.SPECTROMETER.HW_INTEGRATION_TIME_MAX_US

        # Session tracking
        self._session_id = 0  # Current session ID
        self._session_active = False  # Whether actively capturing

        # Current settings
        self._integration_time_ms = config.SPECTROMETER.DEFAULT_INTEGRATION_TIME_MS
        self._scans_to_average = config.SPECTROMETER.DEFAULT_SCANS_TO_AVERAGE
        self._collection_mode = config.MODES.DEFAULT_COLLECTION_MODE

        # Reference scans (for reflectance mode)
        self._dark_reference: Optional[np.ndarray] = None
        self._dark_reference_integration_ms: Optional[int] = None
        self._white_reference: Optional[np.ndarray] = None
        self._white_reference_integration_ms: Optional[int] = None

        # Capture type tracking
        self._current_capture_type = config.MODES.SPECTRA_TYPE_RAW

    def start(self):
        """Start the spectrometer controller thread."""
        if self._thread is not None and self._thread.is_alive():
            print("WARNING: SpectrometerController thread already running")
            return

        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="SpectrometerController"
        )
        self._thread.start()
        print("SpectrometerController thread started")

    def stop(self):
        """Stop the spectrometer controller thread."""
        if self._thread is None or not self._thread.is_alive():
            print("SpectrometerController thread not running")
            return

        print("Stopping SpectrometerController thread...")
        self.shutdown_flag.set()

        try:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                print("WARNING: SpectrometerController thread did not stop gracefully")
            else:
                print("SpectrometerController thread stopped successfully")
        except Exception as e:
            print(f"Error stopping SpectrometerController thread: {e}")
        finally:
            self._thread = None

    def _run_loop(self):
        """
        Main thread loop.

        This loop:
        1. Initializes the spectrometer hardware
        2. Processes commands from the request queue
        3. Captures spectral data when session is active
        4. Sends results to the result queue
        5. Cleans up on shutdown
        """
        print("SpectrometerController: Thread loop started")

        # Initialize hardware
        if not self._initialize_spectrometer():
            print("ERROR: Failed to initialize spectrometer. Thread exiting.")
            return

        try:
            while not self.shutdown_flag.is_set():
                # Process all pending commands
                self._process_commands()

                # If session is active, capture data
                if self._session_active and self._is_spectrometer_ready():
                    self._capture_and_send_result()
                else:
                    # No active session, sleep briefly to avoid busy-waiting
                    time.sleep(0.05)

        except Exception as e:
            print(f"ERROR: Exception in SpectrometerController loop: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Cleanup
            self._cleanup_spectrometer()
            print("SpectrometerController: Thread loop finished")

    def _initialize_spectrometer(self) -> bool:
        """
        Initialize the spectrometer hardware.

        Returns:
            True if initialization successful, False otherwise
        """
        if not config.HARDWARE["USE_SPECTROMETER"]:
            print("SpectrometerController: Spectrometer disabled in config")
            return False

        if sb is None or Spectrometer is None:
            print(
                "ERROR: Seabreeze libraries not loaded. Cannot initialize spectrometer."
            )
            return False

        try:
            # List available devices
            devices = sb.list_devices()
            if not devices:
                print("ERROR: No spectrometer devices found")
                return False

            # Open first device
            self.spectrometer = Spectrometer.from_serial_number(
                devices[0].serial_number
            )
            if not self.spectrometer or not hasattr(self.spectrometer, "_dev"):
                print("ERROR: Failed to create Spectrometer instance")
                return False

            # Get wavelength calibration
            self.wavelengths = self.spectrometer.wavelengths()
            if self.wavelengths is None or len(self.wavelengths) == 0:
                print("ERROR: Failed to get wavelengths from device")
                if self.spectrometer:
                    self.spectrometer.close()
                self.spectrometer = None
                return False

            print(f"Spectrometer initialized: {self.spectrometer.model}")
            print(f"  Serial: {self.spectrometer.serial_number}")
            print(
                f"  Wavelength range: {self.wavelengths[0]:.1f} - {self.wavelengths[-1]:.1f} nm"
            )
            print(f"  Pixels: {len(self.wavelengths)}")

            # Query hardware integration time limits
            try:
                min_us, max_us = self.spectrometer.integration_time_micros_limits
                self._hw_min_integration_us = int(min_us)
                self._hw_max_integration_us = int(max_us)
                print(
                    f"  Integration time limits: {self._hw_min_integration_us} - {self._hw_max_integration_us} µs"
                )
            except (AttributeError, TypeError, ValueError) as e:
                print(
                    f"  WARNING: Could not query integration limits ({e}). Using defaults."
                )

            return True

        except Exception as e:
            print(f"ERROR: Exception during spectrometer initialization: {e}")
            import traceback

            traceback.print_exc()
            self.spectrometer = None
            return False

    def _is_spectrometer_ready(self) -> bool:
        """
        Check if spectrometer is ready for capture.

        Returns:
            True if ready, False otherwise
        """
        if not config.HARDWARE["USE_SPECTROMETER"]:
            return False
        if self.spectrometer is None:
            return False
        if self.wavelengths is None or len(self.wavelengths) == 0:
            return False

        # Check if device is still open
        dev_proxy = getattr(self.spectrometer, "_dev", None)
        if dev_proxy is None or not hasattr(dev_proxy, "is_open"):
            return False

        return dev_proxy.is_open

    def _cleanup_spectrometer(self):
        """Close the spectrometer and cleanup resources."""
        if self.spectrometer is not None:
            try:
                self.spectrometer.close()
                print("Spectrometer closed successfully")
            except Exception as e:
                print(f"Error closing spectrometer: {e}")
            finally:
                self.spectrometer = None
                self.wavelengths = None

    def _process_commands(self):
        """Process all pending commands in the request queue."""
        try:
            while True:
                try:
                    cmd = self.request_queue.get_nowait()
                    self._handle_command(cmd)
                except queue.Empty:
                    break
        except Exception as e:
            print(f"ERROR: Exception processing commands: {e}")

    def _handle_command(self, cmd: SpectrometerCommand):
        """
        Handle a single command.

        Args:
            cmd: Command to process
        """
        if cmd.command_type == CMD_START_SESSION:
            self._start_new_session()

        elif cmd.command_type == CMD_STOP_SESSION:
            self._stop_session()

        elif cmd.command_type == CMD_UPDATE_SETTINGS:
            self._update_settings(cmd)

        elif cmd.command_type == CMD_CAPTURE_DARK_REF:
            self._capture_dark_reference()

        elif cmd.command_type == CMD_CAPTURE_WHITE_REF:
            self._capture_white_reference()

        elif cmd.command_type == CMD_SET_COLLECTION_MODE:
            if cmd.collection_mode is not None:
                self._set_collection_mode(cmd.collection_mode)

        elif cmd.command_type == CMD_AUTO_INTEG_CAPTURE:
            if cmd.test_integration_us is not None:
                self._capture_for_auto_integration(cmd.test_integration_us)
            else:
                print("WARNING: AUTO_INTEG_CAPTURE requires test_integration_us")

        elif cmd.command_type == CMD_SHUTDOWN:
            print("SpectrometerController: Shutdown command received")
            self.shutdown_flag.set()

        else:
            print(f"WARNING: Unknown command type: {cmd.command_type}")

    def _start_new_session(self):
        """
        Start a new capture session.

        This increments the session_id and marks the session as active.
        All subsequent scans will have this new session_id.
        """
        # Increment session ID with wraparound to prevent overflow
        self._session_id = (self._session_id + 1) % (2**31)
        self._session_active = True

        # Reset capture type
        self._current_capture_type = config.MODES.SPECTRA_TYPE_RAW

        print(f"SpectrometerController: New session started (ID: {self._session_id})")

    def _stop_session(self):
        """Stop the current capture session."""
        self._session_active = False
        print(f"SpectrometerController: Session stopped (ID: {self._session_id})")

    def _update_settings(self, cmd: SpectrometerCommand):
        """
        Update capture settings and start a new session.

        Args:
            cmd: Command with new settings
        """
        settings_changed = False

        if cmd.integration_time_ms is not None:
            if cmd.integration_time_ms != self._integration_time_ms:
                self._integration_time_ms = cmd.integration_time_ms
                settings_changed = True
                print(
                    f"SpectrometerController: Integration time updated to {self._integration_time_ms} ms"
                )

        if cmd.scans_to_average is not None:
            if cmd.scans_to_average != self._scans_to_average:
                self._scans_to_average = cmd.scans_to_average
                settings_changed = True
                print(
                    f"SpectrometerController: Scans to average updated to {self._scans_to_average}"
                )

        # If settings changed, start new session to invalidate in-progress scans
        if settings_changed and self._session_active:
            self._start_new_session()

    def _set_collection_mode(self, mode: str):
        """
        Set the collection mode (RAW or REFLECTANCE).

        Args:
            mode: Collection mode
        """
        if mode not in config.MODES.AVAILABLE_COLLECTION_MODES:
            print(f"WARNING: Invalid collection mode: {mode}")
            return

        if mode != self._collection_mode:
            self._collection_mode = mode
            print(f"SpectrometerController: Collection mode set to {mode}")

            # Start new session to invalidate in-progress scans
            if self._session_active:
                self._start_new_session()

    def _capture_dark_reference(self):
        """
        Capture a dark reference scan.

        Stores both the intensity data and the integration time used.
        The integration time is important for reference validation in
        reflectance mode - references must match current integration time.
        """
        print("SpectrometerController: Capturing dark reference...")
        self._current_capture_type = config.MODES.SPECTRA_TYPE_DARK_REF

        # Stop active session during reference capture
        was_active = self._session_active
        self._session_active = False

        # Capture dark reference
        raw_intensities = self._capture_single_scan()
        if raw_intensities is not None:
            self._dark_reference = raw_intensities
            self._dark_reference_integration_ms = self._integration_time_ms
            print(
                f"SpectrometerController: Dark reference captured successfully "
                f"(integration: {self._dark_reference_integration_ms} ms)"
            )
        else:
            print("ERROR: Failed to capture dark reference")

        # Resume session if it was active
        if was_active:
            self._start_new_session()

        self._current_capture_type = config.MODES.SPECTRA_TYPE_RAW

    def _capture_white_reference(self):
        """
        Capture a white reference scan.

        Stores both the intensity data and the integration time used.
        The integration time is important for reference validation in
        reflectance mode - references must match current integration time.
        """
        print("SpectrometerController: Capturing white reference...")
        self._current_capture_type = config.MODES.SPECTRA_TYPE_WHITE_REF

        # Stop active session during reference capture
        was_active = self._session_active
        self._session_active = False

        # Capture white reference
        raw_intensities = self._capture_single_scan()
        if raw_intensities is not None:
            self._white_reference = raw_intensities
            self._white_reference_integration_ms = self._integration_time_ms
            print(
                f"SpectrometerController: White reference captured successfully "
                f"(integration: {self._white_reference_integration_ms} ms)"
            )
        else:
            print("ERROR: Failed to capture white reference")

        # Resume session if it was active
        if was_active:
            self._start_new_session()

        self._current_capture_type = config.MODES.SPECTRA_TYPE_RAW

    def _capture_and_send_result(self):
        """
        Capture spectral data and send result to the result queue.

        This method:
        1. Captures the current session_id (scan starts NOW)
        2. Captures spectral data (may take several seconds)
        3. Processes data (averaging, reflectance calculation)
        4. Sends result with session_id to result queue
        5. UI checks if session_id matches current session
        """
        # Capture session ID at START of scan (not end)
        scan_session_id = self._session_id

        # Capture data
        raw_intensities = self._capture_with_averaging()
        if raw_intensities is None:
            return

        # Process data based on collection mode
        processed_intensities = raw_intensities
        spectra_type = self._current_capture_type
        raw_intensities_for_result: Optional[np.ndarray] = None

        if (
            self._collection_mode == config.MODES.MODE_REFLECTANCE
            and self._current_capture_type == config.MODES.SPECTRA_TYPE_RAW
        ):
            # Calculate reflectance if references are available
            if self._dark_reference is not None and self._white_reference is not None:
                processed_intensities = self._calculate_reflectance(raw_intensities)
                spectra_type = config.MODES.SPECTRA_TYPE_REFLECTANCE
                # Store raw intensities for saving alongside reflectance
                raw_intensities_for_result = raw_intensities.copy()
            else:
                print(
                    "WARNING: Reflectance mode but references not available. Sending raw data."
                )

        # Create result
        result = SpectrometerResult(
            wavelengths=self.wavelengths.copy(),
            intensities=processed_intensities,
            timestamp=datetime.datetime.now(),
            integration_time_ms=self._integration_time_ms,
            collection_mode=self._collection_mode,
            scans_to_average=self._scans_to_average,
            session_id=scan_session_id,  # Session ID when scan STARTED
            spectra_type=spectra_type,
            is_valid=(
                scan_session_id == self._session_id
            ),  # Valid if session hasn't changed
            raw_intensities=raw_intensities_for_result,  # Raw data for reflectance saves
        )

        # Send to result queue (non-blocking)
        try:
            self.result_queue.put_nowait(result)
        except queue.Full:
            print("WARNING: Result queue full. Dropping oldest result.")
            try:
                self.result_queue.get_nowait()  # Remove oldest
                self.result_queue.put_nowait(result)  # Add new
            except queue.Empty:
                pass

    def _capture_single_scan(self) -> Optional[np.ndarray]:
        """
        Capture a single scan from the spectrometer.

        Returns:
            Intensity array or None if capture failed
        """
        if not self._is_spectrometer_ready():
            return None

        try:
            # Convert integration time to microseconds
            integration_us = self._integration_time_ms * 1000

            # Clamp to hardware limits
            integration_us_clamped = max(
                self._hw_min_integration_us,
                min(integration_us, self._hw_max_integration_us),
            )

            # Set integration time
            self.spectrometer.integration_time_micros(integration_us_clamped)

            # Capture intensities
            intensities = self.spectrometer.intensities(
                correct_dark_counts=True, correct_nonlinearity=True
            )

            # Validate result
            if intensities is None or len(intensities) != len(self.wavelengths):
                print("WARNING: Invalid intensity data from spectrometer")
                return None

            return intensities

        except Exception as e:
            print(f"ERROR: Exception during spectral capture: {e}")
            return None

    def _capture_with_averaging(self) -> Optional[np.ndarray]:
        """
        Capture spectral data with optional scan averaging.

        Returns:
            Averaged intensity array or None if capture failed
        """
        if self._scans_to_average <= 1:
            # No averaging, just capture single scan
            return self._capture_single_scan()

        # Capture multiple scans and average
        accumulated = None
        valid_scans = 0

        for i in range(self._scans_to_average):
            intensities = self._capture_single_scan()
            if intensities is not None:
                if accumulated is None:
                    accumulated = intensities.astype(np.float64)
                else:
                    accumulated += intensities.astype(np.float64)
                valid_scans += 1
            else:
                print(f"WARNING: Scan {i+1}/{self._scans_to_average} failed")

        if valid_scans == 0:
            return None

        # Return average
        return (accumulated / valid_scans).astype(np.float64)

    def _calculate_reflectance(self, raw_intensities: np.ndarray) -> np.ndarray:
        """
        Calculate reflectance from raw intensities using references.

        Reflectance = (Raw - Dark) / (White - Dark)

        Note: Reflectance values CAN exceed 1.0 in legitimate cases:
        - Fluorescence from the target
        - Specular reflection at certain angles
        - Target more reflective than white reference at specific wavelengths

        Args:
            raw_intensities: Raw intensity array

        Returns:
            Reflectance array (clipped to minimum 0.0, no upper bound)
        """
        numerator = raw_intensities - self._dark_reference
        denominator = self._white_reference - self._dark_reference

        # Calculate reflectance with division-by-zero protection
        reflectance = np.full_like(raw_intensities, 0.0, dtype=float)
        valid_denom = np.abs(denominator) > config.DIVISION_EPSILON
        reflectance[valid_denom] = numerator[valid_denom] / denominator[valid_denom]

        # Only clip negative values (physically impossible)
        # Do NOT clip values > 1.0 as these can be legitimate (fluorescence, etc.)
        return np.maximum(reflectance, 0.0)

    def _capture_for_auto_integration(self, test_integration_us: int):
        """
        Capture a single scan for auto-integration at a specified integration time.

        This method is used during the auto-integration algorithm to test different
        integration times. It captures a single scan (no averaging) and returns
        the result with peak ADC value for the algorithm to evaluate.

        Args:
            test_integration_us: Integration time to test (in microseconds)
        """
        if not self._is_spectrometer_ready():
            print("WARNING: Spectrometer not ready for auto-integ capture")
            return

        # Capture session ID at START of scan
        scan_session_id = self._session_id

        try:
            # Clamp to hardware limits
            clamped_integration_us = max(
                self._hw_min_integration_us,
                min(test_integration_us, self._hw_max_integration_us),
            )

            # Set integration time
            self.spectrometer.integration_time_micros(clamped_integration_us)

            # Capture single scan (no averaging for auto-integration)
            intensities = self.spectrometer.intensities(
                correct_dark_counts=True, correct_nonlinearity=True
            )

            # Validate result
            if intensities is None or len(intensities) != len(self.wavelengths):
                print("WARNING: Invalid intensity data from auto-integ capture")
                return

            # Calculate peak ADC value
            peak_adc = float(np.max(intensities))

            # Create result with auto-integration data
            result = SpectrometerResult(
                wavelengths=self.wavelengths.copy(),
                intensities=intensities,
                timestamp=datetime.datetime.now(),
                integration_time_ms=int(round(clamped_integration_us / 1000.0)),
                collection_mode=config.MODES.MODE_RAW,  # Auto-integ always uses RAW
                scans_to_average=1,  # No averaging during auto-integ
                session_id=scan_session_id,
                spectra_type=config.MODES.SPECTRA_TYPE_AUTO_INTEG,
                is_valid=(scan_session_id == self._session_id),
                raw_intensities=None,
                peak_adc_value=peak_adc,
                test_integration_us=clamped_integration_us,
            )

            # Send to result queue
            try:
                self.result_queue.put_nowait(result)
            except queue.Full:
                print("WARNING: Result queue full during auto-integ. Dropping oldest.")
                try:
                    self.result_queue.get_nowait()
                    self.result_queue.put_nowait(result)
                except queue.Empty:
                    pass

        except Exception as e:
            print(f"ERROR: Exception during auto-integ capture: {e}")
            import traceback

            traceback.print_exc()
