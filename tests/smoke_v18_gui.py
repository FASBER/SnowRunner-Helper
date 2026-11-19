"""Run with xvfb-run -a python tests/smoke_v18_gui.py"""
import json
import os
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as tmp:
    os.environ['HOME'] = tmp
    from app import Application
    from game_bridge import profile_key
    folder = Path(tmp) / 'saves'
    folder.mkdir()
    file = folder / 'CompleteSave.cfg'
    data = {'CompleteSave': {'SslValue': {'persistentProfileData': {'money': 50},
            'visitedLevels': ['level_us_01_01'],
            'levelStates': {'warehouse_demo': {'cargoAvailable': {'metalBeams': 3}}}}}}
    file.write_text(json.dumps(data), encoding='utf-8')
    root = tk.Tk()
    app = Application(root)
    app.config['game_save_dir'] = str(folder)
    messagebox.askyesno = lambda *args, **kwargs: True
    root.update()
    assert app._switch_profile(profile_key(file))
    app._sync_active_profile()
    app.load = [('metal_beams', 4)]
    app.save_profile_draft()
    draft_win = app.drafts_dialog()
    root.update()
    assert draft_win.winfo_exists()
    app.profiles.create_named_draft(app.active_profile_key, 'Доставка', app.load)
    draft_win.destroy()
    depot_win = app.warehouse_preview_dialog()
    root.update()
    assert depot_win.winfo_exists()
    app.profiles.map_game_cargo(app.active_profile_key, 'metalBeams', 'metal_beams')
    depot_win.destroy()
    route_win = app.route_planner_dialog()
    root.update()
    assert route_win.winfo_exists()
    app.profiles.save_route(app.active_profile_key, 'Тестовая поездка',
                            ['level_us_01_01','warehouse_demo'], app.load)
    route_win.destroy()
    schema_win = app.save_structure_dialog()
    root.update()
    assert schema_win.winfo_exists()
    schema_win.destroy()
    app.close_app()
    root.update_idletasks()
print('GUI v18 named drafts and warehouse preview OK')
