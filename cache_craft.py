"""Read-only extractor of explicit craftSettings from an initial.cache_block (SnowRunner).
Never interprets inferred/truncated data as recipes.
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_DOC = 'https://expeditions-guides.saber.games/map_modding/creating_a_map/zones/snowrunner_zones/storehouse_craft_and_energy_zones/'


def match_balanced(data:bytes, open_pos:int):
    opens={ord('['):ord(']'),ord('{'):ord('}')}
    open_token=data[open_pos]
    if open_token not in opens: raise ValueError('Missing opening bracket')
    stack=[opens[open_token]]
    quoted=False; escaped=False
    for i in range(open_pos+1,len(data)):
        c=data[i]
        if quoted:
            if escaped: escaped=False
            elif c==92:escaped=True
            elif c==34:quoted=False
            continue
        if c==34:quoted=True
        elif c in opens: stack.append(opens[c])
        elif c in (ord(']'),ord('}')):
            if not stack or c!=stack.pop(): raise ValueError('Unbalanced delimiters')
            if not stack:return i
    raise ValueError('Truncated block')


def list_items(data:bytes):
    """Return complete top-level {...} objects from a [..] contents."""
    items=[];i=0
    while i<len(data):
        if data[i]==ord('{'):
            end=match_balanced(data,i)
            items.append(data[i:end+1]);i=end+1
        else:i+=1
    return items


def field_str(block:bytes,name:str):
    m=re.search(rb'(?<![A-Za-z_])'+name.encode()+rb'\s*=\s*"([^"]*)"',block)
    return m.group(1).decode('utf8','replace') if m else None

def field_int(block:bytes,name:str,default=None):
    m=re.search(rb'(?<![A-Za-z_])'+name.encode()+rb'\s*=\s*(-?\d+)',block)
    return int(m.group(1)) if m else default

def before_zone(data:bytes,start:int):
    window=data[max(0,start-8000):start].decode('utf8','replace')
    z=re.search(r'^\s*ZonePropertyStorehouseCraft\s*=\s*\{\s*$',window,re.M)
    # Take last occurrence
    props=list(re.finditer(r'^( *)(ZonePropertyStorehouseCraft)\s*=\s*\{',window,re.M))
    p=props[-1] if props else None
    prefix=window[:p.start()] if p else window
    # Strongest evidence: directly associated zoneId + mapId in reward updates,
    # but only if it is close to the ZoneProperty block.
    recent=prefix[-1600:]
    zone_matches=list(re.finditer(r'\bzoneId\s*=\s*"([^"]+)"',recent))
    map_matches=list(re.finditer(r'\bmapId\s*=\s*"([^"]+)"',recent))
    if zone_matches and map_matches and map_matches[-1].start()>zone_matches[-1].start():
        zone=zone_matches[-1].group(1);mapname=map_matches[-1].group(1)
        return zone,mapname,'objective_reward'
    # Static zone: nearest enclosing key at 3-space indentation.
    names=list(re.finditer(r'^   ([A-Z][A-Z_0-9]+)\s*=\s*\{',prefix,re.M))
    if not names:
        return None,None,'unresolved_zone'
    zone=names[-1].group(1)
    mapname='level_'+zone[:2].lower()+'_'+zone[3:5]+'_'+zone[6:8] if re.match(r'^(?:US|RU)_\d\d_\d\d_',zone) else None
    return zone,mapname,'base_zone'


def extract(path):
    b=Path(path).read_bytes();results=[];zones=[];issues=[]
    for k,m in enumerate(re.finditer(rb'\bcraftSettings\s*=\s*\[',b),1):
        begin=m.end()-1
        end=match_balanced(b,begin)
        zone,mapname,origin=before_zone(b,m.start())
        items=list_items(b[begin+1:end]);zones.append({'zone_id':zone,'map_id':mapname,'origin':origin,'items':len(items),'offset':m.start()})
        for j,item in enumerate(items,1):
            name=field_str(item,'name')
            count=field_int(item,'craftCount',1)
            energy=field_int(item,'energy',0)
            inputs=[]
            comp=re.search(rb'\bcargoComponents\s*=\s*\[',item)
            if comp:
                cbeg=comp.end()-1;cend=match_balanced(item,cbeg)
                for c in list_items(item[cbeg+1:cend]):
                    inputs.append({'cargo_id':field_str(c,'name'),'count':field_int(c,'count',1)})
            if not name or count<=0 or energy<0 or any(not x['cargo_id'] or x['count']<=0 for x in inputs):
                issues.append({'zone':zone,'entry':j,'output':name,'reason':'invalid fields'})
                continue
            if not inputs and not energy:
                issues.append({'zone':zone,'entry':j,'output':name,'reason':'neither ingredients nor energy'})
                # preserve as an explicit entry but flag not importable; user may investigate
            results.append({'id':f'cache-{k:02d}-{j:02d}', 'source':'initial.cache_block', 'zone':zone,'map':mapname,'origin':origin,
                'output':{'cargo_id':name,'count':count},'inputs':inputs,'energy':energy,
                'confidence':'explicit_craftSettings','source_offset':m.start(),'source_item_index':j,
                'extraction_note':'Defaults assumed where omitted: count=1, craftCount=1.'})
    return results,zones,issues,hashlib.sha256(b).hexdigest()


# Internal SnowRunner cargo name => app catalog ID; no guesses for unknown IDs.
GAME_ALIASES = {'CargoMetalPlanks': 'metal_beams', 'CargoMetalRoll': 'metal_rolls', 'CargoPipesSmall': 'small_pipes', 'CargoPipesMedium': 'medium_pipes', 'CargoPipeLarge': 'large_pipe', 'CargoWoodenPlanks': 'wooden_planks', 'CargoLogsShort': 'short_logs', 'CargoLogsMedium': 'medium_logs', 'CargoLogsLong': 'long_logs', 'CargoConcreteBlocks': 'concrete_blocks', 'CargoConcreteSlab': 'concrete_slab', 'CargoBricks': 'bricks', 'CargoBags': 'cement', 'CargoBags2': 'packaged_sand', 'CargoContainerSmall': 'cargo_container', 'CargoCrateLarge': 'consumables', 'CargoForkliftCaravanContainer2': 'cabin', 'CargoRailway': 'rail_section', 'CargoBarrels': 'oil_barrels', 'CargoWaterPipe': 'water_pipe', 'CargoVehiclesSpareParts': 'vehicle_spare_parts', 'CargoTetrapod': 'tetrapod', 'CargoWoodenPlanks2': 'wooden_planks_type2', 'CargoWoodenPlanks4': 'wooden_planks_type4', 'CargoServiceSparePartsSpecial': 'service_spare_parts_special'}

def game_recipes_from_cache(path, cargo):
    """Read a standalone cache block. Raises on unknown IDs to avoid fake recipes."""
    path=Path(path)
    if path.stat().st_size > 96*1024*1024:raise ValueError('cache_block is larger than the 96MB safety limit')
    with path.open('rb') as f:
        sig=f.read(4)
    if sig!=b'1SER':raise ValueError('Not a supported SnowRunner 1SER cache_block')
    records,zones,issues,digest=extract(path)
    accepted=[];skipped=set();seen=set()
    for r in records:
        if not r['map'] or (r['zone'] or '').startswith('PROG_SANDBOX'):
            continue
        o=GAME_ALIASES.get(r['output']['cargo_id'])
        inputs={}
        for x in r['inputs']:
            i=GAME_ALIASES.get(x['cargo_id'])
            if i is None:skipped.add(x['cargo_id'])
            else:inputs[i]=inputs.get(i,0)+x['count']
        if o is None:
            skipped.add(r['output']['cargo_id'])
            continue
        if any(x['cargo_id'] not in GAME_ALIASES for x in r['inputs']):continue
        if o not in cargo or any(x not in cargo for x in inputs):continue
        sig=(r['map'],r['zone'],r['origin'],r['output']['cargo_id'],r['output']['count'],tuple(sorted(inputs.items())),r['energy'])
        rid='cache-'+hashlib.sha256(repr(sig).encode()).hexdigest()[:18]
        if rid in seen:continue
        seen.add(rid)
        rec={
          'id':rid,'region':r['map'],'map':r['map'],
          'name':{'ru':cargo[o]['ru'],'en':cargo[o]['en']},
          'inputs':inputs,'outputs':{o:r['output']['count']},
          'generator':r['energy']>0,'energy':r['energy'],
          'notes':{'ru':'Рецепт из игрового файла.',
                   'en':'Recipe from game file.'},
          'verified':'local_game_data','game_zone':r['zone'],
          'unlock_condition':r['origin'],
          'source_game_ids':{'output':r['output']['cargo_id'],'inputs':[x['cargo_id'] for x in r['inputs']]},
          'source_format_url':SOURCE_DOC
        }
        accepted.append(rec)
    report={'json_files':0,'craft_entries':len(records),'json_candidates':0,
            'archive_entries':len(zones),'imported':len(accepted),
            'unknown_ids':sorted(skipped),'files_digest':digest,'source_kind':'cache_block',
            'test_zone_entries_skipped':sum(1 for x in records if not x['map'])}
    return accepted,report
