# pysb-app/ui/plotting.py

import hashlib
import time
import numpy as np
import pygame
import config


##
# @brief Crop spectral data to a specific wavelength range.
# @param wavelengths Array of wavelength values (nm).
# @param intensities Array of intensity values.
# @param min_wavelength Minimum wavelength to keep (inclusive). None = no minimum filter.
# @param max_wavelength Maximum wavelength to keep (inclusive). None = no maximum filter.
# @return Tuple of (cropped_wavelengths, cropped_intensities).
# @details If no cropping is requested, returns copies of original arrays.
#          If cropping results in empty array, returns original data with warning.
def crop_wavelength_range(
    wavelengths: np.ndarray,
    intensities: np.ndarray,
    min_wavelength: float | None = None,
    max_wavelength: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Crop spectral data to a specific wavelength range."""
    assert isinstance(wavelengths, np.ndarray) and isinstance(intensities, np.ndarray)
    assert len(wavelengths) == len(
        intensities
    ), "Wavelengths and intensities must have same length"

    # If no cropping is requested, return copies
    if min_wavelength is None and max_wavelength is None:
        return wavelengths.copy(), intensities.copy()

    # Create boolean mask for wavelengths in range
    mask = np.ones(len(wavelengths), dtype=bool)

    if min_wavelength is not None:
        mask &= wavelengths >= min_wavelength

    if max_wavelength is not None:
        mask &= wavelengths <= max_wavelength

    # Apply mask
    cropped_wavelengths = wavelengths[mask]
    cropped_intensities = intensities[mask]

    # Ensure we got some data
    if len(cropped_wavelengths) == 0:
        print(
            f"WARNING: Wavelength crop resulted in empty array. Range: {min_wavelength}-{max_wavelength} nm, "
            f"Data range: {wavelengths[0]:.1f}-{wavelengths[-1]:.1f} nm. Returning original data."
        )
        return wavelengths.copy(), intensities.copy()

    return cropped_wavelengths, cropped_intensities


##
# @brief Reduce data points for display performance using block averaging or interpolation.
# @param wavelengths Array of wavelength values (nm).
# @param intensities Array of intensity values.
# @param target_points Target number of points for display (default: 300).
# @return Tuple of (decimated_wavelengths, decimated_intensities).
# @details Uses block averaging for larger decimation factors, linear interpolation for smaller factors.
#          If data length is already smaller than target, returns copies without decimation.
def decimate_spectral_data_for_display(
    wavelengths: np.ndarray, intensities: np.ndarray, target_points: int = 300
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce data points for display performance."""
    assert isinstance(wavelengths, np.ndarray) and isinstance(intensities, np.ndarray)
    assert isinstance(target_points, int) and target_points > 0

    if len(wavelengths) <= target_points:
        return wavelengths.copy(), intensities.copy()

    decimation_factor = len(wavelengths) // target_points
    if decimation_factor <= 2:
        # Linear interpolation for small decimation
        indices = np.linspace(0, len(wavelengths) - 1, target_points, dtype=int)
        return wavelengths[indices], intensities[indices]
    else:
        # Block averaging for larger decimation
        trim_length = (len(wavelengths) // decimation_factor) * decimation_factor

        wl_trimmed = wavelengths[:trim_length]
        int_trimmed = intensities[:trim_length]

        wl_blocks = wl_trimmed.reshape(-1, decimation_factor)
        int_blocks = int_trimmed.reshape(-1, decimation_factor)

        # Take mean of each block for wavelengths and intensities
        decimated_wl = np.mean(wl_blocks, axis=1)
        decimated_int = np.mean(int_blocks, axis=1)

        # If after block averaging, we don't have exactly target_points, interpolate
        if len(decimated_wl) != target_points and len(decimated_wl) > 1:
            current_indices = np.arange(len(decimated_wl))
            target_indices = np.linspace(0, len(decimated_wl) - 1, target_points)
            final_wl = np.interp(target_indices, current_indices, decimated_wl)
            final_int = np.interp(target_indices, current_indices, decimated_int)
            return final_wl, final_int

        return decimated_wl, decimated_int


##
# @brief Apply fast numpy-based smoothing using convolution.
# @param intensities Array of intensity values.
# @param window_size Size of smoothing window (default: 5). Will be converted to odd number.
# @return Smoothed intensity array.
# @details Uses normalized convolution kernel for fast smoothing. Returns copy if window_size <= 1.
def apply_fast_smoothing(intensities: np.ndarray, window_size: int = 5) -> np.ndarray:
    """Fast numpy-based smoothing."""
    assert isinstance(intensities, np.ndarray)
    assert isinstance(window_size, int) and window_size > 0

    if window_size <= 1 or len(intensities) < window_size:
        return intensities.copy()

    if window_size % 2 == 0:  # Ensure odd window size for symmetry
        window_size += 1

    # Create normalized convolution kernel
    kernel = np.ones(window_size, dtype=np.float32) / window_size

    # Apply convolution with 'same' mode to maintain array size
    smoothed = np.convolve(intensities.astype(np.float32), kernel, mode="same")

    return smoothed


##
# @brief Complete optimization pipeline with wavelength cropping, smoothing, and decimation.
# @param wavelengths Array of wavelength values (nm).
# @param intensities Array of intensity values.
# @param display_width Target number of points for display (default: 300).
# @param apply_smoothing Whether to apply smoothing (default: True).
# @param smoothing_window Smoothing window size (default: 5).
# @return Tuple of (processed_wavelengths, processed_intensities).
# @details Applies three-stage processing: 1) Crop to wavelength range, 2) Smooth, 3) Decimate.
def prepare_display_data(
    wavelengths: np.ndarray,
    intensities: np.ndarray,
    display_width: int = 300,
    apply_smoothing: bool = True,
    smoothing_window: int = 5,
) -> tuple[np.ndarray, np.ndarray]:
    """Complete optimization pipeline with wavelength cropping, smoothing, and decimation."""
    assert isinstance(wavelengths, np.ndarray) and isinstance(intensities, np.ndarray)
    assert isinstance(display_width, int) and display_width > 0
    assert isinstance(smoothing_window, int) and smoothing_window > 0

    # Step 1: Crop to desired wavelength range
    cropped_wl, cropped_int = crop_wavelength_range(
        wavelengths,
        intensities,
        min_wavelength=config.PLOTTING.WAVELENGTH_RANGE_MIN_NM,
        max_wavelength=config.PLOTTING.WAVELENGTH_RANGE_MAX_NM,
    )

    # Step 2: Apply smoothing if requested
    if apply_smoothing and smoothing_window > 1:
        smoothed_intensities = apply_fast_smoothing(cropped_int, smoothing_window)
    else:
        smoothed_intensities = cropped_int.copy()

    # Step 3: Decimate for display performance
    return decimate_spectral_data_for_display(
        cropped_wl, smoothed_intensities, display_width
    )


##
# @class OptimizedPygamePlotter
# @brief High-performance plotter with data decimation and numpy vectorization.
# @details Renders spectral data with axes, ticks, labels, and grid lines.
#          Uses pre-computed screen coordinates and separate static/plot surfaces for efficiency.
#          Handles NaN/inf values safely to prevent pygame rendering errors.
class OptimizedPygamePlotter:
    """High-performance plotter with data decimation and numpy vectorization."""

    ##
    # @brief Initializes the plotter with display parameters.
    # @param parent_surface Pygame surface to draw on.
    # @param plot_widget_rect Rectangle defining the plot area.
    # @param initial_x_data Optional initial wavelength data.
    # @param x_label_text X-axis label (default: "Wavelength (nm)").
    # @param y_label_text Y-axis label (default: "Intensity").
    # @param bg_color Background color (default: black).
    # @param axis_color Axis line color (default: gray).
    # @param plot_color Plot line color (default: cyan).
    # @param text_color Text color (default: white).
    # @param grid_color Grid line color (default: dark gray).
    # @param num_x_ticks Number of X-axis ticks (default: 5).
    # @param num_y_ticks Number of Y-axis ticks (default: 5).
    # @param target_display_points Maximum number of display points (default: 300).
    def __init__(
        self,
        parent_surface: pygame.Surface,
        plot_widget_rect: pygame.Rect,
        initial_x_data: np.ndarray | None = None,
        x_label_text: str = "Wavelength (nm)",
        y_label_text: str = "Intensity",
        bg_color: tuple[int, int, int] = (0, 0, 0),
        axis_color: tuple[int, int, int] = (128, 128, 128),
        plot_color: tuple[int, int, int] = (0, 255, 255),
        text_color: tuple[int, int, int] = (255, 255, 255),
        grid_color: tuple[int, int, int] = (40, 40, 40),
        num_x_ticks: int = 5,
        num_y_ticks: int = 5,
        target_display_points: int = 300,
    ):
        assert parent_surface is not None, "Parent surface cannot be None"
        assert plot_widget_rect is not None, "Plot rect cannot be None"
        assert pygame.font.get_init(), "Pygame font system not initialized"
        assert target_display_points > 10, "Target display points must be reasonable"

        ## @var parent_surface
        # @brief The pygame surface to draw the plot on.
        self.parent_surface = parent_surface

        ## @var plot_widget_rect
        # @brief Rectangle defining the plot area on the parent surface.
        self.plot_widget_rect = plot_widget_rect

        ## @var target_display_points
        # @brief Maximum number of points to display after decimation.
        self.target_display_points = target_display_points

        # Load fonts
        try:
            ## @var axis_label_font
            # @brief Font for axis labels.
            self.axis_label_font = pygame.font.Font(
                config.FONTS.PLOTTER_AXIS_LABEL, config.FONT_SIZES.PLOTTER_AXIS
            )
        except:
            self.axis_label_font = pygame.font.Font(
                None, config.FONT_SIZES.PLOTTER_AXIS
            )

        try:
            ## @var tick_label_font
            # @brief Font for tick labels.
            self.tick_label_font = pygame.font.Font(
                config.FONTS.PLOTTER_TICK_LABEL, config.FONT_SIZES.PLOTTER_TICK
            )
        except:
            self.tick_label_font = pygame.font.Font(
                None, config.FONT_SIZES.PLOTTER_TICK
            )

        ## @var x_label_text
        # @brief X-axis label text.
        self.x_label_text = x_label_text

        ## @var y_label_text
        # @brief Y-axis label text.
        self.y_label_text = y_label_text

        ## @var bg_color
        # @brief Background color of the plot.
        self.bg_color = bg_color

        ## @var axis_color
        # @brief Color of axis lines.
        self.axis_color = axis_color

        ## @var plot_color
        # @brief Color of the plot line.
        self.plot_color = plot_color

        ## @var text_color
        # @brief Color of text (labels and ticks).
        self.text_color = text_color

        ## @var grid_color
        # @brief Color of grid lines.
        self.grid_color = grid_color

        ## @var num_x_ticks
        # @brief Number of X-axis tick marks.
        self.num_x_ticks = max(0, num_x_ticks)

        ## @var num_y_ticks
        # @brief Number of Y-axis tick marks.
        self.num_y_ticks = max(0, num_y_ticks)

        ## @var y_tick_format_str
        # @brief Format string for Y-axis tick labels.
        self.y_tick_format_str = "{:.1f}"

        ## @var padding_left
        # @brief Left padding for axes and labels.
        self.padding_left = 60

        ## @var padding_right
        # @brief Right padding.
        self.padding_right = 20

        ## @var padding_top
        # @brief Top padding.
        self.padding_top = 20

        ## @var padding_bottom
        # @brief Bottom padding for X-axis label.
        self.padding_bottom = 50

        ## @var graph_area
        # @brief Rectangle defining the actual plotting area (inside padding).
        self.graph_area = pygame.Rect(
            self.plot_widget_rect.left + self.padding_left,
            self.plot_widget_rect.top + self.padding_top,
            max(
                20, self.plot_widget_rect.width - self.padding_left - self.padding_right
            ),
            max(
                20,
                self.plot_widget_rect.height - self.padding_top - self.padding_bottom,
            ),
        )

        ## @var original_x_data
        # @brief Original wavelength data before decimation.
        self.original_x_data: np.ndarray | None = None

        ## @var display_x_data
        # @brief Decimated wavelength data for display.
        self.display_x_data: np.ndarray | None = None

        ## @var display_y_data
        # @brief Decimated intensity data for display.
        self.display_y_data: np.ndarray | None = None

        ## @var screen_x_coords
        # @brief Pre-computed screen X coordinates for plotting.
        self.screen_x_coords: np.ndarray | None = None

        ## @var screen_y_coords
        # @brief Pre-computed screen Y coordinates for plotting.
        self.screen_y_coords: np.ndarray | None = None

        ## @var x_min_val
        # @brief Minimum X value for axis scaling.
        self.x_min_val = 0.0

        ## @var x_max_val
        # @brief Maximum X value for axis scaling.
        self.x_max_val = 1.0

        ## @var y_min_val_display
        # @brief Minimum Y value for display range.
        self.y_min_val_display = 0.0

        ## @var y_max_val_display
        # @brief Maximum Y value for display range.
        self.y_max_val_display = 1.0

        ## @var static_surface
        # @brief Surface for static elements (axes, labels, ticks, grid).
        self.static_surface = pygame.Surface(self.plot_widget_rect.size)

        ## @var plot_surface
        # @brief Transparent surface for the plot line (can be redrawn independently).
        self.plot_surface = pygame.Surface(self.plot_widget_rect.size, pygame.SRCALPHA)

        ## @var needs_static_redraw
        # @brief Flag indicating static elements need redrawing.
        self.needs_static_redraw = True

        ## @var needs_plot_redraw
        # @brief Flag indicating plot line needs redrawing.
        self.needs_plot_redraw = True

        if initial_x_data is not None and len(initial_x_data) > 0:
            self.set_x_data_static(initial_x_data)

        self._render_static_elements()

    ##
    # @brief Set wavelength data (X-axis) and compute display coordinates.
    # @param x_data Wavelength array.
    # @details Decimates data if needed and pre-computes screen coordinates.
    def set_x_data_static(self, x_data: np.ndarray):
        """Set wavelength data (X-axis) and compute display coordinates."""
        assert isinstance(x_data, np.ndarray) and x_data.ndim == 1 and len(x_data) > 0

        self.original_x_data = x_data.copy()

        # Decimate X data for display
        if len(x_data) > self.target_display_points:
            indices = np.linspace(
                0, len(x_data) - 1, self.target_display_points, dtype=int
            )
            self.display_x_data = x_data[indices].copy()
        else:
            self.display_x_data = x_data.copy()

        self.x_min_val = float(np.min(self.display_x_data))
        self.x_max_val = float(np.max(self.display_x_data))
        if self.x_max_val == self.x_min_val:
            self.x_max_val = self.x_min_val + 1.0

        self._precompute_screen_x_coordinates()
        self.needs_static_redraw = True

    ##
    # @brief Pre-compute X screen coordinates from wavelength data.
    # @details Handles NaN/inf values by filtering them out.
    def _precompute_screen_x_coordinates(self):
        """Pre-compute X coordinates with NaN handling."""
        if self.display_x_data is None or len(self.display_x_data) == 0:
            self.screen_x_coords = None
            return

        x_range = self.x_max_val - self.x_min_val
        if x_range <= config.DIVISION_EPSILON:
            x_range = 1.0

        # Ensure input data is finite
        valid_x_data = self.display_x_data[np.isfinite(self.display_x_data)]
        if len(valid_x_data) == 0:
            self.screen_x_coords = None
            return

        normalized_x = (valid_x_data - self.x_min_val) / x_range
        raw_coords = self.graph_area.left + normalized_x * self.graph_area.width

        # Store only finite coordinates
        self.screen_x_coords = raw_coords[np.isfinite(raw_coords)].astype(np.float32)
        if len(self.screen_x_coords) == 0:
            self.screen_x_coords = None

    ##
    # @brief Set intensity data (Y-axis) and compute display coordinates.
    # @param y_data Intensity array or None to clear.
    # @details Expects y_data to be pre-decimated to match display_x_data length.
    def set_y_data(self, y_data: np.ndarray | None):
        """Set intensity data (Y-axis) and compute display coordinates."""
        if y_data is None:
            self.display_y_data = None
            self.screen_y_coords = None
            self.needs_plot_redraw = True
            return

        assert isinstance(y_data, np.ndarray) and y_data.ndim == 1

        # Y data is expected to be already decimated to match display_x_data length
        if self.display_x_data is not None and len(y_data) == len(self.display_x_data):
            self.display_y_data = y_data.copy().astype(np.float32)
        elif len(y_data) == self.target_display_points:
            self.display_y_data = y_data.copy().astype(np.float32)
        else:
            # Fallback: resample if lengths don't match
            print(
                f"WARNING: Y_data length ({len(y_data)}) mismatch with display_x_data. Attempting to resample."
            )
            if self.display_x_data is not None and len(self.display_x_data) > 1:
                current_indices = np.linspace(0, 1, len(y_data))
                target_indices = np.linspace(0, 1, len(self.display_x_data))
                self.display_y_data = np.interp(
                    target_indices, current_indices, y_data
                ).astype(np.float32)
            else:
                self.display_y_data = None
                self.screen_y_coords = None
                self.needs_plot_redraw = True
                return

        self._precompute_screen_y_coordinates()
        self.needs_plot_redraw = True

    ##
    # @brief Pre-compute Y screen coordinates from intensity data.
    # @details Handles NaN/inf values and clamps to display range.
    def _precompute_screen_y_coordinates(self):
        """Pre-compute Y coordinates with NaN handling."""
        if self.display_y_data is None or len(self.display_y_data) == 0:
            self.screen_y_coords = None
            return

        y_range = self.y_max_val_display - self.y_min_val_display
        if y_range <= config.DIVISION_EPSILON:
            y_range = 1.0

        # Ensure input data is finite
        valid_y_data = self.display_y_data[np.isfinite(self.display_y_data)]
        if len(valid_y_data) == 0:
            self.screen_y_coords = None
            return

        clamped_y = np.clip(
            valid_y_data, self.y_min_val_display, self.y_max_val_display
        )
        normalized_y = (clamped_y - self.y_min_val_display) / y_range
        raw_coords = self.graph_area.bottom - normalized_y * self.graph_area.height

        # Store only finite coordinates
        self.screen_y_coords = raw_coords[np.isfinite(raw_coords)].astype(np.float32)
        if len(self.screen_y_coords) == 0:
            self.screen_y_coords = None

    ##
    # @brief Set Y-axis display limits.
    # @param y_min Minimum Y value.
    # @param y_max Maximum Y value.
    def set_y_limits(self, y_min: float, y_max: float):
        """Set Y-axis display limits."""
        assert isinstance(y_min, (int, float)) and isinstance(y_max, (int, float))

        y_min_f, y_max_f = float(y_min), float(y_max)

        if y_max_f == y_min_f:
            y_max_f = y_min_f + 1.0
        if y_max_f < y_min_f:
            y_min_f, y_max_f = y_max_f, y_min_f

        if self.y_min_val_display != y_min_f or self.y_max_val_display != y_max_f:
            self.y_min_val_display = y_min_f
            self.y_max_val_display = y_max_f

            if self.display_y_data is not None:
                self._precompute_screen_y_coordinates()

            self.needs_static_redraw = True
            self.needs_plot_redraw = True

    ##
    # @brief Set Y-axis label text.
    # @param label New label text.
    def set_y_label(self, label: str):
        """Set Y-axis label text."""
        assert isinstance(label, str)
        if self.y_label_text != label:
            self.y_label_text = label
            self.needs_static_redraw = True

    ##
    # @brief Set Y-axis tick format string.
    # @param format_str Format string (e.g., "{:.1f}").
    def set_y_tick_format(self, format_str: str):
        """Set Y-axis tick format string."""
        assert isinstance(format_str, str)
        if self.y_tick_format_str != format_str:
            self.y_tick_format_str = format_str
            self.needs_static_redraw = True

    ##
    # @brief Render static plot elements (axes, labels, ticks, grid).
    # @details Only redraws if needs_static_redraw flag is set.
    def _render_static_elements(self):
        """Render static plot elements (axes, labels, ticks, grid)."""
        if not self.needs_static_redraw:
            return

        self.static_surface.fill(self.bg_color)

        if not self.axis_label_font or not self.tick_label_font:
            self.needs_static_redraw = False
            return

        graph_left = self.graph_area.left - self.plot_widget_rect.left
        graph_right = self.graph_area.right - self.plot_widget_rect.left
        graph_top = self.graph_area.top - self.plot_widget_rect.top
        graph_bottom = self.graph_area.bottom - self.plot_widget_rect.top

        # Draw axes
        pygame.draw.line(
            self.static_surface,
            self.axis_color,
            (graph_left, graph_bottom),
            (graph_right, graph_bottom),
            1,
        )
        pygame.draw.line(
            self.static_surface,
            self.axis_color,
            (graph_left, graph_top),
            (graph_left, graph_bottom),
            1,
        )

        # Draw X-axis ticks and labels
        if (
            self.num_x_ticks > 0
            and self.x_max_val > self.x_min_val
            and self.display_x_data is not None
        ):
            x_tick_values = np.linspace(
                self.x_min_val, self.x_max_val, self.num_x_ticks + 1
            )
            for val in x_tick_values:
                x_pos = graph_left + (val - self.x_min_val) / (
                    self.x_max_val - self.x_min_val
                ) * (graph_right - graph_left)
                pygame.draw.line(
                    self.static_surface,
                    self.axis_color,
                    (x_pos, graph_bottom),
                    (x_pos, graph_bottom + 5),
                    1,
                )
                try:
                    label_surf = self.tick_label_font.render(
                        f"{val:.0f}", True, self.text_color
                    )
                    label_rect = label_surf.get_rect(
                        centerx=x_pos, top=graph_bottom + 7
                    )
                    self.static_surface.blit(label_surf, label_rect)
                except pygame.error:
                    pass

        # Draw Y-axis ticks, labels, and grid
        if self.num_y_ticks > 0 and self.y_max_val_display > self.y_min_val_display:
            y_tick_values = np.linspace(
                self.y_min_val_display, self.y_max_val_display, self.num_y_ticks + 1
            )
            for val in y_tick_values:
                y_pos = graph_bottom - (val - self.y_min_val_display) / (
                    self.y_max_val_display - self.y_min_val_display
                ) * (graph_bottom - graph_top)
                pygame.draw.line(
                    self.static_surface,
                    self.axis_color,
                    (graph_left - 5, y_pos),
                    (graph_left, y_pos),
                    1,
                )
                pygame.draw.line(
                    self.static_surface,
                    self.grid_color,
                    (graph_left + 1, y_pos),
                    (graph_right, y_pos),
                    1,
                )
                try:
                    label_str = self.y_tick_format_str.format(val)
                    label_surf = self.tick_label_font.render(
                        label_str, True, self.text_color
                    )
                    label_rect = label_surf.get_rect(
                        right=graph_left - 7, centery=y_pos
                    )
                    self.static_surface.blit(label_surf, label_rect)
                except (pygame.error, ValueError):
                    pass

        # Draw X-axis label
        if self.x_label_text:
            try:
                x_label_surf = self.axis_label_font.render(
                    self.x_label_text, True, self.text_color
                )
                x_label_rect = x_label_surf.get_rect(
                    centerx=(graph_left + graph_right) // 2, top=graph_bottom + 25
                )
                self.static_surface.blit(x_label_surf, x_label_rect)
            except pygame.error:
                pass

        # Draw Y-axis label (rotated)
        if self.y_label_text:
            try:
                y_label_surf = self.axis_label_font.render(
                    self.y_label_text, True, self.text_color
                )
                y_label_rotated = pygame.transform.rotate(y_label_surf, 90)
                y_label_rect = y_label_rotated.get_rect(
                    centerx=15, centery=(graph_top + graph_bottom) // 2
                )
                self.static_surface.blit(y_label_rotated, y_label_rect)
            except pygame.error:
                pass

        self.needs_static_redraw = False

    ##
    # @brief Render the plot line.
    # @details Only redraws if needs_plot_redraw flag is set. Handles NaN/inf safely.
    def _render_plot_line(self):
        """Render spectral data line with proper NaN/inf handling."""
        if not self.needs_plot_redraw:
            return

        self.plot_surface.fill((0, 0, 0, 0))  # Clear previous plot line

        # Check if we have valid coordinate arrays
        if (
            self.screen_x_coords is None
            or self.screen_y_coords is None
            or len(self.screen_x_coords) < 2
            or len(self.screen_y_coords) < 2
            or len(self.screen_x_coords) != len(self.screen_y_coords)
        ):
            self.needs_plot_redraw = False
            return

        # Convert coordinates relative to the plot_widget_rect
        plot_x_coords = self.screen_x_coords - self.plot_widget_rect.left
        plot_y_coords = self.screen_y_coords - self.plot_widget_rect.top

        try:
            # Filter out NaN and infinite values before pygame
            finite_mask = np.isfinite(plot_x_coords) & np.isfinite(plot_y_coords)
            if not np.any(finite_mask):  # No valid points
                self.needs_plot_redraw = False
                return

            valid_x = plot_x_coords[finite_mask]
            valid_y = plot_y_coords[finite_mask]

            if len(valid_x) < 2:  # Need at least 2 points to draw lines
                self.needs_plot_redraw = False
                return

            # Create point list with guaranteed finite values
            points_array = np.column_stack((valid_x, valid_y))
            point_list = [(float(x), float(y)) for x, y in points_array]

            if len(point_list) > 1:
                # Set clipping rectangle
                clip_rect = pygame.Rect(
                    self.graph_area.left - self.plot_widget_rect.left,
                    self.graph_area.top - self.plot_widget_rect.top,
                    self.graph_area.width,
                    self.graph_area.height,
                )
                self.plot_surface.set_clip(clip_rect)

                # Draw the lines
                pygame.draw.lines(
                    self.plot_surface, self.plot_color, False, point_list, 1
                )

                self.plot_surface.set_clip(None)  # Reset clipping

        except Exception as e:
            print(f"ERROR: Error rendering plot line: {e}")

        self.needs_plot_redraw = False

    ##
    # @brief Draw the complete plot to the parent surface.
    # @details Renders both static elements and plot line.
    def draw(self):
        """Draw the complete plot to the parent surface."""
        self._render_static_elements()
        self._render_plot_line()
        self.parent_surface.blit(self.static_surface, self.plot_widget_rect.topleft)
        self.parent_surface.blit(self.plot_surface, self.plot_widget_rect.topleft)

    ##
    # @brief Get performance statistics.
    # @return Dictionary with performance metrics.
    def get_performance_stats(self) -> dict:
        """Get performance statistics."""
        stats = {
            "original_data_points": (
                len(self.original_x_data) if self.original_x_data is not None else 0
            ),
            "display_data_points": (
                len(self.display_x_data) if self.display_x_data is not None else 0
            ),
            "decimation_ratio": 0.0,
            "memory_usage_mb": 0.0,
        }
        if stats["original_data_points"] > 0 and stats["display_data_points"] > 0:
            stats["decimation_ratio"] = (
                stats["display_data_points"] / stats["original_data_points"]
            )

        arrays_to_check = [
            self.original_x_data,
            self.display_x_data,
            self.display_y_data,
            self.screen_x_coords,
            self.screen_y_coords,
        ]
        total_bytes = sum(
            arr.nbytes
            for arr in arrays_to_check
            if arr is not None and hasattr(arr, "nbytes")
        )
        stats["memory_usage_mb"] = total_bytes / (1024 * 1024)
        return stats

    ##
    # @brief Clear all data from the plotter.
    def clear_data(self):
        """Clear all data from the plotter."""
        self.original_x_data = None
        self.display_x_data = None
        self.display_y_data = None
        self.screen_x_coords = None
        self.screen_y_coords = None
        self.needs_plot_redraw = True


##
# @class FastSpectralRenderer
# @brief Ultra-fast spectral renderer with caching and performance monitoring.
# @details Wraps OptimizedPygamePlotter with additional caching and data preparation pipeline.
#          Monitors rendering performance (FPS, frame times).
class FastSpectralRenderer:
    """Ultra-fast spectral renderer with caching and performance monitoring."""

    ##
    # @brief Initialize the renderer.
    # @param parent_surface Pygame surface to draw on.
    # @param plot_rect Rectangle defining the plot area.
    # @param target_fps Target frames per second (default: 30).
    # @param max_display_points Maximum number of display points (default: 300).
    def __init__(
        self,
        parent_surface: pygame.Surface,
        plot_rect: pygame.Rect,
        target_fps: int = 30,
        max_display_points: int = 300,
    ):
        assert parent_surface is not None, "Parent surface required"
        assert plot_rect is not None, "Plot rectangle required"
        assert target_fps > 0, "Target FPS must be positive"
        assert max_display_points > 10, "Display points must be reasonable"

        ## @var plotter
        # @brief The underlying OptimizedPygamePlotter instance.
        self.plotter = OptimizedPygamePlotter(
            parent_surface=parent_surface,
            plot_widget_rect=plot_rect,
            target_display_points=max_display_points,
        )

        ## @var max_display_points
        # @brief Maximum number of points to display.
        self.max_display_points = max_display_points

        ## @var _last_raw_data_hash
        # @brief MD5 hash of last raw data for cache validation.
        self._last_raw_data_hash: str | None = None

        ## @var _cached_display_data
        # @brief Cached processed display data.
        self._cached_display_data: np.ndarray | None = None

        ## @var smoothing_enabled
        # @brief Whether smoothing is enabled.
        self.smoothing_enabled = True

        ## @var smoothing_window
        # @brief Smoothing window size.
        self.smoothing_window = 5

        ## @var frame_times
        # @brief List of recent frame times for FPS calculation.
        self.frame_times: list[float] = []

    ##
    # @brief Set wavelength data with validation.
    # @param wavelengths Wavelength array.
    def set_wavelengths(self, wavelengths):
        """Set wavelength data with validation."""
        assert isinstance(wavelengths, np.ndarray), "Wavelengths must be numpy array"
        assert len(wavelengths) > 0, "Wavelengths cannot be empty"

        # Clear cache when wavelengths change
        self._last_raw_data_hash = None
        self._cached_display_data = None

        # Set wavelengths on plotter
        self.plotter.set_x_data_static(wavelengths)

    ##
    # @brief Update spectrum with new intensity data.
    # @param intensities Intensity array.
    # @param apply_smoothing Whether to apply smoothing (default: True).
    # @param force_update Force update even if data hash matches (default: False).
    # @return True if update successful, False otherwise.
    def update_spectrum(
        self,
        intensities: np.ndarray,
        apply_smoothing: bool = True,
        force_update: bool = False,
    ) -> bool:
        """Update spectrum with new intensity data."""
        frame_start_time = time.perf_counter()

        if self.plotter.original_x_data is None:
            print("WARNING: No wavelengths set, cannot update spectrum")
            return False

        if not force_update:
            data_hash = hashlib.md5(intensities.tobytes()).hexdigest()
            if (
                data_hash == self._last_raw_data_hash
                and self._cached_display_data is not None
            ):
                self.plotter.set_y_data(self._cached_display_data)
                return True
            self._last_raw_data_hash = data_hash

        try:
            original_wavelengths = self.plotter.original_x_data
            if original_wavelengths is None:
                print(
                    "WARNING: original_x_data not set in plotter. Cannot update spectrum."
                )
                return False

            # Verify array lengths match
            if len(original_wavelengths) != len(intensities):
                print(
                    f"ERROR: Wavelength/intensity length mismatch! "
                    f"wavelengths={len(original_wavelengths)}, intensities={len(intensities)}"
                )
                return False

            # Use the global prepare_display_data function
            display_wavelengths, display_intensities = prepare_display_data(
                wavelengths=original_wavelengths,
                intensities=intensities,
                display_width=self.max_display_points,
                apply_smoothing=apply_smoothing and self.smoothing_enabled,
                smoothing_window=self.smoothing_window,
            )

            self._cached_display_data = display_intensities.copy()

            # Update plotter display wavelengths if they changed (WITHOUT overwriting original_x_data)
            current_plotter_wl = self.plotter.display_x_data
            if current_plotter_wl is None or not np.array_equal(
                current_plotter_wl, display_wavelengths
            ):
                # Directly update display_x_data without touching original_x_data
                self.plotter.display_x_data = display_wavelengths.copy()
                self.plotter.x_min_val = float(np.min(display_wavelengths))
                self.plotter.x_max_val = float(np.max(display_wavelengths))
                if self.plotter.x_max_val == self.plotter.x_min_val:
                    self.plotter.x_max_val = self.plotter.x_min_val + 1.0
                self.plotter._precompute_screen_x_coordinates()
                self.plotter.needs_static_redraw = True

            # Set the cropped intensity data
            self.plotter.set_y_data(display_intensities)

            frame_time = time.perf_counter() - frame_start_time
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 100:
                self.frame_times = self.frame_times[-100:]

            return True

        except Exception as e:
            print(f"ERROR: FastSpectralRenderer error during update_spectrum: {e}")
            return False

    ##
    # @brief Draw the spectrum plot.
    def draw(self):
        """Draw the spectrum plot."""
        self.plotter.draw()

    ##
    # @brief Set Y-axis limits.
    # @param y_min Minimum Y value.
    # @param y_max Maximum Y value.
    def set_y_limits(self, y_min: float, y_max: float):
        """Set Y-axis limits."""
        self.plotter.set_y_limits(y_min, y_max)

    ##
    # @brief Set Y-axis label.
    # @param label Label text.
    def set_y_label(self, label: str):
        """Set Y-axis label."""
        self.plotter.set_y_label(label)

    ##
    # @brief Set Y-axis tick format.
    # @param format_str Format string.
    def set_y_tick_format(self, format_str: str):
        """Set Y-axis tick format."""
        self.plotter.set_y_tick_format(format_str)

    ##
    # @brief Get performance information.
    # @return Dictionary with performance metrics or None if no data.
    def get_performance_info(self) -> dict | None:
        """Get performance information."""
        plotter_stats = self.plotter.get_performance_stats()

        if not self.frame_times:
            return plotter_stats

        avg_frame_time = np.mean(self.frame_times) if self.frame_times else 0
        max_frame_time = np.max(self.frame_times) if self.frame_times else 0
        estimated_fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0

        plotter_stats.update(
            {
                "avg_frame_time_ms": avg_frame_time * 1000,
                "max_frame_time_ms": max_frame_time * 1000,
                "estimated_fps": estimated_fps,
            }
        )
        return plotter_stats

    ##
    # @brief Configure smoothing parameters.
    # @param enabled Whether smoothing is enabled (default: True).
    # @param window_size Smoothing window size (default: 5).
    def configure_smoothing(self, enabled: bool = True, window_size: int = 5):
        """Configure smoothing parameters."""
        assert isinstance(enabled, bool), "Enabled must be boolean"
        assert (
            isinstance(window_size, int) and window_size > 0
        ), "Window size must be positive integer"

        self.smoothing_enabled = enabled
        self.smoothing_window = window_size

        self._last_raw_data_hash = None  # Invalidate cache
        self._cached_display_data = None
        print(
            f"INFO: FastSpectralRenderer smoothing configured: enabled={enabled}, window={window_size}"
        )
