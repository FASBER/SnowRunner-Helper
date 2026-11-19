"""Headless UI smoke test: run with xvfb-run on Linux."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from PIL import ImageGrab
from app import Application

root=tk.Tk()
app=Application(root)
root.update_idletasks();root.update()
assert root.winfo_exists()
app.page='recipes'
app.render()
root.update_idletasks();root.update()
ImageGrab.grab().save(str(Path(__file__).resolve().parents[1]/'PREVIEW_RECIPES.png'))
editor=app.recipe_editor()
root.update_idletasks();root.update()
assert len(editor.materials)==2
assert editor.materials[0]['direction']=='input'
assert editor.materials[1]['direction']=='output'
editor.entries['name'].set('Тестовый крафт')
editor.add_material('input','cement',2)
editor.update_preview()
assert 'Цемент' in editor.preview['text']
editor.geometry('870x850+150+40')
root.update_idletasks();root.update()
ImageGrab.grab().save(str(Path(__file__).resolve().parents[1]/'PREVIEW_EDITOR.png'))
editor.save()
root.update_idletasks();root.update()
assert len(app.custom)==1
assert app.custom[0]['inputs']=={'metal_rolls':1,'cement':2}
assert app.custom[0]['outputs']=={'metal_beams':1}
assert app.custom[0]['verified']=='user_created'
print('UI smoke successful, saved recipe')
root.destroy()
