"""Compatibility reader for real Steam SnowRunner CompleteSave*.cfg snapshots.

The game can terminate JSON with one NUL byte and wrap slot 2/3 in
CompleteSave1/CompleteSave2. This decoder reads original bytes WITHOUT ever
writing to a game file. Only the returned in-memory dictionary is normalized.
"""
from __future__ import annotations

import json
from pathlib import Path

KNOWN_WRAPPERS = ('CompleteSave', 'CompleteSave1', 'CompleteSave2', 'CompleteSave3')
MAX_BYTES_FALLBACK = 64 * 1024 * 1024


def decode_save_bytes(raw: bytes) -> dict:
    """Accept the game's one terminal NUL, but no arbitrary trailing junk."""
    if raw.endswith(b'\x00'):
        raw = raw[:-1]
    try:
        value = json.loads(raw.decode('utf-8-sig'),
                           parse_constant=lambda constant: (_ for _ in ()).throw(
                               ValueError('Invalid numeric constant')))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError('Unsupported or incomplete save format') from exc
    if not isinstance(value, dict):
        raise ValueError('Save JSON root must be an object')

    # The original file can have a slot-specific envelope. Its location remains
    # the identity of the chosen profile; this is just an internal JSON adapter.
    if 'CompleteSave' not in value:
        present = [key for key in KNOWN_WRAPPERS[1:] if key in value]
        if len(present) == 1 and isinstance(value[present[0]], dict):
            value['CompleteSave'] = value.pop(present[0])
    return value


def read_save_json(path: Path) -> dict:
    """Read an unchanged file, with the same size/stability safeguards as v0.31.14."""
    from game_bridge import MAX_SAVE_BYTES
    file = Path(path)
    before = file.stat()
    if before.st_size == 0 or before.st_size > MAX_SAVE_BYTES:
        raise ValueError('Save size is empty or above safety limit')
    with file.open('rb') as stream:
        raw = stream.read(MAX_SAVE_BYTES + 1)
    after = file.stat()
    if (len(raw) > MAX_SAVE_BYTES or
            (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise ValueError('Save file changed during reading; retry after the game saves')
    return decode_save_bytes(raw)


def install_save_reader() -> bool:
    """Install once in both import paths used by game_bridge and profile_sync.

    profile_sync.snapshot_save() looks up the decoder in its module globals at
    invocation time; app.py does not need to be replaced.
    """
    import game_bridge
    import profile_sync
    if (getattr(game_bridge, '_save_reader_v315_installed', False)
            and getattr(profile_sync, '_save_reader_v315_installed', False)):
        return False
    game_bridge.read_save_json = read_save_json
    profile_sync.read_save_json = read_save_json
    game_bridge._save_reader_v315_installed = True
    profile_sync._save_reader_v315_installed = True
    return True
