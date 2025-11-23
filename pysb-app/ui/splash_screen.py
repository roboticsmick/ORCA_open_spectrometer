# pysb-app/ui/splash_screen.py

import time
import pygame
import config
from ui import display_utils

##
# @brief Displays the splash screen for a configured duration.
# @param screen The Pygame surface to draw on.
# @param leak_detected_flag A threading.Event that signals if a leak has been detected.
#                          If set, the splash screen exits immediately.
# @details The splash screen displays the application logo centered on the screen.
#          It waits for the duration specified in config.SPLASH_DURATION_S, checking
#          periodically for the leak detection flag to allow for emergency shutdown.
def show(screen, leak_detected_flag):
    """Displays the splash screen for a configured duration."""
    screen.fill(config.COLORS.BLACK)

    display_utils.draw_image_centered(
        screen,
        config.IMAGES.LOGO,
        scale_dims=None,
        fallback_text="PySB-App"
    )

    # Update the display immediately after drawing
    display_utils.update_display(screen)

    # Wait for the specified duration, but check for leak flag periodically
    start_time = time.monotonic()
    while time.monotonic() - start_time < config.SPLASH_DURATION_S:
        if leak_detected_flag.is_set():
            return # Exit immediately if a leak is detected
        time.sleep(0.1) # Don't hog the CPU
