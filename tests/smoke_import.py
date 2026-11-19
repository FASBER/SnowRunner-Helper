import sys,json,tempfile,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from app import Application
from tkinter import filedialog,messagebox
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'test_zone.json'
    p.write_text(json.dumps({'craftSettings':[{'name':'metal_beams','craftCount':1,'cargoComponents':[{'name':'metal_rolls','count':2}]}]}))
    filedialog.askopenfilename=lambda **kw:str(p)
    messagebox.showinfo=lambda *args,**kwargs:None
    root=tk.Tk()
    app=Application(root)
    assert not app.official
    app.import_game_data()
    assert len(app.official)==1
    assert app.official[0]['inputs']=={'metal_rolls':2}
    assert app.official[0]['region']=='game_files'
    app.change('lang','en')
    app.page='recipes';app.render();root.update()
    assert len(app.official)==1
    print('Game import GUI / language / persistence OK')
    root.destroy()
