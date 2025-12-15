## @file terms_screen.py
#  @brief Terms and conditions / disclaimer display screen.
#
#  Shows the application disclaimer text with optional auto-advance timeout.
#  User can press A or B to continue, or wait for timeout if configured.
#  Monitors leak detection flag for emergency exit.

import time
import pygame
import config
from ui import display_utils

##
# @brief Displays the terms and conditions / disclaimer screen.
# @param screen The Pygame surface to draw on.
# @param button_handler The ButtonHandler instance for processing user input.
# @param leak_detected_flag A threading.Event that signals if a leak has been detected.
# @details This screen shows the application's disclaimer text. If config.TERMS_DURATION_S
#          is greater than 0, the screen auto-advances after that duration. Otherwise,
#          the user must press A (ENTER) or B (BACK) to continue. The screen exits
#          immediately if a leak is detected.
def show(screen, button_handler, leak_detected_flag):
    """Displays the terms/disclaimer screen."""
    screen.fill(config.COLORS.BLACK)

    # Load fonts (matching original code)
    try:
        font_disclaimer = pygame.font.Font(config.FONTS.MAIN, config.FONT_SIZES.DISCLAIMER)
    except:
        font_disclaimer = pygame.font.Font(None, config.FONT_SIZES.DISCLAIMER)

    try:
        font_hint = pygame.font.Font(config.FONTS.HINT, config.FONT_SIZES.HINT)
    except:
        font_hint = pygame.font.Font(None, config.FONT_SIZES.HINT)

    # Render each line individually (original code approach)
    lines = config.DISCLAIMER_TEXT.splitlines()
    rendered = []
    max_w = 0
    total_h = 0
    line_spacing = 4  # Original line spacing

    for line_txt in lines:
        if line_txt.strip():
            surf = font_disclaimer.render(line_txt, True, config.COLORS.WHITE)
            rendered.append(surf)
            max_w = max(max_w, surf.get_width())
            total_h += surf.get_height() + line_spacing
        else:
            rendered.append(None)
            total_h += (font_disclaimer.get_height() // 2) + line_spacing

    if total_h > 0 and line_spacing > 0 and len(rendered) > 0:
        total_h -= line_spacing

    # Add hint
    hint_surf = font_hint.render("Press A or B to continue...", True, config.COLORS.YELLOW)
    total_h += hint_surf.get_height() + 10

    # Center vertically (original code approach)
    start_y = max(10, (config.SCREEN_HEIGHT - total_h) // 2)

    # Draw all lines
    current_y = start_y
    for surf in rendered:
        if surf:
            screen.blit(surf, surf.get_rect(centerx=config.SCREEN_WIDTH // 2, top=current_y))
            current_y += surf.get_height() + line_spacing
        else:
            current_y += (font_disclaimer.get_height() // 2) + line_spacing

    # Draw hint
    screen.blit(hint_surf, hint_surf.get_rect(centerx=config.SCREEN_WIDTH // 2, top=current_y + 10))

    # Update the display immediately after drawing
    display_utils.update_display(screen)

    start_time = time.monotonic()
    while not leak_detected_flag.is_set():
        # Check for button press
        button_handler.check_pygame_events() # Make sure we process events
        if button_handler.get_pressed(config.BTN_ENTER) or button_handler.get_pressed(config.BTN_BACK):
            break

        # Check for timeout if configured
        if config.TERMS_DURATION_S > 0:
            if time.monotonic() - start_time >= config.TERMS_DURATION_S:
                break

        time.sleep(0.05) # Small delay to prevent busy-waiting
