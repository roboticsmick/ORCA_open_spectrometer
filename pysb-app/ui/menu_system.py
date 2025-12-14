# pysb-app/ui/menu_system.py

import pygame
import datetime
import calendar
import config
from ui import display_utils


##
# @class MenuSystem
# @brief Manages and renders the main menu, handling navigation and settings changes.
# @details This class provides a menu interface for configuring spectrometer settings
#          and starting data capture. It supports keyboard and GPIO button navigation,
#          displays network status, signals when reference captures are needed, and
#          allows field-by-field date/time editing with offset tracking.
class MenuSystem:
    """Manages and draws the main menu, handling navigation and settings changes."""

    # Field constants for date/time editing
    FIELD_YEAR, FIELD_MONTH, FIELD_DAY = "year", "month", "day"
    FIELD_HOUR, FIELD_MINUTE = "hour", "minute"

    # Field constants for wavelength range editing
    FIELD_WL_MIN, FIELD_WL_MAX = "wl_min", "wl_max"

    ##
    # @brief Initializes the MenuSystem.
    # @param screen The Pygame surface to draw on.
    # @param button_handler The ButtonHandler instance for processing user input.
    # @param settings The SpectrometerSettings dataclass instance to modify.
    # @param network_info The NetworkInfo instance for displaying network status.
    # @param temp_sensor Optional TempSensorInfo instance for temperature display and fan control.
    # @details Sets up fonts, menu structure, and initializes flags for reference captures.
    def __init__(
        self, screen, button_handler, settings, network_info, temp_sensor=None
    ):
        assert screen is not None, "screen parameter cannot be None"
        assert button_handler is not None, "button_handler parameter cannot be None"
        assert settings is not None, "settings parameter cannot be None"
        assert network_info is not None, "network_info parameter cannot be None"

        ## @var screen
        # @brief The Pygame surface for rendering the menu.
        self.screen = screen

        ## @var button_handler
        # @brief ButtonHandler instance for input processing.
        self.button_handler = button_handler

        ## @var settings
        # @brief SpectrometerSettings dataclass holding current configuration.
        self.settings = settings

        ## @var network_info
        # @brief NetworkInfo instance for network status display.
        self.network_info = network_info

        ## @var temp_sensor
        # @brief TempSensorInfo instance for temperature display and fan control (can be None).
        self.temp_sensor = temp_sensor

        ## @var font_title
        # @brief Font for the menu title.
        try:
            self.font_title = pygame.font.Font(
                config.FONTS.TITLE, config.FONT_SIZES.TITLE
            )
        except:
            self.font_title = pygame.font.Font(None, config.FONT_SIZES.TITLE)

        ## @var font_item
        # @brief Font for menu item labels.
        try:
            self.font_item = pygame.font.Font(
                config.FONTS.MAIN, config.FONT_SIZES.MENU_ITEM
            )
        except:
            self.font_item = pygame.font.Font(None, config.FONT_SIZES.MENU_ITEM)

        ## @var font_value
        # @brief Font for menu item values (same as font_item).
        self.font_value = self.font_item

        ## @var font_info
        # @brief Font for network information display.
        try:
            self.font_info = pygame.font.Font(config.FONTS.MAIN, config.FONT_SIZES.INFO)
        except:
            self.font_info = pygame.font.Font(None, config.FONT_SIZES.INFO)

        ## @var _menu_items
        # @brief List of menu item dictionaries defining structure and behavior.
        self._menu_items = []

        ## @var _selected_index
        # @brief Index of the currently selected menu item.
        self._selected_index = 0

        ## @var _edit_mode
        # @brief Boolean indicating if a value is being edited.
        self._edit_mode = False

        ## @var dark_reference_required
        # @brief Flag to signal that a dark reference capture is needed.
        self.dark_reference_required = False

        ## @var white_reference_required
        # @brief Flag to signal that a white reference capture is needed.
        self.white_reference_required = False

        ## @var _time_offset
        # @brief Time offset (timedelta) applied to system time for display and CSV timestamps.
        self._time_offset = datetime.timedelta(0)

        ## @var _original_offset_on_edit_start
        # @brief Backup of time offset when entering date/time edit mode (for cancel operation).
        self._original_offset_on_edit_start = None

        ## @var _datetime_being_edited
        # @brief Temporary datetime object being edited (None when not editing date/time).
        self._datetime_being_edited = None

        ## @var _editing_field
        # @brief Currently selected field when editing date/time or wavelength range.
        self._editing_field = None

        ## @var _wavelength_range_editing
        # @brief Temporary wavelength range values being edited [min, max].
        self._wavelength_range_editing = None

        ## @var _original_wavelength_range
        # @brief Backup of wavelength range when entering edit mode (for cancel operation).
        self._original_wavelength_range = None

        self._build_menu_items()

    ##
    # @brief Defines the structure and content of the menu items.
    # @details Creates a list of menu item dictionaries with types: "action", "numeric", "choice", "datetime", "info".
    #          Datetime item supports field-by-field editing (year/month/day/hour/minute).
    #          Info items are read-only display items (WiFi, IP).
    def _build_menu_items(self):
        """Defines the structure of the menu."""
        self._menu_items = [
            {"label": "Start Capture", "type": "action", "action": "START_CAPTURE"},
            {
                "label": "Integration Time (ms)",
                "type": "numeric",
                "value_key": "integration_time_ms",
                "min": config.SPECTROMETER.MIN_INTEGRATION_TIME_MS,
                "max": config.SPECTROMETER.MAX_INTEGRATION_TIME_MS,
                "step": config.SPECTROMETER.INTEGRATION_TIME_STEP_MS,
            },
            {
                "label": "Collection Mode",
                "type": "choice",
                "value_key": "collection_mode",
                "choices": ["RAW", "REFLECTANCE"],
            },
            {
                "label": "Scans to Average",
                "type": "numeric",
                "value_key": "scans_to_average",
                "min": config.SPECTROMETER.MIN_SCANS_TO_AVERAGE,
                "max": config.SPECTROMETER.MAX_SCANS_TO_AVERAGE,
                "step": config.SPECTROMETER.SCANS_TO_AVERAGE_STEP,
            },
            {"label": "Plot range", "type": "wavelength_range"},
            {"label": "Fan", "type": "fan_threshold"},
            {"label": "Date", "type": "datetime"},
            {"label": "WiFi", "type": "info", "display": "wifi"},
            {"label": "IP", "type": "info", "display": "ip"},
        ]
        assert len(self._menu_items) > 0, "Menu must have at least one item"

    ##
    # @brief Processes button presses and updates the menu state.
    # @return Action string ("START_CAPTURE", "QUIT") or None if no action taken.
    # @details Handles navigation (UP/DOWN), value editing (UP/DOWN when in edit mode), and ENTER confirmation.
    #          With only 4 physical buttons, UP/DOWN serve dual purpose: navigation when not editing,
    #          value adjustment when editing.
    def handle_input(self):
        """Processes button presses and updates the menu state. Returns any action."""
        action = None

        if self.button_handler.get_pressed(config.BTN_UP):
            if self._edit_mode:
                # In edit mode: UP adjusts value up
                selected_item = self._menu_items[self._selected_index]
                if selected_item.get("type") == "datetime":
                    self._change_datetime_field(1)
                elif selected_item.get("type") == "wavelength_range":
                    self._change_wavelength_field(1)
                else:
                    self._change_value(1)
            else:
                # Navigation mode: UP moves selection up
                self._selected_index = (self._selected_index - 1) % len(
                    self._menu_items
                )

        elif self.button_handler.get_pressed(config.BTN_DOWN):
            if self._edit_mode:
                # In edit mode: DOWN adjusts value down
                selected_item = self._menu_items[self._selected_index]
                if selected_item.get("type") == "datetime":
                    self._change_datetime_field(-1)
                elif selected_item.get("type") == "wavelength_range":
                    self._change_wavelength_field(-1)
                else:
                    self._change_value(-1)
            else:
                # Navigation mode: DOWN moves selection down
                self._selected_index = (self._selected_index + 1) % len(
                    self._menu_items
                )

        elif self.button_handler.get_pressed(config.BTN_ENTER):
            selected_item = self._menu_items[self._selected_index]
            item_type = selected_item.get("type")

            if item_type == "action":
                return selected_item.get("action")  # e.g., "START_CAPTURE"
            elif item_type in ["numeric", "choice", "fan_threshold"]:
                self._edit_mode = not self._edit_mode  # Toggle edit mode
            elif item_type == "datetime":
                if not self._edit_mode:
                    # Entering edit mode for datetime
                    self._enter_datetime_edit_mode(selected_item)
                else:
                    # Already in edit mode - advance to next field or save
                    if self._advance_datetime_field(selected_item):
                        # All fields complete - save and exit
                        self._commit_time_offset_changes()
                        self._edit_mode = False
                        self._datetime_being_edited = None
                        self._editing_field = None
            elif item_type == "wavelength_range":
                if not self._edit_mode:
                    # Entering edit mode for wavelength range
                    self._enter_wavelength_range_edit_mode()
                else:
                    # Already in edit mode - advance to next field or save
                    if self._advance_wavelength_field():
                        # All fields complete - save and exit
                        self._commit_wavelength_range_changes()
                        self._edit_mode = False
                        self._wavelength_range_editing = None
                        self._editing_field = None

        elif self.button_handler.get_pressed(config.BTN_BACK):
            if self._edit_mode:
                # Exit edit mode
                selected_item = self._menu_items[self._selected_index]
                if selected_item.get("type") == "datetime":
                    # Restore original time offset (cancel changes)
                    if self._original_offset_on_edit_start is not None:
                        self._time_offset = self._original_offset_on_edit_start
                    self._datetime_being_edited = None
                    self._editing_field = None
                elif selected_item.get("type") == "wavelength_range":
                    # Restore original wavelength range (cancel changes)
                    if self._original_wavelength_range is not None:
                        config.PLOTTING.WAVELENGTH_RANGE_MIN_NM = (
                            self._original_wavelength_range[0]
                        )
                        config.PLOTTING.WAVELENGTH_RANGE_MAX_NM = (
                            self._original_wavelength_range[1]
                        )
                    self._wavelength_range_editing = None
                    self._editing_field = None
                self._edit_mode = False

        return action

    ##
    # @brief Changes the value of the currently selected setting.
    # @param direction Integer indicating direction of change (-1 for left/down, +1 for right/up).
    # @details Sets reference_required flags when settings change. Handles numeric and choice types.
    def _change_value(self, direction):
        """Changes the value of the currently selected setting."""
        assert isinstance(direction, int), "direction must be an integer"
        assert direction in (-1, 1), "direction must be -1 or 1"

        selected_item = self._menu_items[self._selected_index]
        item_type = selected_item.get("type")
        key = selected_item.get("value_key")

        # A setting was changed, so references are now invalid (for spectrometer settings).
        # Fan threshold changes do not affect spectrometer references.
        if item_type != "fan_threshold":
            self.dark_reference_required = True
            self.white_reference_required = True

        if item_type == "numeric":
            current_val = getattr(self.settings, key)
            step = selected_item["step"]
            new_val = current_val + (step * direction)
            new_val = max(selected_item["min"], min(selected_item["max"], new_val))
            setattr(self.settings, key, new_val)

        elif item_type == "choice":
            choices = selected_item["choices"]
            current_val = getattr(self.settings, key)
            try:
                current_idx = choices.index(current_val)
                new_idx = (current_idx + direction) % len(choices)
                setattr(self.settings, key, choices[new_idx])
            except ValueError:
                setattr(self.settings, key, choices[0])

        elif item_type == "fan_threshold":
            # Adjust fan threshold via temp_sensor
            if self.temp_sensor is not None:
                current_threshold = self.temp_sensor.get_fan_threshold_c()
                step = config.FAN_THRESHOLD_STEP_C
                new_threshold = current_threshold + (step * direction)
                new_threshold = max(
                    config.FAN_THRESHOLD_MIN_C,
                    min(config.FAN_THRESHOLD_MAX_C, new_threshold),
                )
                self.temp_sensor.set_fan_threshold_c(new_threshold)

    ##
    # @brief Gets the current display time with applied time offset.
    # @return datetime.datetime object with offset applied.
    # @details This method should be used for all time displays and CSV timestamps.
    def get_current_display_time(self):
        """Returns the current time with the time offset applied."""
        assert isinstance(
            self._time_offset, datetime.timedelta
        ), "Time offset must be a timedelta"
        try:
            return datetime.datetime.now() + self._time_offset
        except OverflowError:
            print("WARNING: Time offset overflow. Resetting to zero.")
            self._time_offset = datetime.timedelta(0)
            return datetime.datetime.now()

    ##
    # @brief Enters edit mode for date/time fields.
    # @param item Menu item dictionary for the datetime field being edited.
    # @details Saves the current time offset and initializes editing state.
    #          Always starts with FIELD_YEAR for the combined datetime item.
    def _enter_datetime_edit_mode(self, item):
        """Enters datetime edit mode, saving current offset and setting initial field."""
        assert item.get("type") == "datetime", "Item must be datetime type"

        self._edit_mode = True
        self._original_offset_on_edit_start = self._time_offset
        self._datetime_being_edited = self.get_current_display_time()

        # Combined datetime item always starts with year
        self._editing_field = self.FIELD_YEAR

    ##
    # @brief Advances to the next field in date/time editing.
    # @param item Menu item dictionary for the datetime field being edited.
    # @return True if all fields are complete (ready to save), False otherwise.
    # @details Handles all 5 fields in sequence: year → month → day → hour → minute.
    def _advance_datetime_field(self, item):
        """Advances to the next field in datetime editing. Returns True if complete."""
        assert item.get("type") == "datetime", "Item must be datetime type"
        assert self._editing_field is not None, "Editing field must be set"

        # Combined datetime: year → month → day → hour → minute
        if self._editing_field == self.FIELD_YEAR:
            self._editing_field = self.FIELD_MONTH
            return False
        elif self._editing_field == self.FIELD_MONTH:
            self._editing_field = self.FIELD_DAY
            return False
        elif self._editing_field == self.FIELD_DAY:
            self._editing_field = self.FIELD_HOUR
            return False
        elif self._editing_field == self.FIELD_HOUR:
            self._editing_field = self.FIELD_MINUTE
            return False
        elif self._editing_field == self.FIELD_MINUTE:
            return True  # Complete

        return False

    ##
    # @brief Changes the value of the currently selected datetime field.
    # @param delta Integer indicating direction of change (-1 for decrease, +1 for increase).
    def _change_datetime_field(self, delta):
        """Changes the value of the currently selected datetime field."""
        assert isinstance(delta, int) and delta in (-1, 1), "Delta must be -1 or 1"
        assert self._datetime_being_edited is not None, "No datetime being edited"
        assert self._editing_field is not None, "No field selected"

        if self._editing_field in [self.FIELD_YEAR, self.FIELD_MONTH, self.FIELD_DAY]:
            self._change_date_field(delta)
        elif self._editing_field in [self.FIELD_HOUR, self.FIELD_MINUTE]:
            self._change_time_field(delta)

    ##
    # @brief Changes a date field (year, month, or day).
    # @param delta Integer indicating direction of change (-1 for decrease, +1 for increase).
    def _change_date_field(self, delta):
        """Changes the selected date field (year, month, or day)."""
        assert self._datetime_being_edited is not None
        assert self._editing_field in [
            self.FIELD_YEAR,
            self.FIELD_MONTH,
            self.FIELD_DAY,
        ]
        assert delta in [-1, 1]

        dt = self._datetime_being_edited
        y, m, d = dt.year, dt.month, dt.day

        if self._editing_field == self.FIELD_YEAR:
            y = max(1970, min(2100, y + delta))
        elif self._editing_field == self.FIELD_MONTH:
            m = (m - 1 + delta + 12) % 12 + 1
        elif self._editing_field == self.FIELD_DAY:
            max_d = calendar.monthrange(y, m)[1]
            d = (d - 1 + delta + max_d) % max_d + 1

        new_dt = self._get_safe_datetime(y, m, d, dt.hour, dt.minute, dt.second)
        if new_dt:
            self._datetime_being_edited = new_dt

    ##
    # @brief Changes a time field (hour or minute).
    # @param delta Integer indicating direction of change (-1 for decrease, +1 for increase).
    def _change_time_field(self, delta):
        """Changes the selected time field (hour or minute)."""
        assert self._datetime_being_edited is not None
        assert self._editing_field in [self.FIELD_HOUR, self.FIELD_MINUTE]
        assert delta in [-1, 1]

        td = datetime.timedelta(
            hours=delta if self._editing_field == self.FIELD_HOUR else 0,
            minutes=delta if self._editing_field == self.FIELD_MINUTE else 0,
        )
        try:
            self._datetime_being_edited += td
        except OverflowError:
            print("WARNING: Time field change overflowed.")

    ##
    # @brief Commits the edited datetime by calculating and saving the new time offset.
    def _commit_time_offset_changes(self):
        """Commits the edited datetime by updating the time offset."""
        assert self._datetime_being_edited is not None, "No datetime to commit"
        try:
            self._time_offset = self._datetime_being_edited - datetime.datetime.now()
            print(f"INFO: Time offset updated to {self._time_offset}")
        except Exception as e:
            print(f"ERROR: Failed to commit time offset: {e}")

    ##
    # @brief Safely creates a datetime object with validation.
    # @param year Year value (1970-2100).
    # @param month Month value (1-12).
    # @param day Day value (1-31).
    # @param hour Hour value (0-23).
    # @param minute Minute value (0-59).
    # @param second Second value (0-59).
    # @return datetime.datetime object or None if invalid.
    @staticmethod
    def _get_safe_datetime(year, month, day, hour=0, minute=0, second=0):
        """Safely creates a datetime object, returning None if invalid."""
        assert all(isinstance(v, int) for v in [year, month, day, hour, minute, second])
        try:
            return datetime.datetime(
                year, max(1, min(12, month)), day, hour, minute, second
            )
        except ValueError as e:
            print(
                f"WARNING: Invalid datetime: Y{year}-M{month}-D{day} H{hour}:M{minute}:S{second}. {e}"
            )
            return None

    ##
    # @brief Enters edit mode for wavelength range fields.
    # @details Saves the current wavelength range and initializes editing state.
    #          Always starts with FIELD_WL_MIN.
    def _enter_wavelength_range_edit_mode(self):
        """Enters wavelength range edit mode, saving current values and setting initial field."""
        self._edit_mode = True
        self._original_wavelength_range = [
            config.PLOTTING.WAVELENGTH_RANGE_MIN_NM,
            config.PLOTTING.WAVELENGTH_RANGE_MAX_NM,
        ]
        self._wavelength_range_editing = [
            config.PLOTTING.WAVELENGTH_RANGE_MIN_NM,
            config.PLOTTING.WAVELENGTH_RANGE_MAX_NM,
        ]
        self._editing_field = self.FIELD_WL_MIN

    ##
    # @brief Advances to the next field in wavelength range editing.
    # @return True if all fields are complete (ready to save), False otherwise.
    def _advance_wavelength_field(self):
        """Advances to the next field in wavelength range editing. Returns True if complete."""
        assert self._editing_field is not None, "Editing field must be set"

        if self._editing_field == self.FIELD_WL_MIN:
            self._editing_field = self.FIELD_WL_MAX
            return False
        elif self._editing_field == self.FIELD_WL_MAX:
            return True  # Complete

        return False

    ##
    # @brief Changes the value of the currently selected wavelength range field.
    # @param delta Integer indicating direction of change (-1 for decrease, +1 for increase).
    # @details Enforces min/max limits and minimum gap between min and max values.
    def _change_wavelength_field(self, delta):
        """Changes the value of the currently selected wavelength range field."""
        assert isinstance(delta, int) and delta in (-1, 1), "Delta must be -1 or 1"
        assert (
            self._wavelength_range_editing is not None
        ), "No wavelength range being edited"
        assert self._editing_field is not None, "No field selected"

        step = config.PLOTTING.WAVELENGTH_EDIT_STEP_NM
        min_limit = config.PLOTTING.WAVELENGTH_EDIT_MIN_LIMIT_NM
        max_limit = config.PLOTTING.WAVELENGTH_EDIT_MAX_LIMIT_NM
        min_gap = config.PLOTTING.WAVELENGTH_EDIT_MIN_GAP_NM

        if self._editing_field == self.FIELD_WL_MIN:
            # Editing minimum wavelength
            new_min = self._wavelength_range_editing[0] + (step * delta)
            # Clamp to limits and ensure gap with max
            new_min = max(
                min_limit, min(new_min, self._wavelength_range_editing[1] - min_gap)
            )
            self._wavelength_range_editing[0] = new_min
        elif self._editing_field == self.FIELD_WL_MAX:
            # Editing maximum wavelength
            new_max = self._wavelength_range_editing[1] + (step * delta)
            # Clamp to limits and ensure gap with min
            new_max = max(
                self._wavelength_range_editing[0] + min_gap, min(new_max, max_limit)
            )
            self._wavelength_range_editing[1] = new_max

    ##
    # @brief Commits the edited wavelength range to config.
    def _commit_wavelength_range_changes(self):
        """Commits the edited wavelength range to config."""
        assert (
            self._wavelength_range_editing is not None
        ), "No wavelength range to commit"
        config.PLOTTING.WAVELENGTH_RANGE_MIN_NM = self._wavelength_range_editing[0]
        config.PLOTTING.WAVELENGTH_RANGE_MAX_NM = self._wavelength_range_editing[1]
        print(
            f"INFO: Wavelength range updated to "
            f"{self._wavelength_range_editing[0]:.0f}nm - {self._wavelength_range_editing[1]:.0f}nm"
        )

    ##
    # @brief Calculates the rectangle around the currently edited wavelength range field.
    # @param value_str The wavelength range string being displayed.
    # @param value_x The x-coordinate where the value starts.
    # @param value_y The y-coordinate where the value is rendered.
    # @return pygame.Rect for the blue box, or None if field is unknown.
    # @details Wavelength range format is "###nm - ###nm" (e.g., "400nm - 620nm").
    def _calculate_wavelength_field_rect(self, value_str, value_x, value_y):
        """Calculates the rectangle around the currently edited wavelength range field."""
        assert self._editing_field is not None, "Editing field must be set"

        # Format: "400nm - 620nm"
        # Find the position of " - " separator
        separator_idx = value_str.find(" - ")
        if separator_idx == -1:
            return None

        if self._editing_field == self.FIELD_WL_MIN:
            # First field: from start to before "nm"
            # Find the first "nm" which ends the min value
            nm_idx = value_str.find("nm")
            if nm_idx == -1:
                return None
            start_idx = 0
            end_idx = nm_idx + 2  # Include "nm"
        elif self._editing_field == self.FIELD_WL_MAX:
            # Second field: after " - " to end
            start_idx = separator_idx + 3  # After " - "
            end_idx = len(value_str)
        else:
            return None

        # Get the text before and the field text
        text_before = value_str[:start_idx]
        text_field = value_str[start_idx:end_idx]

        # Calculate widths
        width_before = self.font_value.size(text_before)[0] if text_before else 0
        width_field = self.font_value.size(text_field)[0]
        height = self.font_value.get_height()

        # Calculate rectangle position
        rect_x = value_x + width_before
        rect_y = value_y
        rect_width = width_field
        rect_height = height

        return pygame.Rect(rect_x, rect_y, rect_width, rect_height)

    ##
    # @brief Calculates the rectangle around the currently edited datetime field.
    # @param dt The datetime object being displayed.
    # @param value_x The x-coordinate where the datetime value starts.
    # @param value_y The y-coordinate where the datetime value is rendered.
    # @return pygame.Rect for the blue box, or None if field is unknown.
    # @details Datetime format is "YYYY-MM-DD HH:MM" (e.g., "2025-11-09 13:21").
    #          Calculates text width for each field to position the rectangle accurately.
    def _calculate_field_rect(self, dt, value_x, value_y):
        """Calculates the rectangle around the currently edited datetime field."""
        assert self._editing_field is not None, "Editing field must be set"

        # Full datetime string: "YYYY-MM-DD HH:MM"
        full_str = dt.strftime("%Y-%m-%d %H:%M")

        # Define field positions and their text in the format string
        # Format: "2025-11-09 13:21"
        #          0123456789012345
        field_info = {
            self.FIELD_YEAR: (0, 4),  # "2025"
            self.FIELD_MONTH: (5, 7),  # "11"
            self.FIELD_DAY: (8, 10),  # "09"
            self.FIELD_HOUR: (11, 13),  # "13"
            self.FIELD_MINUTE: (14, 16),  # "21"
        }

        if self._editing_field not in field_info:
            return None

        start_idx, end_idx = field_info[self._editing_field]

        # Get the text before, during, and after the field
        text_before = full_str[:start_idx]
        text_field = full_str[start_idx:end_idx]

        # Calculate widths
        width_before = self.font_value.size(text_before)[0] if text_before else 0
        width_field = self.font_value.size(text_field)[0]
        height = self.font_value.get_height()

        # Calculate rectangle position
        rect_x = value_x + width_before
        rect_y = value_y
        rect_width = width_field
        rect_height = height

        return pygame.Rect(rect_x, rect_y, rect_width, rect_height)

    ##
    # @brief Draws the hint text at the bottom of the screen.
    # @details Shows different hints based on whether the user is in edit mode or navigation mode.
    #          For datetime editing, shows which field is currently selected.
    def _draw_hints(self):
        """Draws the hint text at the bottom of the screen."""
        # Different hints for edit mode vs navigation mode
        if self._edit_mode:
            selected_item = self._menu_items[self._selected_index]
            if selected_item.get("type") == "datetime" and self._editing_field:
                # Show which field is being edited
                hint = f"A: Next/Save | B: Cancel | X/Y: Edit {self._editing_field.upper()}"
            elif (
                selected_item.get("type") == "wavelength_range" and self._editing_field
            ):
                # Show which wavelength field is being edited
                field_name = (
                    "MIN" if self._editing_field == self.FIELD_WL_MIN else "MAX"
                )
                hint = f"A: Next/Save | B: Cancel | X/Y: Edit {field_name}"
            else:
                hint = "A: Save | B: Cancel | X: Up | Y: Down"
        else:
            hint = "A: Select/Edit | X: Up | Y: Down"

        hint_surface = self.font_info.render(hint, True, config.COLORS.YELLOW)
        hint_rect = hint_surface.get_rect(
            centerx=config.SCREEN_WIDTH // 2, bottom=config.SCREEN_HEIGHT - 5
        )
        self.screen.blit(hint_surface, hint_rect)

    ##
    # @brief Renders the complete menu to the screen.
    # @details Draws title, menu items with values, highlights selected item, and hint text.
    #          Selected items are shown in yellow, editing values in green.
    #          Info items (Date, Time, WiFi, IP) are shown in grey when unavailable.
    def draw(self):
        """Renders the menu to the screen."""
        self.screen.fill(config.COLORS.BLACK)

        # Title (original code style: centered at top=8)
        title_surf = self.font_title.render(
            "OPEN SPECTRO MENU", True, config.COLORS.YELLOW
        )
        self.screen.blit(
            title_surf, title_surf.get_rect(centerx=config.SCREEN_WIDTH // 2, top=8)
        )

        # Items (original spacing: MENU_MARGIN_TOP=38, MENU_SPACING=19, MENU_MARGIN_LEFT=12)
        y_pos = config.MENU_MARGIN_TOP
        for idx, item in enumerate(self._menu_items):
            assert isinstance(item, dict), "Menu item must be a dictionary"

            color = config.COLORS.WHITE
            if idx == self._selected_index:
                color = config.COLORS.YELLOW

            # Draw Label
            label_surface = self.font_item.render(item["label"], True, color)
            self.screen.blit(label_surface, (config.MENU_MARGIN_LEFT, y_pos))

            # Draw Value (if any)
            value = None
            value_color = config.COLORS.CYAN

            if "value_key" in item:
                value = str(getattr(self.settings, item["value_key"]))
                if self._edit_mode and idx == self._selected_index:
                    value_color = config.COLORS.YELLOW

            elif item["type"] == "datetime":
                # Handle combined datetime item with offset
                # Use edited datetime if currently editing this field, otherwise use display time
                dt_to_display = (
                    self._datetime_being_edited
                    if self._edit_mode
                    and idx == self._selected_index
                    and self._datetime_being_edited
                    else self.get_current_display_time()
                )

                # Combined format: "2025-11-09 13:21"
                value = dt_to_display.strftime("%Y-%m-%d %H:%M")

                # Change color to green when editing
                if self._edit_mode and idx == self._selected_index:
                    value_color = config.COLORS.YELLOW

            elif item["type"] == "wavelength_range":
                # Handle wavelength range item
                # Use edited values if currently editing, otherwise use config values
                if (
                    self._edit_mode
                    and idx == self._selected_index
                    and self._wavelength_range_editing is not None
                ):
                    wl_min = self._wavelength_range_editing[0]
                    wl_max = self._wavelength_range_editing[1]
                    value_color = config.COLORS.YELLOW
                else:
                    wl_min = config.PLOTTING.WAVELENGTH_RANGE_MIN_NM
                    wl_max = config.PLOTTING.WAVELENGTH_RANGE_MAX_NM

                # Format: "400nm - 620nm"
                value = f"{int(wl_min)}nm - {int(wl_max)}nm"

            elif item["type"] == "fan_threshold":
                # Handle fan threshold display with current temperature
                if self.temp_sensor is not None:
                    threshold = self.temp_sensor.get_fan_threshold_c()
                    temp = self.temp_sensor.get_temperature_c()
                    if isinstance(temp, (float, int)):
                        value = f"Threshold {threshold}C (Current {temp:.0f}C)"
                    else:
                        value = f"Threshold {threshold}C (Temp: {temp})"
                    if self._edit_mode and idx == self._selected_index:
                        value_color = config.COLORS.YELLOW
                else:
                    value = "Not Available"
                    value_color = config.COLORS.GRAY

            elif item["type"] == "info":
                # Handle info items (WiFi, IP)
                display_type = item.get("display")
                if display_type == "wifi":
                    value = self.network_info.get_wifi_name()
                    # Grey out if not connected
                    if "Not Connected" in value or "Error" in value:
                        value_color = config.COLORS.GRAY
                elif display_type == "ip":
                    value = self.network_info.get_ip_address()
                    # Grey out if no IP
                    if "No IP" in value or "Error" in value:
                        value_color = config.COLORS.GRAY

            if value:
                value_surface = self.font_value.render(value, True, value_color)
                value_x = self.screen.get_width() - 30 - value_surface.get_width()
                self.screen.blit(value_surface, (value_x, y_pos))

                # Draw blue box around edited values
                if self._edit_mode and idx == self._selected_index:
                    if item["type"] == "datetime" and self._editing_field:
                        # For datetime: box around specific field (year, month, day, hour, minute)
                        field_rect = self._calculate_field_rect(
                            dt_to_display, value_x, y_pos
                        )
                        if field_rect:
                            pygame.draw.rect(
                                self.screen, config.COLORS.BLUE, field_rect, 1
                            )
                    elif item["type"] == "wavelength_range" and self._editing_field:
                        # For wavelength_range: box around specific field (min or max)
                        field_rect = self._calculate_wavelength_field_rect(
                            value, value_x, y_pos
                        )
                        if field_rect:
                            pygame.draw.rect(
                                self.screen, config.COLORS.BLUE, field_rect, 1
                            )
                    elif item["type"] in ["numeric", "choice", "fan_threshold"]:
                        # For numeric/choice/fan_threshold: box around entire value
                        value_rect = pygame.Rect(
                            value_x - 2,
                            y_pos,
                            value_surface.get_width() + 2,
                            value_surface.get_height(),
                        )
                        pygame.draw.rect(self.screen, config.COLORS.BLUE, value_rect, 1)

            y_pos += config.MENU_SPACING

        # Draw the hint text at the bottom
        self._draw_hints()
