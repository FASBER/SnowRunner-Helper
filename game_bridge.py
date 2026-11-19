"""Read-only discovery of installed SnowRunner game archives and save slots.

Never writes to a game directory. Importable without Windows-specific modules.
No inference of the currently active save slot: changed timestamps are not proof.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import zipfile
from pathlib import Path

GAME_RELATIVE = Path('preload') / 'paks' / 'client' / 'initial.pak'
SLOT_RE = re.compile(r'^CompleteSave([123]?)\.(cfg|dat)$', re.I)
MAX_SAVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_RECORDS = 100_000


def steam_libraries(steam_root: Path) -> list[Path]:
    """Find Steam libraries without relying on a fixed drive letter."""
    root = Path(steam_root)
    libraries = [root]
    vdf = root / 'steamapps' / 'libraryfolders.vdf'
    try:
        text = vdf.read_text(encoding='utf-8-sig')
    except (OSError, UnicodeError):
        return libraries
    for match in re.findall(r'"path"\s*"([^"]+)"', text, re.I):
        p = Path(match.replace('\\\\', '\\'))
        if p not in libraries:
            libraries.append(p)
    return libraries


def candidate_steam_roots() -> list[Path]:
    roots = []
    for env in ('PROGRAMFILES(X86)', 'PROGRAMFILES', 'LOCALAPPDATA'):
        prefix = os.environ.get(env)
        if prefix:
            roots.extend((Path(prefix) / 'Steam', Path(prefix) / 'Valve' / 'Steam'))
    if os.name == 'nt':
        for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
            roots.extend((Path(f'{letter}:/Steam'), Path(f'{letter}:/SteamLibrary')))
    return list(dict.fromkeys(roots))


def discover_game_archives(extra_roots=(), steam_roots=None, only_extra=False) -> list[Path]:
    """Find initial.pak in common installation directories and explicit folder(s)."""
    candidates = []
    for raw in extra_roots:
        path = Path(raw).expanduser()
        candidates.extend((path, path / 'initial.pak', path / GAME_RELATIVE,
                           path / 'SnowRunner' / GAME_RELATIVE,
                           path / 'en_us' / GAME_RELATIVE))
    for steam in ([] if only_extra else candidate_steam_roots()) if steam_roots is None else steam_roots:
        for lib in steam_libraries(Path(steam)):
            candidates.append(lib / 'steamapps' / 'common' / 'SnowRunner' / GAME_RELATIVE)
    for env in (() if only_extra else ('PROGRAMFILES', 'PROGRAMFILES(X86)')):
        base = os.environ.get(env)
        if base:
            candidates.extend((Path(base) / 'Epic Games' / 'SnowRunner' / GAME_RELATIVE,
                               Path(base) / 'Epic Games' / 'SnowRunner' / 'en_us' / GAME_RELATIVE))
    unique = {}
    for candidate in candidates:
        if candidate.is_dir():
            candidate /= GAME_RELATIVE
        try:
            if candidate.is_file() and candidate.name.casefold() == 'initial.pak':
                resolved = candidate.resolve()
                unique[str(resolved).casefold()] = resolved
        except OSError:
            continue
    return list(unique.values())


def _save_folders(extra_roots=(), steam_roots=None, only_extra=False) -> list[Path]:
    folders = []
    home = Path.home()
    doc_candidates = [home / 'Documents', home / 'OneDrive' / 'Documents']
    userprofile = os.environ.get('USERPROFILE')
    if userprofile:
        doc_candidates.append(Path(userprofile) / 'Documents')
    for docs in (() if only_extra else doc_candidates):
        storage = docs / 'My Games' / 'SnowRunner' / 'base' / 'storage'
        if storage.is_dir():
            folders.extend(p for p in storage.iterdir() if p.is_dir() and p.name.lower() != 'backupslots')
    for steam in ([] if only_extra else candidate_steam_roots()) if steam_roots is None else steam_roots:
        # Steam's per-user saves normally reside below its main installation,
        # but checking all known library roots handles nonstandard setups.
        for library in steam_libraries(Path(steam)):
            userdata = library / 'userdata'
            if userdata.is_dir():
                folders.extend(p / '1465360' / 'remote' for p in userdata.iterdir()
                               if p.is_dir() and (p / '1465360' / 'remote').is_dir())
    for raw in extra_roots:
        path = Path(raw).expanduser()
        if path.is_dir():
            folders.extend((path, path / 'base' / 'storage'))
            storage = path / 'base' / 'storage'
            if storage.is_dir():
                folders.extend(p for p in storage.iterdir() if p.is_dir() and p.name.lower() != 'backupslots')
    return list(dict.fromkeys(p.resolve() for p in folders if p.is_dir()))


def profile_key(path: Path) -> str:
    """Stable local identity based on file location, NOT a guessed in-game identity."""
    norm = os.path.normcase(os.path.abspath(str(path)))
    return hashlib.sha256(norm.encode('utf-8', 'surrogatepass')).hexdigest()[:20]


def discover_save_slots(extra_roots=(), steam_roots=None, only_extra=False) -> list[dict]:
    slots = []
    for folder in _save_folders(extra_roots, steam_roots, only_extra):
        for file in folder.iterdir():
            match = SLOT_RE.fullmatch(file.name)
            if not match or not file.is_file():
                continue
            slot = int(match[1]) + 1 if match[1] else 1
            try:
                stat = file.stat()
            except OSError:
                continue
            slots.append({'path': str(file), 'profile_key': profile_key(file),
                          'slot': slot, 'platform_hint': 'Steam' if file.suffix.lower() == '.cfg' else 'Epic/other',
                          'modified_ns': stat.st_mtime_ns, 'size': stat.st_size})
    return sorted(slots, key=lambda item: (item['platform_hint'], item['path'].casefold()))


def read_save_json(path: Path) -> dict:
    """Read only a stable JSON save. Reject an in-progress write or unknown encoding."""
    path = Path(path)
    before = path.stat()
    if before.st_size == 0 or before.st_size > MAX_SAVE_BYTES:
        raise ValueError('Save size is empty or above safety limit')
    with path.open('rb') as stream:
        raw = stream.read(MAX_SAVE_BYTES + 1)
    after = path.stat()
    if len(raw) > MAX_SAVE_BYTES or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Save file changed during reading; retry after the game saves')
    try:
        result = json.loads(raw.decode('utf-8-sig'), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Invalid numeric constant')))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise ValueError('Unsupported or incomplete save format') from exc
    if not isinstance(result, dict):
        raise ValueError('Save JSON root must be an object')
    return result


def inspect_save(path: Path) -> dict:
    """Report only well-known, verifiable fields. Do not guess the active slot."""
    result = read_save_json(path)
    parent = result.get('CompleteSave')
    if isinstance(parent, dict):
        result = parent
    data = result.get('SslValue')
    if isinstance(data, dict):
        result = data
    return {'slot_file': Path(path).name, 'top_level_keys': sorted(result.keys())[:100],
            'recognized_json': True}


def inspect_archive(path: Path) -> dict:
    """Fast index-only check: no extraction and no writes to initial.pak."""
    path = Path(path)
    if not zipfile.is_zipfile(path):
        raise ValueError('initial.pak is not a readable ZIP/PAK archive')
    with zipfile.ZipFile(path) as z:
        count = xml = json_count = cache = 0
        for info in z.infolist():
            if info.is_dir():
                continue
            count += 1
            if count > MAX_ARCHIVE_RECORDS:
                raise ValueError('Too many archive entries')
            lower = info.filename.casefold()
            xml += int(lower.endswith('.xml'))
            json_count += int(lower.endswith('.json'))
            cache += int(lower.endswith('initial.cache_block'))
    return {'path': str(path), 'entries': count, 'xml': xml,
            'json': json_count, 'cache_blocks': cache}


def status_summary(archives, slots, lang='ru') -> str:
    if lang == 'ru':
        lines = [f'Установок с initial.pak: {len(archives)}', f'Слотов сохранений: {len(slots)}']
        lines += [f'Ресурсы: {p}' for p in archives]
        lines += [f'Слот {s["slot"]} ({s["platform_hint"]}): {s["path"]}' for s in slots]
        lines.append('Активный слот не определяется по дате файла: переключение только с подтверждением.')
        return '\n'.join(lines)
    lines = [f'Game archives: {len(archives)}', f'Save slots: {len(slots)}']
    lines += [f'Assets: {p}' for p in archives]
    lines += [f'Slot {s["slot"]} ({s["platform_hint"]}): {s["path"]}' for s in slots]
    lines.append('Active slot cannot be inferred from file timestamps; switching requires confirmation.')
    return '\n'.join(lines)
