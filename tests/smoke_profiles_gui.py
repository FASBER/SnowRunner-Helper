"""Manual xvfb smoke: run `xvfb-run -a python tests/smoke_profiles_gui.py`."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import tkinter as tk
from tkinter import messagebox
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import Application
from core import SETTINGS_FILE, USER_DIR
from game_bridge import profile_key

with TemporaryDirectory() as temporary:
    saves = Path(temporary) / 'saves'
    saves.mkdir()
    a = saves / 'CompleteSave.cfg'
    b = saves / 'CompleteSave1.cfg'
    a.write_text(json.dumps({'CompleteSave': {'SslValue': {
        'persistentProfileData': {'money': 400, 'trucksInWarehouse': [{'type':'truck_demo'}]},
        'objectiveStates': {'task': 'not_known'}}}}), encoding='utf-8')
    b.write_text(json.dumps({'SslValue': {'persistentProfileData': {'money': 15}}}), encoding='utf-8')
    root = tk.Tk()
    app = Application(root)
    app.config['game_save_dir'] = str(saves)
    root.update()
    # A manual draft must be stored before switching to the game save.
    app.load = [('metal_beams', 4)]
    messagebox.askyesno = lambda *args, **kwargs: True
    assert app._switch_profile(profile_key(a))
    assert app.profiles.manifest('local') == [('metal_beams', 4)]
    app.load = [('wooden_planks', 2)]
    app.save_profile_draft()
    snap = app._sync_active_profile()
    assert snap['statistics']['money'] == 400
    assert snap['retained_trucks']['count'] == 1
    root.update()
    # Another slot must not inherit draft or snapshot.
    assert app._switch_profile(profile_key(b))
    assert app.load == []
    app.load = [('metal_beams', 1)]
    app.save_profile_draft()
    app._sync_active_profile()
    assert app._switch_profile(profile_key(a))
    assert app.load == [('wooden_planks', 2)]
    assert app.profiles.read(profile_key(b))['game_snapshot']['statistics']['money'] == 15
    assert app.profiles.read(profile_key(a))['game_snapshot']['statistics']['money'] == 400
    win = app.game_connection_dialog()
    root.update_idletasks();root.update()
    assert win.winfo_exists()
    assert app.root.winfo_exists()
    # No modal save needed as app is already synced.
    win.destroy()
    app.close_app()
    try:
        root.update()
    except tk.TclError:
        pass
print('GUI profile switching and per-slot autosave smoke OK')
