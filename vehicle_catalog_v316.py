"""Evidence-led offline truck/trailer catalog and read-only personal fleet.

No invented truck entries, photos, capacities, DLC flags or trailer ownership.
The installed SnowRunner initial.pak is the only optional catalog source here.
Archive indexing is bounded and cacheable; this module never writes to game data.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import zipfile

MAX_ENTRIES = 100_000
MAX_CACHE_BYTES = 3_000_000
VALID_ID = re.compile(r'^[\w.\-]{2,120}$')


def _category_from_path(path):
    cleaned = path.lower().replace('\\','/')
    if not cleaned.endswith('.xml'):
        return None
    sections = cleaned.split('/')
    if 'classes' not in sections:
        return None
    tail = sections[sections.index('classes')+1:]
    if not tail:return None
    section = tail[0]
    # Only known class directory families. Do not infer mechanics from names.
    if section in ('trucks','truck'):
        return 'truck'
    if section in ('trailers','trailer'):
        return 'trailer'
    if section in ('truck_addons','truckaddons','addons'):
        return 'addon'
    return None


def classify_trailer_id(identifier):
    """Classify only the semitrailer prefix present in game IDs."""
    return 'semitrailer' if identifier.lower().startswith('semitrailer') else 'trailer'


def index_archive(path):
    archive = Path(path)
    if not archive.is_file() or archive.stat().st_size < 128:
        raise ValueError('Game initial.pak not found')
    records = {}
    with zipfile.ZipFile(archive,'r') as z:
        infos = z.infolist()
        if len(infos)>MAX_ENTRIES:
            raise ValueError('Initial.pak contains too many records')
        for info in infos:
            if info.is_dir():continue
            category = _category_from_path(info.filename)
            if category is None:continue
            stem = Path(info.filename.replace('\\','/')).stem
            if not VALID_ID.fullmatch(stem) or stem.startswith('_'):
                continue
            if category=='trailer':
                category=classify_trailer_id(stem)
            key=(category,stem.casefold())
            records[key] = {'id':stem,'category':category,
                            'source':'local initial.pak','path':info.filename}
    return sorted(records.values(),key=lambda r:(r['category'],r['id'].casefold()))


def read_cached_catalog(user_directory):
    path = Path(user_directory)/'vehicle_catalog_v316.json'
    try:
        if path.stat().st_size>MAX_CACHE_BYTES:return []
        data=json.loads(path.read_text(encoding='utf-8'))
        if data.get('schema')!=1:return []
        return [r for r in data.get('records',[]) if isinstance(r,dict) and
                r.get('category') in ('truck','trailer','semitrailer','addon') and
                isinstance(r.get('id'),str)][:30000]
    except (OSError,ValueError,TypeError,AttributeError):
        return []


def scan_and_cache_catalog(archive, user_directory):
    from os import replace
    records=index_archive(archive)
    folder=Path(user_directory)
    folder.mkdir(parents=True,exist_ok=True)
    dest=folder/'vehicle_catalog_v316.json'
    tmp=folder/'vehicle_catalog_v316.json.tmp'
    # App cache only; never modify the user's real game archive.
    tmp.write_text(json.dumps({'schema':1,'archive':str(archive),'records':records},
                 ensure_ascii=False,indent=2),encoding='utf-8')
    replace(tmp,dest)
    return records


def fleet_from_save(raw):
    """Locate trucks stored in retained list, garages and registered on maps.

    The main Save JSON does NOT reliably include trailers currently placed on
    maps. Never label purchased trailer upgrade counts as owned trailers.
    """
    data=raw
    if not isinstance(data,dict):return []
    for wrapper in ('CompleteSave','CompleteSave1','CompleteSave2'):
        if isinstance(data.get(wrapper),dict):
            data=data[wrapper];break
    if isinstance(data.get('SslValue'),dict):data=data['SslValue']
    result=[]
    prof=data.get('persistentProfileData')
    if not isinstance(prof,dict):prof={}
    for record in prof.get('trucksInWarehouse',[]) if isinstance(prof.get('trucksInWarehouse'),list) else []:
        if isinstance(record,dict) and isinstance(record.get('type'),str) and record['type']:
            result.append({'id':record['type'],'where':'Склад техники','source':'trucksInWarehouse'})
    garages=data.get('garagesData')
    if isinstance(garages,dict):
        for map_id,garage in list(garages.items())[:1000]:
            if not isinstance(garage,dict):continue
            slots=garage.get('slotsDatas')
            if not isinstance(slots,dict):continue
            for slot_name,slot in list(slots.items())[:20]:
                desc=slot.get('truckDesc') if isinstance(slot,dict) else None
                if not isinstance(desc,dict):continue
                truck_type=desc.get('type')
                if isinstance(truck_type,str) and truck_type:
                    result.append({'id':truck_type,'where':f'Гараж: {map_id} ({slot_name})',
                                   'source':'garagesData'})
    # Some game builds use modTruckOnLevels; those are not necessarily owned.
    return result


def fleet_from_source(path):
    from save_reader_v315 import read_save_json
    return fleet_from_save(read_save_json(Path(path)))


def summary_owned(snapshot):
    retained=(snapshot or {}).get('retained_trucks') or {}
    entries=retained.get('models') if isinstance(retained,dict) else {}
    if not isinstance(entries,dict):return []
    return [{'id':k,'count':v} for k,v in entries.items()
            if isinstance(k,str) and isinstance(v,int) and v>0]


def evidence_image_path(vehicle_id,category,root, user_dir=None):
    """Use only exact-ID provided artwork; never substitute a different model."""
    if not VALID_ID.fullmatch(vehicle_id):return None
    candidates=[]
    if user_dir is not None:
        candidates.append(Path(user_dir)/'vehicle_icons'/category/(vehicle_id+'.png'))
    candidates.append(Path(root)/'assets'/'vehicles'/category/(vehicle_id+'.png'))
    for path in candidates:
        if path.is_file():
            return path
    return None
