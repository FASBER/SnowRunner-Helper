"""Friendly profile captions without guessing a Steam identity.

Steam loginusers.vdf is read locally (never modified); user overrides live in
SnowRunner Helper settings.json, not in the game or snapshot.  Missing/ambiguous
Steam matches use the explicit save slot name, never a truncated hash.
"""
from __future__ import annotations

import re
from pathlib import Path

_ID32_OFFSET = 76561197960265728


def _source_path(app):
    key = getattr(app, 'active_profile_key', 'local')
    if key == 'local':
        return None
    try:
        data = app.profiles.read(key)
        source = data.get('source_path')
        return Path(source) if isinstance(source, str) and source else None
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return None


def _steam_id_from_save_path(source):
    """Only an unambiguous userdata/<id>/1465360/remote layout qualifies."""
    if source is None:
        return None
    parts = source.parts
    lower = [v.casefold() for v in parts]
    for index in range(len(parts)-3):
        if (lower[index] == 'userdata' and lower[index+2] == '1465360' and
                lower[index+3] == 'remote' and parts[index+1].isdecimal()):
            return str(_ID32_OFFSET + int(parts[index+1]))
    return None


def _steam_loginusers_candidates(source):
    seen = set()
    if source is not None:
        parts = source.parts
        for index, part in enumerate(parts):
            if part.casefold() == 'userdata':
                candidate = Path(*parts[:index]) / 'config' / 'loginusers.vdf'
                key = str(candidate).casefold()
                if key not in seen:
                    seen.add(key)
                    yield candidate
    try:
        from game_bridge import candidate_steam_roots
        roots = candidate_steam_roots()
    except (ImportError, AttributeError):
        roots = []
    for root in roots:
        candidate = Path(root) / 'config' / 'loginusers.vdf'
        key = str(candidate).casefold()
        if key not in seen:
            seen.add(key)
            yield candidate


def _persona_from_vdf(vdf, steamid64):
    """Read Valve loginusers blocks; never return somebody else's nickname."""
    escaped_id = re.escape(steamid64)
    start = re.search(r'"'+escaped_id+r'"\s*\{', vdf)
    if not start:
        return None
    opener = vdf.find('{', start.start())
    level = 1
    end = opener+1
    while level and end < len(vdf):
        if vdf[end] == '{': level += 1
        elif vdf[end] == '}': level -= 1
        end += 1
    if level:
        return None
    matched = re.search(r'"PersonaName"\s*"([^"\r\n]{1,80})"', vdf[opener+1:end], re.I)
    if matched:
        return matched.group(1).replace('\\\\', '\\').strip()
    return None


def steam_persona_for_source(source):
    steamid64 = _steam_id_from_save_path(source)
    if not steamid64:
        return None
    for vdf in _steam_loginusers_candidates(source):
        try:
            if vdf.is_file() and vdf.stat().st_size <= 3_000_000:
                text = vdf.read_text(encoding='utf-8-sig', errors='replace')
                name = _persona_from_vdf(text, steamid64)
                if name:
                    return name
        except OSError:
            continue
    return None


def display_profile(app):
    key = getattr(app, 'active_profile_key', 'local')
    config = getattr(app, 'config', {})
    overrides = config.get('profile_display_names', {}) if isinstance(config, dict) else {}
    if isinstance(overrides, dict):
        label = overrides.get(key)
        if isinstance(label, str) and label.strip():
            return label.strip()[:70]
    if key == 'local':
        return 'Локальный'
    source = _source_path(app)
    persona = steam_persona_for_source(source)
    if persona:
        return persona
    if source is not None:
        matched = re.fullmatch(r'CompleteSave([123]?)\.(?:cfg|dat)', source.name, re.I)
        if matched:
            slot = 1 if not matched.group(1) else int(matched.group(1))+1
            return f'Steam · слот {slot}' if source.suffix.casefold() == '.cfg' else f'Слот {slot}'
        return 'Сохранение SnowRunner'
    return 'Игровой профиль'


def edit_profile_name(app):
    from tkinter import simpledialog, messagebox
    from core import SETTINGS_FILE, save_json
    key = getattr(app, 'active_profile_key', 'local')
    existing = app.config.get('profile_display_names', {})
    current = existing.get(key, '') if isinstance(existing, dict) else ''
    chosen = simpledialog.askstring('SnowRunner Helper',
        'Название профиля (пустое поле — автоматическое имя Steam):',
        initialvalue=current, parent=app.root)
    if chosen is None:
        return
    chosen = chosen.strip()
    if len(chosen) > 70 or any(ord(c) < 32 for c in chosen):
        messagebox.showwarning('SnowRunner Helper', 'Имя должно быть до 70 символов без управляющих знаков.', parent=app.root)
        return
    aliases = dict(existing) if isinstance(existing, dict) else {}
    if chosen:aliases[key] = chosen
    else:aliases.pop(key, None)
    app.config['profile_display_names'] = aliases
    try:
        save_json(SETTINGS_FILE, app.config)
    except (OSError, ValueError) as exc:
        messagebox.showerror('SnowRunner Helper', str(exc), parent=app.root)
        return
    if getattr(app, 'game', None):
        app.game.redraw()
