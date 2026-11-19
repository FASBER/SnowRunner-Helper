"""Optional import of SnowRunner craftSettings from locally owned game-zone JSON.

Only records with the exact craftSettings structure described in Saber's modding docs
are accepted. This tool does not certify an archive as unmodified or officially signed.
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path

SOURCE_DOC = ('https://expeditions-guides.saber.games/map_modding/creating_a_map/'
              'zones/snowrunner_zones/storehouse_craft_and_energy_zones/')
MAX_FILE = 4 * 1024 * 1024
MAX_TOTAL = 192 * 1024 * 1024
MAX_FILES = 15000


def _normalized(value):
    return re.sub(r'[^a-z0-9а-яё]+', '', str(value).casefold())


def build_aliases(cargo):
    result = {}
    ambiguous = set()
    for cid, item in cargo.items():
        for label in (cid, item.get('en', ''), item.get('ru', ''),
                      'Cargo_' + cid, 'cargo_' + cid):
            key = _normalized(label)
            if key in result and result[key] != cid:
                ambiguous.add(key)
            else:
                result[key] = cid
    for key in ambiguous:
        result.pop(key, None)
    return result


def _walk(node):
    if isinstance(node, dict):
        if isinstance(node.get('craftSettings'), list):
            yield node['craftSettings']
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _entries_from_json(content, file_name):
    root = json.loads(content)
    for group in _walk(root):
        for entry in group:
            if isinstance(entry, dict):
                yield entry, file_name


def _source_files(path):
    path = Path(path)
    if path.suffix.lower() == '.json':
        if path.stat().st_size > MAX_FILE:
            raise ValueError('JSON file is too large / Файл JSON слишком большой')
        yield path.name, path.read_bytes()
        return
    if path.suffix.lower() not in ('.pak', '.zip') or not zipfile.is_zipfile(path):
        raise ValueError('Choose game-zone JSON or ZIP/PAK with JSON files / Выберите JSON или PAK/ZIP с JSON')
    total = 0
    with zipfile.ZipFile(path) as archive:
        for i, item in enumerate(archive.infolist()):
            if i >= MAX_FILES or total >= MAX_TOTAL:
                break
            if item.is_dir() or not item.filename.lower().endswith('.json'):
                continue
            if item.file_size > MAX_FILE or total + item.file_size > MAX_TOTAL:
                continue
            total += item.file_size
            with archive.open(item) as f:
                yield item.filename, f.read(MAX_FILE + 1)


def describe_import_failure(path, report, lang='ru'):
    """Actionable, honest explanation of a zero-result import."""
    filename = Path(path).name
    is_ru = lang == 'ru'
    parsed = report.get('json_files', 0)
    found = report.get('craft_entries', 0)
    json_candidates = report.get('json_candidates', 0)
    archive_entries = report.get('archive_entries', 0)
    unknown = report.get('unknown_ids', [])
    if is_ru:
        head = (f'Файл: {filename}\n'
                f'JSON-файлов в архиве: {json_candidates}\n'
                f'JSON успешно прочитано: {parsed}\n'
                f'Записей в craftSettings: {found}\n')
        if not json_candidates:
            reason = ('В файле нет доступных JSON с рецептами. Архивы карт SnowRunner могут '
                      'содержать данные в других форматах. Текущая версия импортирует '
                      'только JSON с craftSettings.')
        elif not parsed:
            reason = ('JSON обнаружены, но не удалось их прочитать. Возможно, они '
                      'повреждены, имеют нестандартный формат или превышают лимит размера.')
        elif not found:
            reason = ('JSON прочитаны, но ни в одном нет списка craftSettings. '
                      'Возможно, выбран архив не той карты либо настройки производственных зон '
                      'хранятся в другом формате.')
        elif unknown:
            reason = ('Рецепты найдены, но названия грузов не совпали с каталогом приложения. '
                      'Неизвестные ID: ' + ', '.join(unknown[:8]))
        else:
            reason = ('Записи craftSettings найдены, но их поля или количества отличаются '
                      'от ожидаемой структуры, либо материалы отсутствуют в каталоге.')
        tail = ('\n\nПроверь содержимое PAK в 7-Zip. Если там нет JSON с craftSettings, '
                'импорт напрямую из этого PAK пока не поддерживается. Не изменяй файлы игры.')
    else:
        head = (f'File: {filename}\n'
                f'JSON files in archive: {json_candidates}\n'
                f'JSON files parsed: {parsed}\n'
                f'craftSettings entries: {found}\n')
        if not json_candidates:
            reason = 'No accessible JSON files. Some SnowRunner map PAKs use other formats; only JSON craftSettings can be imported.'
        elif not parsed:
            reason = 'JSON files were found but not parsed. They may be malformed, non-standard, or exceed size limits.'
        elif not found:
            reason = 'Parsed JSON files do not contain craftSettings. Another map or format may be needed.'
        elif unknown:
            reason = 'Recipes contain cargo names not matched by this catalog. Unknown IDs: '+', '.join(unknown[:8])
        else:
            reason = 'craftSettings entries were found, but their schema or cargo quantities are not supported.'
        tail = '\n\nCheck the PAK in 7-Zip for JSON with craftSettings. Do not modify game files.'
    return head + '\n' + reason + tail


def _count_archive_json(path):
    p = Path(path)
    if p.suffix.lower() == '.json':
        return 1, 1
    if p.suffix.lower() not in ('.pak', '.zip') or not zipfile.is_zipfile(p):
        return 0, 0
    with zipfile.ZipFile(p) as z:
        entries = z.infolist()
        return len(entries), sum(1 for info in entries if not info.is_dir() and info.filename.lower().endswith('.json'))


def import_recipes(path, cargo):
    # A SnowRunner initial.cache_block contains text-serialized craftSettings,
    # not ordinary JSON. Import only fully parsed structured blocks.
    p = Path(path)
    if p.name.lower().endswith('.cache_block'):
        from cache_craft import game_recipes_from_cache
        return game_recipes_from_cache(p, cargo)
    if p.suffix.lower() == '.pak' and zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            candidates=[i for i in z.infolist() if i.filename.lower().endswith('initial.cache_block') and i.file_size <= 96*1024*1024]
            if candidates:
                import tempfile
                from cache_craft import game_recipes_from_cache
                with tempfile.TemporaryDirectory() as td:
                    t=Path(td)/'initial.cache_block'
                    with z.open(candidates[0]) as f, t.open('wb') as out:
                        import shutil
                        shutil.copyfileobj(f,out,1024*1024)
                    return game_recipes_from_cache(t,cargo)
    """Return accepted recipes and report. Unrecognized cargo IDs are NEVER guessed."""
    aliases = build_aliases(cargo)
    archive_entries, json_candidates = _count_archive_json(path)
    recipes = []
    unmatched = set()
    seen = set()
    parsed_files = 0
    relevant = 0
    source_hash = hashlib.sha256()
    for fname, content in _source_files(path):
        source_hash.update(fname.encode('utf-8', 'replace'))
        source_hash.update(hashlib.sha256(content).digest())
        try:
            entries = list(_entries_from_json(content, fname))
        except (ValueError, UnicodeError, RecursionError):
            continue
        parsed_files += 1
        for entry, filename in entries:
            relevant += 1
            # Only precisely shaped official crafting entries; generator energy is not cargo.
            target_raw = entry.get('name')
            count = entry.get('craftCount')
            components = entry.get('cargoComponents')
            if not isinstance(target_raw, str) or not isinstance(count, int) or count < 1 or count > 999:
                continue
            if not isinstance(components, list):
                continue
            output = aliases.get(_normalized(target_raw))
            if output is None:
                unmatched.add(target_raw)
                continue
            ingredients = {}
            valid = True
            for item in components:
                if not isinstance(item, dict):
                    valid = False
                    break
                raw = item.get('name')
                qty = item.get('count')
                cid = aliases.get(_normalized(raw))
                if cid is None:
                    unmatched.add(str(raw))
                    valid = False
                    break
                if not isinstance(qty, int) or qty < 1 or qty > 999:
                    valid = False
                    break
                ingredients[cid] = ingredients.get(cid, 0) + qty
            if not valid:
                continue
            energy = entry.get('energy', 0)
            if not isinstance(energy, (int, float)) or energy < 0:
                continue
            if not ingredients and not energy:
                continue
            signature = (filename, output, count, tuple(sorted(ingredients.items())), energy)
            if signature in seen:
                continue
            seen.add(signature)
            digest = hashlib.sha256(repr(signature).encode()).hexdigest()[:16]
            title = cargo[output]['ru']
            recipes.append({
                'id': 'game-' + digest, 'region': 'game_files', 'map': Path(filename).stem,
                'name': {'ru': title, 'en': cargo[output]['en']},
                'inputs': ingredients, 'outputs': {output: count},
                'generator': bool(energy), 'energy': energy,
                'notes': {'ru': 'Импортировано из файла: ' + filename,
                          'en': 'Imported from file: ' + filename},
                'verified': 'local_game_data', 'source_format_url': SOURCE_DOC,
            })
    return recipes, {'json_files': parsed_files, 'craft_entries': relevant,
                     'json_candidates': json_candidates, 'archive_entries': archive_entries,
                     'imported': len(recipes), 'unknown_ids': sorted(unmatched)[:40],
                     'files_digest': source_hash.hexdigest()}
