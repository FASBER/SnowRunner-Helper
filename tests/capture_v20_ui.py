import os,sys,tempfile
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab,Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as t:
    os.environ['HOME']=t
    from app import Application
    root=tk.Tk()
    root.geometry('1319x747+40+40')
    app=Application(root)
    app.config['lang']='ru'
    app.page='recipes'
    app.config['appearance']['animations']=False
    app.render()
    root.geometry('1319x747+40+40')
    for i in range(3):
        root.update_idletasks();root.update()
    x=root.winfo_rootx(); y=root.winfo_rooty()
    w=root.winfo_width(); h=root.winfo_height()
    image=ImageGrab.grab(bbox=(x,y,x+w,y+h))
    out=Path('/mnt/data/SnowRunner_v20_Левая_панель_исправлена.png')
    image.save(out)
    crop=image.crop((0,0,320,h))
    crop.save('/mnt/data/SnowRunner_v20_Левая_панель_крупно.png')
    print('Screenshot',out,image.size,'crop',crop.size)
    root.destroy()
