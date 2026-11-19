"""Read-only SnowRunner save snapshotting and isolated application-owned profiles.

This module NEVER writes to a game save. Only our own per-profile JSON files
under the application's user-data directory may be updated.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from game_bridge import profile_key, read_save_json

PROFILE_KEY_RE = re.compile(r'^(?:local|[0-9a-f]{20})$')
MAX_ITEM_QUANTITY = 9999
MAX_NAMED_DRAFTS = 100
MAX_DRAFT_HISTORY = 30


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def unwrap_save(value: dict) -> dict:
    """Official JSON envelopes vary; do not search arbitrary nested objects."""
    current = _obj(value)
    if isinstance(current.get('CompleteSave'), dict):
        current = current['CompleteSave']
    if isinstance(current.get('SslValue'), dict):
        current = current['SslValue']
    return current


def _nonnegative_number(value: Any):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value < 10**15:
        return value
    return None


def _fleet(trucks: Any) -> dict:
    """Show retained truck models only; do not mislabel these as map garages."""
    if not isinstance(trucks, list):
        return {'available': False}
    models = {}
    unknown = 0
    for truck in trucks[:5000]:
        model = _obj(truck).get('type')
        if isinstance(model, str) and model and len(model) <= 128:
            models[model] = models.get(model, 0) + 1
        else:
            unknown += 1
    return {'available': True, 'count': len(trucks), 'models': dict(sorted(models.items())),
            'unidentified': unknown}



def _string_list(value: Any, *, cap: int = 10000) -> dict:
    """Explicitly stored IDs only; malformed or unknown formats remain unavailable."""
    if not isinstance(value, list):
        return {'available': False, 'count': None, 'items': []}
    ids = sorted({s for s in value[:cap] if isinstance(s, str) and 0 < len(s) <= 160})
    return {'available': True, 'count': len(ids), 'items': ids[:500],
            'truncated': len(value) > cap or len(ids) > 500}


def _garage_statuses(value: Any) -> dict:
    """Status 2 is open; other integer values are preserved but not guessed."""
    if not isinstance(value, dict):
        return {'available': False, 'count': None, 'open_count': None, 'opened': []}
    opened = []
    statuses = {}
    for map_id, status in list(value.items())[:5000]:
        if not isinstance(map_id, str) or not 0 < len(map_id) <= 160:
            continue
        if type(status) is int and 0 <= status <= 100:
            statuses[map_id] = status
            if status == 2:
                opened.append(map_id)
    return {'available': True, 'count': len(statuses), 'open_count': len(opened),
            'opened': sorted(opened)[:500], 'statuses': statuses if len(statuses) <= 500 else {},
            'truncated': len(value) > 500 or len(opened) > 500}


def _warehouse_candidates(save: dict) -> dict:
    """Identify *candidate* facility cargoAvailable counters, never live inventory.

    JSON layout varies by game version. We only show exact cargoAvailable mappings
    associated with a warehouse identifier. This is intentionally NOT used as
    authoritative inventory or as an input to automatic cargo planning.
    """
    pending = [(save, (), 0)]
    candidates: list[dict] = []
    examined = 0
    too_many = False
    while pending:
        node, ancestry, depth = pending.pop()
        examined += 1
        if examined > 200_000:
            too_many = True
            break
        if depth > 12 or len(candidates) >= 250:
            if len(candidates) >= 250:
                too_many = True
            continue
        if isinstance(node, dict):
            facility_name = next((node[k] for k in ('id', 'name', 'zoneId', 'zoneName')
                                  if isinstance(node.get(k), str) and
                                  node[k].lower().startswith('warehouse_')), None)
            location_keys = (facility_name,) if facility_name else ancestry
            location = next((k for k in reversed(location_keys)
                             if isinstance(k, str) and k.lower().startswith('warehouse_')), None)
            items = node.get('cargoAvailable')
            if location and isinstance(items, dict):
                valid = {}
                for cargo, count in list(items.items())[:500]:
                    if (isinstance(cargo, str) and 0 < len(cargo) <= 128
                            and type(count) is int and -1 <= count <= 10_000_000):
                        valid[cargo] = count
                if valid:
                    candidates.append({'warehouse_id': location, 'cargo': dict(sorted(valid.items())),
                                       'raw_field': 'cargoAvailable', 'verified': False})
            for key, child in list(node.items())[:2000]:
                if isinstance(child, (dict, list)):
                    new_ancestry = ancestry + ((key,) if isinstance(key, str) else ())
                    pending.append((child, new_ancestry, depth + 1))
        elif isinstance(node, list):
            for child in node[:2000]:
                if isinstance(child, (dict, list)):
                    pending.append((child, ancestry, depth + 1))
    candidates.sort(key=lambda c: c['warehouse_id'])
    return {'available': bool(candidates), 'verified': False,
            'count': len(candidates), 'candidates': candidates,
            'truncated': too_many,
            'reason': ('candidate cargoAvailable fields, unverified save schema'
                       if candidates else 'no recognized warehouse cargoAvailable mapping')}


def extract_snapshot(raw: dict) -> dict:
    """Read-only, conservative extraction of known save JSON fields.

    Completed objectives in finishedObjs are explicitly recorded by the game.
    The warehouse mapping is tentative and never considered verified inventory.
    Unknown or absent fields are not misrepresented as zeros.
    """
    value = unwrap_save(raw)
    profile = _obj(value.get('persistentProfileData'))
    objectives = value.get('objectiveStates')
    unlocked = profile.get('unlockedItemNames')
    completed = _string_list(value.get('finishedObjs'))
    visited = _string_list(value.get('visitedLevels'))
    garages = _garage_statuses(value.get('levelGarageStatuses'))
    recognized = (isinstance(value.get('persistentProfileData'), dict) or
                  isinstance(value.get('objectiveStates'), dict) or
                  isinstance(value.get('finishedObjs'), list) or
                  isinstance(value.get('visitedLevels'), list) or
                  isinstance(value.get('levelGarageStatuses'), dict) or
                  isinstance(value.get('gameTime'), (int, float)) or
                  isinstance(value.get('isFirstGarageDiscovered'), bool))
    return {
        'format': 'snowrunner-json' if recognized else 'unknown-json',
        'recognized': recognized,
        'fields_present': sorted(str(k) for k in value.keys())[:150],
        'statistics': {
            'money': _nonnegative_number(profile.get('money')),
            'experience': _nonnegative_number(profile.get('experience')),
            'game_time': _nonnegative_number(value.get('gameTime')),
        },
        'objectives': {
            'available': isinstance(objectives, dict),
            'known_entries': len(objectives) if isinstance(objectives, dict) else None,
            'completed': completed['count'] if completed['available'] else None,
            'finished_ids': completed['items'],
            'finished_truncated': completed.get('truncated', False),
        },
        'retained_trucks': _fleet(profile.get('trucksInWarehouse')),
        'unlocked_item_records': len(unlocked) if isinstance(unlocked, dict) else None,
        'visited_levels': visited,
        'garages': garages,
        'cargo_depots': _warehouse_candidates(value),
        'map_fog': {'available': False, 'reason': 'fog is stored in separate binary files'},
    }


def save_signature(path: Path) -> tuple[int, int]:
    """Fingerprint only; file modification does NOT identify active game slot."""
    stat = Path(path).stat()
    return stat.st_size, stat.st_mtime_ns


def snapshot_save(path: Path) -> tuple[dict, tuple[int, int]]:
    """Double-check that a save was not replaced during parsing."""
    file = Path(path)
    before = save_signature(file)
    parsed = read_save_json(file)
    result = extract_snapshot(parsed)
    if not result['recognized']:
        raise ValueError('JSON save has no recognized SnowRunner fields; no data imported')
    after = save_signature(file)
    if before != after:
        raise ValueError('Save changed while parsing; retry after the game saves')
    return result, after


def _clean_manifest(manifest: Any) -> list[list]:
    """Only valid cargo/quantity pairs enter stored drafts (no arbitrary data)."""
    from core import CARGO, cargo_slots
    if not isinstance(manifest, list):
        return []
    cleaned = []
    for row in manifest[:500]:
        if not isinstance(row, (list, tuple)) or len(row) != 2:
            continue
        cargo, amount = row
        if (not isinstance(cargo, str) or cargo not in CARGO
                or cargo_slots(cargo) is None or not isinstance(amount, int)
                or isinstance(amount, bool) or not 1 <= amount <= MAX_ITEM_QUANTITY):
            continue
        cleaned.append([cargo, amount])
    return cleaned


class ProfileStore:
    """One separate file per profile; app data never mixed with game saves."""
    def __init__(self, location: Path):
        self.root = Path(location)
        self.root.mkdir(parents=True, exist_ok=True)

    def file(self, key: str) -> Path:
        if not isinstance(key, str) or not PROFILE_KEY_RE.fullmatch(key):
            raise ValueError('Invalid profile identifier')
        return self.root / (key + '.json')

    def read(self, key: str) -> dict:
        path = self.file(key)
        if not path.exists():
            return {'version': 1, 'profile_key': key, 'draft': {'load': []},
                    'game_snapshot': None, 'source_path': None, 'last_signature': None}
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f'Profile data unreadable; preserved: {path}') from exc
        if not isinstance(data, dict) or data.get('profile_key') != key or data.get('version') != 1:
            raise ValueError(f'Unexpected profile structure; preserved: {path}')
        return data

    def _write(self, key: str, data: dict) -> None:
        target = self.file(key)
        # No writes to any game directory. Use exclusive tempfile + atomic replace.
        fd, name = tempfile.mkstemp(prefix='.profile-', suffix='.tmp', dir=str(self.root))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def save_draft(self, key: str, manifest: list, *, note: str | None = None) -> dict:
        data = self.read(key)
        draft = _obj(data.get('draft')).copy()
        new_load = _clean_manifest(manifest)
        # Keep bounded recovery checkpoints for *actual changes* only.
        # No history entry is created on forced autosave of the same load.
        if draft.get('updated_at') and _clean_manifest(draft.get('load')) != new_load:
            history = data.get('draft_history')
            history = history if isinstance(history, list) else []
            history.append({'load': _clean_manifest(draft.get('load')),
                            'note': str(draft.get('note', ''))[:5000],
                            'saved_at': str(draft.get('updated_at', ''))[:80]})
            data['draft_history'] = history[-MAX_DRAFT_HISTORY:]
        draft['load'] = new_load
        if note is not None:
            draft['note'] = str(note)[:5000]
        draft['updated_at'] = datetime.now(timezone.utc).isoformat()
        data['draft'] = draft
        self._write(key, data)
        return data

    @staticmethod
    def _draft_name(name: str) -> str:
        if not isinstance(name, str):
            raise ValueError('Draft name must be text')
        result = ' '.join(name.split())
        if not result or len(result) > 80 or any(ord(ch) < 32 for ch in result):
            raise ValueError('Draft name must contain 1–80 printable characters')
        return result

    @staticmethod
    def _named(data: dict) -> list[dict]:
        value = data.get('named_drafts', [])
        if not isinstance(value, list):
            raise ValueError('Invalid named drafts; file preserved')
        return value

    @staticmethod
    def _entry(items: list[dict], draft_id: str) -> dict:
        if not isinstance(draft_id, str):
            raise ValueError('Invalid draft ID')
        for item in items:
            if isinstance(item, dict) and item.get('id') == draft_id:
                return item
        raise ValueError('Named draft not found')

    @staticmethod
    def _unique_name(items: list[dict], name: str, *, exclude_id: str | None = None):
        normalized = name.casefold()
        for item in items:
            if (isinstance(item, dict) and item.get('id') != exclude_id and
                    str(item.get('name', '')).casefold() == normalized):
                raise ValueError('A draft with this name already exists in this profile')

    def list_named_drafts(self, key: str, query: str = '') -> list[dict]:
        items = self._named(self.read(key))
        search = str(query).strip().casefold()[:100]
        result = []
        for item in items[:MAX_NAMED_DRAFTS]:
            if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                continue
            title = str(item.get('name', ''))
            if search and search not in title.casefold():
                continue
            result.append({'id': item['id'], 'name': title, 'updated_at': item.get('updated_at'),
                           'load': _clean_manifest(item.get('load', [])),
                           'note': str(item.get('note', ''))[:5000]})
        return sorted(result, key=lambda x: x['name'].casefold())

    def create_named_draft(self, key: str, name: str, manifest: list, *, note: str = '') -> dict:
        data = self.read(key)
        items = self._named(data)
        if len(items) >= MAX_NAMED_DRAFTS:
            raise ValueError('Named draft limit reached')
        name = self._draft_name(name)
        self._unique_name(items, name)
        entry = {'id': uuid.uuid4().hex, 'name': name, 'load': _clean_manifest(manifest),
                 'note': str(note)[:5000], 'updated_at': datetime.now(timezone.utc).isoformat()}
        data['named_drafts'] = [*items, entry]
        self._write(key, data)
        return entry.copy()

    def rename_named_draft(self, key: str, draft_id: str, new_name: str) -> None:
        data = self.read(key)
        items = self._named(data)
        item = self._entry(items, draft_id)
        name = self._draft_name(new_name)
        self._unique_name(items, name, exclude_id=draft_id)
        item['name'] = name
        item['updated_at'] = datetime.now(timezone.utc).isoformat()
        self._write(key, data)

    def duplicate_named_draft(self, key: str, draft_id: str, name: str) -> dict:
        data = self.read(key)
        item = self._entry(self._named(data), draft_id)
        return self.create_named_draft(key, name, item.get('load', []), note=item.get('note', ''))

    def delete_named_draft(self, key: str, draft_id: str) -> None:
        data = self.read(key)
        items = self._named(data)
        self._entry(items, draft_id)
        data['named_drafts'] = [x for x in items if not (isinstance(x, dict) and x.get('id') == draft_id)]
        self._write(key, data)

    def restore_named_draft(self, key: str, draft_id: str) -> list[tuple[str, int]]:
        item = self._entry(self._named(self.read(key)), draft_id)
        # Save into current load and append its previous load to recovery history.
        self.save_draft(key, item.get('load', []), note=item.get('note', ''))
        return self.manifest(key)

    def list_routes(self, key: str) -> list[dict]:
        data = self.read(key)
        routes = data.get('routes', [])
        if not isinstance(routes, list):
            raise ValueError('Invalid route records; profile preserved')
        results = []
        for value in routes[:100]:
            if not isinstance(value, dict) or not isinstance(value.get('id'), str):
                continue
            stops = value.get('stops', [])
            if not isinstance(stops, list):
                continue
            results.append({'id': value['id'], 'name': str(value.get('name', ''))[:80],
                            'stops': [x for x in stops[:40] if isinstance(x, str)],
                            'load': _clean_manifest(value.get('load')),
                            'notes': str(value.get('notes', ''))[:2000],
                            'updated_at': value.get('updated_at', '')})
        return sorted(results, key=lambda x: x['name'].casefold())

    def save_route(self, key: str, name: str, stops: list, manifest: list,
                   *, route_id: str | None = None, notes: str = '') -> dict:
        name = self._draft_name(name)
        if (not isinstance(stops, list) or len(stops) > 40 or
                any(not isinstance(p, str) or not 1 <= len(p.strip()) <= 120 or
                    any(ord(c) < 32 for c in p) for p in stops)):
            raise ValueError('Route stops must be printable names (maximum 40)')
        data = self.read(key)
        routes = data.get('routes', [])
        if not isinstance(routes, list):
            raise ValueError('Invalid route records; profile preserved')
        if route_id is None and len(routes) >= 100:
            raise ValueError('Route limit reached')
        if route_id is not None and not isinstance(route_id, str):
            raise ValueError('Invalid route ID')
        if any(isinstance(p, dict) and str(p.get('name', '')).casefold() == name.casefold() and
               p.get('id') != route_id for p in routes):
            raise ValueError('A route with this name already exists')
        now = datetime.now(timezone.utc).isoformat()
        entry = {'id': route_id or uuid.uuid4().hex, 'name': name,
                 'stops': [p.strip() for p in stops], 'load': _clean_manifest(manifest),
                 'notes': str(notes)[:2000], 'updated_at': now}
        if route_id is not None:
            self._entry(routes, route_id)
            data['routes'] = [entry if isinstance(p, dict) and p.get('id') == route_id
                              else p for p in routes]
        else:
            data['routes'] = [*routes, entry]
        self._write(key, data)
        return entry.copy()

    def delete_route(self, key: str, route_id: str) -> None:
        data = self.read(key)
        routes = data.get('routes', [])
        if not isinstance(routes, list):
            raise ValueError('Invalid route records; profile preserved')
        self._entry(routes, route_id)
        data['routes'] = [p for p in routes if not (isinstance(p, dict) and p.get('id') == route_id)]
        self._write(key, data)

    def cargo_mappings(self, key: str) -> dict[str, str]:
        from core import CARGO
        value = self.read(key).get('manual_cargo_mappings', {})
        if not isinstance(value, dict):
            return {}
        return {raw: cid for raw, cid in value.items()
                if isinstance(raw, str) and 0 < len(raw) <= 128 and isinstance(cid, str) and cid in CARGO}

    def map_game_cargo(self, key: str, raw_id: str, cargo_id: str | None) -> None:
        from core import CARGO
        if not isinstance(raw_id, str) or not 0 < len(raw_id) <= 128:
            raise ValueError('Invalid game cargo ID')
        if cargo_id is not None and (not isinstance(cargo_id, str) or cargo_id not in CARGO):
            raise ValueError('Unknown catalog cargo ID')
        data = self.read(key)
        mapping = self.cargo_mappings(key)
        if cargo_id is None:
            mapping.pop(raw_id, None)
        else:
            mapping[raw_id] = cargo_id
        if len(mapping) > 500:
            raise ValueError('Too many cargo mappings')
        data['manual_cargo_mappings'] = mapping
        self._write(key, data)

    def list_draft_history(self, key: str) -> list[dict]:
        history = self.read(key).get('draft_history', [])
        if not isinstance(history, list):
            return []
        return [{'load': _clean_manifest(x.get('load')), 'note': str(x.get('note', ''))[:5000],
                 'saved_at': str(x.get('saved_at', ''))[:80]}
                for x in reversed(history[-MAX_DRAFT_HISTORY:]) if isinstance(x, dict)]

    def restore_draft_history(self, key: str, index: int) -> list[tuple[str, int]]:
        entries = self.list_draft_history(key)
        if type(index) is not int or not 0 <= index < len(entries):
            raise ValueError('History entry not found')
        old = entries[index]
        self.save_draft(key, old['load'], note=old['note'])
        return self.manifest(key)

    def save_game_snapshot(self, key: str, source: Path, snapshot: dict,
                           signature: tuple[int, int]) -> dict:
        if key == 'local' or key != profile_key(source):
            raise ValueError('Profile does not match game save path')
        data = self.read(key)
        # Updates only game_snapshot; user's existing draft and manual values survive.
        data['source_path'] = str(Path(source).resolve())
        data['game_snapshot'] = snapshot
        data['last_signature'] = list(signature)
        data['last_synced_utc'] = datetime.now(timezone.utc).isoformat()
        self._write(key, data)
        return data

    def manifest(self, key: str) -> list[tuple[str, int]]:
        return [tuple(x) for x in _clean_manifest(_obj(self.read(key).get('draft')).get('load', []))]


class SaveMonitor:
    """Debounced disk check. Only watches the *user-selected* save, never guesses."""
    def __init__(self):
        self.pending: dict[str, tuple[int, int]] = {}

    def check(self, source: Path, previous: list | tuple | None) -> str:
        """unchanged, pending, or changed (stable on two consecutive polls)."""
        source = Path(source)
        key = str(source.resolve())
        try:
            now = save_signature(source)
        except OSError:
            self.pending.pop(key, None)
            return 'missing'
        prior = previous if isinstance(previous, (list, tuple)) else []
        if list(now) == list(prior):
            self.pending.pop(key, None)
            return 'unchanged'
        if self.pending.get(key) == now:
            return 'changed'
        self.pending[key] = now
        return 'pending'
