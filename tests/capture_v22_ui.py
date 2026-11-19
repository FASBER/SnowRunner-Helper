"""Smoke capture of actual interactive Expedition UI (not a mockup)."""
import os, sys, tempfile
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
output=Path(os.environ.get('SCREENSHOT_OUT','/mnt/data/new_ui_work/previews'))
output.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as home:
    os.environ['HOME']=home
    from app import Application
    root=tk.Tk()
    root.geometry('1319x747+25+25')
    app=Application(root)
    app.config['lang']='ru'
    app.config['animations']=False
    app.config['appearance']['animations']=False
    for page,name in [('recipes','01_Крафт'),('cargo','02_Грузы'),('calculator','03_Калькулятор'),('settings','04_Настройки'),('manual','05_Справочник')]:
        app.game.show(page)
        for i in range(3):
            root.update_idletasks();root.update()
        x,y=root.winfo_rootx(),root.winfo_rooty()
        w,h=root.winfo_width(),root.winfo_height()
        img=ImageGrab.grab(bbox=(x,y,x+w,y+h))
        img.save(output/(name+'.png'))
        print('CAPTURE',name,img.size, 'new_ui',app.game.new_ui)
    # Switchable old skin checks
    app.change('ui_design','classic')
    app.game.show('recipes')
    root.update_idletasks();root.update()
    assert not app.game.new_ui
    img=ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height()))
    img.save(output/'06_Классический_UI.png')
    print('CLASSIC SWITCH OK')
    root.destroy()
