"""Real GUI captures of bottom-anchored Settings navigation for v21."""
import os, sys, tempfile
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab, Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
out=Path('/mnt/data')
with tempfile.TemporaryDirectory() as t:
    os.environ['HOME']=t
    from app import Application
    root=tk.Tk()
    root.geometry('1319x747+40+40')
    app=Application(root)
    app.config['lang']='ru'
    app.config['appearance']['animations']=False
    app.page='recipes'
    app.render()
    root.geometry('1319x747+40+40')
    for _ in range(4):
        root.update_idletasks();root.update()
    x=root.winfo_rootx();y=root.winfo_rooty()
    w=root.winfo_width();h=root.winfo_height()
    im=ImageGrab.grab(bbox=(x,y,x+w,y+h))
    im.save(out/'SnowRunner_v21_Настройки_внизу.png')
    im.crop((0,115,275,747)).save(out/'SnowRunner_v21_Боковая_панель_крупно.png')
    app.game.show('settings')
    for _ in range(3):
        root.update_idletasks();root.update()
    image=ImageGrab.grab(bbox=(x,y,x+w,y+h))
    image.save(out/'SnowRunner_v21_Настройки_активны.png')
    print('Captured:',im.size,image.size)
    root.destroy()
