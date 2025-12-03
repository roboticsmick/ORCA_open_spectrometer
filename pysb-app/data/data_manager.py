# pysb-app/data/data_manager.py

"""
## @file data_manager.py
#  @brief Data Manager Thread for saving spectral data to CSV and generating plots.
#
#  This module provides a background thread that handles all file I/O operations
#  for spectral data. It processes save requests from the UI thread and writes
#  data to CSV files with daily folder organization.
#
#  Key Features:
#  - Daily folder organization (DATA_DIR/YYYY-MM-DD/)
#  - CSV file with header row (wavelengths as column headers)
#  - Matplotlib plot generation for saved spectra
#  - Thread-safe queue-based communication
#  - Support for RAW, REFLECTANCE, DARK, WHITE spectra types
#  - Saves raw intensities alongside reflectance when in reflectance mode
"""

import threading
import queue
import os
import csv
import datetime
import numpy as np
from dataclasses import dataclass
from typing import Optional

import config

# ==============================================================================
# MATPLOTLIB IMPORT (Non-GUI Backend)
# ==============================================================================

plt = None

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-GUI backend for headless rendering
    import matplotlib.pyplot as plt
    print("DataManager: Matplotlib loaded successfully (Agg backend).")
except ImportError as e:
    print(f"WARNING: Matplotlib not available: {e}")
    print("Plot generation will be disabled.")


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================


@dataclass
class SaveRequest:
    """
    ## @brief Data packet sent from the UI thread to the Data Manager thread.
    #
    #  Contains all data required to save a spectral capture to disk.
    #
    #  @param wavelengths Wavelength array (nm).
    #  @param intensities Intensity array (ADC counts or reflectance).
    #  @param timestamp When the scan was captured.
    #  @param integration_time_ms Integration time in milliseconds.
    #  @param scans_to_average Number of scans averaged (1 = no averaging).
    #  @param spectra_type Type of spectra (RAW, REFLECTANCE, DARK, WHITE).
    #  @param collection_mode Collection mode used (RAW or REFLECTANCE).
    #  @param lens_type Lens type used for capture.
    #  @param temperature_c Optional temperature reading at capture time.
    #  @param raw_intensities_for_reflectance Raw intensities when saving reflectance.
    """

    wavelengths: np.ndarray
    intensities: np.ndarray
    timestamp: datetime.datetime
    integration_time_ms: int
    scans_to_average: int
    spectra_type: str
    collection_mode: str
    lens_type: str = config.MODES.DEFAULT_LENS_TYPE
    temperature_c: Optional[float] = None
    raw_intensities_for_reflectance: Optional[np.ndarray] = None


# ==============================================================================
# DATA MANAGER THREAD
# ==============================================================================


