"""Reusable non-destructive color remapping for the SnowRunner canvas UI.

This keeps the approved Expedition geometry and clickable hitboxes intact.
The 'game' palette is exactly as before; alternate themes change only paints.
"""
from __future__ import annotations
import colorsys
import re

THEME_LABELS = {
    'game': ('SnowRunner', 'SnowRunner'),
    'dark': ('Тёмная', 'Dark'),
    'light': ('Светлая', 'Light'),
    'forest': ('Лесная', 'Forest'),
}


def _parse(color):
    if not isinstance(color, str) or not re.fullmatch(r'#[A-Fa-f0-9]{6}', color):
        return None
    return tuple(int(color[i:i+2], 16) for i in (1, 3, 5))


def _hex(rgb):
    return '#'+''.join(f'{max(0, min(255, int(round(v)))):02X}' for v in rgb)


def _mix(a, b, t):
    return tuple(a[i] * (1-t) + b[i] * t for i in range(3))


def _accent(rgb):
    r,g,b=(x / 255 for x in rgb)
    h,s,v=colorsys.rgb_to_hsv(r,g,b)
    return (0.075 <= h <= .17 and s >= .33 and v >= .42)


def theme_color(color, theme='game', kind='surface'):
    """Turn a legacy hexadecimal paint into theme-appropriate paint.

    Colors that are not '#RRGGBB' (e.g. Tk transparent outlines) pass unchanged.
    Text and surface paints have separate contrast rules.
    """
    rgb=_parse(color)
    if rgb is None or theme not in THEME_LABELS or theme == 'game':
        return color
    bright=sum(rgb)/3
    if _accent(rgb):
        return {'dark':'#E9AE42','light':'#A66C17','forest':'#D5BF6A'}[theme]
    if kind == 'text':
        if theme == 'light':
            return '#27333A' if bright>208 or bright<100 else '#63717A'
        if theme == 'forest':
            return '#EAF1E6' if bright>208 else '#AFC6B5' if bright>130 else '#E7EBDD'
        return '#EDF0F0' if bright>208 else '#AFB7BC' if bright>125 else '#E8ECED'
    if theme == 'light':
        if bright >= 200: return '#27343A'  # Very light borders/icons on pale UI
        if bright >= 128: return '#8B9A9B'
        # Preserve gentle differences between background, row, and hover surfaces.
        amount=min(1.0,bright/128)
        return _hex(_mix((244,242,236),(205,220,221),amount))
    if theme == 'forest':
        if bright >= 190: return '#E5EBDD'
        if bright >= 135: return '#A7C1AC'
        amount=min(1.0,bright/135)
        return _hex(_mix((10,26,22),(48,83,57),amount))
    # Dark mode: keep an industrial, neutral blue-grey instead of a second
    # copy of the SnowRunner gold/navy palette.
    if bright >= 190: return '#EDF0F0'
    if bright >= 135: return '#AAB6BE'
    amount=min(1.0,bright/135)
    return _hex(_mix((13,17,22),(53,63,72),amount))


def theme_background(image, theme):
    """Preserve theme support and load the explicitly approved UI adapter.

    All other modules, profile data, OTA updater and user settings are unchanged.
    """
    from approved_reference_v311 import install_approved_ui, decorate_background
    # Install the explicit save-slot selection dialog, including its Save action.
    from profile_selector_v314 import install_profile_selector
    install_profile_selector()
    if image.size == (1319, 747) and image.getpixel((20,180))[:3] == (8,24,33):
        install_approved_ui()
    decorated = decorate_background(image,theme)
    if decorated is not image:
        return decorated
    if theme == 'game' or theme not in THEME_LABELS:
        return image
    from PIL import Image, ImageOps
    rgb = image.convert('RGB')
    top = min(92, rgb.height)
    body = rgb.crop((0,top,rgb.width,rgb.height))
    if body.height < 1:
        return rgb
    gradient = ImageOps.grayscale(body)
    if theme=='light':
        body = ImageOps.colorize(gradient, black='#E5E9E2', white='#FFFFFF')
    elif theme=='forest':
        body = ImageOps.colorize(gradient, black='#0C1B14', white='#487254')
    else:
        body = ImageOps.colorize(gradient, black='#11161B', white='#52606E')
    result=rgb.copy()
    result.paste(body,(0,top))
    return result
