"""Self-contained regression checks for the 0.31.16 overlay (no game install)."""
import json
import sys
import types
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from player_identity_v316 import (_persona_from_vdf, _steam_id_from_save_path,
    display_profile)
from hotkey_upgrade_v316 import pressed_modifiers
from vehicle_catalog_v316 import (index_archive, fleet_from_save,
    scan_and_cache_catalog, read_cached_catalog, evidence_image_path)
from changelog_ui_v316 import load_notes


def test_identity_not_a_fake_steam_name():
    app=SimpleNamespace(active_profile_key='profile-hash',config={},profiles=SimpleNamespace(
        read=lambda key:{'source_path':'C:/NotSteam/CompleteSave2.cfg'}))
    assert display_profile(app)=='Steam · слот 3'
    app.config['profile_display_names']={'profile-hash':'Зимний водитель'}
    assert display_profile(app)=='Зимний водитель'


def test_steam_persona_exact_id():
    sid='76561197960265729'
    p=Path('C:/Steam/userdata/1/1465360/remote/CompleteSave.cfg')
    assert _steam_id_from_save_path(p)==sid
    vdf='"users" { "'+sid+'" { "PersonaName" "Tester" } "76561197960265730" { "PersonaName" "Wrong" } }'
    assert _persona_from_vdf(vdf,sid)=='Tester'
    assert _persona_from_vdf(vdf,'76561197960265731') is None


def test_combo_shift_control_and_win():
    ev=SimpleNamespace(state=0x0001|0x0004)
    assert pressed_modifiers(ev)==['Ctrl','Shift']
    assert pressed_modifiers(SimpleNamespace(state=0),lambda vk:vk in (0xA2,0xA0,0x5B))==['Ctrl','Shift','Win']


def test_real_catalog_from_xml_paths(tmp_path):
    fake=tmp_path/'initial.pak'
    with zipfile.ZipFile(fake,'w') as z:
        z.writestr('[media]/classes/trucks/truck_4x4.xml','x'*100)
        z.writestr('[media]/classes/trailers/trailer_2.xml','')
        z.writestr('[media]/classes/trailers/semitrailer_heavy.xml','')
        z.writestr('[media]/classes/truck_addons/flatbed.xml','')
        z.writestr('[media]/textures/random.xml','')
    catalog=index_archive(fake)
    assert {(i['id'],i['category']) for i in catalog}=={
        ('truck_4x4','truck'),('trailer_2','trailer'),
        ('semitrailer_heavy','semitrailer'),('flatbed','addon')}
    assert scan_and_cache_catalog(fake,tmp_path)==catalog
    assert read_cached_catalog(tmp_path)==catalog
    assert evidence_image_path('truck_4x4','truck',tmp_path,tmp_path) is None


def test_fleet_uses_only_actual_save_records():
    payload = {
        'persistentProfileData':{'trucksInWarehouse':[
            {'type':'kenworth_963'},{'type':'tayga_6455b'}]},
        'garagesData':{'US_01_01':{'slotsDatas':{
            'slot1':{'truckDesc':{'type':'azov_73210'}},
            'slot2':{'truckDesc':None}}}},
        'modTruckOnLevels':[{'type':'not_known_to_be_owned'}]
    }
    doc={'CompleteSave2':{'SslValue':payload}}
    fleet=fleet_from_save(doc)
    assert len(fleet)==3
    assert any(x['id']=='azov_73210' and x['where'].startswith('Гараж:') for x in fleet)
    assert 'not_known_to_be_owned' not in [x['id'] for x in fleet]


def test_changelog_collapsible_notes_and_version():
    notes=load_notes(ROOT)
    assert notes[0]['version']=='0.31.16'
    assert 'Добавлено' in notes[0]['sections']


def test_weight_sort_missing_last(monkeypatch):
    import expedition_upgrade_v316 as up
    stub=types.ModuleType('core')
    stub._sort_name=lambda x,lang:x['id']
    stub.sort_cargo=lambda items,mode,lang:sorted(items,key=lambda x:x['id'])
    monkeypatch.setitem(sys.modules,'core',stub)
    records=[{'id':'x_unknown'}, {'id':'bricks'}, {'id':'metal_beams'}]
    sorted_rows=up.sort_entries(records,'weight_asc','ru')
    assert sorted_rows[-1]['id']=='x_unknown'
    assert [r['id'] for r in sorted_rows[:-1]]==['bricks','metal_beams'] or set(r['id'] for r in sorted_rows[:-1])=={'bricks','metal_beams'}
    assert up.sort_entries(records,'weight_desc','ru')[-1]['id']=='x_unknown'


def test_image_quality_checker_flags_missing_not_fake(tmp_path):
    from image_quality_audit_v316 import audit_folder
    from PIL import Image
    folder=tmp_path/'cargo';folder.mkdir()
    Image.new('RGBA',(32,32),(0,0,0,0)).save(folder/'bricks.png')
    report=audit_folder(folder,('bricks','metal_beams'))
    assert report['missing']==['metal_beams']
    assert report['transparent_capable']==1
    assert report['4k_by_pixel_count']==0


def test_release_metadata_synchronized():
    release=json.loads((ROOT/'version.json').read_text(encoding='utf-8'))
    assert release['version']=='0.31.16'
    assert (ROOT/'VERSION.txt').read_text().strip()==release['version']
    assert '0.31.16' in (ROOT/'setup_snowrunner.iss').read_text()
    assert '0.31.16' in (ROOT/'build_installer_windows.bat').read_text()


def test_ui_settings_button_hit_areas_inside_workplace(monkeypatch):
    import expedition_upgrade_v316 as up
    fakeappearance=types.ModuleType('appearance')
    fakeappearance.PRESETS={'snow':{'ru':'Снежный конвой','en':'Snow convoy'}}
    monkeypatch.setitem(sys.modules,'appearance',fakeappearance)
    coords=[]
    class Fake:
        reference_ui=True
        lang='ru'
        appearance={'preset':'snow'}
        app=SimpleNamespace(config={'theme':'game','ui_scale':100,'text_size':100},
            updater=SimpleNamespace(open_settings=lambda:None),
            overlay=SimpleNamespace(shortcut='Ctrl+Shift+F9',toggle=lambda:None,shortcut_dialog=lambda:None),
            appearance_editor=lambda:None,game_connection_dialog=lambda:None,recipe_editor=lambda:None,
            adjust=lambda *args:None)
        def round(self,*a):pass
        def line(self,*a):pass
        def txt(self,*a,**kw):pass
        def button(self,x1,y1,x2,y2,*a,**kw):coords.append((x1,y1,x2,y2))
        def about_dialog(self):pass
        def cycle_theme(self):pass
        def change(self,*a):pass
    up._draw_settings(Fake())
    assert len(coords)>=12
    assert all(200<=a<c<=1290 and 179<=b<d<=713 for a,b,c,d in coords)
