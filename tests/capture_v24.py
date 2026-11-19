"""Capture real interactive UI at reference resolution."""
import os, sys, tempfile
from pathlib import Path
import tkinter as tk
from PIL import ImageGrab
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
out=Path(os.getenv('SCREENSHOT_OUT','/mnt/data/snowrunner_v24/previews'))
out.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory() as home:
    os.environ['HOME']=home
    from app import Application
    root=tk.Tk()
    root.geometry('1536x864+3+3')
    app=Application(root)
    app.config['animations']=False
    app.config['appearance']['animations']=False
    app.config['sort']='name_asc'
    app.config['ui_design']='expedition'
    app.game.reference_ui=True
    root.geometry('1536x864+3+3')
    app.game._build_background()
    for page,name in [('cargo','01_Грузы_как_на_образце'),('recipes','02_Крафт'),('calculator','03_Калькулятор'),('manual','04_Справочник'),('settings','05_Настройки')]:
        app.game.show(page)
        for i in range(4):root.update_idletasks();root.update()
        x,y=root.winfo_rootx(),root.winfo_rooty()
        im=ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height()))
        im.save(out/(name+'.png'))
        print('capture',name, im.size, app.game.reference_ui)
    # Smoke interactions: search and list filter category
    app.game.show('cargo')
    app.game.search.set('кирпичи');root.update_idletasks();root.update()
    assert len(app.game.visible_cargo())>=1
    app.game.search.set('')
    app.game._reference_choose_category('wood')
    assert app.game.visible_cargo() and all(app.game._reference_category(c)=='wood' for c in app.game.visible_cargo())
    app.game._reference_choose_category('')
    app.game._reference_select('metal_beams')
    assert app.game.cargo_detail_open
    app.game._reference_close_detail()
    assert not app.game.cargo_detail_open
    root.destroy()
print('GUI SMOKE PASS')
