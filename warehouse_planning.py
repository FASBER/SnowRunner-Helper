"""Conservative per-warehouse inventory preview from *unverified* save fields.

The game save is never modified. Cargo IDs are mapped *manually* by the user;
unknown and ambiguous fields cannot silently enter a numeric plan.
"""
from __future__ import annotations
from core import CARGO


def preview_warehouse(snapshot: dict, warehouse_id: str, cargo_mapping: dict,
                      manifest: list[tuple[str, int]]) -> dict:
    depots = snapshot.get('cargo_depots', {}) if isinstance(snapshot, dict) else {}
    matches = [x for x in depots.get('candidates', [])
               if isinstance(x, dict) and x.get('warehouse_id') == warehouse_id]
    if len(matches) != 1:
        raise ValueError('Warehouse unavailable or ambiguous; choose a unique candidate')
    raw = matches[0].get('cargo', {})
    if not isinstance(raw, dict) or not isinstance(cargo_mapping, dict):
        raise ValueError('Unsupported warehouse information')
    quantities = {}
    ambiguous = set()
    for raw_id, amount in raw.items():
        cargo_id = cargo_mapping.get(raw_id)
        if not isinstance(cargo_id, str) or cargo_id not in CARGO or type(amount) is not int or amount < -1:
            continue
        if cargo_id in quantities:
            ambiguous.add(cargo_id)
        else:
            quantities[cargo_id] = amount
    rows = []
    for cargo_id, requested in manifest:
        if not isinstance(cargo_id, str) or cargo_id not in CARGO or type(requested) is not int or requested < 1:
            continue
        if cargo_id in ambiguous or cargo_id not in quantities:
            rows.append({'cargo_id': cargo_id, 'required': requested,
                         'observed': None, 'shortage': None, 'status': 'unknown'})
        elif quantities[cargo_id] == -1:
            rows.append({'cargo_id': cargo_id, 'required': requested,
                         'observed': -1, 'shortage': 0, 'status': 'tentative_unlimited'})
        else:
            count = quantities[cargo_id]
            rows.append({'cargo_id': cargo_id, 'required': requested,
                         'observed': count, 'shortage': max(0, requested - count),
                         'status': 'tentative_shortage' if requested > count else 'tentative_covered'})
    return {'warehouse_id': warehouse_id, 'verified': False, 'auto_deduction': False,
            'rows': rows, 'mapped_raw_ids': sorted(k for k in raw if cargo_mapping.get(k) in CARGO),
            'unmapped_raw_ids': sorted(k for k in raw if cargo_mapping.get(k) not in CARGO),
            'ambiguous_cargo_ids': sorted(ambiguous),
            'warning': 'Unverified save fields and manual ID mapping; estimates only.'}
