## @file leak_warning.py
#  @brief Critical leak warning display for emergency shutdown.
#
#  Displays a full-screen red warning when a leak is detected, instructing
#  the user to wait for full shutdown before removing the housing.

import pygame
import config
import time
from ui import display_utils


## @brief Display critical leak warning screen and wait for shutdown.
#
#  Fills the screen with red and displays a warning message about the
#  detected leak. Holds for 5 seconds to allow the user to read the message
#  before the application terminates.
#
#  @param[in] screen The pygame surface to draw on.
def show(screen):
    screen.fill(config.COLORS.RED)

    font_title = pygame.font.Font(None, 36)
    font_body = pygame.font.Font(None, 24)

    title_rect = pygame.Rect(0, 20, config.SCREEN_WIDTH, 50)
    display_utils.draw_text(screen, "CRITICAL: LEAK DETECTED!", font_title, config.COLORS.WHITE, title_rect)

    body_rect = pygame.Rect(20, 80, config.SCREEN_WIDTH - 40, config.SCREEN_HEIGHT - 100)
    body_text = "Powering down immediately.\nDo NOT remove the housing until\nthe device is fully powered off."
    display_utils.draw_text(screen, body_text, font_body, config.COLORS.WHITE, body_rect)

    display_utils.update_display(screen)

    # Keep the message on screen for a few seconds before shutdown
    time.sleep(5)