class DataManager:
    """
    ## @brief Background thread for saving spectral data to disk.
    #
    #  This class manages a background thread that processes save requests
    #  from the UI and writes spectral data to CSV files with optional
    #  Matplotlib plot generation.
    #
    #  File Organization:
    #  - DATA_DIR/YYYY-MM-DD/YYYY-MM-DD_spectra_log.csv
    #  - DATA_DIR/YYYY-MM-DD/spectrum_{type}_{lens}_{timestamp}.png
    #
    #  CSV Format:
    #  - Header: timestamp_utc, spectra_type, lens_type, integration_time_ms,
    #            scans_to_average, temperature_c, [wavelength columns]
    #  - Data: ISO timestamp, type, lens, integration_ms, avg_count, temp, [intensities]
    #
    #  Queue Communication:
    #  - Save requests received via save_queue
    #  - All file I/O happens on background thread to avoid UI blocking
    """

    def __init__(
        self,
        shutdown_flag: threading.Event,
        save_queue: queue.Queue,
    ):
        """
        ## @brief Initialize the data manager.
        #
        #  @param[in] shutdown_flag Global shutdown event (set to terminate thread).
        #  @param[in] save_queue Queue for receiving save requests.
        """
        assert shutdown_flag is not None, "shutdown_flag cannot be None"
        assert save_queue is not None, "save_queue cannot be None"

        self.shutdown_flag = shutdown_flag
        self.save_queue = save_queue

        # Thread management
        self._thread: Optional[threading.Thread] = None

        # Daily scan counter (resets each day)
        self._current_date_str: str = ""
        self._scans_today_count: int = 0

    def start(self):
        """
        ## @brief Start the data manager background thread.
        """
        if self._thread is not None and self._thread.is_alive():
            print("WARNING: DataManager thread already running")
            return

        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="DataManager"
        )
        self._thread.start()
        print("DataManager thread started")

    def stop(self):
        """
        ## @brief Stop the data manager background thread.
        """
        if self._thread is None or not self._thread.is_alive():
            print("DataManager thread not running")
            return

        print("Stopping DataManager thread...")

        try:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                print("WARNING: DataManager thread did not stop gracefully")
            else:
                print("DataManager thread stopped successfully")
        except Exception as e:
            print(f"Error stopping DataManager thread: {e}")
        finally:
            self._thread = None

    def _run_loop(self):
        """
        ## @brief Main thread loop.
        #
        #  This loop:
        #  1. Waits for save requests from the queue
        #  2. Processes each request (write CSV, generate plot)
        #  3. Continues until shutdown_flag is set
        """
        print("DataManager: Thread loop started")

        # Ensure data directory exists
        try:
            os.makedirs(config.DATA_DIR, exist_ok=True)
            print(f"DataManager: Data directory ready: {config.DATA_DIR}")
        except OSError as e:
            print(f"ERROR: Could not create data directory: {e}")
            return

        try:
            while not self.shutdown_flag.is_set():
                # Wait for save request with timeout
                try:
                    request: SaveRequest = self.save_queue.get(timeout=0.5)
                    self._process_save_request(request)
                except queue.Empty:
                    continue  # No request, check shutdown flag and continue

        except Exception as e:
            print(f"ERROR: Exception in DataManager loop: {e}")
            import traceback

            traceback.print_exc()

        finally:
            print("DataManager: Thread loop finished")

    def _process_save_request(self, request: SaveRequest):
        """
        ## @brief Process a single save request.
        #
        #  @param[in] request SaveRequest containing data to save.
        """
        assert request is not None, "SaveRequest cannot be None"
        assert request.wavelengths is not None, "wavelengths cannot be None"
        assert request.intensities is not None, "intensities cannot be None"
        assert request.timestamp is not None, "timestamp cannot be None"

        print(f"DataManager: Processing save request ({request.spectra_type})...")

        # Validate spectra type
        valid_spectra_types = [
            config.MODES.SPECTRA_TYPE_RAW,
            config.MODES.SPECTRA_TYPE_REFLECTANCE,
            config.MODES.SPECTRA_TYPE_DARK_REF,
            config.MODES.SPECTRA_TYPE_WHITE_REF,
            config.MODES.SPECTRA_TYPE_RAW_TARGET_FOR_REFLECTANCE,
        ]

        if request.spectra_type not in valid_spectra_types:
            print(f"WARNING: Invalid spectra_type: {request.spectra_type}. Not saved.")
            return

        # Save to CSV
        csv_success = self._save_to_csv(request)

        if csv_success:
            print(f"DataManager: Saved {request.spectra_type} to CSV successfully")

            # Generate plot only for OOI scans (RAW or REFLECTANCE)
            should_save_plot = request.spectra_type in [
                config.MODES.SPECTRA_TYPE_RAW,
                config.MODES.SPECTRA_TYPE_REFLECTANCE,
            ]

            if should_save_plot and plt is not None:
                self._save_plot(request)

            # If reflectance mode, also save the raw target intensities
            if (
                request.spectra_type == config.MODES.SPECTRA_TYPE_REFLECTANCE
                and request.raw_intensities_for_reflectance is not None
            ):
                self._save_raw_for_reflectance(request)
        else:
            print(f"ERROR: Failed to save {request.spectra_type} to CSV")

    def _get_daily_folder(self, timestamp: datetime.datetime) -> Optional[str]:
        """
        ## @brief Get or create the daily folder for the given timestamp.
        #
        #  @param[in] timestamp Timestamp to determine the folder date.
        #  @return Path to the daily folder, or None if creation failed.
        """
        date_str = timestamp.strftime("%Y-%m-%d")
        daily_folder = os.path.join(config.DATA_DIR, date_str)

        try:
            os.makedirs(daily_folder, exist_ok=True)
            return daily_folder
        except OSError as e:
            print(f"ERROR: Could not create daily folder {daily_folder}: {e}")
            return None

    def _update_daily_scan_count(self, date_str: str, csv_path: str):
        """
        ## @brief Update the daily scan counter.
        #
        #  Resets counter when date changes and reads existing count from CSV.
        #
        #  @param[in] date_str Current date string (YYYY-MM-DD).
        #  @param[in] csv_path Path to the CSV file for today.
        """
        if date_str != self._current_date_str:
            # Date changed, reset counter
            self._current_date_str = date_str
            self._scans_today_count = 0

            # Count existing OOI scans in today's CSV
            if os.path.isfile(csv_path):
                try:
                    with open(csv_path, "r", newline="") as f:
                        reader = csv.reader(f)
                        next(reader, None)  # Skip header
                        for row in reader:
                            if len(row) >= 2:
                                spectra_type = row[1]
                                if spectra_type in [
                                    config.MODES.SPECTRA_TYPE_RAW,
                                    config.MODES.SPECTRA_TYPE_REFLECTANCE,
                                ]:
                                    self._scans_today_count += 1
                    print(
                        f"DataManager: Found {self._scans_today_count} existing scans in today's log"
                    )
                except Exception as e:
                    print(f"WARNING: Error reading scan count from CSV: {e}")
                    self._scans_today_count = 0

    def _save_to_csv(self, request: SaveRequest) -> bool:
        """
        ## @brief Save spectral data to CSV file.
        #
        #  @param[in] request SaveRequest containing data to save.
        #  @return True if save successful, False otherwise.
        """
        daily_folder = self._get_daily_folder(request.timestamp)
        if daily_folder is None:
            return False

        date_str = request.timestamp.strftime("%Y-%m-%d")
        csv_path = os.path.join(daily_folder, f"{date_str}_{config.CSV_BASE_FILENAME}")

        # Update scan counter
        self._update_daily_scan_count(date_str, csv_path)

        # Format timestamp
        ts_utc_str = request.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Format temperature
        temp_str = ""
        if request.temperature_c is not None:
            temp_str = f"{request.temperature_c:.2f}"

        try:
            # Check if header is needed
            header_needed = not (
                os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0
            )

            with open(csv_path, "a", newline="") as csvf:
                writer = csv.writer(csvf)

                # Write header if needed
                if header_needed:
                    header_row = [
                        "timestamp_utc",
                        "spectra_type",
                        "lens_type",
                        "integration_time_ms",
                        "scans_to_average",
                        "temperature_c",
                    ]
                    header_row.extend([f"{float(wl):.2f}" for wl in request.wavelengths])
                    writer.writerow(header_row)

                # Write data row
                data_row = [
                    ts_utc_str,
                    request.spectra_type,
                    request.lens_type,
                    request.integration_time_ms,
                    request.scans_to_average,
                    temp_str,
                ]
                data_row.extend([f"{float(i):.4f}" for i in request.intensities])
                writer.writerow(data_row)

            # Increment scan count for OOI scans
            if request.spectra_type in [
                config.MODES.SPECTRA_TYPE_RAW,
                config.MODES.SPECTRA_TYPE_REFLECTANCE,
            ]:
                self._scans_today_count += 1

            return True

        except Exception as e:
            print(f"ERROR: Exception saving to CSV: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _save_raw_for_reflectance(self, request: SaveRequest):
        """
        ## @brief Save raw target intensities alongside reflectance data.
        #
        #  When saving a reflectance spectrum, also save the raw target
        #  intensities that were used to calculate the reflectance.
        #
        #  @param[in] request SaveRequest with raw_intensities_for_reflectance set.
        """
        assert request.raw_intensities_for_reflectance is not None

        # Create a new SaveRequest for the raw target
        raw_request = SaveRequest(
            wavelengths=request.wavelengths,
            intensities=request.raw_intensities_for_reflectance,
            timestamp=request.timestamp,
            integration_time_ms=request.integration_time_ms,
            scans_to_average=request.scans_to_average,
            spectra_type=config.MODES.SPECTRA_TYPE_RAW_TARGET_FOR_REFLECTANCE,
            collection_mode=request.collection_mode,
            lens_type=request.lens_type,
            temperature_c=request.temperature_c,
            raw_intensities_for_reflectance=None,  # No recursion
        )

        # Save to CSV (no plot for raw target)
        csv_success = self._save_to_csv(raw_request)
        if csv_success:
            print("DataManager: Saved RAW_REFLECTANCE to CSV")
        else:
            print("ERROR: Failed to save RAW_REFLECTANCE to CSV")

    def _save_plot(self, request: SaveRequest):
        """
        ## @brief Save a Matplotlib plot of the spectrum.
        #
        #  @param[in] request SaveRequest containing data to plot.
        """
        if plt is None:
            return

        daily_folder = self._get_daily_folder(request.timestamp)
        if daily_folder is None:
            return

        plot_ts_str = request.timestamp.strftime("%Y-%m-%d-%H%M%S")
        plot_file = os.path.join(
            daily_folder,
            f"spectrum_{request.spectra_type}_{request.lens_type}_{plot_ts_str}.png",
        )

        fig = None
        ax = None

        try:
            fig, ax = plt.subplots(figsize=(8, 6))
            if fig is None or ax is None:
                raise RuntimeError("Failed to create figure/axes for plot")

            # Plot data
            ax.plot(request.wavelengths, request.intensities)

            # Title with scan info
            title_scan_count = self._scans_today_count
            ax.set_title(
                f"Spectrum ({request.spectra_type}) - {plot_ts_str}\n"
                f"Lens: {request.lens_type}, "
                f"Integ: {request.integration_time_ms}ms, "
                f"Avg: {request.scans_to_average}, "
                f"Scan#: {title_scan_count}",
                fontsize=10,
            )

            # Axis labels
            ax.set_xlabel("Wavelength (nm)")
            if request.spectra_type == config.MODES.SPECTRA_TYPE_REFLECTANCE:
                ax.set_ylabel("Reflectance")
            else:
                ax.set_ylabel("Intensity")

            # Grid
            ax.grid(True, linestyle="--", alpha=0.7)

            # Save
            fig.tight_layout()
            fig.savefig(plot_file, dpi=150)
            print(f"DataManager: Plot saved: {plot_file}")

        except Exception as e:
            print(f"ERROR: Exception saving plot: {e}")
            import traceback

            traceback.print_exc()

        finally:
            if fig is not None and plt is not None:
                try:
                    plt.close(fig)
                except Exception:
                    pass
