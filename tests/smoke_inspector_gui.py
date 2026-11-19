"""Manual smoke, run under xvfb-run on Linux; Windows GUI is not tested here."""
from pathlib import Path
import sys, tempfile, zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import ImageGrab
from app import Application
from core import USER_DIR

with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp)
    with zipfile.ZipFile(folder / 'level_us_04_02.pak', 'w') as pak:
        pak.writestr('[scene]:data.stg', b'BINARY\0craftSettings\0' + b'\x00' * 128)
        pak.writestr('pak.load_list', b'demo')
    messages=[]
    ask_folder=filedialog.askdirectory
    ask_file=filedialog.askopenfilename
    info=messagebox.showinfo
    try:
        filedialog.askdirectory=lambda **kw: str(folder)
        filedialog.askopenfilename=lambda **kw: str(folder / 'level_us_04_02.pak')
        messagebox.showinfo=lambda *args, **kwargs: messages.append((args, kwargs))
        root=tk.Tk()
        root.geometry('1320x750+0+0')
        app=Application(root)
        app.config['theme']='game'
        app.config['lang']='ru'
        app.page='recipes'
        app.render()
        root.update()
        app.scan_game_folder()
        assert messages and 'Найдено STG: 1' in str(messages[-1])
        path=USER_DIR / 'SNOWRUNNER_SCAN_REPORT.txt'
        assert path.exists()
        assert 'level_us_04_02.pak' in path.read_text(encoding='utf-8')
        assert 'НЕ' in path.read_text(encoding='utf-8')
        app.import_game_data()
        assert len(messages)>=2 and 'декод' in str(messages[-1])
        app.config['lang']='en'
        app.render()
        root.update()
        print('Game-theme & English GUI / scan-button / PAK diagnostics OK')
        root.destroy()
    finally:
        filedialog.askdirectory=ask_folder
        filedialog.askopenfilename=ask_file
        messagebox.showinfo=info
