"""Privacy-conscious read-only view of a SnowRunner JSON save's field structure.

Only field *names from a reviewed allowlist*, type names and depth are displayed.
No values, paths, objective IDs, map IDs, player IDs or truck identifiers.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from game_bridge import read_save_json

KNOWN_FIELDS = frozenset({
    'CompleteSave','SslType','SslValue','persistentProfileData','objectiveStates',
    'finishedObjs','visitedLevels','levelGarageStatuses','levelStates','gameTime',
    'isFirstGarageDiscovered','money','experience','trucksInWarehouse','type',
    'fuel','damage','engineDamage','ownedTrucks','unlockedItemNames','cargoAvailable',
    'truckData','garage','trucks','mapId','levelId','retainedMapId',
    'warehouse','zones','id','name','zoneId','zoneName','discoveredTrucks',
    'discoveredUpgrades','lastLevelState','gameStat','distance',
})


def structural_report(raw: dict, *, max_nodes: int = 8000, max_depth: int = 7) -> str:
    if not isinstance(raw, dict):
        raise ValueError('Expected save JSON object')
    paths = defaultdict(set)
    todo = [(raw, '$', 0)]
    seen = 0
    while todo and seen < max_nodes:
        value, path, depth = todo.pop()
        seen += 1
        kind = ('object' if isinstance(value, dict) else 'array' if isinstance(value, list)
                else 'boolean' if isinstance(value, bool) else
                'number' if isinstance(value, (int,float)) else
                'text' if isinstance(value, str) else 'null' if value is None else 'other')
        paths[path].add(kind)
        if depth >= max_depth:
            continue
        if isinstance(value, dict):
            # Values and arbitrary keys (often IDs) are never output.
            for key, child in list(value.items())[:2000]:
                safe = key if isinstance(key, str) and key in KNOWN_FIELDS else '*'
                todo.append((child, path + '.' + safe, depth + 1))
        elif isinstance(value, list):
            # Only a short sample of types; no array contents are included.
            for child in value[:20]:
                todo.append((child, path + '[]', depth + 1))
    result = ['SnowRunner save structure — REDACTED',
              'Only known field names and type shapes. No save values or IDs.',
              f'Scanned up to {max_depth} levels; node scan truncated: {bool(todo)}', '']
    result.extend(f'{path}: {", ".join(sorted(types))}' for path, types in sorted(paths.items()))
    return '\n'.join(result)


def report_save_structure(path: Path) -> str:
    return structural_report(read_save_json(path))
