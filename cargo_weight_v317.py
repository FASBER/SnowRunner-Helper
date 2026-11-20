"""Read-only cargo mass presentation. Never convert slot counts into mass.

Only source-attested numeric cargo weights are shown. The catalog in v0.31.6
contains no such values, so its correct output is 'Нет данных' / 'No data'.
"""
from __future__ import annotations
import math

VERIFIED_MASS_SOURCES = frozenset({'local_game_data', 'official_game_files'})


def verified_mass_t(entry):
    """Return mass in metric tons only for provenance-tagged game data."""
    if not isinstance(entry, dict):
        return None
    if entry.get('mass_source') not in VERIFIED_MASS_SOURCES:
        return None
    value = entry.get('mass_t')
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def cargo_weight_label(entry, lang='ru'):
    value = verified_mass_t(entry)
    if value is None:
        return 'Нет данных' if lang == 'ru' else 'No data'
    number = f'{value:.2f}'.rstrip('0').rstrip('.')
    if lang == 'ru':
        return number.replace('.', ',') + ' т'
    return number + ' t'
