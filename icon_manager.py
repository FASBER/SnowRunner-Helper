"""Persist user-selected cargo pictures between application versions."""
from __future__ import annotations
from pathlib import Path
import os
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from core import USER_DIR, ROOT, CARGO

USER_ICONS = USER_DIR / 'icons'
ALLOWED = {'.png', '.jpg', '.jpeg', '.webp'}
MAX_UPLOAD = 25 * 1024 * 1024
MAX_PIXELS = 24_000_000
MAX_EDGE = 768


def cargo_icon_path(cargo_id, user_folder=None, bundled_folder=None, legacy_folder=None):
    """Resolve chosen icon first, and ship-bundled one as fallback."""
    if cargo_id not in CARGO:
        raise ValueError('Unknown cargo: ' + str(cargo_id))
    folder = Path(user_folder) if user_folder is not None else USER_ICONS
    bundled = Path(bundled_folder) if bundled_folder is not None else ROOT / 'assets' / 'cargo'
    paths = [folder / f'{cargo_id}.png']
    if legacy_folder is not None:
        paths.append(Path(legacy_folder) / f'{cargo_id}.png')
    paths.append(bundled / f'{cargo_id}.png')
    return next((p for p in paths if p.is_file()), None)


def has_custom_icon(cargo_id, user_folder=None):
    if cargo_id not in CARGO:
        return False
    folder = Path(user_folder) if user_folder is not None else USER_ICONS
    return (folder / f'{cargo_id}.png').is_file()


def install_cargo_icon(cargo_id, file_path, user_folder=None):
    """Validate chosen artwork and write safely as an optimized RGBA PNG."""
    if cargo_id not in CARGO:
        raise ValueError('Неизвестный груз / Unknown cargo')
    src = Path(file_path)
    if src.suffix.lower() not in ALLOWED:
        raise ValueError('Поддерживаются PNG, JPG, JPEG и WebP / Supported: PNG, JPG, JPEG, WebP')
    if not src.is_file() or src.stat().st_size > MAX_UPLOAD:
        raise ValueError('Файл отсутствует или больше 25 МБ / Missing or over 25 MB')
    try:
        with Image.open(src) as picture:
            w, h = picture.size
            if w <= 0 or h <= 0 or w * h > MAX_PIXELS:
                raise ValueError('Слишком большое изображение / Image is too large')
            picture = ImageOps.exif_transpose(picture)
            picture.load()
            picture = picture.convert('RGBA')
            picture.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError('Не удаётся открыть изображение / Cannot open image') from exc
    folder = Path(user_folder) if user_folder is not None else USER_ICONS
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f'{cargo_id}.png'
    tmp = folder / f'.{cargo_id}-{uuid.uuid4().hex}.png'
    try:
        picture.save(tmp, format='PNG', optimize=True)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def reset_cargo_icon(cargo_id, user_folder=None):
    if cargo_id not in CARGO:
        raise ValueError('Unknown cargo')
    folder = Path(user_folder) if user_folder is not None else USER_ICONS
    dest = folder / f'{cargo_id}.png'
    if dest.exists():
        dest.unlink()
        return True
    return False
