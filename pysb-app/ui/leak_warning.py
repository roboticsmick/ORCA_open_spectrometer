# pysb-app/ui/leak_warning.py

import pygame
import config
import time
from ui import display_utils

def show(screen):
    """Displays a critical leak warning message."""
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
