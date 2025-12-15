## @file display_utils.py
#  @brief Common display utilities for text rendering and display updates.
#
#  Provides helper functions for text wrapping, image loading, and display
#  updates. Handles both Adafruit PiTFT framebuffer mode (RGB565) and
#  standard pygame window mode transparently.

import os
import pygame
import config

def draw_text(surface, text, font, color, rect, aa=True, bkg=None):
    """!
    @brief Draws text onto a Pygame surface, automatically wrapping it to fit within a given rectangle.
    @details This function handles multi-line text and word wrapping. Text is centered horizontally
             within the provided rectangle. If the text exceeds the vertical bounds of the rectangle,
             it will be truncated.
    @param surface The Pygame surface to draw the text on (e.g., the main screen).
    @param text The string of text to be rendered. Newline characters will be respected.
    @param font The Pygame font object to use for rendering.
    @param color The color of the text.
    @param rect The pygame.Rect object that defines the boundaries for the text.
    @param aa Boolean flag to enable or disable anti-aliasing.
    @param bkg The background color for the text. If None, the background is transparent.
    @return The y-coordinate of the bottom of the last line of text drawn.
    """
    y = rect.top
    line_spacing = -2
    font_height = font.size("Tg")[1]

    for line in text.splitlines():
        while line:
            i = 1
            if y + font_height > rect.bottom:
                break
            while font.size(line[:i])[0] < rect.width and i < len(line):
                i += 1
            if i < len(line):
                i = line.rfind(" ", 0, i) + 1
            if i == 0:
                i = 1  # Fallback for very long words
            image = font.render(line[:i], aa, color, bkg)
            image_rect = image.get_rect(centerx=rect.centerx, top=y)
            surface.blit(image, image_rect)
            y += font_height + line_spacing
            line = line[i:]
    return y

def draw_image_centered(screen, image_path, scale_dims=None, fallback_text=""):
    """!
    @brief Loads and draws an image, centered on the screen.
    @details If the image fails to load, this function will print a warning to the console
             and can optionally render fallback text in its place.
    @param screen The Pygame surface to draw the image on.
    @param image_path The file path to the image to be loaded.
    @param scale_dims A tuple (width, height) to scale the image to. If None, the original size is used.
    @param fallback_text If the image cannot be loaded, this text will be drawn on the screen instead.
    @return True if the image was loaded and drawn successfully, False otherwise.
    """
    try:
        img = pygame.image.load(image_path)
        if scale_dims:
            img = pygame.transform.scale(img, scale_dims)
        rect = img.get_rect(center=screen.get_rect().center)
        screen.blit(img, rect)
        return True
    except pygame.error:
        print(f"WARN: Could not load image at '{image_path}'.")
        if fallback_text:
            font = pygame.font.Font(None, 40)
            draw_text(screen, fallback_text, font, (255, 255, 255), screen.get_rect())
        return False

_fb_write_count = 0  # Track framebuffer writes for debugging

def update_display(screen):
    """!
    @brief Updates the physical display based on hardware configuration.
    @details For Adafruit PiTFT: Writes pygame Surface to /dev/fb1 framebuffer (RGB565 format).
             For standard mode: Calls pygame.display.flip().
             This function handles the difference between framebuffer and window modes.
    @param screen The pygame.Surface to render to the display.
    @return None
    """
    global _fb_write_count
    assert screen is not None, "Screen surface cannot be None"

    if config.HARDWARE["USE_ADAFRUIT_PITFT"]:
        # Adafruit PiTFT: Manual framebuffer write
        try:
            # Convert pygame surface to RGB888 raw bytes
            raw = pygame.image.tostring(screen, "RGB")
            # Convert RGB888 to RGB565 for framebuffer
            rgb565_data = bytearray()
            for i in range(0, len(raw), 3):
                if i + 2 < len(raw):
                    r = raw[i] >> 3        # 8 bits -> 5 bits
                    g = raw[i + 1] >> 2    # 8 bits -> 6 bits
                    b = raw[i + 2] >> 3    # 8 bits -> 5 bits
                    rgb565 = (r << 11) | (g << 5) | b
                    rgb565_data.extend(rgb565.to_bytes(2, byteorder="little"))
            # Write to framebuffer device
            with open("/dev/fb1", "wb") as fb:
                fb.write(rgb565_data)
            _fb_write_count += 1
            if _fb_write_count <= 3:  # Only print first few writes
                print(f"Framebuffer write #{_fb_write_count} completed ({len(rgb565_data)} bytes)")
        except Exception as e:
            print(f"ERROR: Failed to update Adafruit PiTFT framebuffer: {e}")
    else:
        # Standard window mode: use pygame's flip
        try:
            if pygame.display.get_init() and pygame.display.get_surface():
                pygame.display.flip()
        except Exception as e:
            print(f"ERROR: Failed to update pygame display: {e}")
