"""Non-destructive inspection of locally owned SnowRunner archives.

This module DOES NOT decode SnowRunner's compiled data.stg format. It reports
ZIP entries and tiny, bounded binary probes so an actual game sample can be
studied separately. In particular, a string hit is NEVER considered a recipe.
No game data or archive members are extracted or modified.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import zipfile

# Bounded stream reads. No whole-map file is loaded into memory.
PROBE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVES = 500
HEADER_BYTES = 48
_MARKERS = {
    'craftSettings (ASCII)': b'craftSettings',
    'craftSettings (UTF-16LE)': 'craftSettings'.encode('utf-16le'),
    'ZonePropertyStorehouseCraft (ASCII)': b'ZonePropertyStorehouseCraft',
}


def _is_stg(name: str) -> bool:
    return name.replace('\\', '/').lower().endswith('data.stg')


def _probe_stream(stream, limit: int = PROBE_BYTES):
    first = b''
    scanned = 0
    carry = b''
    hits = {k: 0 for k in _MARKERS}
    max_pattern = max(map(len, _MARKERS.values()))
    fingerprint = hashlib.sha256()
    while scanned < limit:
        chunk = stream.read(min(1024 * 1024, limit - scanned))
        if not chunk:
            break
        if not first:
            first = chunk[:HEADER_BYTES]
        fingerprint.update(chunk)
        data = carry + chunk
        for key, marker in _MARKERS.items():
            # Exclude matches entirely within carry (already counted).
            p = 0
            while True:
                offset = data.find(marker, p)
                if offset < 0:
                    break
                if offset + len(marker) > len(carry):
                    hits[key] += 1
                p = offset + 1
        scanned += len(chunk)
        carry = data[-(max_pattern - 1):]
    return {'scanned_bytes': scanned, 'header_hex': first.hex(' '),
            'sample_sha256': fingerprint.hexdigest(),
            'markers': {k: v for k, v in hits.items() if v}}


def scan_pak(path: str | Path, *, probe: bool = True):
    """Inventory ZIP-compatible PAK and optionally probe one compiled STG."""
    path = Path(path)
    result = {'file': str(path), 'archive_bytes': path.stat().st_size,
              'entries': 0, 'json_names': [], 'stg_names': [], 'other_names': [],
              'stg_probe': None, 'error': None}
    if not zipfile.is_zipfile(path):
        result['error'] = 'Файл не является читаемым ZIP-совместимым PAK.'
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                result['entries'] += 1
                name = entry.filename
                if name.lower().endswith('.json'):
                    result['json_names'].append(name)
                elif _is_stg(name):
                    result['stg_names'].append(name)
                elif name.lower().endswith('.stg'):
                    result['other_names'].append(name)
            if probe and result['stg_names']:
                stg_name = result['stg_names'][0]
                info = archive.getinfo(stg_name)
                with archive.open(info) as stream:
                    result['stg_probe'] = _probe_stream(stream)
                result['stg_probe']['uncompressed_bytes'] = info.file_size
                result['stg_probe']['member'] = stg_name
    except (OSError, RuntimeError, zipfile.BadZipFile, EOFError) as error:
        result['error'] = f'Не удалось прочитать архив: {type(error).__name__}: {error}'
    return result


def scan_stg(path: str | Path):
    """Analyze a standalone STG, without assuming any internal structures."""
    path = Path(path)
    with path.open('rb') as stream:
        probe = _probe_stream(stream)
    probe.update({'member': path.name, 'uncompressed_bytes': path.stat().st_size})
    return {'file': str(path), 'archive_bytes': path.stat().st_size,
            'entries': 1, 'json_names': [], 'stg_names': [path.name],
            'other_names': [], 'stg_probe': probe, 'error': None}


def _compact_pak_line(info):
    short = Path(info['file']).name
    return f"  {short} — записей: {info['entries']}, STG: {len(info['stg_names'])}, JSON: {len(info['json_names'])}" + (f"; ошибка: {info['error']}" if info['error'] else '')


def format_report(results, location: str, lang='ru') -> str:
    """Readable technical report. No game archive data is copied into it."""
    num_stg = sum(len(x['stg_names']) for x in results)
    num_json = sum(len(x['json_names']) for x in results)
    errors = sum(bool(x['error']) for x in results)
    ru = lang == 'ru'
    if ru:
        lines = ['SnowRunner Craft Assistant — диагностика игровых файлов',
                 'Только чтение. Файлы игры не менялись.',
                 f'Выбранный путь: {location}',
                 f'Проверено файлов: {len(results)}; STG: {num_stg}; JSON: {num_json}; ошибок чтения: {errors}', '',
                 'ВАЖНО: STG — скомпилированный бинарный формат. Этот инструмент не декодирует рецепты из STG.',
                 'Наличие текста craftSettings в бинарном файле само по себе НЕ подтверждает рецепт.',
                 'Документация Saber: https://expeditions-guides.saber.games/map_modding/creating_a_map/zones/snowrunner_zones/storehouse_craft_and_energy_zones/',
                 '', 'Список проверенных файлов:']
    else:
        lines = ['SnowRunner Craft Assistant — game file diagnostic',
                 'Read-only. No game files were changed.',
                 f'Selected path: {location}',
                 f'Files checked: {len(results)}; STG: {num_stg}; JSON: {num_json}; read errors: {errors}', '',
                 'IMPORTANT: STG is a compiled binary format. This tool does NOT decode STG recipes.',
                 'An occurrence of the string craftSettings alone is NOT proof of a crafting recipe.',
                 'Saber documentation: https://expeditions-guides.saber.games/map_modding/creating_a_map/zones/snowrunner_zones/storehouse_craft_and_energy_zones/',
                 '', 'Inspected files:']
    for item in results:
        lines.append(_compact_pak_line(item))
        for name in item['stg_names'][:3]:
            lines.append(f'    STG: {name}')
        for name in item['json_names'][:5]:
            lines.append(f'    JSON: {name}')
        p = item.get('stg_probe')
        if p:
            lines.extend([f'    Sampled STG: {p["member"]}',
                          f'    Sampled bytes: {p["scanned_bytes"]} / {p["uncompressed_bytes"]} (first bytes only)',
                          f'    STG header (hex, first {HEADER_BYTES} bytes): {p["header_hex"]}',
                          f'    Sample SHA-256: {p["sample_sha256"]}',
                          f'    Markers within sample: {p["markers"] or "none"}'])
    if ru:
        lines += ['', 'Дальше: для исследования формата нужен сам data.stg из одного PAK.',
                  'В WinRAR выбери [scene]:data.stg → «Извлечь», затем передай файл для исследования.',
                  'Если он слишком большой, отправь этот отчёт и размер файла. Не передавай сохранения игры.',
                  'Исходные .pak и .stg не переписывались.']
    else:
        lines += ['', 'Next: analysis requires an actual data.stg from a game PAK.',
                  'In WinRAR select [scene]:data.stg → Extract, then provide that file for study.',
                  'If too large, send this report and the file size. Game saves are not needed.',
                  'Original .pak and .stg files were not changed.']
    return '\n'.join(lines) + '\n'


def inspect_path(path: str | Path, *, lang='ru'):
    """Scan a folder of PAKs, one PAK, or a standalone STG.

    For entire game folders, only archive directory metadata is read; no payloads.
    For one PAK/STG, at most 16 MiB of one STG is streamed as a binary probe.
    """
    path = Path(path)
    if path.is_dir():
        candidates = sorted(p for p in path.glob('*.pak') if p.is_file())[:MAX_ARCHIVES]
        if not candidates:
            raise ValueError('В выбранной папке нет файлов .pak / No .pak files in selected folder')
        results = [scan_pak(p, probe=False) for p in candidates]
    elif path.suffix.lower() == '.stg':
        results = [scan_stg(path)]
    elif path.suffix.lower() in ('.pak', '.zip'):
        results = [scan_pak(path, probe=True)]
    else:
        raise ValueError('Выбери папку PAK, файл .pak, .zip или .stg')
    return {'results': results, 'report': format_report(results, str(path), lang),
            'files': len(results), 'stg': sum(len(x['stg_names']) for x in results),
            'json': sum(len(x['json_names']) for x in results),
            'errors': sum(bool(x['error']) for x in results)}


def main():
    """Standalone Windows-friendly fallback if the main GUI cannot start."""
    import argparse
    parser = argparse.ArgumentParser(description='Read-only SnowRunner PAK/STG diagnostic')
    parser.add_argument('path', nargs='?', help='Path to client folder or .pak / .stg file')
    parser.add_argument('--lang', choices=('ru', 'en'), default='ru')
    args = parser.parse_args()
    source = args.path or input('Путь к папке client или файлу PAK/STG: ').strip().strip('"')
    outcome = inspect_path(source, lang=args.lang)
    report_path = Path.home() / 'SnowRunnerCraftAssistant' / 'SNOWRUNNER_SCAN_REPORT.txt'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(outcome['report'], encoding='utf-8')
    print(f'Файлов: {outcome["files"]}; STG: {outcome["stg"]}; JSON: {outcome["json"]}')
    print('Отчёт:', report_path)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, EOFError) as exc:
        print('Не удалось выполнить проверку:', exc)
        raise SystemExit(1)
