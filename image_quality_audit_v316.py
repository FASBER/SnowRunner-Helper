"""Offline asset inventory. Never manufactures 4K detail or substitutes truck art.

Used for release QA: count icon coverage, report source pixel size and alpha.
The fact that an image has 3840 px does not prove original 4K detail.
"""
from __future__ import annotations
from pathlib import Path
from PIL import Image


def inspect_art(path):
    try:
        p=Path(path)
        with Image.open(p) as im:
            w,h=im.size
            alpha=('A' in im.getbands()) or ('transparency' in im.info)
            return {'file':p.name,'width':w,'height':h,'transparent_capable':alpha,
                    'long_side_4k':max(w,h)>=3840,
                    'large_source':max(w,h)>=2160,'bytes':p.stat().st_size}
    except (OSError,ValueError):
        return {'file':Path(path).name,'error':'unreadable'}


def audit_folder(path, expected_ids=()):
    root=Path(path)
    present={p.stem:p for p in root.glob('*.png')} if root.is_dir() else {}
    expected={str(cid) for cid in expected_ids}
    scanned=[inspect_art(p) for p in present.values()]
    return {'directory':str(root),'found':len(present),
            'expected':len(expected),'missing':sorted(expected-set(present)),
            '4k_by_pixel_count':sum(1 for a in scanned if a.get('long_side_4k')),
            'transparent_capable':sum(1 for a in scanned if a.get('transparent_capable')),
            'artwork':sorted(scanned,key=lambda a:a['file'])}


def audit_game_assets(root, cargos=(), recipes=(), vehicles=()):
    root=Path(root)
    return {
        'cargo':audit_folder(root/'assets'/'cargo',cargos),
        'craft':audit_folder(root/'assets'/'recipes',recipes),
        'trucks':audit_folder(root/'assets'/'vehicles'/'truck',vehicles),
        'trailer':audit_folder(root/'assets'/'vehicles'/'trailer'),
        'semitrailer':audit_folder(root/'assets'/'vehicles'/'semitrailer'),
        'addons':audit_folder(root/'assets'/'vehicles'/'addon'),
        'note':'Dimensions/alpha are measurable; originality, detail and use permissions require human/source review.'
    }
