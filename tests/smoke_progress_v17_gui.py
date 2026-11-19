"""Run with xvfb-run -a python tests/smoke_progress_v17_gui.py."""
import json
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application
from game_bridge import profile_key

with tempfile.TemporaryDirectory() as temp:
    folder = Path(temp)
    save = folder / 'CompleteSave.cfg'
    save.write_text(json.dumps({'CompleteSave': {'SslValue': {
        'persistentProfileData': {'money': 1200, 'experience': 50},
        'finishedObjs': ['TASK_ONE', 'TASK_TWO'],
        'visitedLevels': ['level_us_01_01'],
        'levelGarageStatuses': {'level_us_01_01': 2},
        'levelStates': {'warehouse_us_01_02_1': {'cargoAvailable': {'mediumPlanks': 2}}},
    }}}),encoding='utf-8')
    root = tk.Tk()
    app = Application(root)
    app.config['game_save_dir'] = str(folder)
    messagebox.askyesno = lambda *args, **kwargs: True
    root.update()
    assert app._switch_profile(profile_key(save))
    snapshot = app._sync_active_profile()
    assert snapshot['objectives']['completed'] == 2
    assert snapshot['visited_levels']['count'] == 1
    assert snapshot['garages']['open_count'] == 1
    text = app._snapshot_details_text(snapshot)
    assert 'TASK_ONE' in text and 'warehouse_us_01_02_1' in text
    win = app.view_saved_progress()
    root.update()
    assert win.winfo_exists()
    assert len([w for w in win.winfo_children() if isinstance(w, tk.Frame)]) >= 1
    win.destroy()
    connection = app.game_connection_dialog()
    root.update()
    assert connection.winfo_exists()
    connection.destroy()
    app.close_app()
print('GUI progress explorer v17 smoke OK')
